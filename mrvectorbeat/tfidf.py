import math

from mrvectorbeat import tekst


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
