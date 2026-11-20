import gzip
import hashlib
import heapq
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

WIKI = "https://en.wikipedia.org/wiki/"
USER_AGENT = "MrVectorbeat-crawler/1.0 (studentski projekat)"
PAUZA = 1.0                     # najmanje 1 s izmedju dva zahteva (postavka)

# imenski prostori Vikipedije koji nisu clanci (Category:, File:, Talk:...)
NE_CLANCI = {"special", "file", "image", "media", "category", "help", "talk", "template",
             "wikipedia", "portal", "user", "draft", "module", "mediawiki", "timedtext",
             "book", "education program", "gadget", "gadget definition", "topic"}

# delovi stranice koji nisu tekst clanka: navigacione kutije, fusnote, linkovi za izmenu...
NIJE_TEKST = [".navbox", ".vertical-navbox", ".reflist", ".references", ".reference", "cite",
              ".citation",
              ".mw-editsection", ".hatnote", ".metadata", ".sistersitebox", ".ambox",
              ".authority-control", ".noprint", "style", "script"]


def normalizuj(url, osnova=WIKI):
    """Adresa clanka u jednom obliku: https://en.wikipedia.org/wiki/Naslov_clanka.
    Vraca None ako link ne vodi na clanak engleske Vikipedije."""
    delovi = urlsplit(urljoin(osnova, url))
    if delovi.netloc != "en.wikipedia.org" or not delovi.path.startswith("/wiki/") or delovi.query:
        return None
    # fragment (#Istorija) se odbacuje: ista stranica
    naslov = unquote(delovi.path[len("/wiki/"):]).replace(" ", "_")
    # Ime_(identifier) su linkovi iz sablona za ISBN, IMDb... a ne iz teksta
    if not naslov or naslov == "Main_Page" or naslov.endswith("_(identifier)"):
        return None
    if ":" in naslov:
        prostor = naslov.split(":", 1)[0].replace("_", " ").lower()
        if prostor.removesuffix(" talk") in NE_CLANCI:
            return None
    # prvo slovo naslova na Vikipediji nije osetljivo na velicinu
    return WIKI + naslov[0].upper() + naslov[1:]


def obradi_stranicu(html):
    """Iz HTML-a clanka: kanonska adresa, naslov, tekst clanka i linkovi ka drugim
    clancima (samo iz teksta clanka, bez ponavljanja, redom kojim se javljaju)."""
    soup = BeautifulSoup(html, "html.parser")
    kanonski = soup.find("link", rel="canonical")
    kanonski = normalizuj(kanonski["href"]) if kanonski else None
    naslov = soup.find("h1", id="firstHeading")
    naslov = " ".join(naslov.get_text().split()) if naslov else ""

    sadrzaj = soup.select_one("#mw-content-text .mw-parser-output")
    if sadrzaj is None:
        return {"kanonski": kanonski, "naslov": naslov, "tekst": "", "linkovi": []}
    for deo in sadrzaj.select(", ".join(NIJE_TEKST)):
        deo.decompose()

    linkovi = []
    for a in sadrzaj.find_all("a", href=True):
        link = normalizuj(a["href"])
        if link and link != kanonski and link not in linkovi:
            linkovi.append(link)
    tekst = " ".join(sadrzaj.get_text(" ").split())
    return {"kanonski": kanonski, "naslov": naslov, "tekst": tekst, "linkovi": linkovi}


class Preuzimac:
    """Pristojno preuzimanje sa Vikipedije: robots.txt, jedan po jedan zahtev sa pauzom,
    sopstveni User-Agent. Svaki odgovor se cuva na disku, pa se isti zahtev ne salje dvaput."""

    def __init__(self, folder, user_agent=USER_AGENT, pauza=PAUZA):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.sesija = requests.Session()
        self.sesija.headers["User-Agent"] = user_agent
        self.user_agent = user_agent
        self.pauza = pauza
        self.poslednji_zahtev = 0.0
        self.robots = None
        self.poslato_zahteva = 0

    def _putanja(self, url):
        return self.folder / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json.gz")

    def _sacekaj(self):
        cekaj = self.pauza - (time.monotonic() - self.poslednji_zahtev)
        if cekaj > 0:
            time.sleep(cekaj)
        self.poslednji_zahtev = time.monotonic()

    def _get(self, url):
        for pokusaj in range(3):
            self._sacekaj()
            self.poslato_zahteva += 1
            odgovor = self.sesija.get(url, timeout=30)
            # 429: server trazi da usporimo; 5xx: privremena greska
            if odgovor.status_code == 429 or odgovor.status_code >= 500:
                time.sleep(int(odgovor.headers.get("Retry-After", 10 * (pokusaj + 1))))
                continue
            return odgovor
        return odgovor

    def _ucitaj_robots(self):
        self.robots = RobotFileParser()
        self.robots.parse(self._get("https://en.wikipedia.org/robots.txt").text.splitlines())
        self.pauza = max(self.pauza, self.robots.crawl_delay(self.user_agent) or 0)

    def u_kesu(self, url):
        return self._putanja(url).exists()

    def iz_kesa(self, url):
        """Vec preuzeta stranica ili None, bez slanja zahteva."""
        putanja = self._putanja(url)
        if not putanja.exists():
            return None
        with gzip.open(putanja, "rt", encoding="utf-8") as f:
            return json.load(f)

    def preuzmi(self, url):
        """Obradjena stranica (recnik iz obradi_stranicu, plus url i status) ili None
        ako robots.txt zabranjuje adresu. Iz kesa ako je vec preuzeta."""
        stranica = self.iz_kesa(url)
        if stranica is not None:
            return stranica

        if self.robots is None:
            self._ucitaj_robots()
        if not self.robots.can_fetch(self.user_agent, url):
            return None

        putanja = self._putanja(url)
        odgovor = self._get(url)
        if odgovor.status_code == 200:
            stranica = obradi_stranicu(odgovor.text)
        else:
            stranica = {"kanonski": None, "naslov": "", "tekst": "", "linkovi": []}
        stranica["url"] = url
        stranica["status"] = odgovor.status_code
        # 4xx se cuva (stranica ne postoji), 429 i 5xx ne: to su privremene greske
        if odgovor.status_code < 500 and odgovor.status_code != 429:
            with gzip.open(putanja, "wt", encoding="utf-8") as f:
                json.dump(stranica, f, ensure_ascii=False)
        return stranica


# --- Muzika i fokusirani obilazak ---

MUZICKE_RECI = {
    "music", "musical", "musician", "musicians", "song", "songs", "album", "albums",
    "single", "singles", "band", "bands", "singer", "singers", "rapper", "rappers", "rap",
    "hip", "hop", "rock", "pop", "jazz", "genre", "genres", "guitar", "guitarist", "drummer",
    "bassist", "vocals", "vocalist", "lyrics", "record", "records", "recording", "recorded",
    "label", "labels", "chart", "charts", "billboard", "tour", "concert", "concerts", "studio",
    "dj", "ep", "remix", "producer", "composer", "orchestra", "grammy", "duo", "soul", "punk",
    "metal", "indie", "edm", "techno", "house", "folk", "country", "blues", "reggae",
    "discography", "mixtape", "track", "tracks", "hit", "hits", "released", "debut",
}
PRAG_MUZIKE = 2.0               # muzickih reci na 100 reci teksta
VISEZNACNA = ("may refer to", "most commonly refers to")
SUFIKSI = ["band", "singer", "rapper", "musician", "DJ"]


def ocena_muzike(tekst):
    """Koliko reci od 100 u tekstu su muzicke (odluka na osnovu sadrzaja stranice)."""
    reci = re.findall(r"[a-z]+", tekst.lower())
    if not reci:
        return 0.0
    return 100 * sum(1 for r in reci if r in MUZICKE_RECI) / len(reci)


def je_muzicka(stranica):
    return ocena_muzike(stranica["tekst"]) >= PRAG_MUZIKE


def je_o_delu(stranica):
    """Clanak o pesmi ili albumu, npr. "Middle_of_the_Night_(... song)": ime izvodjaca bez
    svog clanka ponekad preusmerava na njegovu pesmu."""
    naslov = (stranica["kanonski"] or stranica["url"]).lower()
    zagrada = naslov.rsplit("_(", 1)[1] if "_(" in naslov else ""
    return any(rec in zagrada for rec in ("song", "album", "ep)", "single", "mixtape", "soundtrack"))


def je_viseznacna(stranica):
    pocetak = stranica["tekst"][:300].lower()
    return any(fraza in pocetak for fraza in VISEZNACNA)


def _muzicki_kandidati(viseznacna, osnova):
    """Linkovi sa stranice visezacnosti oblika "Ime_(...)" gde je u zagradi muzicka rec,
    npr. Nirvana_(band), Seeb_(DJs)."""
    kandidati = []
    for link in viseznacna["linkovi"]:
        if link.startswith(osnova + "_(") and link.endswith(")"):
            zagrada = link[len(osnova) + 2:-1].lower().replace("_", " ")
            if any(rec in MUZICKE_RECI or rec in ("djs", "group", "producer")
                   for rec in zagrada.split()):
                kandidati.append(link)
    return kandidati


def broj_pomenutih_pesama(stranica, pesme):
    tekst = stranica["tekst"].lower()
    return sum(1 for pesma in pesme if len(pesma) >= 4 and pesma in tekst)


def nadji_clanak_izvodjaca(preuzimac, ime, pesme=()):
    """Clanak o izvodjacu: prvo "Ime"; ako je to stranica visezacnosti, muzicki linkovi
    sa nje; ako je clanak o necem drugom (Europe, Logic), Ime_(band), Ime_(rapper)...
    Od muzickih kandidata bira se onaj koji pominje najvise pesama izvodjaca iz kataloga
    (`pesme`, mala slova), npr. The Game (rapper), a ne The Game (band).
    Vraca stranicu ili None."""
    osnova = normalizuj(quote(ime.replace(" ", "_")))
    if osnova is None:
        return None
    stranica = preuzimac.preuzmi(osnova)
    if stranica is None or stranica["status"] != 200:
        return None
    if je_viseznacna(stranica):
        kandidati = _muzicki_kandidati(stranica, osnova)
    elif je_muzicka(stranica) and not je_o_delu(stranica):
        return stranica
    else:
        kandidati = [f"{osnova}_({sufiks})" for sufiks in SUFIKSI]
    najbolja, najvise = None, -1
    for kandidat in kandidati:
        stranica = preuzimac.preuzmi(kandidat)
        if stranica and stranica["status"] == 200 and not je_viseznacna(stranica)                 and je_muzicka(stranica) and not je_o_delu(stranica):
            pomenutih = broj_pomenutih_pesama(stranica, pesme)
            if pomenutih > 0:
                return stranica
            if pomenutih > najvise:
                najbolja, najvise = stranica, pomenutih
    return najbolja


def obidji(preuzimac, izvodjaci, dodatnih_stranica, ispis=print):
    """Fokusirani obilazak. Prvo clanci o izvodjacima (redom kojim su dati), pa najvise
    `dodatnih_stranica` drugih stranica iz prioritetnog reda: prioritet linka je zbir
    ocena muzike muzickih stranica koje na njega pokazuju; linkovi sa nemuzickih stranica
    se ne prate. izvodjaci: {ime: pesme izvodjaca (mala slova)}.
    Vraca {"izvodjaci": {ime: adresa clanka}, "preuzete": [adrese]}."""
    preuzete = []               # svaka preuzeta adresa (200), redom
    vec_preuzete = set()
    kanonske = set()
    prioritet = {}              # adresa -> zbir ocena stranica koje na nju pokazuju
    red = []                    # (-prioritet, adresa); zastareli unosi se preskacu

    def zapamti(stranica):
        if stranica["url"] not in vec_preuzete:
            vec_preuzete.add(stranica["url"])
            preuzete.append(stranica["url"])
        kanonske.add(stranica["kanonski"] or stranica["url"])
        ocena = ocena_muzike(stranica["tekst"])
        if ocena < PRAG_MUZIKE:
            return
        for link in stranica["linkovi"]:
            if link not in kanonske:
                prioritet[link] = prioritet.get(link, 0.0) + ocena
                heapq.heappush(red, (-prioritet[link], link))
        # posle vise povecanja istog prioriteta red ima mnogo zastarelih unosa
        if len(red) > 3 * len(prioritet):
            red[:] = [(-p, a) for a, p in prioritet.items() if a not in kanonske]
            heapq.heapify(red)

    clanci = {}
    for i, ime in enumerate(izvodjaci, start=1):
        pre = preuzimac.poslato_zahteva
        stranica = nadji_clanak_izvodjaca(preuzimac, ime, izvodjaci[ime])
        if stranica is not None:
            clanci[ime] = stranica["kanonski"] or stranica["url"]
            zapamti(stranica)
        if i % 100 == 0 or preuzimac.poslato_zahteva > pre and i % 25 == 0:
            ispis(f"izvodjaci: {i}/{len(izvodjaci)}, nadjeno {len(clanci)}, "
                  f"zahteva {preuzimac.poslato_zahteva}")

    dodato = 0
    while red and dodato < dodatnih_stranica:
        minus_prioritet, adresa = heapq.heappop(red)
        if adresa in kanonske or -minus_prioritet < prioritet[adresa]:
            continue
        kanonske.add(adresa)
        stranica = preuzimac.preuzmi(adresa)
        if stranica is None or stranica["status"] != 200 or stranica["kanonski"] in kanonske                 and stranica["kanonski"] != adresa:
            continue
        zapamti(stranica)
        dodato += 1
        if dodato % 100 == 0:
            ispis(f"dodatne stranice: {dodato}/{dodatnih_stranica}, zahteva {preuzimac.poslato_zahteva}")
    return {"izvodjaci": clanci, "preuzete": preuzete}
