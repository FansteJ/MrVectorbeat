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

import gc
import html
import math

import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from mrvectorbeat import evaluacija, isecak, jezicki, pipeline, prikaz, rangiranje, tekst, trie

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


# cache_resource: rang-liste imaju ~18 MB, a cache_data bi ih kopirao pri svakom kliku
@st.cache_resource
def ucitaj_evaluaciju():
    return pipeline.ucitaj_evaluaciju()


@st.cache_data
def ucitaj_qrels():
    return pipeline.ucitaj_qrels()


@st.cache_data
def ucitaj_parametre_bm25():
    return pipeline.ucitaj_parametre_bm25()


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


# cache_resource iz istog razloga kao ucitaj_katalog: bez kopije pri svakom kliku
@st.cache_resource
def ucitaj_katalog_po_id():
    return ucitaj_katalog().set_index("track_id")


@st.cache_resource
def ucitaj_jezicki():
    jezicki.ucitaj_wordnet()
    return pipeline.ucitaj_jezicki()


# cache_resource: tokeni svih pesama su veliki, cache_data bi ih kopirao pri svakom kliku
@st.cache_resource
def ucitaj_tokene_po_pesmi():
    return pipeline.ucitaj_tokene()


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
tfidf_model = ucitaj_tfidf()
bm25_model = ucitaj_bm25()
jezicki_model = ucitaj_jezicki()
tokeni_po_pesmi = ucitaj_tokene_po_pesmi()


@st.cache_resource
def ucitaj_porodice_po_id():
    return rangiranje.porodice_po_id(ind, porodice)


porodica_po_id = ucitaj_porodice_po_id()


# Ucitani modeli imaju milione objekata koji se nikad ne brisu, a Python-ov
# sakupljac smeca bi ih povremeno sve pregledao (~0,85 s zastoja usred upita).
# freeze ih iskljucuje iz tog pregleda. Radi se jednom, posle ucitavanja.
@st.cache_resource
def zamrzni_ucitane_modele():
    gc.collect()
    gc.freeze()


zamrzni_ucitane_modele()


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

    MAKS_REZULTATA = 20
    katalog_po_id = ucitaj_katalog_po_id()

    def delovi_u_html(delovi):
        return "".join(f"<span class='rezultat'>{html.escape(deo)}</span>" if istaknut
                       else html.escape(deo) for deo, istaknut in delovi)

    # on_click se izvrsava pre ponovnog pokretanja skripta, pa je stanje
    # uskladjeno i otvoren je uvek tacno jedan panel
    def otvori_slicne(track_id):
        st.session_state.slicne_za = track_id
        st.session_state.par = None

    def zatvori_slicne():
        st.session_state.slicne_za = None
        st.session_state.par = None

    def izaberi_par(track_id):
        st.session_state.par = track_id

    def prikazi_par(id_a, red_a, termini_a, id_b, red_b):
        termini_b = tekst.obradi(red_b["lyrics"])
        _, reci = tfidf_model.doprinos_reci(id_a, termini_a, id_b, termini_b)
        najvaznije = {termin for termin, *_ in reci}
        oblici = isecak.oblici_termina([red_a["lyrics"], red_b["lyrics"]], najvaznije)

        st.markdown("**Reci koje najvise doprinose slicnosti**")
        st.table([{"Rec": oblici[termin],
                   f"Puta u: {red_a['track_name']}": u_a,
                   f"Puta u: {red_b['track_name']}": u_b,
                   "Udeo u slicnosti": f"{udeo * 100:.1f}%"}
                  for termin, u_a, u_b, udeo in reci])

        levo, desno = st.columns(2)
        for kolona, red in [(levo, red_a), (desno, red_b)]:
            with kolona:
                st.markdown(f"**{html.escape(red['track_name'])}** · {html.escape(red['track_artist'])}",
                            unsafe_allow_html=True)
                tekst_pesme = delovi_u_html(isecak.istakni(red["lyrics"], najvaznije))
                st.markdown(f"<div style='max-height:420px; overflow-y:auto; font-size:14px; "
                            f"line-height:1.7; color:#c8c8d0'>{tekst_pesme}</div>",
                            unsafe_allow_html=True)

    def prikazi_slicne(track_id):
        id_a = ind.track_ids.index(track_id)
        red_a = katalog_po_id.loc[track_id]
        termini_a = tekst.obradi(red_a["lyrics"])
        slicne = tfidf_model.slicne(ind, id_a, termini_a, porodica_po_id)

        with st.container(border=True):
            k1, k2 = st.columns([7, 1])
            k1.markdown(f"**Slicne pesme:** {html.escape(red_a['track_name'])} · "
                        f"{html.escape(red_a['track_artist'])}", unsafe_allow_html=True)
            k2.button("Zatvori", key=f"zatvori_{track_id}", on_click=zatvori_slicne)
            if not slicne:
                st.info("Nema pesama sa slicnim tekstom.")
            for mesto_b, (id_b, slicnost) in enumerate(slicne, start=1):
                track_id_b = ind.track_ids[id_b]
                red_b = katalog_po_id.loc[track_id_b]
                k1, k2 = st.columns([7, 1])
                with k1:
                    prikaz.kartica(mesto_b, red_b, skor=slicnost)
                k2.button("Uporedi", key=f"uporedi_{track_id}_{track_id_b}",
                          on_click=izaberi_par, args=(track_id_b,))
                if st.session_state.get("par") == track_id_b:
                    prikazi_par(id_a, red_a, termini_a, id_b, red_b)
    rezim = st.radio("Rezim", ["Rangirano", "Bulov", "Frazni", "Blizina"], horizontal=True,
                     label_visibility="collapsed")

    # pogodak: (track_id, pozicije za isecak, da li se istice ceo raspon, ocena ili None)
    pogoci = []
    termini = []
    unet_upit = False
    if rezim == "Rangirano":
        k1, k2 = st.columns([1, 4])
        mera = k1.selectbox("Mera", rangiranje.MODELI)
        upit = k2.text_input("Upit", placeholder="npr. dancing in the moonlight")
        if upit:
            unet_upit = True
            termini = tekst.obradi(upit)
            trazeni = termini
            # ista funkcija se koristi i za evaluaciju, pa se meri bas ova lista
            rangirano = rangiranje.rangiraj(mera, upit, ind, tfidf_model, bm25_model, porodica_po_id)
            for id_pesme, ocena in rangirano:
                pogoci.append((ind.track_ids[id_pesme], None, True, ocena))

    elif rezim == "Bulov":
        k1, k2 = st.columns([1, 4])
        operator = k1.selectbox("Operator", ["I", "ILI", "BEZ"],
                                help="I: sve reci · ILI: bar jedna · BEZ: prva rec, a bez ostalih")
        upit = k2.text_input("Reci", placeholder="npr. love night")
        if upit:
            unet_upit = True
            termini = tekst.obradi(upit)
            # Bulova pretraga ne vraca pozicije; mesto za isecak se trazi tek pri
            # prikazu (pozicije = None), samo za prikazane pesme
            for id_pesme in ind.bulova(upit, operator):
                pogoci.append((ind.track_ids[id_pesme], None, True, None))
            # kod BEZ se isecak pravi oko prve reci, jer ostale ne smeju da se jave
            trazeni = termini[:1] if operator == "BEZ" else termini

    elif rezim == "Frazni":
        upit = st.text_input("Fraza", placeholder="npr. hold me tight")
        if upit:
            unet_upit = True
            termini = tekst.obradi(upit)
            for id_pesme, poceci in ind.frazni(upit):
                # isecak oko prvog pogotka: sve reci fraze od tog pocetka
                pozicije = [poceci[0] + k for k in range(len(termini))]
                pogoci.append((ind.track_ids[id_pesme], pozicije, True, None))

    else:
        k1, k2, k3 = st.columns([2, 2, 1])
        rec1 = k1.text_input("Prva rec", placeholder="npr. love")
        rec2 = k2.text_input("Druga rec", placeholder="npr. heart")
        rastojanje = k3.number_input("Rastojanje manje od", min_value=2, max_value=50, value=5)
        if rec1 and rec2:
            unet_upit = True
            termini = tekst.obradi(rec1) + tekst.obradi(rec2)
            try:
                for id_pesme, parovi in ind.blizina(rec1, rec2, rastojanje):
                    pogoci.append((ind.track_ids[id_pesme], list(parovi[0]), False, None))
            except ValueError as e:
                st.warning(str(e))

    if unet_upit:
        if not termini:
            st.info("Upit posle obrade nema nijednu rec (samo stop-reci), pa nema rezultata.")
        elif not pogoci:
            st.info("Nijedna pesma ne odgovara upitu.")
        else:
            if rezim != "Rangirano":
                # rezimi bez ocene: popularnije pesme idu prve
                popularnost = katalog_po_id.loc[[p[0] for p in pogoci], "track_popularity"].tolist()
                redosled = sorted(range(len(pogoci)), key=lambda i: popularnost[i], reverse=True)
                pogoci = [pogoci[i] for i in redosled]

            ukupno = f"Pronadjeno pesama: {len(pogoci)}"
            if len(pogoci) > MAKS_REZULTATA:
                ukupno += f" · prikazano prvih {MAKS_REZULTATA}"
            st.caption(ukupno)

            for mesto, (track_id, pozicije, raspon, ocena) in enumerate(pogoci[:MAKS_REZULTATA], start=1):
                red = katalog_po_id.loc[track_id]
                if rezim == "Rangirano":
                    k1, k2 = st.columns([7, 1])
                    with k1:
                        prikaz.kartica(mesto, red, skor=ocena)
                    k2.button("Slicne pesme", key=f"slicne_{track_id}",
                              on_click=otvori_slicne, args=(track_id,))
                else:
                    prikaz.kartica(mesto, red, skor=ocena)
                if pozicije is None:
                    pozicije = [isecak.prvo_pojavljivanje(red["lyrics"], trazeni)]
                delovi = isecak.isecak(red["lyrics"], pozicije, raspon=raspon)
                st.markdown(f"<div style='color:#a8a8b3; font-size:14px; margin:-4px 0 16px 50px'>"
                            f"{delovi_u_html(delovi)}</div>", unsafe_allow_html=True)
                if rezim == "Rangirano" and st.session_state.get("slicne_za") == track_id:
                    prikazi_slicne(track_id)


# --- Jezicki model -----------------------------------------------------

elif strana == "Jezicki model":
    st.title("Jezicki model i prosirenje upita")
    st.caption("Treci nacin rangiranja, i sta se sve moze dodati upitu.")

    # Koristi: ucitaj_jezicki(mu), ucitaj_bm25(), ucitaj_tokene_po_pesmi(),
    #          ucitaj_qrels(), ind, df, prikaz.kartica()

    katalog_po_id = ucitaj_katalog_po_id()
    MAKS_REZULTATA = 20

    def termini_pesme(id_pesme):
        return set(tokeni_po_pesmi[ind.track_ids[id_pesme]])

    st.subheader("Koja je ovo pesma?")
    upit = st.text_input("Deo stiha kojeg se secate", placeholder="npr. found love in a place without hope")
    if upit:
        reci, rangirano, dodate = rangiranje.koja_je_pesma(jezicki_model, ind, upit,
                                                          termini_pesme, porodica_po_id)
        if not reci:
            st.info("Upit posle obrade nema nijednu rec (samo stop-reci), pa nema rezultata.")
        elif not rangirano:
            st.info("Nijedna pesma ne sadrzi nijednu rec upita.")
        else:
            if dodate:
                st.info(f"Ukljuceni su i rezultati za: {', '.join(dodate)}")
            ukupno = f"Pronadjeno pesama: {len(rangirano)}"
            if len(rangirano) > MAKS_REZULTATA:
                ukupno += f" · prikazano prvih {MAKS_REZULTATA}"
            st.caption(ukupno)

            for mesto, (id_pesme, ocena) in enumerate(rangirano[:MAKS_REZULTATA], start=1):
                prikaz.kartica(mesto, katalog_po_id.loc[ind.track_ids[id_pesme]], skor=ocena)
                sadrzi, nedostaje = jezicki.sadrzi_nedostaje(reci, termini_pesme(id_pesme))
                delovi = []
                if sadrzi:
                    delovi.append(f"Sadrzi: {html.escape(', '.join(sadrzi))}")
                if nedostaje:
                    delovi.append(f"<span style='color:#e0707a'>Nedostaje: "
                                  f"{html.escape(', '.join(nedostaje))}</span>")
                st.markdown(f"<div style='color:#a8a8b3; font-size:14px; margin:-4px 0 16px 50px'>"
                            f"{' · '.join(delovi)}</div>", unsafe_allow_html=True)


# --- Evaluacija --------------------------------------------------------

elif strana == "Evaluacija":
    st.title("Evaluacija pretrage")

    # Koristi: ucitaj_evaluaciju(), ucitaj_qrels(), ucitaj_tfidf(),
    #          ucitaj_bm25(), ind, df, prikaz.kartica()

    # rang-liste je napravio scripts.pripremi; ovde se nad njima samo racunaju mere,
    # jednom (za AP se prolazi kroz cele liste, pa ne sme pri svakom kliku)
    @st.cache_resource
    def izracunaj_mere():
        upiti = evaluacija.ocene_po_porodicama(ucitaj_qrels(), porodice.get)
        return upiti, evaluacija.mere_svih_upita(ucitaj_evaluaciju(), upiti, porodice.get)

    upiti_eval, mere_eval = izracunaj_mere()

    NAZIVI_KOLONA = {"P@5": "P@5", "RR": "MRR", "AP": "MAP", "nDCG@5": "nDCG@5"}
    GLAVNA_MERA = {evaluacija.BEZ_GRESKE: "MRR", evaluacija.SA_GRESKOM: "MRR",
                   evaluacija.TEMATSKI: "nDCG@5"}
    NASLOVI = {evaluacija.BEZ_GRESKE: "Upiti za jednu pesmu, bez greske",
               evaluacija.SA_GRESKOM: "Upiti za jednu pesmu, sa greskom u kucanju",
               evaluacija.TEMATSKI: "Tematski upiti"}

    st.header("Mere po grupama upita")
    for grupa in evaluacija.GRUPE:
        broj = sum(1 for p in upiti_eval.values() if evaluacija.grupa(p) == grupa)
        glavna = GLAVNA_MERA[grupa]
        st.subheader(f"{NASLOVI[grupa]} ({broj} upita)")
        proseci = evaluacija.proseci_grupe(mere_eval, upiti_eval, grupa)
        tabela = pd.DataFrame(proseci).T.rename(columns=NAZIVI_KOLONA)
        tabela.index.name = "Model"
        # najbolji model u svakoj koloni podebljan, glavna mera obojena
        stil = (tabela.style.format("{:.3f}")
                .highlight_max(axis=0, props="font-weight:bold")
                .set_properties(subset=[glavna], **{"color": "#32a852"}))
        st.table(stil)
        st.caption(f"Glavna mera za ovu grupu: {glavna}. Vrednosti su proseci preko {broj} upita.")

    # --- Pregled jednog upita ---
    st.header("Pregled upita")
    katalog_po_id = ucitaj_katalog_po_id()
    rang_liste = ucitaj_evaluaciju()

    def bez_markdown(tekst_naslova):
        # [ ] bi zatvorile :green[...] pre vremena, a * _ ` bi menjali izgled
        tekst_naslova = tekst_naslova.replace("[", "(").replace("]", ")")
        for znak in "*_`~#$\\":
            tekst_naslova = tekst_naslova.replace(znak, "\\" + znak)
        return tekst_naslova

    BOJA = {2: "green", 1: "blue", 0: "gray"}

    k1, k2 = st.columns([1, 3])
    izabrana_grupa = k1.selectbox("Grupa", evaluacija.GRUPE, format_func=lambda g: NASLOVI[g])
    upiti_grupe = sorted(u for u, p in upiti_eval.items() if evaluacija.grupa(p) == izabrana_grupa)
    upit = k2.selectbox("Upit", upiti_grupe)
    podaci = upiti_eval[upit]

    if podaci["skup"] == evaluacija.POZNATA:
        trazene = [t for t in katalog_po_id.index if porodice[t] in evaluacija.ocene_za_mere(podaci)]
        naslovi = sorted({f"{katalog_po_id.loc[t, 'track_name']} · {katalog_po_id.loc[t, 'track_artist']}"
                          for t in trazene})
        st.caption("Trazena pesma: " + "; ".join(naslovi))
    st.caption(":green[zeleno] ocena 2 · :blue[plavo] ocena 1 · :gray[sivo] ocena 0 (nije u fajlu)")

    kolone = st.columns(len(rangiranje.MODELI))
    for kolona, model in zip(kolone, rangiranje.MODELI):
        with kolona:
            st.subheader(model)
            prvih_5 = rang_liste[model][upit][:5]
            if not prvih_5:
                st.write("Model nije vratio nijednu pesmu.")
            for mesto, track_id in enumerate(prvih_5, start=1):
                red = katalog_po_id.loc[track_id]
                ocena = podaci["ocene"].get(porodice[track_id], 0)
                st.markdown(f":{BOJA[ocena]}[{mesto}. {bez_markdown(red['track_name'])}]  \n"
                            f"<span style='color:#8b8b98; font-size:13px'>"
                            f"{html.escape(red['track_artist'])}</span>", unsafe_allow_html=True)
            vrednosti = mere_eval[model][upit]
            # za jedan upit mere su RR i AP; MRR i MAP su njihovi proseci u tabelama
            st.markdown(" · ".join(f"**{ime}** {vrednost:.3f}" for ime, vrednost in vrednosti.items()))

    # --- Parametri BM25 ---
    st.header("Parametri BM25")
    parametri = ucitaj_parametre_bm25()
    izabrano_k1, izabrano_b = parametri["izabrano"]
    broj_bez_greske = sum(1 for p in upiti_eval.values()
                          if evaluacija.grupa(p) == evaluacija.BEZ_GRESKE)

    k1, k2, k3 = st.columns(3)
    k1.metric("Izabrano k1", f"{izabrano_k1:g}")
    k2.metric("Izabrano b", f"{izabrano_b:g}")
    k3.metric("MRR sa izabranim", f"{max(parametri['mrr'][izabrano_b]):.3f}")

    # jedna kolona po b, redovi su vrednosti k1 (za tabelu tacnih vrednosti ispod)
    grafik = pd.DataFrame({f"b = {b:g}": mrr for b, mrr in parametri["mrr"].items()},
                          index=pd.Index(parametri["k1"], name="k1"))
    # za grafik: jedan red po tacki (k1, b, MRR)
    tacke = pd.DataFrame([{"k1": k1_vrednost, "b": f"b = {b:g}", "MRR": vrednost}
                          for b, mrr in parametri["mrr"].items()
                          for k1_vrednost, vrednost in zip(parametri["k1"], mrr)])
    osa_x = {"field": "k1", "type": "quantitative", "title": "k1"}
    # zero: False -> y-osa prati podatke (0,74-1,0), umesto da pocinje od 0
    osa_y = {"field": "MRR", "type": "quantitative", "title": "MRR", "scale": {"zero": False}}
    opis_tacke = [{"field": "b"}, {"field": "k1"}, {"field": "MRR", "format": ".3f"}]
    izabrana = [{"filter": f"datum.k1 == {izabrano_k1} && datum.b == 'b = {izabrano_b:g}'"}]
    st.vega_lite_chart(tacke, {
        "height": 420,
        "layer": [
            # jedna linija po b, sa tackom na svakoj izmerenoj vrednosti k1
            {"mark": {"type": "line", "point": True, "strokeWidth": 2},
             "encoding": {"x": osa_x, "y": osa_y,
                          "color": {"field": "b", "type": "nominal", "title": None,
                                    "scale": {"scheme": "category10"}},
                          "tooltip": opis_tacke}},
            # izabrana tacka: krug (sa istim opisom, jer pokriva tacku ispod) i natpis
            {"transform": izabrana,
             "mark": {"type": "point", "size": 400, "filled": False, "color": "white", "strokeWidth": 2},
             "encoding": {"x": osa_x, "y": osa_y, "tooltip": opis_tacke}},
            {"transform": izabrana,
             "mark": {"type": "text", "align": "left", "dx": 16, "dy": -4, "color": "white"},
             "encoding": {"x": osa_x, "y": osa_y,
                          "text": {"value": f"izabrano: k1 = {izabrano_k1:g}, b = {izabrano_b:g}"}}},
        ],
    }, width="stretch")
    st.caption(f"MRR nad {broj_bez_greske} upita za jednu pesmu bez greske, za "
               f"{len(parametri['k1'])} vrednosti k1 i {len(parametri['b'])} vrednosti b. "
               f"Zaokruzena tacka je izabrani par. Vrednosti racuna scripts.pripremi; "
               f"izabrane k1 i b koristi strana Stihovi.")
    with st.expander("Tacne vrednosti"):
        st.table(grafik.T.style.format("{:.3f}").highlight_max(axis=None, props="font-weight:bold"))


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
