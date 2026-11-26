"""Hypertextualisation des définitions : chaque mot qui est une entrée du dictionnaire devient un lien.

Principe (résultat calculé à l'enregistrement, jamais à l'affichage) :
  1. Tokenisation Unicode qui conserve tout le reste du texte tel quel (espaces, ponctuation,
     ɓ ɗ ŋ ƴ, Adlam…) : on ne remplace que les mots reconnus.
  2. Résolution par paliers, du plus sûr au moins sûr (voir docs/PLAN_DICTIONNAIRE_PULAAR.md §7) :
       « exact »    forme identique (casse ignorée) à un lemme ou à une forme variante ;
       « approx »   (désactivé par défaut) même mot sans lettres spéciales : ƴ→y, ɓ→b… ;
       « mutation » (désactivé tant qu'aucune alternance n'est validée) initiale alternée.
     Les flexions (pluriels, conjugaisons, extensions verbales) ne sont PAS devinées : elles exigent
     des paradigmes validés qui n'existent pas encore dans la base. Voir le rapport de faisabilité.
  3. Règles : jamais de lien vers l'entrée en cours de lecture ; mots-outils et mots trop fréquents
     laissés en texte ; un lien par cible et par définition (le premier) ; homonymes : le plus
     proche (même variété, plus petit numéro) est le lien, les autres sont dans `data-alternatives`.
  4. Visibilité : une définition d'une entrée PUBLIQUE ne pointe que vers des entrées publiques ;
     une définition non publique (aperçu équipe) peut pointer vers tout ce qui n'est pas brouillon.
"""
import html
import json
import re
from collections import Counter
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction
from django.urls import reverse

from .slug import cle_recherche, forme_exacte

VERSION = "liens-v1"
LONGUEUR_MIN = 3
MAX_ALTERNATIVES = 5

_MOT = r"(?:[^\W_]|[̀-ͯ\U0001E944-\U0001E94A])+"
TOKEN_RE = re.compile(rf"{_MOT}(?:[\-'’ʼ]{_MOT})*")


_SUSPENDU = False


class suspendre:
    """`with liens.suspendre():` coupe le recalcul automatique (imports et retraits en masse) ;
    l'appelant recalcule ensuite en une fois."""

    def __enter__(self):
        global _SUSPENDU
        self._avant, _SUSPENDU = _SUSPENDU, True

    def __exit__(self, *exc):
        global _SUSPENDU
        _SUSPENDU = self._avant


def suspendu():
    return _SUSPENDU


def _reglage(nom, defaut):
    return getattr(settings, nom, defaut)


@dataclass(frozen=True)
class Cible:
    id: int
    slug: str
    lemma: str
    dialect_id: int
    homonym: int
    public: bool


@dataclass
class Index:
    formes: dict = field(default_factory=dict)            # forme exacte -> [Cible]
    approx: dict = field(default_factory=dict)            # clé sans lettres spéciales -> [Cible]
    formes_par_entree: dict = field(default_factory=dict)  # id -> {formes de l'entrée}
    exclus: set = field(default_factory=set)
    forces: set = field(default_factory=set)
    mutations: list = field(default_factory=list)         # [(a, b)] actives
    avec_approx: bool = False
    base_url: str = ""

    @classmethod
    def construire(cls, avec_approx=None):
        from .models import PulaarEntry, PulaarEntryVariant, PulaarMutation, PulaarSource, PulaarStopword
        idx = cls(avec_approx=_reglage("LIENS_APPROX", False) if avec_approx is None else avec_approx)
        idx.base_url = reverse("pulaar:terme", kwargs={"slug": "SLUGMARQUE"}).replace("SLUGMARQUE/", "")
        publiables = set(PulaarSource.PUBLIABLES)
        cibles = {}
        for i, slug, lemma, d, h, droits in (PulaarEntry.objects.exclude(status=PulaarEntry.BROUILLON)
                                             .values_list("id", "slug", "lemma", "dialect_id", "homonym_index",
                                                          "source__rights_status")):
            cibles[i] = Cible(i, slug, lemma, d, h, droits in publiables)
            idx._ajouter(cibles[i], lemma)
        for entry_id, form in PulaarEntryVariant.objects.filter(entry_id__in=list(cibles)).values_list("entry_id", "form"):
            idx._ajouter(cibles[entry_id], form)
        for s in PulaarStopword.objects.all():
            (idx.exclus if s.mode == PulaarStopword.EXCLURE else idx.forces).add(s.cle)
        idx.mutations = [(m.initiale_a.casefold(), m.initiale_b.casefold())
                         for m in PulaarMutation.objects.filter(actif=True)]
        return idx

    def _ajouter(self, cible, texte):
        f = forme_exacte(texte)
        if not f or " " in f or not re.search(r"[^\W\d_]", f):
            return  # vide, ponctuation seule ou expression à plusieurs mots : non liable mot à mot
        self.formes_par_entree.setdefault(cible.id, set()).add(f)
        liste = self.formes.setdefault(f, [])
        if cible not in liste:
            liste.append(cible)
        if self.avec_approx:
            k = cle_recherche(f)
            if k and k != f:
                self.approx.setdefault(k, [])
                if cible not in self.approx[k]:
                    self.approx[k].append(cible)

    # -- résolution ---------------------------------------------------------------------------
    def _candidats(self, f):
        """(niveau, [Cible]) pour la forme `f`, ou (None, [])."""
        if f in self.formes:
            return "exact", self.formes[f]
        for a, b in self.mutations:
            for src, dst in ((a, b), (b, a)):
                if f.startswith(src) and (dst + f[len(src):]) in self.formes:
                    trouves = self.formes[dst + f[len(src):]]
                    if len({c.lemma.casefold() for c in trouves}) == 1:  # une seule lecture possible
                        return "mutation", trouves
        if self.avec_approx:
            trouves = self.approx.get(cle_recherche(f))
            if trouves and len({forme_exacte(c.lemma) for c in trouves}) == 1:
                return "approx", trouves
        return None, []

    def resoudre(self, mot, *, entree_id, dialecte_id, propres, public_only):
        """(principal, alternatives, niveau) ou None si le mot reste en texte brut."""
        f = forme_exacte(mot)
        if f in propres or f in self.exclus:
            return None
        if len(f) < _reglage("LIENS_LONGUEUR_MIN", LONGUEUR_MIN) and f not in self.forces:
            return None
        niveau, cands = self._candidats(f)
        cands = [c for c in cands if c.id != entree_id and (c.public or not public_only)]
        if not cands:
            return None
        cands.sort(key=lambda c: (c.dialect_id != dialecte_id, c.homonym, c.id))
        return cands[0], cands[1:1 + MAX_ALTERNATIVES], niveau

    # -- rendu --------------------------------------------------------------------------------
    def lier(self, texte, *, entree_id, dialecte_id, public_only, repeter=False):
        """Retourne (html, nombre de liens). Tout ce qui n'est pas un mot reconnu est copié tel quel,
        échappé."""
        propres = self.formes_par_entree.get(entree_id, set())
        contexte = dict(entree_id=entree_id, dialecte_id=dialecte_id, propres=propres, public_only=public_only)
        deja, sortie, fin, nb = set(), [], 0, 0

        def a_lier(mot):
            r = self.resoudre(mot, **contexte)
            if r is None or (not repeter and r[0].id in deja):
                return None
            deja.add(r[0].id)
            return self._ancre(mot, *r)

        for m in TOKEN_RE.finditer(texte):
            sortie.append(html.escape(texte[fin:m.start()], quote=False))
            mot = m.group()
            rendu = a_lier(mot)
            if rendu is None and "-" in mot:  # composé : on essaie chaque morceau
                morceaux = mot.split("-")
                rendus = [a_lier(p) or html.escape(p, quote=False) for p in morceaux]
                if any(r.startswith("<a ") for r in rendus):
                    rendu = "-".join(rendus)
            if rendu is None:
                rendu = html.escape(mot, quote=False)
            else:
                nb += rendu.count("<a ")
            sortie.append(rendu)
            fin = m.end()
        sortie.append(html.escape(texte[fin:], quote=False))
        return "".join(sortie), nb

    def _ancre(self, mot, principal, alternatives, niveau):
        attrs = [f'href="{self.base_url}{principal.slug}/"', 'class="tc-lien"',
                 f'data-entry-id="{principal.id}"', f'data-match="{niveau}"']
        if alternatives:
            alt = [{"id": c.id, "slug": c.slug, "lemma": c.lemma, "url": f"{self.base_url}{c.slug}/"}
                   for c in alternatives]
            attrs.append(f'data-homonyms="{len(alternatives) + 1}"')
            attrs.append(f'data-alternatives="{html.escape(json.dumps(alt, ensure_ascii=False), quote=True)}"')
        return f'<a {" ".join(attrs)}>{html.escape(mot, quote=False)}</a>'


# -- calcul et stockage --------------------------------------------------------------------------
def _public(entree):
    from .models import PulaarEntry, PulaarSource
    return entree.status != PulaarEntry.BROUILLON and entree.source.rights_status in PulaarSource.PUBLIABLES


def _qs_sens():
    from .models import PulaarSense
    return PulaarSense.objects.select_related("entry", "entry__source").only(
        "id", "text", "text_html", "liens_version", "entry__id", "entry__dialect_id", "entry__status",
        "entry__source__rights_status")


def relier_sens(ids=None, *, index=None, simuler=False, tous=False):
    """Calcule et enregistre `text_html` pour les sens `ids` (ou tous). Retourne (sens traités, liens)."""
    from .models import PulaarSense
    index = index or Index.construire()
    qs = _qs_sens()
    if not tous:
        ids = list(ids or [])
        if not ids:
            return 0, 0
        qs = qs.filter(pk__in=ids)
    lot, traites, liens = [], 0, 0
    for s in qs.iterator(chunk_size=1000):
        s.text_html, nb = index.lier(s.text, entree_id=s.entry_id, dialecte_id=s.entry.dialect_id,
                                     public_only=_public(s.entry))
        s.liens_version = VERSION
        lot.append(s)
        traites += 1
        liens += nb
        if len(lot) >= 500 and not simuler:
            PulaarSense.objects.bulk_update(lot, ["text_html", "liens_version"])
            lot = []
    if lot and not simuler:
        PulaarSense.objects.bulk_update(lot, ["text_html", "liens_version"])
    return traites, liens


def relier_en_retard(index=None):
    """Sens jamais calculés ou calculés par une ancienne version : ce que fait le build à chaque déploiement."""
    from .models import PulaarSense
    ids = list(PulaarSense.objects.exclude(liens_version=VERSION).values_list("id", flat=True))
    return relier_sens(ids, index=index)


def sens_qui_mentionnent(cles):
    """Sens dont le texte contient une de ces clés (large : le calcul tranche) ou qui pointent déjà vers ces entrées."""
    from django.db.models import Q
    from .models import PulaarSense
    cond = Q(pk__in=[])
    for k in {c for c in cles if c}:
        cond |= Q(text_key__contains=k)
    return list(PulaarSense.objects.filter(cond).values_list("id", flat=True))


def sens_qui_pointent_vers(entree_id):
    from .models import PulaarSense
    return list(PulaarSense.objects.filter(text_html__contains=f'data-entry-id="{entree_id}"')
                .values_list("id", flat=True))


def compter_frequences():
    """Occurrences de chaque mot (forme exacte) dans toutes les définitions."""
    from .models import PulaarSense
    c = Counter()
    for texte in PulaarSense.objects.values_list("text", flat=True).iterator(chunk_size=2000):
        c.update(forme_exacte(m) for m in TOKEN_RE.findall(texte))
    return c


def actualiser_mots_outils(seuil=None, frequences=None):
    """Recrée les lignes « automatiques » : mots qui sont des entrées ET dépassent `seuil` occurrences.
    Les lignes manuelles ne sont jamais touchées ni écrasées."""
    from .models import PulaarStopword
    seuil = seuil or _reglage("LIENS_FREQUENCE_MAX", 500)
    frequences = frequences if frequences is not None else compter_frequences()
    formes = Index.construire().formes
    manuelles = set(PulaarStopword.objects.filter(origine=PulaarStopword.MANUEL).values_list("cle", flat=True))
    PulaarStopword.objects.filter(origine=PulaarStopword.AUTO).delete()
    lignes = [PulaarStopword(forme=f, cle=f, mode=PulaarStopword.EXCLURE, origine=PulaarStopword.AUTO, occurrences=n)
              for f, n in frequences.most_common() if n >= seuil and f in formes and f not in manuelles]
    PulaarStopword.objects.bulk_create(lignes)
    return len(lignes)


def recalculer_tout(seuil=None):
    """Tout refaire : fréquences → mots-outils automatiques → liens de toutes les définitions."""
    f = compter_frequences()
    n_outils = actualiser_mots_outils(seuil, f)
    traites, liens = relier_sens(tous=True)
    return {"mots_outils": n_outils, "sens": traites, "liens": liens}


def rapport_mutations(paires):
    """Mesure SANS rien écrire : pour chaque paire d'initiales (a, b), combien de mots non trouvés
    deviendraient trouvables. À montrer à un lexicographe avant d'activer quoi que ce soit."""
    idx = Index.construire()
    freq = compter_frequences()
    inconnus = {f: n for f, n in freq.items()
                if f not in idx.formes and len(f) >= LONGUEUR_MIN and f not in idx.exclus}
    res = []
    for a, b in paires:
        a, b = a.casefold(), b.casefold()
        trouves = []
        for f, n in inconnus.items():
            for src, dst in ((a, b), (b, a)):
                if f.startswith(src) and (dst + f[len(src):]) in idx.formes:
                    trouves.append((f, n, dst + f[len(src):]))
                    break
        trouves.sort(key=lambda t: -t[1])
        res.append({"paire": f"{a}:{b}", "mots": len(trouves), "occurrences": sum(t[1] for t in trouves),
                    "exemples": trouves[:8]})
    return res


def stats():
    from .models import PulaarSense
    total = PulaarSense.objects.count()
    calcules = PulaarSense.objects.filter(liens_version=VERSION).count()
    avec = PulaarSense.objects.filter(liens_version=VERSION, text_html__contains="<a ").count()
    return {"sens": total, "calcules": calcules, "avec_liens": avec}
