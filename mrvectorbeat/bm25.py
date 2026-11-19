import math
from collections import defaultdict
from operator import itemgetter

from mrvectorbeat import tekst

# podrazumevano kao na vezbama; pripremi.py ih zameni vrednostima izabranim merenjem
K1 = 1.5
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
        # |d| / avgdl za svaku pesmu, da se pri upitu ne deli iznova
        self.relativna_duzina = [d / self.prosecna_duzina for d in self.duzina]

    def bm25(self, indeks, upit, k1=None, b=None):
        """BM25 ocena pesama koje sadrze bar jednu rec upita.
        Kao na vezbama, ponovljena rec upita se broji onoliko puta koliko se javlja.
        Vraca [(id pesme, ocena), ...] od najvece ka najmanjoj."""
        k1 = self.k1 if k1 is None else k1
        b = self.b if b is None else b

        broj_u_upitu = {}
        for termin in tekst.obradi(upit):
            broj_u_upitu[termin] = broj_u_upitu.get(termin, 0) + 1

        # k1 * (1 - b + b * |d|/avgdl) = k1 * (1 - b) + k1 * b * |d|/avgdl:
        # prvi deo ne zavisi od pesme, pa se racuna jednom, pre petlje
        stalni_deo = k1 * (1 - b)
        deo_po_duzini = k1 * b
        relativna_duzina = self.relativna_duzina

        ocene = defaultdict(float)      # pesma koje jos nema pocinje od 0
        for termin, puta in broj_u_upitu.items():
            idf = self.idf.get(termin)
            if idf is None:         # reci nema ni u jednoj pesmi
                continue
            tezina = puta * idf * (k1 + 1)
            for id_pesme, pozicije in indeks.postings_za(termin):
                tf = len(pozicije)
                doprinos = tezina * tf / (tf + stalni_deo + deo_po_duzini * relativna_duzina[id_pesme])
                ocene[id_pesme] += doprinos
        return sorted(ocene.items(), key=itemgetter(1), reverse=True)
