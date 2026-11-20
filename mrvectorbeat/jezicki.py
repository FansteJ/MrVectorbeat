import math
from collections import Counter, defaultdict
from operator import itemgetter

from mrvectorbeat import tekst

# Izabrano na osnovu merenja (scripts.pripremi, jezicki_parametri.pkl): MRR je skoro
# isti za mu od 1 do 100, a mu = 100 je najveci na tom delu koji jos pronalazi pesmu
# i kad su reci zamenjene drugim (primer iz postavke).
MU = 100.0


class JezickiModel:
    """Jezicki model (query likelihood) sa Dirichlet ublazavanjem.
    Sve sto ne zavisi od upita se racuna jednom: verovatnoca svake reci u celom
    katalogu p_C(w) i duzina svake pesme. Broj pojavljivanja se cita iz indeksa."""

    def __init__(self, indeks, mu=MU):
        self.mu = mu
        broj_pesama = len(indeks.track_ids)
        self.duzina = [0] * broj_pesama
        ukupno_puta = {}                    # cf: koliko puta se rec javlja u celom katalogu
        for termin, lista in indeks.postings.items():
            ukupno_puta[termin] = 0
            for id_pesme, pozicije in lista:
                self.duzina[id_pesme] += len(pozicije)
                ukupno_puta[termin] += len(pozicije)
        self.ukupno_reci = sum(self.duzina)                  # |C|
        self.p_c = {t: cf / self.ukupno_reci for t, cf in ukupno_puta.items()}

    def oceni(self, indeks, tezine, mu=None):
        """log p(upit | pesma) = sum tezina(w) * log((tf + mu*p_C(w)) / (|d| + mu))
        za pesme koje sadrze bar jednu rec upita. tezine: {termin: tezina}.
        Pesma kojoj neke reci nedostaju ostaje, samo sa manjom ocenom.
        Vraca [(id pesme, ocena), ...] od najvece ka najmanjoj."""
        mu = self.mu if mu is None else mu
        # reci kojih nema u katalogu su iste za sve pesme (p_C = 0), pa ne menjaju poredak
        tezine = {t: w for t, w in tezine.items() if t in self.p_c}
        if not tezine:
            return []

        # Ocena = "osnova" (kao da pesma nema nijednu rec upita, ista za sve pesme)
        #       + "dodatak" za reci koje pesma sadrzi (sabira se kroz postings)
        #       - deo koji zavisi samo od duzine pesme
        osnova = sum(w * math.log(mu * self.p_c[t]) for t, w in tezine.items())
        dodatak = defaultdict(float)
        for termin, w in tezine.items():
            mu_pc = mu * self.p_c[termin]
            for id_pesme, pozicije in indeks.postings_za(termin):
                dodatak[id_pesme] += w * math.log(1 + len(pozicije) / mu_pc)
        ukupna_tezina = sum(tezine.values())
        ocene = [(id_pesme, osnova + d - ukupna_tezina * math.log(self.duzina[id_pesme] + mu))
                 for id_pesme, d in dodatak.items()]
        return sorted(ocene, key=itemgetter(1), reverse=True)

    def pretrazi(self, indeks, upit, mu=None):
        """Otkucan upit: svaka rec ima tezinu koliko puta je otkucana (kao na vezbama)."""
        return self.oceni(indeks, Counter(tekst.obradi(upit)), mu)


def reci_upita(upit):
    """Reci upita koje ulaze u pretragu, kako ih je korisnik otkucao, uz njihov termin:
    [(rec, termin), ...]. Stop-reci se izostavljaju."""
    reci = tekst.izdvoj_reci(tekst.mala_slova(upit))
    return [(reci[pozicija], termin) for termin, pozicija in tekst.obradi_sa_pozicijama(upit)]


def sadrzi_nedostaje(reci, termini_pesme):
    """Deli reci upita na one koje pesma sadrzi i one koje joj nedostaju."""
    sadrzi = [rec for rec, termin in reci if termin in termini_pesme]
    nedostaje = [rec for rec, termin in reci if termin not in termini_pesme]
    return sadrzi, nedostaje
