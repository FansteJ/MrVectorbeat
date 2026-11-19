# scripts/pripremi.py
#
# SABLON. Skripta koja JEDNOM gradi sve modele i cuva ih u artifacts/,
# pre pokretanja aplikacije - app.py posle samo ucitava gotove fajlove.
#
# Pokretanje iz korena projekta:
#   python -m scripts.pripremi
#
# Poziva funkcije napravi_X() iz mrvectorbeat/pipeline.py. Dok su one
# prazne, skripta prolazi bez greske, ali nista ne gradi. Kad napisete
# neku funkciju, ispod njenog poziva dodajte ispis (sta je napravljeno,
# koliko cega) - tako odmah vidite da li radi.
#
# VAZNO: ovo nije fiksno - koraci i funkcije su samo PREDLOG, menjajte
# ih kako vam odgovara. Redosled je ipak bitan: kasniji koraci koriste
# ono sto su napravili raniji (indeks se gradi iz tokena, TF-IDF i BM25
# iz indeksa...).

from mrvectorbeat import pipeline

# Katalog
kat = pipeline.napravi_katalog()
print(f"Katalog: {len(kat)} pesama, {kat['porodica'].nunique()} porodica")

# Tokeni
tok = pipeline.napravi_tokene()
print(f"Tokeni: {sum(len(t) for t in tok.values())} termina, "
      f"{len({t for ts in tok.values() for t in ts})} razlicitih")

# Trie
obicno, obrnuto = pipeline.napravi_trie()
print(f"Trie: {obicno.broj_cvorova} cvorova (obicno), {obrnuto.broj_cvorova} (obrnuto)")

# K-gramski indeks
kg = pipeline.napravi_kgram()
print(f"K-gramski indeks: {len(kg.imena)} imena, {len(kg.postings)} k-grama")

# Invertovani indeks
ind = pipeline.napravi_indeks()
print(f"Invertovani indeks: {len(ind.postings)} termina, {len(ind.track_ids)} pesama")

# TF-IDF model
tfidf = pipeline.napravi_tfidf()
print(f"TF-IDF model: idf za {len(tfidf.idf)} termina, duzine vektora za {tfidf.broj_pesama} pesama")

# BM25 i evaluacija
bm25 = pipeline.napravi_bm25()
print(f"BM25 model: prosecna duzina pesme {bm25.prosecna_duzina:.1f} termina")
parametri = pipeline.napravi_parametre_bm25()
k1, b = parametri["izabrano"]
print(f"BM25 parametri: k1={k1}, b={b} (MRR {max(parametri['mrr'][b]):.3f}, "
      f"{len(parametri['k1'])} x {len(parametri['b'])} kombinacija)")
# rang-liste za evaluaciju se prave tek posle izbora k1 i b
rang_liste = pipeline.napravi_evaluaciju()
print(f"Evaluacija: rang-liste za {len(next(iter(rang_liste.values())))} upita kroz {len(rang_liste)} modela")

# Jezicki model
pipeline.napravi_jezicki()

# PageRank nad grafom izvodjaca
# Vas crawler pravi graf izvodjaca - pokrenite ga pre ovog koraka.
pipeline.napravi_rangove()

# k-d stablo
pipeline.napravi_kdrvo()

# Semanticki model
pipeline.napravi_semantiku()

# RAG korpus
pipeline.napravi_rag_korpus()

# Hibridna pretraga
pipeline.napravi_hibrid_evaluaciju()

# Autoplay
pipeline.napravi_autoplay()

print("Priprema: gotovo")
