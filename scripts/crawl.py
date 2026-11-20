# scripts/crawl.py
#
# Crawler: prikuplja clanke sa Vikipedije o izvodjacima iz kataloga i stranicama
# na koje oni upucuju. Pokrece se pre scripts.pripremi (graf se pravi od rezultata):
#   python -m scripts.crawl
#   python -m scripts.crawl --izvodjaca 50 --dodatnih 100     (probni obilazak)
#
# Traje nekoliko sati (pauza 1 s po zahtevu). Sve sto je preuzeto ostaje u data/wiki/,
# pa moze da se prekine (Ctrl+C) i ponovo pokrene: vec preuzete stranice se citaju sa
# diska, bez zahteva, i obilazak nastavlja gde je stao.

import argparse
import json

from mrvectorbeat import crawler, pipeline
from mrvectorbeat.katalog import osnovni_naslov

FOLDER = "data/wiki"
DODATNIH_STRANICA = 4000

parser = argparse.ArgumentParser()
parser.add_argument("--izvodjaca", type=int, default=None, help="samo prvih N izvodjaca")
parser.add_argument("--dodatnih", type=int, default=DODATNIH_STRANICA)
argumenti = parser.parse_args()

# izvodjaci sa vise pesama i popularniji prvi, da su najvazniji obidjeni i ako se prekine
df = pipeline.ucitaj_katalog()
po_izvodjacu = df.groupby("track_artist").agg(pesama=("track_id", "size"),
                                                    popularnost=("track_popularity", "max"))
po_izvodjacu = po_izvodjacu.sort_values(["pesama", "popularnost"], ascending=False)
# nazivi pesama sluze da se od vise clanaka istog imena izabere pravi
pesme = df.groupby("track_artist")["track_name"].agg(lambda naslovi: sorted(set(map(osnovni_naslov, naslovi))))
izvodjaci = {ime: pesme[ime] for ime in list(po_izvodjacu.index)[:argumenti.izvodjaca]}

preuzimac = crawler.Preuzimac(FOLDER)
rezultat = crawler.obidji(preuzimac, izvodjaci, argumenti.dodatnih)

with open(f"{FOLDER}/obilazak.json", "w", encoding="utf-8") as f:
    json.dump(rezultat, f, ensure_ascii=False)

preuzete = rezultat["preuzete"]
muzickih = sum(1 for url in preuzete if crawler.je_muzicka(preuzimac.preuzmi(url)))
print(f"\nIzvodjaci: clanak nadjen za {len(rezultat['izvodjaci'])} od {len(izvodjaci)}")
print(f"Preuzeto stranica: {len(preuzete)}, vezanih za muziku: {muzickih} "
      f"({muzickih / len(preuzete):.1%})")
print(f"Poslato zahteva u ovom pokretanju: {preuzimac.poslato_zahteva}")
