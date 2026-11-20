from mrvectorbeat import crawler


class Graf:
    """Usmereni graf preuzetih stranica kao lista susedstva. Cvor je broj 0..n-1;
    adrese[i] je kanonska adresa stranice, izlazni[i] lista cvorova na koje pokazuje.
    izvodjaci_cvora[i]: imena izvodjaca iz kataloga ciji je to clanak (samo za te stranice)."""

    def __init__(self, adrese, naslovi, muzicka, izlazni, cvor_izvodjaca):
        self.adrese = adrese
        self.naslovi = naslovi
        self.muzicka = muzicka
        self.izlazni = izlazni
        self.cvor_izvodjaca = cvor_izvodjaca        # ime izvodjaca -> cvor
        self.izvodjaci_cvora = {}
        for ime, cvor in cvor_izvodjaca.items():
            self.izvodjaci_cvora.setdefault(cvor, []).append(ime)

    @property
    def broj_cvorova(self):
        return len(self.adrese)

    @property
    def broj_grana(self):
        return sum(len(susedi) for susedi in self.izlazni)

    def ulazni(self):
        """Za svaki cvor lista cvorova koji pokazuju na njega."""
        ulazni = [[] for _ in self.adrese]
        for cvor, susedi in enumerate(self.izlazni):
            for sused in susedi:
                ulazni[sused].append(cvor)
        return ulazni


def napravi_graf(preuzimac, obilazak):
    """Graf od rezultata obilaska (crawler.obidji), cita stranice iz kesa.
    Linkovi ka preusmerenjima se prevode na kanonsku adresu; ostaju samo linkovi ka
    preuzetim stranicama, bez ponavljanja i bez linkova na samu sebe."""
    stranice = {}               # kanonska adresa -> stranica
    kanonska = {}               # bilo koja preuzeta adresa -> kanonska
    for url in obilazak["preuzete"]:
        stranica = preuzimac.iz_kesa(url)
        adresa = stranica["kanonski"] or url
        kanonska[url] = adresa
        kanonska[adresa] = adresa
        stranice.setdefault(adresa, stranica)

    adrese = list(stranice)
    broj = {adresa: i for i, adresa in enumerate(adrese)}
    izlazni = []
    for i, adresa in enumerate(adrese):
        susedi = set()
        for link in stranice[adresa]["linkovi"]:
            cilj = broj.get(kanonska.get(link, link))
            if cilj is not None and cilj != i:
                susedi.add(cilj)
        izlazni.append(sorted(susedi))

    naslovi = [stranice[a]["naslov"] or a.removeprefix(crawler.WIKI).replace("_", " ") for a in adrese]
    muzicka = [crawler.je_muzicka(stranice[a]) for a in adrese]
    cvor_izvodjaca = {ime: broj[kanonska[url]] for ime, url in obilazak["izvodjaci"].items()}
    return Graf(adrese, naslovi, muzicka, izlazni, cvor_izvodjaca)
