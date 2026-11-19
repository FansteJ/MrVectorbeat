import math

from mrvectorbeat import tekst


def najbolja_iz_porodice(rangirano, porodica_za):
    """Iz liste [(kljuc, ocena), ...] sortirane od najbolje zadrzava samo prvu,
    tj. najbolje ocenjenu verziju svake porodice. porodica_za(kljuc) -> porodica."""
    vidjene = set()
    rezultat = []
    for kljuc, ocena in rangirano:
        porodica = porodica_za(kljuc)
        if porodica not in vidjene:
            vidjene.add(porodica)
            rezultat.append((kljuc, ocena))
    return rezultat


def tf_tezina(broj):
    """l: broj pojavljivanja prigusen logaritmom."""
    return 1 + math.log10(broj)


class TfIdfModel:
    """Sve sto ne zavisi od upita: idf termina i duzine vektora pesama.
    Broj pojavljivanja termina u pesmi se cita iz pozicionog indeksa (len(pozicije))."""

    def __init__(self, indeks):
        self.broj_pesama = len(indeks.track_ids)
        self.idf = {}                       # termin -> log10(N / df)

        kvadrati_lnc = [0.0] * self.broj_pesama
        kvadrati_ltc = [0.0] * self.broj_pesama
        for termin, lista in indeks.postings.items():
            idf = math.log10(self.broj_pesama / len(lista))
            self.idf[termin] = idf
            for id_pesme, pozicije in lista:
                w = tf_tezina(len(pozicije))
                kvadrati_lnc[id_pesme] += w * w
                kvadrati_ltc[id_pesme] += (w * idf) ** 2

        # norma vektora pesme kao dokumenta (lnc) i kao upita (ltc, za slicne pesme)
        self.duzina_lnc = [math.sqrt(x) for x in kvadrati_lnc]
        self.duzina_ltc = [math.sqrt(x) for x in kvadrati_ltc]

    def tfidf(self, indeks, upit):
        """TF-IDF ocena: zbir (1 + log10 tf) * idf po recima upita koje su u pesmi.
        Ocenjuju se samo pesme iz postings lista reci upita.
        Vraca [(id pesme, ocena), ...] od najvece ocene ka najmanjoj."""
        # svaka rec upita se broji jednom, i kad se ponovi
        termini = dict.fromkeys(tekst.obradi(upit))
        ocene = {}
        for termin in termini:
            idf = self.idf.get(termin)
            if idf is None:         # reci nema ni u jednoj pesmi
                continue
            for id_pesme, pozicije in indeks.postings_za(termin):
                ocene[id_pesme] = ocene.get(id_pesme, 0.0) + tf_tezina(len(pozicije)) * idf
        return sorted(ocene.items(), key=lambda par: par[1], reverse=True)

    def vektor_upita(self, termini):
        """ltc tezine upita i norma vektora. Termini kojih nema u indeksu se preskacu."""
        brojevi = {}
        for termin in termini:
            brojevi[termin] = brojevi.get(termin, 0) + 1
        tezine = {}
        for termin, broj in brojevi.items():
            if termin in self.idf:
                tezine[termin] = tf_tezina(broj) * self.idf[termin]
        norma = math.sqrt(sum(w * w for w in tezine.values()))
        return tezine, norma

    def kosinus(self, indeks, upit):
        """Kosinusna slicnost lnc.ltc izmedju upita i pesama koje sadrze bar jednu rec upita.
        Vraca [(id pesme, slicnost), ...] od najvece ka najmanjoj."""
        tezine, norma = self.vektor_upita(tekst.obradi(upit))
        return self._kosinus_za_vektor(indeks, tezine, norma)

    def _kosinus_za_vektor(self, indeks, tezine_upita, norma_upita):
        if norma_upita == 0:
            return []
        # skalarni proizvod samo po zajednickim terminima, sabran termin po termin
        proizvodi = {}
        for termin, w_upit in tezine_upita.items():
            for id_pesme, pozicije in indeks.postings_za(termin):
                w_pesma = tf_tezina(len(pozicije))     # lnc: bez idf
                proizvodi[id_pesme] = proizvodi.get(id_pesme, 0.0) + w_upit * w_pesma
        slicnosti = [(id_pesme, proizvod / (norma_upita * self.duzina_lnc[id_pesme]))
                     for id_pesme, proizvod in proizvodi.items()]
        return sorted(slicnosti, key=lambda par: par[1], reverse=True)
