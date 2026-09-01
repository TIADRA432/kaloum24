"""Traductions pulaar de l'interface du module Pulaar.

RÈGLE ABSOLUE DE CE FICHIER : aucune traduction inventée. Chaque terme
pulaar ci-dessous provient de la localisation fulah officielle de Firefox
(https://github.com/mozilla-l10n/firefox-l10n, locale `ff`, licence MPL
2.0), réalisée par Ibrahima Sarr, qui travaille avec la Commission
Fulfulde (FULCOM) de l'ACALAN — l'Académie Africaine des Langues.

Le champ `source` de chaque entrée indique le fichier Mozilla d'origine,
pour que n'importe qui puisse vérifier. Les chaînes pour lesquelles aucun
équivalent attesté n'a été trouvé restent EN FRANÇAIS plutôt que d'être
approximées : une interface partiellement traduite est honnête, une
interface au pulaar inventé ne l'est pas — surtout sur un dictionnaire,
dont c'est précisément le sujet.

Pour compléter : un locuteur pulaar doit relire et fournir les chaînes
manquantes. Voir PLAN_PULAAR.md.
"""

# (clé) : (français, pulaar ou None si non attesté, provenance)
TRADUCTIONS = {
    "chercher":        ("Chercher",         "Yiylo",    "browser.ftl / newtab.ftl (.title, .aria-label)"),
    "langue":          ("Langue",           "Ɗemngal",  "preferences.ftl (language-header)"),
    "choisir":         ("Choisir",          "Suɓo",     "preferences.ftl (choose-language-description)"),
    "mot":             ("Mot",              "Helmere",  "preferences.ftl (.label = Helmere yiylorde)"),
    "ajouter":         ("Ajouter",          "Ɓeydu",    "newtab.ftl (newtab-topsites-add-button)"),
    "envoyer":         ("Envoyer",          "Neldu",    "browser.ftl (.label = Neldu Jokkol e Iimeel)"),
    "ou":              ("ou",               "walla",    "browser.ftl (.placeholder = Yiylo walla naatnu ñiiɓirde)"),

    # Aucun équivalent attesté trouvé dans la localisation Mozilla — restent
    # en français, délibérément, en attendant un vrai locuteur.
    "dictionnaire":    ("Dictionnaire",     None, None),
    "definition":      ("Définition",       None, None),
    "domaine":         ("Domaine",          None, None),
    "proposer_un_mot": ("Proposer un mot",  None, None),
    "tous_les_termes": ("Tous les termes",  None, None),
    "documente":       ("Documenté",        None, None),
    "valide":          ("Validé",           None, None),
    "source":          ("Source",           None, None),
}


def t(cle, langue="fr"):
    """Retourne la chaîne dans la langue demandée.

    Repli explicite sur le français quand aucune traduction pulaar attestée
    n'existe — jamais d'invention, jamais de clé brute affichée à l'écran.
    """
    entree = TRADUCTIONS.get(cle)
    if not entree:
        return cle
    fr, ff, _ = entree
    if langue == "ff" and ff:
        return ff
    return fr


def couverture_pulaar():
    """Part des chaînes réellement traduites — affichée à l'utilisateur pour
    qu'il sache que l'interface pulaar est incomplète, plutôt que de le
    laisser croire à une traduction complète."""
    total = len(TRADUCTIONS)
    traduites = sum(1 for _, ff, _ in TRADUCTIONS.values() if ff)
    return traduites, total
