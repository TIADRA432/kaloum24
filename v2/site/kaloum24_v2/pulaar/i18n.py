"""Traductions pulaar de l'interface du dictionnaire.

RÈGLE ABSOLUE : aucune traduction inventée. Chaque terme pulaar ci-dessous
provient de la localisation fulah officielle de Firefox
(https://github.com/mozilla-l10n/firefox-l10n, locale `ff`, licence MPL 2.0),
réalisée par Ibrahima Sarr, qui travaille avec la Commission Fulfulde (FULCOM)
de l'ACALAN. La provenance de chaque entrée est indiquée pour vérification.

Les chaînes sans équivalent attesté restent EN FRANÇAIS plutôt que d'être
approximées : une interface partiellement traduite est honnête, une interface
au pulaar inventé ne l'est pas — surtout sur un dictionnaire. L'IA n'est pas
une autorité linguistique. Pour compléter : un locuteur pulaar doit fournir
et relire les chaînes manquantes.
"""

# clé : (français, pulaar ou None si non attesté, provenance)
TRADUCTIONS = {
    "chercher": ("Chercher", "Yiylo", "browser.ftl / newtab.ftl (.title, .aria-label)"),
    "langue": ("Langue", "Ɗemngal", "preferences.ftl (language-header)"),
    "choisir": ("Choisir", "Suɓo", "preferences.ftl (choose-language-description)"),
    "mot": ("Mot", "Helmere", "preferences.ftl (.label = Helmere yiylorde)"),
    "ajouter": ("Ajouter", "Ɓeydu", "newtab.ftl (newtab-topsites-add-button)"),
    "envoyer": ("Envoyer", "Neldu", "browser.ftl (.label = Neldu Jokkol e Iimeel)"),
    "ou": ("ou", "walla", "browser.ftl (.placeholder = Yiylo walla naatnu ñiiɓirde)"),
    # Aucun équivalent attesté : restent en français en attendant un locuteur.
    "dictionnaire": ("Dictionnaire", None, None),
    "definition": ("Définition", None, None),
    "domaine": ("Domaine", None, None),
    "proposer_un_mot": ("Proposer un mot", None, None),
    "tous_les_termes": ("Tous les termes", None, None),
    "documente": ("Documenté", None, None),
    "valide": ("Validé", None, None),
    "source": ("Source", None, None),
}

LANGUES = ("fr", "ff")


def traduire(cle: str, langue: str = "fr") -> str:
    entree = TRADUCTIONS.get(cle)
    if not entree:
        return cle
    fr, ff, _ = entree
    return ff if (langue == "ff" and ff) else fr


def couverture() -> tuple[int, int]:
    """(chaînes traduites, total) — affiché pour ne pas laisser croire à une
    traduction complète."""
    traduites = sum(1 for _, ff, _ in TRADUCTIONS.values() if ff)
    return traduites, len(TRADUCTIONS)
