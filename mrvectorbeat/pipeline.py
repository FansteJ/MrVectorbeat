# mrvectorbeat/pipeline.py
#
# SABLON. Ovde su samo IMENA funkcija i opis sta svaka treba da radi -
# tela su prazna (pass), pa se svaka funkcija moze pozvati bez greske,
# ali jos nista ne radi.
#
# VAZNO: ovo NISU fiksne funkcije. Imena, parametri i ono sto funkcija
# vraca su samo PREDLOG - slobodno ih menjajte, dodajte nove ili
# izbacite one koje vam ne trebaju, kako vam odgovara.
#
# Ideja ovog fajla: za svaki model postoji par funkcija
#   napravi_X() - gradi model JEDNOM i cuva ga u artifacts/
#                 (poziva je scripts/pripremi.py)
#   ucitaj_X()  - cita vec sacuvan model iz artifacts/
#                 (poziva je app.py)
# Tako aplikacija nikad ne gradi nista iznova pri svakom kliku.

import gc
import pickle
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from mrvectorbeat import evaluacija, katalog, rangiranje, tekst
from mrvectorbeat.bm25 import BM25Model
from mrvectorbeat.indeks import PozicioniIndeks
from mrvectorbeat.jezicki import MU as IZABRANO_MU
from mrvectorbeat.jezicki import JezickiModel
from mrvectorbeat.kgram import KgramIndeks
from mrvectorbeat.tfidf import TfIdfModel
from mrvectorbeat.trie import PrefiksnoStablo

KOREN = Path(__file__).resolve().parent.parent
DATA = KOREN / "data"
ARTIFACTS = KOREN / "artifacts"


def _snimi(objekat, ime_fajla):
    ARTIFACTS.mkdir(exist_ok=True)
    with open(ARTIFACTS / ime_fajla, "wb") as f:
        pickle.dump(objekat, f)


def _ucitaj(ime_fajla):
    with open(ARTIFACTS / ime_fajla, "rb") as f:
        return pickle.load(f)


@contextmanager
def _bez_sakupljaca_smeca():
    """Za duge petlje rangiranja: sakupljac smeca bi stalno pregledao milione objekata
    ucitanih modela. Memorija se i dalje oslobadja odmah (brojanjem referenci);
    sakupljac treba samo za kruzne reference, a ove petlje ih ne prave."""
    gc.disable()
    try:
        yield
    finally:
        gc.enable()


# Kolone koje zadrzavamo u katalogu. Sve ostalo iz CSV-a nam ne treba.
# Kartice u prikaz.py ocekuju bar: track_name, track_artist, godina,
# playlist_genre, tempo.
KOLONE = [
    "track_id",           # jedinstveni ID pesme, kljuc za sve kasnije
    "track_name",
    "track_artist",
    "lyrics",
    "track_album_name",
    "godina",             # ovu kolonu pravimo mi
    "playlist_genre",
    "playlist_subgenre",
    "track_popularity",
    "duration_ms",
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "porodica",           # ovu kolonu pravimo mi - isti kljuc za razlicite
                          # verzije iste pesme
]


def napravi_katalog():
    """Cita data/spotify_songs.csv, cisti ga i snima katalog u artifacts/.
    Vraca: tabelu kataloga."""
    df = pd.read_csv(DATA / "spotify_songs.csv")
    df = katalog.samo_engleske_sa_stihovima(df)
    df["godina"] = katalog.izdvoj_godinu(df["track_album_release_date"])
    df["porodica"] = [katalog.kljuc_porodice(a, n)
                      for a, n in zip(df["track_artist"], df["track_name"])]
    df = df[KOLONE].reset_index(drop=True)

    ARTIFACTS.mkdir(exist_ok=True)
    df.to_parquet(ARTIFACTS / "katalog.parquet", index=False)
    return df


def ucitaj_katalog():
    """Cita gotov katalog iz artifacts/."""
    return pd.read_parquet(ARTIFACTS / "katalog.parquet")


def napravi_tokene():
    """Obradjuje stihove svake pesme i snima tokene u artifacts/.
    Vraca: recnik track_id -> lista termina."""
    df = ucitaj_katalog()
    tokeni = {tid: tekst.obradi(s) for tid, s in zip(df["track_id"], df["lyrics"])}
    _snimi(tokeni, "tokeni.pkl")
    return tokeni


def ucitaj_tokene():
    """Cita gotove tokene iz artifacts/."""
    return _ucitaj("tokeni.pkl")


def _imena():
    return katalog.imena_za_pretragu(ucitaj_katalog())


def napravi_trie():
    """Gradi obicno i obrnuto prefiksno stablo nad imenima pesama i izvodjaca
    i snima ih u artifacts/. Vraca: (obicno, obrnuto)."""
    obicno, obrnuto = PrefiksnoStablo(), PrefiksnoStablo(obrnuto=True)
    for r in _imena().itertuples():
        obicno.dodaj(r.kljuc, r.prikaz, r.tip, r.ucestalost, r.popularnost)
        obrnuto.dodaj(r.kljuc, r.prikaz, r.tip, r.ucestalost, r.popularnost)
    _snimi((obicno, obrnuto), "trie.pkl")
    return obicno, obrnuto


def ucitaj_trie():
    """Cita gotova stabla iz artifacts/. Vraca: (obicno, obrnuto)."""
    return _ucitaj("trie.pkl")


def ucitaj_porodice():
    """Vraca recnik track_id -> porodica."""
    df = ucitaj_katalog()
    return dict(zip(df["track_id"], df["porodica"]))


def ucitaj_popularnost():
    """Vraca recnik ime (pesma ili izvodjac) -> popularnost."""
    pass


def napravi_kgram():
    """Gradi k-gramski indeks nad imenima pesama i izvodjaca i snima ga u
    artifacts/."""
    indeks = KgramIndeks()
    for r in _imena().itertuples():
        indeks.dodaj(r.kljuc, r.prikaz, r.tip, r.ucestalost, r.popularnost)
    _snimi(indeks, "kgram.pkl")
    return indeks


def ucitaj_kgram():
    """Cita gotov k-gramski indeks iz artifacts/."""
    return _ucitaj("kgram.pkl")


def napravi_indeks():
    """Gradi invertovani indeks iz tokena i snima ga u artifacts/."""
    df = ucitaj_katalog()
    tokeni = ucitaj_tokene()
    indeks = PozicioniIndeks()
    for track_id in df["track_id"]:
        indeks.dodaj(track_id, tokeni[track_id])
    _snimi(indeks, "indeks.pkl")
    return indeks


def ucitaj_indeks():
    """Cita gotov indeks iz artifacts/."""
    return _ucitaj("indeks.pkl")


def napravi_tfidf():
    """Gradi TF-IDF model (idf termina, duzine vektora pesama) i snima ga u artifacts/."""
    model = TfIdfModel(ucitaj_indeks())
    _snimi(model, "tfidf.pkl")
    return model


def ucitaj_tfidf():
    """Cita gotov TF-IDF model iz artifacts/."""
    return _ucitaj("tfidf.pkl")


def napravi_bm25():
    """Gradi BM25 model (duzine pesama, prosecna duzina, idf) i snima ga u artifacts/."""
    model = BM25Model(ucitaj_indeks())
    _snimi(model, "bm25.pkl")
    return model


def ucitaj_bm25():
    """Cita gotov BM25 model iz artifacts/."""
    return _ucitaj("bm25.pkl")


def ucitaj_qrels(skup=None):
    """Cita test upite iz data/qrels.csv.

    skup - "poznata_stavka", "tema", ili None za oba.
    Vraca: tabelu (skup, upit, track_id, ocena, tipfeler)."""
    qrels = pd.read_csv(DATA / "qrels.csv")
    if skup is not None:
        qrels = qrels[qrels["skup"] == skup].reset_index(drop=True)
    return qrels


# gusce kod malih k1, gde se MRR najvise menja; k1 = 0 znaci da se gleda samo da li
# je rec u pesmi, a ne koliko puta (tada b nema uticaja)
K1_VREDNOSTI = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
B_VREDNOSTI = [0.0, 0.25, 0.5, 0.75, 1.0]


def napravi_parametre_bm25():
    """MRR nad upitima za jednu pesmu bez greske za svaki par (k1, b), izbor para
    sa najvecim MRR i snimanje BM25 modela sa izabranim parametrima.
    Vraca {"k1": [...], "b": [...], "mrr": {b: [mrr za svako k1]}, "izabrano": (k1, b)}."""
    indeks = ucitaj_indeks()
    tfidf_model = ucitaj_tfidf()
    bm25_model = ucitaj_bm25()
    porodice = ucitaj_porodice()
    porodica_po_id = rangiranje.porodice_po_id(indeks, porodice)
    upiti = evaluacija.ocene_po_porodicama(ucitaj_qrels(), porodice.get)
    bez_greske = [u for u, p in upiti.items() if evaluacija.grupa(p) == evaluacija.BEZ_GRESKE]
    ocene = {u: evaluacija.ocene_za_mere(upiti[u]) for u in bez_greske}

    mrr = {}
    najbolje = None
    with _bez_sakupljaca_smeca():
        for b in B_VREDNOSTI:
            mrr[b] = []
            for k1 in K1_VREDNOSTI:
                zbir_rr = 0.0
                for upit in bez_greske:
                    rangirano = rangiranje.rangiraj("BM25", upit, indeks, tfidf_model, bm25_model,
                                                    porodica_po_id, k1=k1, b=b)
                    # porodice se citaju redom iz iste liste, a RR staje kod prve relevantne
                    porodice_redom = (porodica_po_id[id_pesme] for id_pesme, _ in rangirano)
                    zbir_rr += evaluacija.reciprocni_rang(porodice_redom, ocene[upit])
                vrednost = zbir_rr / len(bez_greske)
                mrr[b].append(vrednost)
                if najbolje is None or vrednost > najbolje[0]:
                    najbolje = (vrednost, k1, b)

    _, k1, b = najbolje
    bm25_model.k1, bm25_model.b = k1, b
    _snimi(bm25_model, "bm25.pkl")

    parametri = {"k1": K1_VREDNOSTI, "b": B_VREDNOSTI, "mrr": mrr, "izabrano": (k1, b)}
    _snimi(parametri, "bm25_parametri.pkl")
    return parametri


def ucitaj_parametre_bm25():
    """Cita MRR za mrezu (k1, b) i izabrane vrednosti iz artifacts/."""
    return _ucitaj("bm25_parametri.pkl")


def napravi_evaluaciju():
    """Rangira sve upite iz qrels kroz sva tri modela, istom funkcijom kao strana
    Stihovi, i snima rang-liste u artifacts/. Mere racuna strana Evaluacija.
    Vraca: {model: {upit: [track_id, ...]}}, cele liste, od najbolje pesme."""
    indeks = ucitaj_indeks()
    tfidf_model = ucitaj_tfidf()
    bm25_model = ucitaj_bm25()
    porodice = ucitaj_porodice()
    porodica_po_id = rangiranje.porodice_po_id(indeks, porodice)
    upiti = ucitaj_qrels()["upit"].unique()

    rang_liste = {}
    with _bez_sakupljaca_smeca():
        for model in rangiranje.MODELI:
            rang_liste[model] = {}
            for upit in upiti:
                # upiti sa greskom u kucanju se ne ispravljaju
                rangirano = rangiranje.rangiraj(model, upit, indeks, tfidf_model, bm25_model, porodica_po_id)
                rang_liste[model][upit] = [indeks.track_ids[id_pesme] for id_pesme, _ in rangirano]
    _snimi(rang_liste, "evaluacija.pkl")
    return rang_liste


def ucitaj_evaluaciju():
    """Cita gotove rang-liste iz artifacts/."""
    return _ucitaj("evaluacija.pkl")


def napravi_jezicki(mu=IZABRANO_MU):
    """Gradi jezicki model (p_C svake reci, duzine pesama) i snima ga u artifacts/.
    mu je izabran merenjem (scripts/izmeri_jezicki.py)."""
    model = JezickiModel(ucitaj_indeks(), mu)
    _snimi(model, "jezicki.pkl")
    return model


def ucitaj_jezicki():
    """Cita gotov jezicki model iz artifacts/."""
    return _ucitaj("jezicki.pkl")


def ucitaj_graf():
    """Cita graf izvodjaca koji je napravio vas crawler."""
    pass


def napravi_rangove():
    """Racuna PageRank nad grafom izvodjaca i snima rang-listu u
    artifacts/."""
    pass


def ucitaj_rangove():
    """Cita gotovu rang-listu iz artifacts/."""
    pass


def napravi_kdrvo():
    """Gradi k-d stablo nad audio-osobinama kataloga i snima ga u
    artifacts/."""
    pass


def ucitaj_kdrvo():
    """Cita gotovo k-d stablo iz artifacts/."""
    pass


def napravi_semantiku():
    """Gradi semanticki model nad katalogom i snima ga u artifacts/."""
    pass


def ucitaj_semantiku():
    """Cita gotov semanticki model iz artifacts/."""
    pass


def napravi_rag_korpus():
    """Gradi korpus za AI DJ Bot-a i snima ga u artifacts/."""
    pass


def ucitaj_rag_korpus():
    """Cita gotov RAG korpus iz artifacts/."""
    pass


def napravi_hibrid_evaluaciju():
    """Racuna metrike hibridne pretrage nad qrels i snima tabelu u
    artifacts/."""
    pass


def ucitaj_hibrid_evaluaciju():
    """Cita gotovu tabelu metrika hibridne pretrage iz artifacts/."""
    pass


def napravi_autoplay():
    """Gradi Autoplay nad data/music4all_istorija.csv i snima ga u
    artifacts/."""
    pass


def ucitaj_autoplay():
    """Cita gotov Autoplay iz artifacts/."""
    pass
