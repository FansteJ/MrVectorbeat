from mrvectorbeat import tekst
from mrvectorbeat.postings import presek, razlika, unija


def _pocetci_sa_pomakom(pocetci, pozicije, pomak):
    """Pocetci s za koje je s + pomak u pozicije. Obe liste su sortirane."""
    i = j = 0
    rezultat = []
    while i < len(pocetci) and j < len(pozicije):
        trazena = pocetci[i] + pomak
        if trazena == pozicije[j]:
            rezultat.append(pocetci[i])
            i += 1
            j += 1
        elif trazena < pozicije[j]:
            i += 1
        else:
            j += 1
    return rezultat


def _spoji_sa_pomakom(kandidati, postings, pomak):
    """Spaja po pesmama (kao presek), a u zajednickim pesmama zadrzava samo
    pocetke fraze iza kojih je ovaj termin tacno pomak mesta dalje."""
    i = j = 0
    rezultat = []
    while i < len(kandidati) and j < len(postings):
        pesma_a, pocetci = kandidati[i]
        pesma_b, pozicije = postings[j]
        if pesma_a == pesma_b:
            ostali = _pocetci_sa_pomakom(pocetci, pozicije, pomak)
            if ostali:
                rezultat.append((pesma_a, ostali))
            i += 1
            j += 1
        elif pesma_a < pesma_b:
            i += 1
        else:
            j += 1
    return rezultat


def _parovi_u_blizini(a, b, rastojanje, ista_rec=False):
    """Parovi (pa, pb) za koje je |pa - pb| < rastojanje. Obe liste su sortirane.
    Ako se trazi ista rec dvaput ("love" i "love"), svaki par se vraca jednom (pa < pb)."""
    rezultat = []
    levo = 0
    for pa in a:
        # pozicije iz b koje su predaleko levo od pa vise nikad nece biti blizu
        while levo < len(b) and b[levo] <= pa - rastojanje:
            levo += 1
        j = levo
        while j < len(b) and b[j] < pa + rastojanje:
            # razlicite reci nikad nisu na istoj poziciji; kod iste reci uzimamo samo pb > pa
            if not ista_rec or b[j] > pa:
                rezultat.append((pa, b[j]))
            j += 1
    return rezultat


class PozicioniIndeks:
    def __init__(self):
        self.track_ids = []     # id pesme -> track_id iz kataloga
        self.postings = {}      # termin -> [(id pesme, [pozicije]), ...], sortirano po id-ju

    def dodaj(self, track_id, termini):
        """termini su vec obradjen stih"""
        # id-jevi rastu redom dodavanja, pa su postings liste sortirane bez sortiranja
        id_pesme = len(self.track_ids)
        self.track_ids.append(track_id)

        # pozicija je redni broj termina u obradjenom stihu (bez stop-reci),
        # pa su reci fraze susedne ako su na uzastopnim pozicijama
        pozicije_termina = {}
        for pozicija, termin in enumerate(termini):
            pozicije_termina.setdefault(termin, []).append(pozicija)
        for termin, pozicije in pozicije_termina.items():
            self.postings.setdefault(termin, []).append((id_pesme, pozicije))

    def postings_za(self, termin):
        return self.postings.get(termin, [])

    def pesme_za(self, termin):
        """Samo id-jevi pesama iz postings liste (sortirani)."""
        return [id_pesme for id_pesme, _ in self.postings_za(termin)]

    # --- Bulova pretraga: svaka prima listu vec obradjenih termina ---

    def i_upit(self, termini):
        """Pesme koje sadrze sve termine."""
        if not termini:
            return []
        # od najkrace liste ka najduzoj: medjurezultat je od starta sto manji
        liste = sorted((self.pesme_za(t) for t in termini), key=len)
        rezultat = liste[0]
        for lista in liste[1:]:
            if not rezultat:
                break
            rezultat = presek(rezultat, lista)
        return rezultat

    def ili_upit(self, termini):
        """Pesme koje sadrze bar jedan termin."""
        rezultat = []
        for t in termini:
            rezultat = unija(rezultat, self.pesme_za(t))
        return rezultat

    def bez_upit(self, termini):
        """Pesme sa prvim terminom, a bez ijednog od ostalih."""
        if not termini:
            return []
        rezultat = self.pesme_za(termini[0])
        for t in termini[1:]:
            if not rezultat:
                break
            rezultat = razlika(rezultat, self.pesme_za(t))
        return rezultat

    def bulova(self, upit, operator):
        """upit je tekst kako ga je korisnik otkucao, operator "I", "ILI" ili "BEZ".
        Vraca sortiranu listu id-jeva pesama."""
        termini = tekst.obradi(upit)
        if operator == "I":
            return self.i_upit(termini)
        if operator == "ILI":
            return self.ili_upit(termini)
        if operator == "BEZ":
            return self.bez_upit(termini)
        raise ValueError(f"Nepoznat operator: {operator}")

    # --- Pozicioni upiti ---

    def frazni(self, upit):
        """Pesme u kojima reci upita stoje jedna za drugom, tim redom.
        Vraca [(id pesme, [pocetne pozicije fraze]), ...]."""
        termini = tekst.obradi(upit)
        if not termini:
            return []
        # kandidati: svaka pozicija prve reci je moguci pocetak fraze
        kandidati = self.postings_za(termini[0])
        for pomak, termin in enumerate(termini[1:], start=1):
            if not kandidati:
                break
            kandidati = _spoji_sa_pomakom(kandidati, self.postings_za(termin), pomak)
        return kandidati

    def blizina(self, rec1, rec2, rastojanje):
        """Pesme u kojima su dve reci na rastojanju manjem od zadatog, bilo kojim redom.
        Vraca [(id pesme, [(pozicija reci 1, pozicija reci 2), ...]), ...]."""
        termini1, termini2 = tekst.obradi(rec1), tekst.obradi(rec2)
        if len(termini1) > 1 or len(termini2) > 1:
            raise ValueError("Upit po blizini prima tacno jednu rec u svakom polju.")
        if not termini1 or not termini2:
            return []

        ista_rec = termini1[0] == termini2[0]
        a, b = self.postings_za(termini1[0]), self.postings_za(termini2[0])
        i = j = 0
        rezultat = []
        while i < len(a) and j < len(b):
            pesma_a, pozicije_a = a[i]
            pesma_b, pozicije_b = b[j]
            if pesma_a == pesma_b:
                parovi = _parovi_u_blizini(pozicije_a, pozicije_b, rastojanje, ista_rec)
                if parovi:
                    rezultat.append((pesma_a, parovi))
                i += 1
                j += 1
            elif pesma_a < pesma_b:
                i += 1
            else:
                j += 1
        return rezultat
