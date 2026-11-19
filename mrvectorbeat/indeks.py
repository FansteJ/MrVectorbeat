from mrvectorbeat import tekst
from mrvectorbeat.postings import presek, razlika, unija


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
