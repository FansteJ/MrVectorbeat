import math

from mrvectorbeat import tekst

K1 = 1.5    # privremeno, vrednosti sa vezbi; biraju se merenjem (MRR za vise k1 i b)
B = 0.75


class BM25Model:
    """Sve sto ne zavisi od upita: duzina svake pesme, prosecna duzina i idf termina.
    Broj pojavljivanja termina u pesmi se cita iz pozicionog indeksa (len(pozicije))."""

    def __init__(self, indeks, k1=K1, b=B):
        self.k1 = k1
        self.b = b
        self.broj_pesama = len(indeks.track_ids)

        # duzina pesme = broj termina posle obrade = zbir tf po svim terminima pesme
        self.duzina = [0] * self.broj_pesama
        self.idf = {}
        for termin, lista in indeks.postings.items():
            df = len(lista)
            # +1 unutar logaritma: idf nikad nije negativan, i kad je rec u vise od pola pesama
            self.idf[termin] = math.log(1 + (self.broj_pesama - df + 0.5) / (df + 0.5))
            for id_pesme, pozicije in lista:
                self.duzina[id_pesme] += len(pozicije)
        self.prosecna_duzina = sum(self.duzina) / self.broj_pesama

    def bm25(self, indeks, upit, k1=None, b=None):
        """BM25 ocena pesama koje sadrze bar jednu rec upita.
        Kao na vezbama, ponovljena rec upita se broji onoliko puta koliko se javlja.
        Vraca [(id pesme, ocena), ...] od najvece ka najmanjoj."""
        k1 = self.k1 if k1 is None else k1
        b = self.b if b is None else b

        broj_u_upitu = {}
        for termin in tekst.obradi(upit):
            broj_u_upitu[termin] = broj_u_upitu.get(termin, 0) + 1

        ocene = {}
        for termin, puta in broj_u_upitu.items():
            idf = self.idf.get(termin)
            if idf is None:         # reci nema ni u jednoj pesmi
                continue
            for id_pesme, pozicije in indeks.postings_za(termin):
                tf = len(pozicije)
                normalizacija = 1 - b + b * self.duzina[id_pesme] / self.prosecna_duzina
                doprinos = idf * tf * (k1 + 1) / (tf + k1 * normalizacija)
                ocene[id_pesme] = ocene.get(id_pesme, 0.0) + puta * doprinos
        return sorted(ocene.items(), key=lambda par: par[1], reverse=True)
