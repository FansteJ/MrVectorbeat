# scripts/izmeri_pagerank.py
#
# Merenje na osnovu kog je izabran faktor prigusenja d (pagerank.D). Pokrece se
# rucno, posle scripts.pripremi:
#   python -m scripts.izmeri_pagerank
#
# Za svako d: broj iteracija do smirivanja, koliko se poredak izvodjaca iz kataloga
# slaze sa prostim brojanjem ulaznih linkova, koliko se prvih 20 izvodjaca poklapa sa
# prethodnim d, i prvih 5 izvodjaca.

import numpy as np

from mrvectorbeat import pagerank, pipeline

D_VREDNOSTI = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99]
PRVIH = 20

g = pipeline.ucitaj_graf()
broj_ulaznih = np.array([len(u) for u in g.ulazni()], dtype=float)
izvodjacki = sorted(g.izvodjaci_cvora)


def mesta(vrednosti):
    """Mesto svakog izvodjaca kad se poredjaju po vrednosti (0 = najveca)."""
    redosled = np.argsort(-vrednosti, kind="stable")
    mesto = np.empty(len(vrednosti))
    mesto[redosled] = np.arange(len(vrednosti))
    return mesto


mesta_ulaznih = mesta(broj_ulaznih[izvodjacki])
print(f"Graf: {g.broj_cvorova} stranica, {g.broj_grana} linkova, {len(izvodjacki)} stranica izvodjaca\n")
print(f"{'d':>5}{'iteracija':>11}{'slaganje sa ulaznim':>21}{'isto u prvih ' + str(PRVIH):>18}   prvih 5")
prethodnih = None
for d in D_VREDNOSTI:
    rang, promene = pagerank.pagerank(g.izlazni, d)
    rang_izvodjaca = rang[izvodjacki]
    # Spirmanov koeficijent: korelacija mesta (1 = isti poredak)
    slaganje = np.corrcoef(mesta(rang_izvodjaca), mesta_ulaznih)[0, 1]
    prvi = [izvodjacki[i] for i in np.argsort(-rang_izvodjaca, kind="stable")[:PRVIH]]
    isto = "" if prethodnih is None else f"{len(set(prvi) & set(prethodnih))}/{PRVIH}"
    imena = ", ".join(g.izvodjaci_cvora[c][0] for c in prvi[:5])
    print(f"{d:>5g}{len(promene):>11}{slaganje:>21.3f}{isto:>18}   {imena}")
    prethodnih = prvi
print(f"\nIzabrano: d = {pagerank.D} (pagerank.D)")
