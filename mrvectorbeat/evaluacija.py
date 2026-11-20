import math
import random
from collections import Counter

from mrvectorbeat import tekst

POZNATA = "poznata_stavka"
TEMA = "tema"
BEZ_GRESKE = "jedna pesma, bez greske"
SA_GRESKOM = "jedna pesma, sa greskom"
TEMATSKI = "tematski"
GRUPE = (BEZ_GRESKE, SA_GRESKOM, TEMATSKI)


# --- Mere kvaliteta rang-liste ---
# Svaka prima rang-listu (kljucevi poredjani od najboljeg) i ocene za jedan upit
# ({kljuc: ocena}, kljuc koji nije u recniku ima ocenu 0). Relevantno = ocena > 0.

def p_at_k(lista, ocene, k=5):
    """Koliki deo prvih k je relevantan. Deli se sa k, kao na vezbama."""
    return sum(1 for kljuc in lista[:k] if ocene.get(kljuc, 0) > 0) / k


def reciprocni_rang(lista, ocene):
    """1 / pozicija prvog relevantnog; 0 ako ga nema u listi."""
    for pozicija, kljuc in enumerate(lista, start=1):
        if ocene.get(kljuc, 0) > 0:
            return 1 / pozicija
    return 0.0


def prosecna_preciznost(lista, ocene):
    """Prosek P@i po pozicijama pogodaka, podeljen brojem SVIH relevantnih,
    i onih koje lista nije vratila."""
    broj_relevantnih = sum(1 for ocena in ocene.values() if ocena > 0)
    if broj_relevantnih == 0:
        return 0.0
    pogodaka = 0
    zbir = 0.0
    for pozicija, kljuc in enumerate(lista, start=1):
        if ocene.get(kljuc, 0) > 0:
            pogodaka += 1
            zbir += pogodaka / pozicija
    return zbir / broj_relevantnih


def _dcg(dobici):
    return sum(dobitak / math.log2(pozicija + 1) for pozicija, dobitak in enumerate(dobici, start=1))


def ndcg_at_k(lista, ocene, k=5):
    """DCG prvih k podeljen DCG-om idealnog poretka. Dobitak je sama ocena,
    pa pesma sa ocenom 2 vredi duplo vise od pesme sa ocenom 1."""
    dobici = [ocene.get(kljuc, 0) for kljuc in lista[:k]]
    # idealan poredak: sve ocene iz fajla, od najvece, i one koje lista nije vratila
    idealni = sorted(ocene.values(), reverse=True)[:k]
    idealni_dcg = _dcg(idealni)
    if idealni_dcg == 0:
        return 0.0
    return _dcg(dobici) / idealni_dcg


MERE = {"P@5": p_at_k, "RR": reciprocni_rang, "AP": prosecna_preciznost, "nDCG@5": ndcg_at_k}


def ocene_po_porodicama(qrels, porodica_za):
    """Ocene iz qrels tabele, prenete na porodice: ocena vazi za sve verzije pesme,
    jer korisnik vidi samo jednu. porodica_za(track_id) -> porodica.
    Vraca {upit: {"skup", "tipfeler", "ocene": {porodica: ocena}}}."""
    upiti = {}
    for skup, upit, track_id, ocena, tipfeler in qrels[
            ["skup", "upit", "track_id", "ocena", "tipfeler"]].itertuples(index=False):
        if upit not in upiti:
            upiti[upit] = {"skup": skup, "tipfeler": int(tipfeler), "ocene": {}}
        ocene = upiti[upit]["ocene"]
        porodica = porodica_za(track_id)
        ocene[porodica] = max(ocene.get(porodica, 0), int(ocena))
    return upiti


def ocene_za_mere(podaci_upita):
    """Ocene koje ulaze u mere. Kod upita za jednu pesmu pogodak je samo ocena 2
    (ocena 1 je druga pesma istog izvodjaca), pa se ocena 1 tu ne racuna."""
    ocene = podaci_upita["ocene"]
    if podaci_upita["skup"] == POZNATA:
        return {porodica: ocena for porodica, ocena in ocene.items() if ocena == 2}
    return ocene


def mere_svih_upita(rang_liste, upiti, porodica_za):
    """Sve cetiri mere za svaki upit i svaki model.
    rang_liste: {model: {upit: [track_id, ...]}}.
    Vraca {model: {upit: {ime mere: vrednost}}}."""
    rezultat = {}
    for model, liste in rang_liste.items():
        rezultat[model] = {}
        for upit, podaci in upiti.items():
            lista = [porodica_za(track_id) for track_id in liste[upit]]
            ocene = ocene_za_mere(podaci)
            rezultat[model][upit] = {ime: mera(lista, ocene) for ime, mera in MERE.items()}
    return rezultat


def proseci_grupe(mere, upiti, ime_grupe):
    """Prosek svake mere preko upita jedne grupe, za svaki model.
    Vraca {model: {ime mere: prosek}}."""
    u_grupi = [upit for upit, podaci in upiti.items() if grupa(podaci) == ime_grupe]
    return {model: {ime: sum(po_upitu[u][ime] for u in u_grupi) / len(u_grupi) for ime in MERE}
            for model, po_upitu in mere.items()}


def zamenjeni_upiti(upiti, termini_porodice, p_c, broj_zamena=2, seme=17):
    """Upiti za jednu pesmu bez greske u kojima je broj_zamena reci zamenjeno drugim
    recima iz kataloga, kao kad korisnik pogresno zapamti stih ("without hope" umesto
    "hopeless"). Nova rec se bira po cestosti u katalogu (ljudi zamenjuju obicne reci),
    i nije iz trazene pesme. Fiksno seme: uvek isti upiti.
    termini_porodice: {porodica: skup termina}. Vraca {upit: Counter termina}."""
    slucajno = random.Random(seme)
    recnik = sorted(p_c)
    verovatnoce = [p_c[t] for t in recnik]
    rezultat = {}
    for upit, podaci in upiti.items():
        if grupa(podaci) != BEZ_GRESKE:
            continue
        termini = tekst.obradi(upit)
        tacni = set()
        for porodica in ocene_za_mere(podaci):
            tacni |= termini_porodice[porodica]
        for i in slucajno.sample(range(len(termini)), min(broj_zamena, len(termini))):
            while True:
                nova = slucajno.choices(recnik, verovatnoce)[0]
                if nova not in tacni and nova not in termini:
                    break
            termini[i] = nova
        rezultat[upit] = Counter(termini)
    return rezultat


def grupa(podaci_upita):
    """Jedna od tri grupe za koje se mere prikazuju posebno."""
    if podaci_upita["skup"] == TEMA:
        return TEMATSKI
    if podaci_upita["tipfeler"]:
        return SA_GRESKOM
    return BEZ_GRESKE
