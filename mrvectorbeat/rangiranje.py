from mrvectorbeat.tfidf import najbolja_iz_porodice

MODELI = ("TF-IDF", "Kosinus (lnc.ltc)", "BM25")


def porodice_po_id(indeks, porodice):
    """Lista porodica po id-ju pesme iz indeksa, da se porodica nadje jednim
    indeksiranjem liste umesto trazenjem track_id-ja u recniku. Pravi se jednom."""
    return [porodice[track_id] for track_id in indeks.track_ids]


def rangiraj(model, upit, indeks, tfidf_model, bm25_model, porodica_po_id, k1=None, b=None):
    """Rang-lista onakva kakvu korisnik vidi na strani Stihovi: ocene izabranog
    modela, pa od vise verzija iste pesme samo najbolje ocenjena.
    Isto se koristi i za evaluaciju, da se meri bas ta lista.
    porodica_po_id: iz porodice_po_id. k1 i b se zadaju samo pri izboru
    parametara BM25; inace vaze oni iz modela.
    Vraca [(id pesme, ocena), ...] od najbolje ka najgoroj."""
    if model == "TF-IDF":
        ocene = tfidf_model.tfidf(indeks, upit)
    elif model == "Kosinus (lnc.ltc)":
        ocene = tfidf_model.kosinus(indeks, upit)
    elif model == "BM25":
        ocene = bm25_model.bm25(indeks, upit, k1, b)
    else:
        raise ValueError(f"Nepoznat model: {model}")
    return najbolja_iz_porodice(ocene, porodica_po_id)
