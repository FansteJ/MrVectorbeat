import math
from collections import defaultdict
from operator import itemgetter

from mrvectorbeat.tfidf import najbolja_iz_porodice

# Rocchio; beta i gama sa vezbi. alfa izabrano merenjem (scripts/izmeri_plejlistu.py):
# sa alfa = 1 upit nadjaca oznacene pesme i promena oznaka skoro ne menja plejlistu
ALFA = 0.25
BETA = 0.75
GAMA = 0.15
BROJ_RECI = 20
# rec iz samo par pesama ima ogroman idf, a ne govori nista o ukusu
MIN_PESAMA_SA_RECI = 50
BROJ_PESAMA = 10
PRETPOSTAVLJENO_DOPADA = 5


def vektor_pesme(tfidf_model, termini):
    """ltc vektor pesme kao recnik {termin: tezina}, duzine 1."""
    tezine, norma = tfidf_model.vektor_upita(termini)
    if norma == 0:
        return {}
    return {t: w / norma for t, w in tezine.items()}


def centroid(vektori):
    zbir = defaultdict(float)
    for vektor in vektori:
        for termin, w in vektor.items():
            zbir[termin] += w
    return {t: w / len(vektori) for t, w in zbir.items()}


def rocchio(upit, dopada, ne_dopada, alfa=ALFA, beta=BETA, gama=GAMA):
    """alfa * upit + beta * centroid(dopada) - gama * centroid(ne dopada).
    Vektori su recnici, pa se racuna samo po terminima koji se u njima javljaju.
    Negativne tezine se odbacuju."""
    novi = defaultdict(float)
    for termin, w in upit.items():
        novi[termin] += alfa * w
    if dopada:
        for termin, w in centroid(dopada).items():
            novi[termin] += beta * w
    if ne_dopada:
        for termin, w in centroid(ne_dopada).items():
            novi[termin] -= gama * w
    return {t: w for t, w in novi.items() if w > 0}


def pesme_koje_se_dopadaju(rezultati, oznake):
    """Pesme oznacene sa "dopada mi se". Ako takvih nema, pretpostavlja se da se
    dopadaju prvi rezultati, bez onih koje je korisnik oznacio da mu se ne dopadaju."""
    dopada = [i for i, ocena in oznake.items() if ocena]
    if not dopada:
        dopada = [i for i in rezultati if i not in oznake][:PRETPOSTAVLJENO_DOPADA]
    return dopada


def napravi_plejlistu(tfidf_model, indeks, termini_upita, rezultati, oznake,
                      termini_pesme, porodica_po_id, alfa=ALFA):
    """Plejlista od pesama slicnih onima koje se dopadaju.
    rezultati: id-jevi pesama prikazanih u pretrazi. oznake: {id pesme: True (dopada se)
    ili False}. Ako se nijedna ne dopada, pretpostavlja se da se dopadaju prvi rezultati.
    termini_pesme(id_pesme): obradjeni stihovi pesme (lista termina).
    alfa se zadaje samo pri merenju.
    Vraca (reci [(termin, tezina), ...], plejlista [(id pesme, slicnost), ...])."""
    dopada = pesme_koje_se_dopadaju(rezultati, oznake)
    ne_dopada = [i for i, ocena in oznake.items() if not ocena]

    vektor = rocchio(vektor_pesme(tfidf_model, termini_upita),
                     [vektor_pesme(tfidf_model, termini_pesme(i)) for i in dopada],
                     [vektor_pesme(tfidf_model, termini_pesme(i)) for i in ne_dopada], alfa)
    vektor = {t: w for t, w in vektor.items() if len(indeks.postings_za(t)) >= MIN_PESAMA_SA_RECI}
    # plejlista se pravi samo od najvaznijih reci; one se prikazuju korisniku
    reci = sorted(vektor.items(), key=itemgetter(1), reverse=True)[:BROJ_RECI]
    norma = math.sqrt(sum(w * w for _, w in reci))
    slicne = tfidf_model.kosinus_za_vektor(indeks, dict(reci), norma)

    # bez pesama koje je korisnik vec video i njihovih drugih verzija
    vidjene = {porodica_po_id[i] for i in rezultati}
    vidjene.update(porodica_po_id[i] for i in oznake)
    nove = [(i, s) for i, s in slicne if porodica_po_id[i] not in vidjene]
    return reci, najbolja_iz_porodice(nove, porodica_po_id)[:BROJ_PESAMA]
