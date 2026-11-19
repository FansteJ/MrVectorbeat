from mrvectorbeat import tekst


def prvo_pojavljivanje(stihovi, termini):
    """Pozicija (u obradjenom stihu) prvog termina iz termini, ili None."""
    for pozicija, termin in enumerate(tekst.obradi(stihovi)):
        if termin in termini:
            return pozicija
    return None


def isecak(stihovi, pozicije, sirina=8, raspon=True):
    """Deo stihova oko pogotka.

    pozicije su pozicije termina pogotka u obradjenom stihu (kao u indeksu).
    raspon=True istice sve reci od prve do poslednje (fraza, zajedno sa stop-recima
    izmedju), raspon=False samo same reci (blizina).
    Vraca listu delova (tekst, istaknut)."""
    if not pozicije:
        return []
    # pozicija termina -> redni broj reci u originalnom tekstu
    rec_za_termin = [rec for _, rec in tekst.obradi_sa_pozicijama(stihovi)]
    mesta = tekst.mesta_reci(stihovi)

    reci = sorted(rec_za_termin[p] for p in pozicije)
    if raspon:
        istaknute = set(range(reci[0], reci[-1] + 1))
    else:
        istaknute = set(reci)
    od = max(0, reci[0] - sirina)
    do = min(len(mesta) - 1, reci[-1] + sirina)

    delovi = []
    if od > 0:
        delovi.append(("… ", False))
    kursor = mesta[od][0]
    for rec in range(od, do + 1):
        pocetak, kraj = mesta[rec]
        # razmak/interpunkcija ispred reci je istaknut samo unutar istaknutog dela
        izmedju_istaknuto = rec in istaknute and rec - 1 in istaknute
        delovi.append((stihovi[kursor:pocetak], izmedju_istaknuto))
        delovi.append((stihovi[pocetak:kraj], rec in istaknute))
        kursor = kraj
    if do < len(mesta) - 1:
        delovi.append((" …", False))

    # susedni delovi sa istom oznakom se spajaju
    spojeni = []
    for deo, istaknut in delovi:
        if spojeni and spojeni[-1][1] == istaknut:
            spojeni[-1] = (spojeni[-1][0] + deo, istaknut)
        elif deo:
            spojeni.append((deo, istaknut))
    return spojeni
