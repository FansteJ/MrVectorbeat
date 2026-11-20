import math
from collections import defaultdict
from operator import itemgetter


class SlicnostIzvodjaca:
    """Slicnost izvodjaca po stranicama koje pokazuju na njih, kao TF-IDF kosinus:
    izvodjac je "dokument", a stranice koje pokazuju na njega su njegovi "termini".
    Tezina stranice je idf = log(N / broj izvodjaca na koje pokazuje): stranica koja
    pokazuje na mnogo izvodjaca (spisak dobitnika nagrade) govori manje od malog zanra."""

    def __init__(self, g):
        izvodjacki = set(g.izvodjaci_cvora)
        broj_izvodjaca = len(izvodjacki)
        # za svaku stranicu: izvodjaci iz kataloga na koje pokazuje
        self.izvodjaci_stranice = [[c for c in susedi if c in izvodjacki] for susedi in g.izlazni]
        self.tezina = [math.log(broj_izvodjaca / len(izv)) if izv else 0.0
                       for izv in self.izvodjaci_stranice]
        # za svakog izvodjaca: stranice koje pokazuju na njega, i duzina njegovog vektora
        self.stranice_izvodjaca = defaultdict(list)
        for stranica, izv in enumerate(self.izvodjaci_stranice):
            for cvor in izv:
                self.stranice_izvodjaca[cvor].append(stranica)
        self.norma = {cvor: math.sqrt(sum(self.tezina[s] ** 2 for s in stranice))
                      for cvor, stranice in self.stranice_izvodjaca.items()}

    def slicni(self, cvor, k=10, broj_stranica=5):
        """Najslicniji izvodjaci iz kataloga: [(cvor, slicnost, zajednicke stranice), ...].
        Zajednicke stranice su poredjane od najvece tezine (najvise govore o slicnosti)."""
        if not self.norma.get(cvor):
            return []
        # skalarni proizvod samo preko stranica koje pokazuju na izabranog izvodjaca
        proizvod = defaultdict(float)
        for stranica in self.stranice_izvodjaca[cvor]:
            w = self.tezina[stranica]
            for drugi in self.izvodjaci_stranice[stranica]:
                if drugi != cvor:
                    proizvod[drugi] += w * w
        slicnosti = [(drugi, p / (self.norma[cvor] * self.norma[drugi]))
                     for drugi, p in proizvod.items() if p > 0]
        slicnosti.sort(key=itemgetter(1), reverse=True)

        moje = set(self.stranice_izvodjaca[cvor])
        rezultat = []
        for drugi, slicnost in slicnosti[:k]:
            zajednicke = [s for s in self.stranice_izvodjaca[drugi] if s in moje]
            zajednicke.sort(key=lambda s: self.tezina[s], reverse=True)
            rezultat.append((drugi, slicnost, zajednicke[:broj_stranica]))
        return rezultat
