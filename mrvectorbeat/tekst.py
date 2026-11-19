import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

_APOSTROFI = str.maketrans({"‘": "'", "’": "'", "`": "'", "´": "'"})
_REC = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def mala_slova(tekst):
    if not isinstance(tekst, str):
        return ""
    return tekst.lower()


def izdvoj_reci(tekst):
    # apostrof se brise da bi "don't" i "dont" bili isti termin
    return [r.replace("'", "") for r in _REC.findall(tekst.translate(_APOSTROFI))]


def _ucitaj_stop_reci():
    try:
        sirova = stopwords.words("english")
    except LookupError:
        nltk.download("stopwords", quiet=True)
        sirova = stopwords.words("english")

    # ista obrada kao za stihove, inace se "don't" iz liste ne poklapa sa "dont"
    stop = set()
    for rec in sirova:
        stop.update(izdvoj_reci(mala_slova(rec)))
    return stop


STOP_RECI = _ucitaj_stop_reci()


def ukloni_stop_reci(reci):
    return [r for r in reci if r not in STOP_RECI]


_STEMER = SnowballStemmer("english")
_KORENI = {}


def stemuj(reci):
    rezultat = []
    for r in reci:
        koren = _KORENI.get(r)
        if koren is None:
            koren = _STEMER.stem(r)
            _KORENI[r] = koren
        rezultat.append(koren)
    return rezultat


def obradi(tekst):
    return stemuj(ukloni_stop_reci(izdvoj_reci(mala_slova(tekst))))


def obradi_sa_pozicijama(tekst):
    """Kao obradi, ali uz svaki termin vraca i poziciju reci u originalnom tekstu.
    Stop-reci se preskacu, ali se racunaju u poziciju."""
    reci = izdvoj_reci(mala_slova(tekst))
    pozicije = [i for i, r in enumerate(reci) if r not in STOP_RECI]
    termini = stemuj([reci[i] for i in pozicije])
    return list(zip(termini, pozicije))
