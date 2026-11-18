import re

import pandas as pd

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


def imena_za_pretragu(df):
    """Tabela (kljuc, prikaz, tip, ucestalost, popularnost) za pesme i izvodjace."""
    delovi = []
    for kolona, tip in [("track_name", "pesma"), ("track_artist", "izvođač")]:
        t = pd.DataFrame({"prikaz": df[kolona], "popularnost": df["track_popularity"]})
        t["kljuc"] = t["prikaz"].str.lower()

        # ako ime postoji u vise oblika ("Ace of Spades" / "Ace Of Spades"), uzima se najcesci
        oblici = t.groupby(["kljuc", "prikaz"]).size().reset_index(name="n")
        oblici = oblici.sort_values("n", ascending=False).drop_duplicates("kljuc")

        g = t.groupby("kljuc")
        zbir = pd.DataFrame({
            "ucestalost": g.size(),
            "popularnost": g["popularnost"].max(),
        }).reset_index()
        zbir = zbir.merge(oblici[["kljuc", "prikaz"]], on="kljuc")
        zbir["tip"] = tip
        delovi.append(zbir[["kljuc", "prikaz", "tip", "ucestalost", "popularnost"]])
    return pd.concat(delovi, ignore_index=True)
