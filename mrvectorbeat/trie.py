import heapq


class Cvor:
    __slots__ = ("deca", "najbolje", "imena")

    def __init__(self):
        self.deca = {}          # slovo -> Cvor
        self.najbolje = None    # najveci prioritet u celom podstablu
        self.imena = []         # imena koja se zavrsavaju bas ovde


PORUKE = {
    "prefiks": "Obrazac bez zvezdice ili sa zvezdicom na kraju (lov, lov*) resava obicno prefiksno stablo.",
    "sufiks": "Obrazac sa zvezdicom na pocetku (*ing) resava obrnuto stablo.",
    "kgram": "Zvezdicu u sredini ili vise zvezdica (be*t, *ove*) resava k-gramski indeks.",
}


def oblik_obrasca(obrazac):
    broj = obrazac.count("*")
    if broj == 0 or (broj == 1 and obrazac.endswith("*")):
        return "prefiks"
    if broj == 1 and obrazac.startswith("*"):
        return "sufiks"
    return "kgram"


def _azuriraj_najbolje(cvor, prioritet):
    if cvor.najbolje is None or prioritet > cvor.najbolje:
        cvor.najbolje = prioritet


class PrefiksnoStablo:
    def __init__(self, obrnuto=False):
        # obrnuto stablo cuva imena unazad, pa "*ing" postaje prefiks "gni"
        self.obrnuto = obrnuto
        self.koren = Cvor()
        self.broj_cvorova = 1
        self.obidjeno = 0       # koliko cvorova je skinuto sa heap-a u poslednjoj pretrazi

    def dodaj(self, kljuc, prikaz, tip, ucestalost, popularnost):
        if self.obrnuto:
            kljuc = kljuc[::-1]
        # prioritet je par: prvo ucestalost, a kod iste ucestalosti popularnost
        prioritet = (ucestalost, popularnost)
        cvor = self.koren
        _azuriraj_najbolje(cvor, prioritet)
        for slovo in kljuc:
            if slovo not in cvor.deca:
                cvor.deca[slovo] = Cvor()
                self.broj_cvorova += 1
            cvor = cvor.deca[slovo]
            _azuriraj_najbolje(cvor, prioritet)
        cvor.imena.append((prioritet, prikaz, tip))

    def _cvor_za(self, prefiks):
        cvor = self.koren
        for slovo in prefiks:
            cvor = cvor.deca.get(slovo)
            if cvor is None:
                return None
        return cvor

    def pretrazi(self, obrazac, k=10):
        """Obicno stablo prihvata "lov" i "lov*", obrnuto samo "*ing"."""
        oblik = oblik_obrasca(obrazac)
        moj = "sufiks" if self.obrnuto else "prefiks"
        if oblik != moj:
            raise ValueError(PORUKE[oblik])

        deo = obrazac.strip("*")
        if self.obrnuto:
            deo = deo[::-1]
        return self.predlozi(deo, k)

    def predlozi(self, prefiks, k=10):
        """k najcescih imena koja pocinju sa prefiks, od najcesceg ka najredjem."""
        self.obidjeno = 0
        pocetak = self._cvor_za(prefiks.lower())
        if pocetak is None:
            return []

        # heapq vadi najmanji element, pa prioritet stavljamo sa minusom.
        # redni broj je tu da se kod istog prioriteta ne porede sami cvorovi.
        heap = []
        redni = 0

        def ubaci(prioritet, stvar):
            nonlocal redni
            heapq.heappush(heap, (-prioritet[0], -prioritet[1], redni, stvar))
            redni += 1

        ubaci(pocetak.najbolje, pocetak)
        rezultat = []
        while heap and len(rezultat) < k:
            stvar = heapq.heappop(heap)[-1]
            if isinstance(stvar, Cvor):
                self.obidjeno += 1
                for prioritet, prikaz, tip in stvar.imena:
                    ubaci(prioritet, (prikaz, tip, prioritet[0]))
                for dete in stvar.deca.values():
                    ubaci(dete.najbolje, dete)
            else:
                # gotovo ime: nista sto je ostalo u heap-u ne moze biti cesce
                rezultat.append(stvar)
        return rezultat
