"""Import d'un lot du dictionnaire (format « v6 » : JSON avec `source`, `entries`…).

Garanties :
- Une source NOUVELLE est toujours créée avec les droits « à vérifier », quoi que dise le
  fichier : un fichier ne peut pas accorder des droits. Les entrées restent donc invisibles
  du public (visibles de l'équipe connectée, avec bandeau).
- Les entrées importées sont « documentées », jamais « validées ».
- Idempotent : une entrée déjà présente (dialecte, mot, classe, n° d'homonyme) est ignorée.
- Rien n'est supprimé ni réécrit dans le texte des définitions ; seuls des défauts
  d'extraction connus sont corrigés dans le MOT VEDETTE (voir `nettoyer`) et chaque
  correction est comptée dans les notes du lot.
"""
import hashlib
import re

from django.db import transaction

from . import liens
from .models import (
    PulaarDialect, PulaarEntry, PulaarEntryVariant, PulaarExample, PulaarImportBatch, PulaarNounClass,
    PulaarPos, PulaarSense, PulaarSource,
)
from .slug import cle_recherche, slugify_pulaar

PARSER_VERSION = "v6-nettoyage-1"
TAILLE_LOT = 500
MARQUEURS_VERBE = {"gd", "gm", "gmj"}  # gollal deereral / muumal / muumal jondiniingal (préface p. 4)
SEPARATEURS = re.compile(r"\s*[:;,]\s*")
# « Baka » + « bakaare: (ndee) edda… » : forme voisine collée au début de la définition
RE_FORME_EN_TETE = re.compile(r"^(?P<forme>[^\s:;()]+)\s*:\s*\((?P<tag>[^)\s]+)\)\s*(?P<reste>.+)$", re.S)
# « Aawdi: ( » + « ndii) ko ko aawirtee » : la parenthèse a été coupée entre le mot et la définition
RE_LEMME_PAREN = re.compile(r"^(?P<mot>[^\s:;(),]+)\s*:\s*\(\s*\)?\s*$")
RE_TAG_EN_TETE = re.compile(r"^(?P<tag>[^\s()]+)\)\s*(?P<reste>.+)$", re.S)


class ImportInvalide(ValueError):
    pass


def _tag_vers_classe(tag, item, classes):
    """Applique une étiquette de la source : classe nominale connue, ou marqueur de verbe."""
    t = tag.strip()
    if t in classes and not item.get("noun_class_marker"):
        item["noun_class_marker"] = t
    elif t.lower() in MARQUEURS_VERBE and item.get("pos_code") in (None, "a-preciser"):
        item["pos_code"] = "verbe"


def nettoyer(item, classes, stats):
    """Corrige les défauts d'extraction connus du mot vedette. Renvoie une copie.

    - mot coupé par une parenthèse (« Aawdi: ( » + « ndii) … ») ;
    - forme collée au début de la définition (« bakaare: (ndee) … ») : variante, ou, si elle
      ne fait que 1 ou 2 lettres, fin du mot coupée par le saut de ligne (« Caytugo » + « l: ») ;
    - formes multiples dans le mot vedette (« Aamde: Aamude », « Alkama,Alkamaari ») :
      première forme = mot, les autres = variantes.
    Le texte des définitions n'est modifié que pour retirer ces fragments déplacés.
    """
    it = {**item, "senses": [dict(s) for s in item.get("senses", [])], "variants": []}
    lemme = it["lemma"].strip()

    m = RE_LEMME_PAREN.match(lemme)
    if m and it["senses"]:
        t = RE_TAG_EN_TETE.match(it["senses"][0]["text"])
        if t:
            _tag_vers_classe(t["tag"], it, classes)
            it["senses"][0]["text"] = t["reste"].strip()
            lemme = m["mot"]
            stats["parenthese_recollee"] += 1

    if it["senses"]:
        f = RE_FORME_EN_TETE.match(it["senses"][0]["text"])
        if f:
            forme = f["forme"]
            _tag_vers_classe(f["tag"], it, classes)
            it["senses"][0]["text"] = f["reste"].strip()
            if len(forme) <= 2:
                lemme = lemme + forme
                stats["mot_recolle"] += 1
            else:
                it["variants"].append(forme)
                stats["forme_en_tete"] += 1

    parts = [p for p in SEPARATEURS.split(lemme) if p.strip()]
    if len(parts) > 1:
        stats["formes_multiples"] += 1
    if parts:
        lemme = parts[0].strip()
        for p in parts[1:]:
            p = p.strip()
            if p and p != lemme and p not in it["variants"]:
                it["variants"].append(p)
    it["lemma"] = lemme
    return it


def _unique(items):
    vus, res = set(), []
    for x in items:
        if x not in vus:
            vus.add(x)
            res.append(x)
    return res


def importer(data, contenu_brut, nom_fichier, utilisateur=None):
    """Importe un lot. `data` = JSON décodé, `contenu_brut` = octets du fichier (empreinte)."""
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list) or not data.get("source", {}).get("name"):
        raise ImportInvalide("Fichier inattendu : il faut un objet JSON avec « source » (nom) et « entries ».")
    empreinte = hashlib.sha256(contenu_brut).hexdigest()
    src = data["source"]
    codes_dialectes = {e.get("dialect_code") for e in data["entries"]}
    dialectes = {d.code: d for d in PulaarDialect.objects.filter(code__in=codes_dialectes)}
    manquants = sorted(c for c in codes_dialectes if c not in dialectes)
    if manquants:
        raise ImportInvalide(f"Dialecte(s) inconnu(s) dans la base : {', '.join(map(str, manquants))}.")
    classes_grammaticales = {p.code: p for p in PulaarPos.objects.all()}
    defaut_pos = classes_grammaticales.get("a-preciser")
    if defaut_pos is None:
        raise ImportInvalide("Classe grammaticale « a-preciser » absente : lancer seed_pulaar.")

    stats = {"parenthese_recollee": 0, "mot_recolle": 0, "forme_en_tete": 0, "formes_multiples": 0}
    with transaction.atomic():
        source, cree = PulaarSource.objects.get_or_create(
            name=src["name"][:200],
            defaults={
                "url": src.get("url", "")[:500], "license": src.get("license", "")[:100],
                "method": (src.get("method") or "import")[:30],
                "rights_status": PulaarSource.A_VERIFIER,  # jamais celui du fichier
                "rights_note": (src.get("rights_note", "") + " Statut des droits fixé par le site : à vérifier.").strip(),
            },
        )
        classes_nominales = {(c.dialect_id, c.marker): c for c in PulaarNounClass.objects.all()}
        marqueurs_connus = {m for (_, m) in classes_nominales} | ({
            (e.get("noun_class_marker") or "") for e in data["entries"]} - {""})
        cles_existantes = set(PulaarEntry.objects.values_list("dialect_id", "lemma", "pos_id", "homonym_index"))
        slugs = set(PulaarEntry.objects.values_list("slug", flat=True))

        lot = PulaarImportBatch.objects.create(
            source=source, file_name=nom_fichier[:255], file_sha256=empreinte, parser_version=PARSER_VERSION,
            imported_by=utilisateur if getattr(utilisateur, "is_authenticated", False) else None)
        vues_dans_fichier = set()
        crees = ignores = n_sens = n_ex = n_var = 0

        def vider(pile):
            nonlocal n_sens, n_ex, n_var
            if not pile:
                return
            entrees = PulaarEntry.objects.bulk_create([p["entree"] for p in pile])
            sens, exemples, variantes = [], [], []
            for e, p in zip(entrees, pile):
                for i, s in enumerate(p["senses"], 1):
                    sens.append(PulaarSense(entry=e, sort_order=s.get("sort_order", i), text=s["text"].strip(),
                                            text_key=cle_recherche(s["text"].strip()), source=source, source_locator=(s.get("source_locator") or "")[:100]))
                for i, x in enumerate(p["examples"], 1):
                    exemples.append(PulaarExample(
                        entry=e, sort_order=x.get("sort_order", i), sense_number=x.get("sense_number"),
                        text=x["text"].strip(), translation=(x.get("translation") or "").strip(), source=source,
                        source_locator=(x.get("source_locator") or "")[:100]))
                for i, v in enumerate(p["variants"], 1):
                    variantes.append(PulaarEntryVariant(entry=e, sort_order=i, form=v[:200], search_key=cle_recherche(v[:200])))
            PulaarSense.objects.bulk_create(sens)
            PulaarExample.objects.bulk_create(exemples)
            PulaarEntryVariant.objects.bulk_create(variantes)
            n_sens += len(sens)
            n_ex += len(exemples)
            n_var += len(variantes)

        pile = []
        for brut in data["entries"]:
            it = nettoyer(brut, marqueurs_connus, stats)
            texte_sens = [s for s in it["senses"] if (s.get("text") or "").strip()]
            if not it["lemma"] or not texte_sens:
                ignores += 1
                continue
            dialecte = dialectes[it["dialect_code"]]
            pos = classes_grammaticales.get(it.get("pos_code"), defaut_pos)
            indice = int(it.get("homonym_index") or 1)
            cle = (dialecte.id, it["lemma"], pos.id, indice)
            if cle in vues_dans_fichier:  # deux mots de la source donnent le même mot vedette : n° suivant
                while (dialecte.id, it["lemma"], pos.id, indice) in vues_dans_fichier:
                    indice += 1
                cle = (dialecte.id, it["lemma"], pos.id, indice)
            vues_dans_fichier.add(cle)
            if cle in cles_existantes:
                ignores += 1
                continue
            cles_existantes.add(cle)

            classe = None
            marqueur = it.get("noun_class_marker")
            if marqueur:
                classe = classes_nominales.get((dialecte.id, marqueur))
                if classe is None:
                    classe, _ = PulaarNounClass.objects.get_or_create(
                        dialect=dialecte, marker=marqueur[:30],
                        defaults={"note": f"Classe nominale attestée dans « {source.name} »."})
                    classes_nominales[(dialecte.id, marqueur)] = classe

            base = slugify_pulaar(it["lemma"])[:200]
            slug, i = base, 2
            while slug in slugs:
                slug, i = f"{base}-{i}", i + 1
            slugs.add(slug)

            pile.append({
                "entree": PulaarEntry(lemma=it["lemma"][:200], slug=slug, dialect=dialecte, pos=pos,
                                      homonym_index=indice, noun_class=classe, source=source,
                                      search_key=cle_recherche(it["lemma"][:200]),
                                      status=PulaarEntry.DOCUMENTE, import_batch=lot),
                "senses": texte_sens, "examples": it.get("examples", []),
                "variants": _unique(it["variants"]),
            })
            crees += 1
            if len(pile) >= TAILLE_LOT:
                vider(pile)
                pile = []
        vider(pile)

        lot.entries_created, lot.entries_skipped = crees, ignores
        lot.senses_created, lot.examples_created, lot.variants_created = n_sens, n_ex, n_var
        lot.notes = (
            f"Source créée : {'oui' if cree else 'non (déjà présente)'}. Droits : {source.get_rights_status_display()}. "
            f"Corrections du mot vedette : {stats['formes_multiples']} mot(s) à formes multiples séparés en mot + variantes ; "
            f"{stats['forme_en_tete']} forme(s) voisine(s) déplacée(s) en variante ; {stats['mot_recolle']} mot(s) "
            f"recollé(s) ; {stats['parenthese_recollee']} parenthèse(s) recollée(s). "
            "La classe grammaticale (nom / verbe / pronom) est déduite par le traitement d'extraction, pas indiquée "
            "telle quelle par la source : à relire."
        )
        lot.save()
    # Les définitions du lot (et celles des lots précédents qui citent ses mots) reçoivent leurs liens.
    liens.relier_en_retard()
    return lot


def retirer_lot(lot):
    """Supprime toutes les entrées d'un lot (sens, exemples, variantes en cascade)."""
    with liens.suspendre(), transaction.atomic():
        n, _ = PulaarEntry.objects.filter(import_batch=lot).delete()
        lot.status = PulaarImportBatch.RETIRE
        lot.save(update_fields=["status"])
    liens.relier_sens(tous=True)  # plus aucun lien vers les mots retirés
    return n
