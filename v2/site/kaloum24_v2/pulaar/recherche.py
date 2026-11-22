"""Recherche du dictionnaire : résultats classés, tolérants au clavier.

Ordre (le premier rang où un mot est trouvé est conservé) :
1 mot exact · 2 mot qui commence par la saisie · 3 mot qui la contient ·
4 forme variante · 5 texte d'une définition · 6 traduction.
Les rangs 5 et 6 fouillent des textes libres : on les écarte pour une saisie très courte
(sinon « a » ramènerait tout le dictionnaire).
"""
from .slug import cle_recherche

RAISONS = {
    1: "mot exact",
    2: "commence par",
    3: "contient",
    4: "forme variante",
    5: "dans une définition",
    6: "dans une traduction",
}
PLAFOND_TEXTE = 300  # au plus 300 entrées par rang de recherche plein texte


def chercher(base, q):
    """Renvoie [(id, rang)] sans doublon, dans l'ordre d'affichage. `base` : queryset d'entrées visibles."""
    k = cle_recherche(q)
    if not k:
        return []
    vus, ordre = set(), []

    def ajouter(qs, rang, plafond=None, tri="search_key"):
        ids = qs.order_by(tri, "homonym_index").values_list("id", flat=True).distinct()
        for i in (ids[:plafond] if plafond else ids):
            if i not in vus:
                vus.add(i)
                ordre.append((i, rang))

    ajouter(base.filter(search_key=k), 1)
    ajouter(base.filter(search_key__startswith=k).exclude(search_key=k), 2)
    if len(k) >= 2:
        ajouter(base.filter(search_key__contains=k), 3)
        ajouter(base.filter(variants__search_key__contains=k), 4)
        ajouter(base.filter(translations__term__icontains=q), 6, PLAFOND_TEXTE)
    if len(k) >= 3:
        ajouter(base.filter(senses__text_key__contains=k), 5, PLAFOND_TEXTE)
    # les rangs 5 et 6 sont ajoutés dans cet ordre mais affichés selon leur rang
    ordre.sort(key=lambda t: t[1])  # tri stable : l'ordre alphabétique de chaque rang est conservé
    return ordre
