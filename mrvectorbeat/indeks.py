from mrvectorbeat import tekst


class PozicioniIndeks:
    def __init__(self):
        self.track_ids = []     # id pesme -> track_id iz kataloga
        self.postings = {}      # termin -> [(id pesme, [pozicije]), ...], sortirano po id-ju

    def dodaj(self, track_id, stihovi):
        # id-jevi rastu redom dodavanja, pa su postings liste sortirane bez sortiranja
        id_pesme = len(self.track_ids)
        self.track_ids.append(track_id)

        # pozicija je redni broj termina u obradjenom stihu (bez stop-reci),
        # pa su reci fraze susedne ako su na uzastopnim pozicijama
        pozicije_termina = {}
        for pozicija, termin in enumerate(tekst.obradi(stihovi)):
            pozicije_termina.setdefault(termin, []).append(pozicija)
        for termin, pozicije in pozicije_termina.items():
            self.postings.setdefault(termin, []).append((id_pesme, pozicije))

    def postings_za(self, termin):
        return self.postings.get(termin, [])
