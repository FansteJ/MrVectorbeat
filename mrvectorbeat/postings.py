# Skupovni operatori nad sortiranim listama id-jeva, algoritmom sa dva pokazivaca.
# Sve tri funkcije pretpostavljaju da su a i b strogo rastuce i vracaju strogo rastucu listu.


def presek(a, b):
    i = j = 0
    rezultat = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            rezultat.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return rezultat


def unija(a, b):
    i = j = 0
    rezultat = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            rezultat.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            rezultat.append(a[i])
            i += 1
        else:
            rezultat.append(b[j])
            j += 1
    # jedna lista je potrosena, ostatak druge ide ceo
    rezultat.extend(a[i:])
    rezultat.extend(b[j:])
    return rezultat


def razlika(a, b):
    """Elementi iz a kojih nema u b."""
    i = j = 0
    rezultat = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        elif a[i] < b[j]:
            rezultat.append(a[i])
            i += 1
        else:
            j += 1
    rezultat.extend(a[i:])
    return rezultat
