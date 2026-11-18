K = 3
PRAG = 0.3      # izabran merenjem na imenima sa greskom i na nasumicnim unosima


def kgrami(tekst):
    """Skup k-grama reci sa granicnicima: "queen" -> {$qu, que, uee, een, en$}."""
    tekst = "$" + tekst + "$"
    return {tekst[i:i + K] for i in range(len(tekst) - K + 1)}


def odgovara(ime, obrazac):
    """Pravo poredjenje imena sa obrascem koji sadrzi zvezdice."""
    delovi = obrazac.split("*")
    prvi, poslednji = delovi[0], delovi[-1]
    if not ime.startswith(prvi):
        return False
    pozicija = len(prvi)
    # srednji delovi moraju da se jave redom, jedan iza drugog
    for deo in delovi[1:-1]:
        nadjeno = ime.find(deo, pozicija)
        if nadjeno == -1:
            return False
        pozicija = nadjeno + len(deo)
    # poslednji deo mora biti na kraju i ne sme da se preklapa sa vec nadjenim
    return ime.endswith(poslednji) and len(ime) - len(poslednji) >= pozicija


class KgramIndeks:
    def __init__(self):
        self.imena = []         # id -> (kljuc, prikaz, tip, ucestalost, popularnost)
        self.postings = {}      # k-gram -> skup id-jeva imena
        self.broj_kgrama = []   # id -> koliko razlicitih k-grama ime ima (|B| u Zakardu)
        self.poslednja = {}     # statistika poslednje pretrage, za prikaz

    def dodaj(self, kljuc, prikaz, tip, ucestalost, popularnost):
        id_imena = len(self.imena)
        self.imena.append((kljuc, prikaz, tip, ucestalost, popularnost))
        grami = kgrami(kljuc)
        self.broj_kgrama.append(len(grami))
        for g in grami:
            self.postings.setdefault(g, set()).add(id_imena)

    def kgrami_obrasca(self, obrazac):
        """K-grami iz delova obrasca izmedju zvezdica (zvezdica ne ulazi u k-gram)."""
        okviren = obrazac
        if not obrazac.startswith("*"):
            okviren = "$" + okviren
        if not obrazac.endswith("*"):
            okviren = okviren + "$"
        rezultat = set()
        for deo in okviren.split("*"):
            for i in range(len(deo) - K + 1):
                rezultat.add(deo[i:i + K])
        return rezultat

    def pretrazi(self, obrazac, k=10):
        obrazac = obrazac.lower()
        grami = self.kgrami_obrasca(obrazac)
        if not grami:
            raise ValueError("Obrazac je prekratak: izmedju zvezdica mora biti bar "
                             f"{K - 1} slova uz granicu imena ili {K} slova u sredini.")

        # presek krece od najkrace liste, da medjurezultat ostane sto manji
        liste = sorted((self.postings.get(g, set()) for g in grami), key=len)
        kandidati = liste[0]
        for lista in liste[1:]:
            if not kandidati:
                break
            kandidati = kandidati & lista

        prosli = [self.imena[i] for i in kandidati if odgovara(self.imena[i][0], obrazac)]
        prosli.sort(key=lambda x: (x[3], x[4]), reverse=True)

        self.poslednja = {"kgrami": sorted(grami), "duzine_lista": [len(l) for l in liste],
                          "kandidata": len(kandidati), "proslo_proveru": len(prosli)}
        return [(prikaz, tip, ucestalost) for _, prikaz, tip, ucestalost, _ in prosli[:k]]

    def ispravka(self, unos, prag=PRAG):
        """Najblize ime po Zakardovom koeficijentu, ili None ako je ispod praga.
        Vraca (prikaz, tip, zakard)."""
        a = kgrami(unos.lower())

        # za svakog kandidata brojimo koliko k-grama deli sa unosom: to je |A ∩ B|
        zajednicki = {}
        for g in a:
            for id_imena in self.postings.get(g, ()):
                zajednicki[id_imena] = zajednicki.get(id_imena, 0) + 1

        najbolji = None
        najbolji_kljuc = None
        for id_imena, presek in zajednicki.items():
            unija = len(a) + self.broj_kgrama[id_imena] - presek
            zakard = presek / unija
            _, prikaz, tip, ucestalost, popularnost = self.imena[id_imena]
            # kod iste slicnosti prednost ima cesce ime
            kljuc_poredjenja = (zakard, ucestalost, popularnost)
            if najbolji_kljuc is None or kljuc_poredjenja > najbolji_kljuc:
                najbolji_kljuc = kljuc_poredjenja
                najbolji = (prikaz, tip, zakard)

        self.poslednja = {"kgrami": sorted(a), "kandidata": len(zajednicki)}
        if najbolji is None or najbolji[2] < prag:
            return None
        return najbolji
