import gzip
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
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
NIJE_TEKST = [".navbox", ".vertical-navbox", ".reflist", ".references", ".reference",
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
    if not naslov or naslov == "Main_Page":
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
    naslov = naslov.get_text(strip=True) if naslov else ""

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

    def preuzmi(self, url):
        """Obradjena stranica (recnik iz obradi_stranicu, plus url i status) ili None
        ako robots.txt zabranjuje adresu. Iz kesa ako je vec preuzeta."""
        putanja = self._putanja(url)
        if putanja.exists():
            with gzip.open(putanja, "rt", encoding="utf-8") as f:
                return json.load(f)

        if self.robots is None:
            self._ucitaj_robots()
        if not self.robots.can_fetch(self.user_agent, url):
            return None

        odgovor = self._get(url)
        if odgovor.status_code == 200:
            stranica = obradi_stranicu(odgovor.text)
        else:
            stranica = {"kanonski": None, "naslov": "", "tekst": "", "linkovi": []}
        stranica["url"] = url
        stranica["status"] = odgovor.status_code
        if odgovor.status_code == 200 or odgovor.status_code == 404:
            with gzip.open(putanja, "wt", encoding="utf-8") as f:
                json.dump(stranica, f, ensure_ascii=False)
        return stranica
