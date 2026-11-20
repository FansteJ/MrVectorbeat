import numpy as np

# izabrano merenjem (scripts/izmeri_pagerank.py)
D = 0.85
EPS = 1e-8


def pagerank(izlazni, d=D, eps=EPS, max_iteracija=1000):
    """PageRank kao na vezbama: PR(p) = (1 - d) / n + d * sum_{q -> p} PR(q) / L(q).
    izlazni[i]: cvorovi na koje pokazuje cvor i. Viseci cvor (bez izlaznih linkova)
    ceo svoj rang salje u skok, koji se deli podjednako svim cvorovima.
    Ponavlja se dok ukupna promena (zbir |novi - stari|) ne padne ispod eps.
    Vraca (rang po cvoru, promena posle svake iteracije)."""
    n = len(izlazni)
    # sve grane kao dva niza: grana k ide od izvori[k] ka ciljevi[k]
    izvori = np.array([i for i, susedi in enumerate(izlazni) for _ in susedi], dtype=np.int64)
    ciljevi = np.array([j for susedi in izlazni for j in susedi], dtype=np.int64)
    broj_izlaznih = np.array([len(susedi) for susedi in izlazni], dtype=float)
    viseci = broj_izlaznih == 0

    rang = np.full(n, 1 / n)
    promene = []
    for _ in range(max_iteracija):
        # deo ranga koji svaka stranica daje jednom svom linku
        po_linku = np.zeros(n)
        po_linku[~viseci] = d * rang[~viseci] / broj_izlaznih[~viseci]
        # svaki cvor dobija zbir onoga sto mu daju stranice koje na njega pokazuju
        novi = np.bincount(ciljevi, weights=po_linku[izvori], minlength=n)
        skok = (1 - d) * rang[~viseci].sum() + rang[viseci].sum()
        novi += skok / n
        promene.append(float(np.abs(novi - rang).sum()))
        rang = novi
        if promene[-1] < eps:
            break
    return rang, promene
