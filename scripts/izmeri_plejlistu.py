# scripts/izmeri_plejlistu.py
#
# Merenje na osnovu kog je izabrano alfa za Rocchio (plejlista.ALFA). Pokrece se
# rucno, posle scripts.pripremi:
#   python -m scripts.izmeri_plejlistu
#
# Za svaki tematski upit iz qrels.csv: pretraga "Koja je ovo pesma?", prvih 20
# rezultata, pa plejlista. Meri se P@10 plejliste (koliko pesama je na temu)
# bez oznaka i sa oznakama (3 relevantne se dopadaju, 2 nerelevantne ne), i koliko
# pesama ostaje isto kad se umesto 3 oznacene pesme oznace 3 druge.

import gc

from mrvectorbeat import evaluacija, pipeline, plejlista, rangiranje

ALFA_VREDNOSTI = [0.0, 0.25, 0.5, 1.0]
BROJ_REZULTATA = 20

indeks = pipeline.ucitaj_indeks()
jezicki_model = pipeline.ucitaj_jezicki()
tfidf_model = pipeline.ucitaj_tfidf()
porodice = pipeline.ucitaj_porodice()
porodica_po_id = rangiranje.porodice_po_id(indeks, porodice)
tokeni = pipeline.ucitaj_tokene()
upiti = evaluacija.ocene_po_porodicama(pipeline.ucitaj_qrels(), porodice.get)


def termini_pesme(id_pesme):
    return tokeni[indeks.track_ids[id_pesme]]


def p_at_10(plejlista_pesama, ocene):
    return sum(1 for id_pesme, _ in plejlista_pesama if ocene.get(porodica_po_id[id_pesme], 0) > 0) / 10


gc.disable()
teme = []
for upit, podaci in upiti.items():
    if evaluacija.grupa(podaci) != evaluacija.TEMATSKI:
        continue
    reci, rangirano, _ = rangiranje.koja_je_pesma(jezicki_model, indeks, upit,
                                                  lambda i: set(termini_pesme(i)), porodica_po_id)
    rezultati = [id_pesme for id_pesme, _ in rangirano[:BROJ_REZULTATA]]
    ocene = podaci["ocene"]
    relevantne = [i for i in rezultati if ocene.get(porodica_po_id[i], 0) > 0]
    nerelevantne = [i for i in rezultati if ocene.get(porodica_po_id[i], 0) == 0]
    teme.append(([termin for _, termin in reci], rezultati, ocene, relevantne, nerelevantne))

print(f"{len(teme)} tematskih upita")
print("alfa    P@10 bez oznaka   P@10 sa oznakama   iste pesme posle promene oznaka")
for alfa in ALFA_VREDNOSTI:
    bez, sa, iste, parova = 0.0, 0.0, 0, 0
    for termini_upita, rezultati, ocene, relevantne, nerelevantne in teme:
        def napravi(oznake):
            return plejlista.napravi_plejlistu(tfidf_model, indeks, termini_upita, rezultati, oznake,
                                               termini_pesme, porodica_po_id, alfa)[1]
        bez += p_at_10(napravi({}), ocene)
        oznake = {i: True for i in relevantne[:3]}
        oznake.update({i: False for i in nerelevantne[:2]})
        sa += p_at_10(napravi(oznake), ocene)
        if len(relevantne) >= 6:
            prva = napravi({i: True for i in relevantne[:3]})
            druga = napravi({i: True for i in relevantne[3:6]})
            iste += len({i for i, _ in prva} & {i for i, _ in druga})
            parova += 1
    print(f"{alfa:<8g}{bez / len(teme):>14.3f}{sa / len(teme):>19.3f}{iste / parova:>21.1f} / 10")
print(f"\nIzabrano: alfa = {plejlista.ALFA:g} (plejlista.ALFA)")
