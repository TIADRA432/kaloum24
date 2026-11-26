"""Slugs des termes Pulaar.

Les consonnes ɓ ɗ ƴ ŋ sont de vraies lettres du pulaar, pas des accents :
une translittération ASCII naïve les SUPPRIME (« Ɗemngal » devenait
« emngal »). On les remplace donc par leur équivalent ASCII avant toute
réduction. Constaté sur un vrai terme en production avec la version Flask.
"""
import re
import unicodedata

LETTRES_AFRICAINES = {
    "ɓ": "b", "Ɓ": "b",    # b implosif
    "ɗ": "d", "Ɗ": "d",    # d implosif
    "ƴ": "y", "Ƴ": "y",    # y glottalisé
    "ŋ": "ng", "Ŋ": "ng",  # ng vélaire
    "ñ": "n", "Ñ": "n",
    "ɲ": "ny", "Ɲ": "ny",
    "ɛ": "e", "Ɛ": "e",
    "ɔ": "o", "Ɔ": "o",
    "ʼ": "", "’": "",      # coup de glotte
}


def slugify_pulaar(texte: str) -> str:
    for lettre, remplacement in LETTRES_AFRICAINES.items():
        texte = texte.replace(lettre, remplacement)
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    texte = re.sub(r"[^\w\s-]", "", texte).strip().lower()
    return re.sub(r"[\s_-]+", "-", texte) or "terme"


def slug_unique(modele, texte: str, exclude_pk=None, champ: str = "slug") -> str:
    base = slugify_pulaar(texte)
    candidat, i = base, 2
    while True:
        qs = modele.objects.filter(**{champ: candidat})
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return candidat
        candidat = f"{base}-{i}"
        i += 1


def cle_recherche(texte: str) -> str:
    """Forme de comparaison d'un mot : minuscules, sans accents, lettres africaines ramenées à
    leur équivalent ASCII (ɗ→d, ɓ→b, ŋ→ng, ƴ→y…), espaces simples. Sert à chercher un mot
    même quand le clavier ne permet pas de taper ses lettres spéciales."""
    for lettre, remplacement in LETTRES_AFRICAINES.items():
        texte = texte.replace(lettre, remplacement)
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii").lower()
    texte = re.sub(r"[^a-z0-9\s]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def forme_exacte(texte: str) -> str:
    """Forme de comparaison STRICTE d'un mot : NFC, minuscules (casefold), apostrophes unifiées.
    Contrairement à `cle_recherche`, elle conserve ɓ ɗ ŋ ƴ et les accents : « ɓe » et « be »
    restent deux mots. Sert aux liens automatiques des définitions."""
    t = unicodedata.normalize("NFC", texte).casefold()
    for a in "’ʼ‘`´":
        t = t.replace(a, "'")
    return t.strip("-' ")
