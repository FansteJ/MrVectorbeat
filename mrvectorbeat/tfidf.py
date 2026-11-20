import math
from collections import Counter, defaultdict
from operator import itemgetter

from mrvectorbeat import tekst


def najbolja_iz_porodice(rangirano, porodica_po_kljucu):
    """Iz liste [(kljuc, ocena), ...] sortirane od najbolje zadrzava samo prvu,
    tj. najbolje ocenjenu verziju svake porodice.
    porodica_po_kljucu[kljuc] -> porodica (lista po id-ju pesme ili recnik)."""
    vidjene = set()
    rezultat = []
    for kljuc, ocena in rangirano:
        porodica = porodica_po_kljucu[kljuc]
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
        Kao na vezbama, ponovljena rec upita se broji onoliko puta koliko se javlja.
        Vraca [(id pesme, ocena), ...] od najvece ocene ka najmanjoj."""
        broj_u_upitu = Counter(tekst.obradi(upit))
        ocene = defaultdict(float)      # pesma koje jos nema pocinje od 0
        for termin, puta in broj_u_upitu.items():
            idf = self.idf.get(termin)
            if idf is None:         # reci nema ni u jednoj pesmi
                continue
            for id_pesme, pozicije in indeks.postings_za(termin):
                ocene[id_pesme] += puta * tf_tezina(len(pozicije)) * idf
        return sorted(ocene.items(), key=itemgetter(1), reverse=True)

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
        return self.kosinus_za_vektor(indeks, tezine, norma)

    def slicne(self, indeks, id_pesme, termini, porodica_po_id, k=10):
        """Pesme ciji je tekst najslicniji pesmi id_pesme (kosinus lnc.ltc, pesma je upit).
        termini su obradjeni stihovi te pesme. Pesme iste porodice se izbacuju.
        Vraca najvise k parova (id pesme, slicnost)."""
        tezine, _ = self.vektor_upita(termini)
        # norma pesme kao upita je izracunata unapred, pri gradnji modela
        rangirano = self.kosinus_za_vektor(indeks, tezine, self.duzina_ltc[id_pesme])
        moja_porodica = porodica_po_id[id_pesme]
        bez_verzija = [(i, s) for i, s in rangirano if porodica_po_id[i] != moja_porodica]
        return najbolja_iz_porodice(bez_verzija, porodica_po_id)[:k]

    def doprinos_reci(self, id_a, termini_a, id_b, termini_b, k=10):
        """Koliko svaka zajednicka rec doprinosi kosinusu izmedju pesme a (upit, ltc)
        i pesme b (dokument, lnc). Kosinus je zbir doprinosa svih zajednickih reci.
        Vraca (kosinus, [(termin, broj u a, broj u b, udeo u kosinusu), ...]) za k najvecih."""
        tezine_a, _ = self.vektor_upita(termini_a)
        brojevi_a, brojevi_b = Counter(termini_a), Counter(termini_b)
        imenilac = self.duzina_ltc[id_a] * self.duzina_lnc[id_b]

        doprinosi = []
        for termin, w_a in tezine_a.items():
            if termin in brojevi_b:
                doprinos = w_a * tf_tezina(brojevi_b[termin]) / imenilac
                doprinosi.append((termin, brojevi_a[termin], brojevi_b[termin], doprinos))
        kosinus = sum(d for _, _, _, d in doprinosi)
        if kosinus == 0:
            return 0.0, []
        doprinosi.sort(key=lambda x: x[3], reverse=True)
        return kosinus, [(t, ba, bb, d / kosinus) for t, ba, bb, d in doprinosi[:k]]

    def kosinus_za_vektor(self, indeks, tezine_upita, norma_upita):
        """Kosinus izmedju vektora upita {termin: tezina} i pesama (lnc) koje sadrze
        bar jedan njegov termin. Vraca [(id pesme, slicnost), ...] od najvece ka najmanjoj."""
        if norma_upita == 0:
            return []
        # skalarni proizvod samo po zajednickim terminima, sabran termin po termin
        proizvodi = defaultdict(float)
        for termin, w_upit in tezine_upita.items():
            for id_pesme, pozicije in indeks.postings_za(termin):
                w_pesma = tf_tezina(len(pozicije))     # lnc: bez idf
                proizvodi[id_pesme] += w_upit * w_pesma
        slicnosti = [(id_pesme, proizvod / (norma_upita * self.duzina_lnc[id_pesme]))
                     for id_pesme, proizvod in proizvodi.items()]
        return sorted(slicnosti, key=itemgetter(1), reverse=True)
