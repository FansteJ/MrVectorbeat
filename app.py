# app.py
#
# SABLON aplikacije. Bocna traka i sve strane vec postoje, ali su strane
# prazne - na svakoj je samo naslov i komentar koje gotove funkcije tu
# mozete koristiti.
#
# Funkcije za ucitavanje (ucitaj_X ispod) pozivaju pipeline.ucitaj_X().
# Dok su one u pipeline.py prazne, vracaju None - aplikacija se pokrece
# bez greske, samo jos nema sta da prikaze.
#
# VAZNO: ovo nije fiksno - imena funkcija, sta primaju i sta vracaju su
# samo PREDLOG, menjajte ih kako vam odgovara.
#
# Pokretanje iz korena projekta:
#   streamlit run app.py

import html
import math

import streamlit as st
from st_keyup import st_keyup

from mrvectorbeat import pipeline, prikaz, tekst, trie

# OVDE IDU importi vasih modula, npr.:
#   from mrvectorbeat import upit, indeks, tfidf, bm25, ...

st.set_page_config(page_title="Mr Vectorbeat", layout="wide")
st.markdown(prikaz.CSS, unsafe_allow_html=True)


# --- Ucitavanje modela ---------------------------------------------------
#
# Svaka funkcija je obavijena dekoratorom da se ucita SAMO JEDNOM, a ne
# pri svakom kliku:
#   @st.cache_data      - za tabele i recnike (pandas DataFrame, dict)
#   @st.cache_resource  - za modele (objekti klasa, FAISS indeks, ...)

@st.cache_resource
def ucitaj_indeks():
    return pipeline.ucitaj_indeks()


@st.cache_resource
def ucitaj_trie():
    return pipeline.ucitaj_trie()


# cache_resource umesto cache_data: cache_data bi pri svakom pritisku tastera
# kopirao ceo katalog (~200 ms). Katalog se zato nigde ne menja direktno.
@st.cache_resource
def ucitaj_katalog():
    return pipeline.ucitaj_katalog()


@st.cache_data
def ucitaj_izvodjace():
    pass


@st.cache_data
def broj_reci():
    pass


@st.cache_resource
def ucitaj_tfidf():
    return pipeline.ucitaj_tfidf()


@st.cache_resource
def ucitaj_bm25():
    return pipeline.ucitaj_bm25()


@st.cache_data
def ucitaj_evaluaciju():
    return pipeline.ucitaj_evaluaciju()


@st.cache_data
def ucitaj_qrels():
    return pipeline.ucitaj_qrels()


@st.cache_data
def ucitaj_graf():
    return pipeline.ucitaj_graf()


@st.cache_resource
def ucitaj_kgram():
    return pipeline.ucitaj_kgram()


@st.cache_data
def ucitaj_porodice():
    return pipeline.ucitaj_porodice()


@st.cache_data
def ucitaj_popularnost():
    return pipeline.ucitaj_popularnost()


@st.cache_resource
def ucitaj_kdrvo():
    return pipeline.ucitaj_kdrvo()


@st.cache_resource
def ucitaj_semantiku():
    return pipeline.ucitaj_semantiku()


@st.cache_resource
def ucitaj_rag_korpus():
    return pipeline.ucitaj_rag_korpus()


@st.cache_resource
def ucitaj_autoplay():
    return pipeline.ucitaj_autoplay()


@st.cache_data
def ucitaj_hibrid_evaluaciju():
    return pipeline.ucitaj_hibrid_evaluaciju()


@st.cache_resource
def ucitaj_sbert():
    pass


@st.cache_resource
def zagrej_ollama():
    pass


@st.cache_data
def ucitaj_labele_pesama():
    pass


@st.cache_data
def ucitaj_labele_autoplay():
    pass


@st.cache_data
def ucitaj_katalog_po_id():
    pass


@st.cache_resource
def ucitaj_jezicki(mu):
    pass


@st.cache_data
def ucitaj_tokene_po_pesmi():
    pass


@st.cache_data
def ucitaj_audio_vektore():
    pass


@st.cache_data
def ucitaj_sbert_vektore():
    pass


ind = ucitaj_indeks()
obicno_stablo, obrnuto_stablo = ucitaj_trie()
kgram_indeks = ucitaj_kgram()
porodice = ucitaj_porodice()
df = ucitaj_katalog()
izvodjaci = ucitaj_izvodjace()
# SBERT i Ollama se ucitavaju odmah pri pokretanju - trebaju i "Po smislu"
# i "AI DJ Bot", pa cekanje ide na start, a ne na prvi upit.
ucitaj_sbert()
zagrej_ollama()


# --- Bocna traka -------------------------------------------------------

with st.sidebar:
    st.markdown(prikaz.LOGO, unsafe_allow_html=True)

    strana = st.radio("Izaberite stranu", ["Obrada teksta", "Pretraga", "Stihovi", "Jezicki model", "Evaluacija",
                                           "Izvodjaci", "Katalog", "Radio", "Po smislu", "AI DJ Bot",
                                           "Hibridna pretraga", "Klasteri", "Autoplay"])

    st.divider()
    st.caption("Ucitani indeksi")
    # OVDE IDE statistika preko prikaz.statistika(labela, broj):
    #   prikaz.statistika("Pesama", len(df))
    #   prikaz.statistika("Izvodjaca", len(izvodjaci))
    #   prikaz.statistika("Reci u indeksu", broj_reci())


# --- Pretraga ----------------------------------------------------------

if strana == "Pretraga":
    st.title("Pretraga")
    st.caption("Kucajte naziv pesme ili izvodjaca. Zvezdica menja bilo koji niz slova: lov*, *ing, be*t.")

    BROJ_PREDLOGA = 10
    unos = st_keyup("Pretraga", key="pretraga_unos", debounce=200,
                    placeholder="npr. queen, lov*, *ing, be*t",
                    label_visibility="collapsed").strip()

    if unos:
        oblik = trie.oblik_obrasca(unos)
        predlozi = []
        greska = None
        try:
            if oblik == "prefiks":
                predlozi = obicno_stablo.pretrazi(unos, BROJ_PREDLOGA)
            elif oblik == "sufiks":
                predlozi = obrnuto_stablo.pretrazi(unos, BROJ_PREDLOGA)
            else:
                # k-gramski indeks samo kad zvezdicu ne mogu da rese stabla
                predlozi = kgram_indeks.pretrazi(unos, BROJ_PREDLOGA)
        except ValueError as e:
            greska = str(e)

        if greska:
            st.warning(greska)
        elif predlozi:
            istaknuto = unos.rstrip("*") if oblik == "prefiks" else ""
            for ime, tip, ucestalost in predlozi:
                prikaz.sugestija(ime, istaknuto, f"{tip} · {ucestalost}×")
        elif oblik == "prefiks":
            # ispravka samo kad dopuna ne vrati nijedno ime
            ispravka = kgram_indeks.ispravka(unos.rstrip("*"))
            if ispravka:
                ime, tip, _ = ispravka
                st.markdown(f"Nijedno ime ne pocinje sa *{unos}*. Da li ste mislili: **{ime}** ({tip})?")
            else:
                st.info("Nema imena koje pocinje ovako, a nema ni dovoljno slicnog.")
        else:
            st.info("Nijedno ime ne odgovara obrascu.")


# --- Katalog -----------------------------------------------------------

elif strana == "Katalog":
    st.title("Katalog")

    if "kat_strana" not in st.session_state:
        st.session_state.kat_strana = 1

    def na_prvu_stranu():
        st.session_state.kat_strana = 1

    SORTIRANJE = {"Popularnost": "track_popularity", "Godina": "godina", "Tempo": "tempo"}

    k1, k2, k3, k4 = st.columns([3, 2, 1.3, 1.3])
    zanrovi = k1.multiselect("Zanr", sorted(df["playlist_genre"].unique()),
                             placeholder="Svi zanrovi", on_change=na_prvu_stranu)
    po_cemu = k2.selectbox("Sortiraj po", list(SORTIRANJE), on_change=na_prvu_stranu)
    smer = k3.selectbox("Smer", ["Opadajuce", "Rastuce"], on_change=na_prvu_stranu)
    po_strani = k4.selectbox("Po strani", [12, 24, 48, 96], index=1, on_change=na_prvu_stranu)

    izbor = df[df["playlist_genre"].isin(zanrovi)] if zanrovi else df
    izbor = izbor.sort_values(SORTIRANJE[po_cemu], ascending=(smer == "Rastuce"), kind="stable")

    broj_strana = max(1, math.ceil(len(izbor) / po_strani))
    st.session_state.kat_strana = min(st.session_state.kat_strana, broj_strana)
    strana_br = st.session_state.kat_strana

    st.caption(f"{len(izbor):,} pesama · strana {strana_br} od {broj_strana}".replace(",", " "))

    deo = izbor.iloc[(strana_br - 1) * po_strani: strana_br * po_strani]
    KOLONA = 6
    for i in range(0, len(deo), KOLONA):
        for kolona, (_, red) in zip(st.columns(KOLONA), deo.iloc[i:i + KOLONA].iterrows()):
            with kolona:
                prikaz.plocica(red)

    n1, n2, n3 = st.columns([1, 2, 1])
    if n1.button("← Prethodna", disabled=strana_br <= 1, width="stretch"):
        st.session_state.kat_strana -= 1
        st.rerun()
    n2.markdown(f"<div style='text-align:center; padding-top:6px'>Strana {strana_br} / {broj_strana}</div>",
                unsafe_allow_html=True)
    if n3.button("Sledeca →", disabled=strana_br >= broj_strana, width="stretch"):
        st.session_state.kat_strana += 1
        st.rerun()


# --- Stihovi -----------------------------------------------------------

elif strana == "Stihovi":
    st.title("Pretraga po stihovima")
    st.caption("Pretrazuje sadrzaj pesama, ne naslove.")

    # Koristi: ind, ucitaj_tfidf(), porodice, df, prikaz.kartica()


# --- Jezicki model -----------------------------------------------------

elif strana == "Jezicki model":
    st.title("Jezicki model i prosirenje upita")
    st.caption("Treci nacin rangiranja, i sta se sve moze dodati upitu.")

    # Koristi: ucitaj_jezicki(mu), ucitaj_bm25(), ucitaj_tokene_po_pesmi(),
    #          ucitaj_qrels(), ind, df, prikaz.kartica()


# --- Evaluacija --------------------------------------------------------

elif strana == "Evaluacija":
    st.title("Evaluacija pretrage")

    # Koristi: ucitaj_evaluaciju(), ucitaj_qrels(), ucitaj_tfidf(),
    #          ucitaj_bm25(), ind, df, prikaz.kartica()


# --- Izvodjaci ---------------------------------------------------------

elif strana == "Izvodjaci":
    st.title("Uticaj izvodjaca")
    st.caption("Ko je najuticajniji izvodjac - PageRank nad grafom koji je "
               "napravio crawler, naspram prostog brojanja linkova.")

    # Koristi: ucitaj_graf(), prikaz.kartica_izvodjaca()


# --- Radio -------------------------------------------------------------

elif strana == "Radio":
    st.title("Radio — slicne pesme po zvuku")
    st.caption("Pretraga po audio-osobinama (tempo, energija, glasnoca...), "
               "ne po tekstu ni zanru. k-d stablo + k-NN nad 9 osobina.")

    # Koristi: ucitaj_kdrvo(), ucitaj_labele_pesama(), ucitaj_katalog_po_id(),
    #          porodice, prikaz.kartica_radio()


# --- Po smislu ---------------------------------------------------------

elif strana == "Po smislu":
    st.title("Pretraga po smislu")
    st.caption("Opisi raspolozenje obicnim jezikom - sistem razume smisao, "
               "ne samo tacne reci iz stihova.")

    # Koristi: ucitaj_semantiku(), ucitaj_sbert(), ucitaj_katalog_po_id(),
    #          prikaz.kartica_smisao()


# --- AI DJ Bot ---------------------------------------------------------

elif strana == "AI DJ Bot":
    st.title("AI DJ Bot")
    st.caption("Pitaj o izvodjacima - bot odgovara na osnovu Wikipedia "
               "clanaka i pokazuje odakle je uzeo odgovor.")

    # Koristi: ucitaj_rag_korpus(), ucitaj_sbert()


# --- Klasteri ----------------------------------------------------------

elif strana == "Klasteri":
    st.title("Klasteri — grupisanje bez unapred poznatih oznaka")
    st.caption("K-means nad dva razlicita prostora: zvuk (9 audio-osobina) "
               "naspram smisla teksta (SBERT).")

    # Koristi: ucitaj_audio_vektore(), ucitaj_sbert_vektore(), df


# --- Autoplay ----------------------------------------------------------

elif strana == "Autoplay":
    st.title("Autoplay — predvidjanje sledece pesme")
    st.caption("Markovljev lanac naspram Transformera, oba obucena na "
               "stvarnoj istoriji slusanja (data/music4all_istorija.csv).")

    # Koristi: ucitaj_autoplay(), ucitaj_labele_autoplay(),
    #          ucitaj_katalog_po_id(), prikaz.kartica()


# --- Hibridna pretraga -------------------------------------------------

elif strana == "Hibridna pretraga":
    st.title("Hibridna pretraga — BM25 + SBERT (RRF)")
    st.caption("Isti upit kroz tacne reci (BM25) i kroz smisao (SBERT), pa "
               "spojeno preko Reciprocal Rank Fusion.")

    # Koristi: ucitaj_bm25(), ucitaj_semantiku(), ind, porodice,
    #          ucitaj_hibrid_evaluaciju(), prikaz.kartica()


# --- Obrada teksta -----------------------------------------------------

else:
    st.title("Obrada teksta")
    st.caption("Kako se stihovi pretvaraju u reci kojima pretrazujemo.")

    unos = st.text_area(
        "Tekst",
        "Don't STOP me now, I'm havin' such a good time! "
        "'Cause I'm dancing, I'm loving every minute...",
        height=120,
    )

    korak1 = tekst.mala_slova(unos)
    korak2 = tekst.izdvoj_reci(korak1)
    korak3 = tekst.ukloni_stop_reci(korak2)
    korak4 = tekst.stemuj(korak3)

    st.subheader("1. Mala slova")
    st.markdown(f"<div class='reci'>{html.escape(korak1)}</div>", unsafe_allow_html=True)

    st.subheader(f"2. Izdvajanje reci  ·  {len(korak2)} reci")
    st.markdown(f"<div class='reci'>{' · '.join(korak2)}</div>", unsafe_allow_html=True)

    st.subheader(f"3. Uklanjanje stop-reci  ·  izbaceno {len(korak2) - len(korak3)}")
    prikaz3 = " · ".join(
        r if r not in tekst.STOP_RECI else f"<s style='color:#6b6b78'>{r}</s>"
        for r in korak2
    )
    st.markdown(f"<div class='reci'>{prikaz3}</div>", unsafe_allow_html=True)

    st.subheader("4. Stemer (Snowball)")
    prikaz4 = " · ".join(
        f"<span class='rezultat'>{k}</span>" if k != r else k
        for r, k in zip(korak3, korak4)
    )
    st.markdown(f"<div class='reci'>{prikaz4}</div>", unsafe_allow_html=True)
