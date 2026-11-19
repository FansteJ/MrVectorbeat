import math


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
