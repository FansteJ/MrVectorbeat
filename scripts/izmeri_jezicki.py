# scripts/izmeri_jezicki.py
#
# Merenje na osnovu kog je izabran mu za Dirichlet ublazavanje (jezicki.MU).
# Nije deo pripreme: mu je konstanta, pa merenje ne utice na artefakte. Pokrece se
# rucno, posle scripts.pripremi, kad treba ponovo proveriti izbor:
#   python -m scripts.izmeri_jezicki
#
# MRR (lista sa jednom verzijom po porodici, ista funkcija kao na strani) nad:
#   - upitima za jednu pesmu bez greske i sa greskom u kucanju (qrels.csv),
#   - istim upitima bez greske sa dve zamenjene reci (korisnik pogresno zapamti stih),
# plus mesto pesme iz primera u postavci.

import gc
from collections import Counter

from mrvectorbeat import evaluacija, pipeline, rangiranje, tekst

MU_VREDNOSTI = [1, 5, 10, 50, 100, 250, 500, 1000, 2000, 5000]
PRIMER_UPIT = "found love in a place without hope"       # primer iz postavke
PRIMER_PORODICA = "rihanna|we found love"

indeks = pipeline.ucitaj_indeks()
model = pipeline.ucitaj_jezicki()
porodice = pipeline.ucitaj_porodice()
porodica_po_id = rangiranje.porodice_po_id(indeks, porodice)
upiti = evaluacija.ocene_po_porodicama(pipeline.ucitaj_qrels(), porodice.get)

termini_porodice = {}
for track_id, termini in pipeline.ucitaj_tokene().items():
    termini_porodice.setdefault(porodice[track_id], set()).update(termini)
skupovi = {
    "bez greske": {u: Counter(tekst.obradi(u)) for u, p in upiti.items()
                   if evaluacija.grupa(p) == evaluacija.BEZ_GRESKE},
    "sa greskom": {u: Counter(tekst.obradi(u)) for u, p in upiti.items()
                   if evaluacija.grupa(p) == evaluacija.SA_GRESKOM},
    "zamenjene": evaluacija.zamenjeni_upiti(upiti, termini_porodice, model.p_c),
}
primer = Counter(tekst.obradi(PRIMER_UPIT))

# petlja pravi mnogo privremenih objekata; sakupljac smeca bi stalno pregledao
# milione objekata ucitanog indeksa, a ovde nema kruznih referenci
gc.disable()
print("mu".ljust(18) + "".join(f"{mu:>8g}" for mu in MU_VREDNOSTI))
for ime, upiti_skupa in skupovi.items():
    red = []
    for mu in MU_VREDNOSTI:
        zbir_rr = 0.0
        for upit, tezine in upiti_skupa.items():
            rangirano = rangiranje.rangiraj_jezicki(model, indeks, tezine, porodica_po_id, mu)
            porodice_redom = (porodica_po_id[id_pesme] for id_pesme, _ in rangirano)
            zbir_rr += evaluacija.reciprocni_rang(porodice_redom, evaluacija.ocene_za_mere(upiti[upit]))
        red.append(zbir_rr / len(upiti_skupa))
    print(f"{ime} ({len(upiti_skupa)})".ljust(18) + "".join(f"{v:8.3f}" for v in red))

mesta = []
for mu in MU_VREDNOSTI:
    rangirano = rangiranje.rangiraj_jezicki(model, indeks, primer, porodica_po_id, mu)
    mesta.append(next(i for i, (id_pesme, _) in enumerate(rangirano, start=1)
                      if porodica_po_id[id_pesme] == PRIMER_PORODICA))
print("mesto primera".ljust(18) + "".join(f"{m:8d}" for m in mesta))
print(f"\nIzabrano: mu = {model.mu:g} (jezicki.MU)")
