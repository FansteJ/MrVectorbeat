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
#
# Drugi deo: tezina WordNet sinonima (jezicki.TEZINA_SINONIMA), MRR pretrage
# "Koja je ovo pesma?" (rangiranje.koja_je_pesma) nad upitima u kojima su reci
# zamenjene sinonimima ili nasumicnim recima.

import gc
import random
from collections import Counter

from mrvectorbeat import evaluacija, jezicki, pipeline, rangiranje, tekst

MU_VREDNOSTI = [1, 5, 10, 50, 100, 250, 500, 1000, 2000, 5000]
PRIMER_UPIT = "found love in a place without hope"       # primer iz postavke
PRIMER_PORODICA = "rihanna|we found love"
TEZINE_SINONIMA = [0.0, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8]
PRIMERI_PROSIRENJA = [(PRIMER_UPIT, PRIMER_PORODICA),
                      ("on the ground brazil", "jennifer lopez|on the floor")]

indeks = pipeline.ucitaj_indeks()
model = pipeline.ucitaj_jezicki()
porodice = pipeline.ucitaj_porodice()
porodica_po_id = rangiranje.porodice_po_id(indeks, porodice)
upiti = evaluacija.ocene_po_porodicama(pipeline.ucitaj_qrels(), porodice.get)

tokeni = pipeline.ucitaj_tokene()
termini_porodice = {}
for track_id, termini in tokeni.items():
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


def reci(upit):
    return [rec for rec, _ in jezicki.reci_upita(upit)]


def trazena_porodica(upit):
    return next(p for p, ocena in upiti[upit]["ocene"].items() if ocena == 2)


# Upiti bez greske sa recima zamenjenim:
#   - WordNet sinonimom kog nema u pesmi (1 ili 2 reci): tu prosirenje treba da pomogne,
#   - nasumicnom reci iz drugih upita koje nema u pesmi (2 reci): tu moze samo da odmogne.
slucajno = random.Random(17)
bez_greske = [u for u, p in upiti.items() if evaluacija.grupa(p) == evaluacija.BEZ_GRESKE]
sve_reci = sorted({rec for u in bez_greske for rec in reci(u)})
jedan_sinonim, dva_sinonima, nasumicne = {}, {}, {}
for upit in bez_greske:
    stare = reci(upit)
    pesma = termini_porodice[trazena_porodica(upit)]
    zamene = {}
    for rec in stare:
        sinonimi = jezicki.sinonimi(rec, model.p_c, pesma)
        if sinonimi:
            zamene[rec] = sinonimi[0][0]
    if zamene:
        izabrane = slucajno.sample(sorted(zamene), min(2, len(zamene)))
        jedan_sinonim[upit] = " ".join(zamene[r] if r == izabrane[0] else r for r in stare)
        if len(izabrane) == 2:
            dva_sinonima[upit] = " ".join(zamene[r] if r in izabrane else r for r in stare)
    if len(stare) >= 3:
        kandidati = [r for r in sve_reci if tekst.obradi(r) and tekst.obradi(r)[0] not in pesma]
        nove = list(stare)
        for k in slucajno.sample(range(len(stare)), 2):
            nove[k] = slucajno.choice(kandidati)
        nasumicne[upit] = " ".join(nove)

skupovi_prosirenja = {
    "bez greske": {u: u for u in bez_greske},
    "sa greskom": {u: u for u, p in upiti.items() if evaluacija.grupa(p) == evaluacija.SA_GRESKOM},
    "1 sinonim": jedan_sinonim,
    "2 sinonima": dva_sinonima,
    "2 nasumicne": nasumicne,
}


def termini_pesme(id_pesme):
    return set(tokeni[indeks.track_ids[id_pesme]])


print()
print("tezina sinonima".ljust(18) + "".join(f"{w:>8g}" for w in TEZINE_SINONIMA))
for ime, parovi in skupovi_prosirenja.items():
    red = []
    for w in TEZINE_SINONIMA:
        zbir_rr = 0.0
        for upit, otkucano in parovi.items():
            _, rangirano, _ = rangiranje.koja_je_pesma(model, indeks, otkucano, termini_pesme,
                                                       porodica_po_id, w)
            porodice_redom = (porodica_po_id[id_pesme] for id_pesme, _ in rangirano)
            zbir_rr += evaluacija.reciprocni_rang(porodice_redom, evaluacija.ocene_za_mere(upiti[upit]))
        red.append(zbir_rr / len(parovi))
    print(f"{ime} ({len(parovi)})".ljust(18) + "".join(f"{v:8.3f}" for v in red))

for upit, porodica in PRIMERI_PROSIRENJA:
    mesta = []
    for w in TEZINE_SINONIMA:
        _, rangirano, _ = rangiranje.koja_je_pesma(model, indeks, upit, termini_pesme, porodica_po_id, w)
        mesta.append(next(i for i, (id_pesme, _) in enumerate(rangirano, start=1)
                          if porodica_po_id[id_pesme] == porodica))
    print(f"mesto: {porodica.split('|')[1]}".ljust(18) + "".join(f"{m:8d}" for m in mesta))
print(f"Izabrano: tezina sinonima = {jezicki.TEZINA_SINONIMA:g} (jezicki.TEZINA_SINONIMA)")
