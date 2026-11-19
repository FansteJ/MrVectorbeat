POZNATA = "poznata_stavka"
TEMA = "tema"


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
