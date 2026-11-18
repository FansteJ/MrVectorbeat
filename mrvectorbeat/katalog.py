import re

from mrvectorbeat import tekst

_ZAGRADE = re.compile(r"\([^)]*\)|\[[^\]]*\]")


def samo_engleske_sa_stihovima(df):
    ima_stihove = df["lyrics"].fillna("").str.strip() != ""
    return df[(df["language"] == "en") & ima_stihove].copy()


def izdvoj_godinu(datum):
    # datum je "2019-08-16", "2019-08" ili "2019" - godina su uvek prva 4 znaka
    return datum.astype(str).str[:4].astype(int)


def _normalizuj(s):
    return " ".join(tekst.izdvoj_reci(tekst.mala_slova(s)))


def osnovni_naslov(naslov):
    # "Song - 2004 Remaster", "Song (feat. X)", "Song [Live]" -> "song"
    naslov = naslov.split(" - ")[0]
    naslov = _ZAGRADE.sub(" ", naslov)
    return _normalizuj(naslov)


def kljuc_porodice(izvodjac, naslov):
    return _normalizuj(izvodjac) + "|" + osnovni_naslov(naslov)
