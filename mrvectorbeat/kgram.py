K = 3


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
        self.poslednja = {}     # statistika poslednje pretrage, za prikaz

    def dodaj(self, kljuc, prikaz, tip, ucestalost, popularnost):
        id_imena = len(self.imena)
        self.imena.append((kljuc, prikaz, tip, ucestalost, popularnost))
        for g in kgrami(kljuc):
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
