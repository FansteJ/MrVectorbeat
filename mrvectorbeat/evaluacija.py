import math

POZNATA = "poznata_stavka"
TEMA = "tema"


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


def grupa(podaci_upita):
    """Jedna od tri grupe za koje se mere prikazuju posebno."""
    if podaci_upita["skup"] == TEMA:
        return "tematski"
    if podaci_upita["tipfeler"]:
        return "jedna pesma, sa greskom"
    return "jedna pesma, bez greske"
