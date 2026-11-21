"""Textes de départ des pages « cadre » (S0) : charte, mentions légales, à propos.

Ce sont des BROUILLONS non publiés. Aucun fait n'est inventé : tout ce qui relève
du statut légal, des personnes ou des adresses est marqué « [À COMPLÉTER] ».
Ils sont créés une seule fois ; l'équipe les modifie ensuite dans l'administration.
"""

A_COMPLETER = "[À COMPLÉTER"


def _p(texte):
    return {"type": "paragraph", "value": f"<p>{texte}</p>"}


def _ul(items):
    return {"type": "paragraph", "value": "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"}


def _section(titre, *contenus):
    return {"type": "section", "value": {"heading": titre, "content": list(contenus)}}


PAGES = [
    {
        "slug": "charte-editoriale",
        "title": "Charte éditoriale",
        "introduction": "Brouillon à faire valider par le directeur de publication et par un juriste avant publication.",
        "body": [
            _section(
                "Notre mission",
                _p("Informer sur la Guinée et l'Afrique de l'Ouest, en français d'abord, et donner leur place "
                   "aux langues du pays, à commencer par le Pulaar."),
            ),
            _section(
                "Exactitude et sources",
                _p("Chaque information est vérifiée avant publication. Les sources sont citées chaque fois que "
                   "c'est possible. Nous distinguons les faits, les analyses et les opinions."),
            ),
            _section(
                "Étiquettes de contenu",
                _ul([
                    "<b>Rédaction</b> : article écrit et relu par l'équipe de Kaloum24.",
                    "<b>Tribune / Opinion</b> : le point de vue de son auteur, qui n'engage pas la rédaction.",
                    "<b>Contribution</b> : texte proposé par une personne extérieure, relu avant publication.",
                    "<b>Décryptage</b> : explication d'un sujet, avec ses sources.",
                ]),
            ),
            _section(
                "Corrections et droit de réponse",
                _p("Toute erreur constatée est corrigée et la correction est signalée en tête de l'article. "
                   "Toute personne mise en cause peut demander un droit de réponse. "
                   "[À COMPLÉTER : adresse de contact, délai de traitement.]"),
            ),
            _section(
                "Contributions extérieures",
                _p("Aucune contribution n'est publiée directement : elle est relue par un relecteur de la rédaction, "
                   "qui peut la modifier avec l'auteur ou la refuser. L'auteur reste responsable de son texte."),
            ),
            _section(
                "Langues locales",
                _p("Les textes en Pulaar et dans les autres langues du pays sont fournis ou validés par des "
                   "locuteurs. Aucune traduction automatique n'est présentée comme fiable : un texte produit par "
                   "une intelligence artificielle n'a pas valeur d'autorité linguistique."),
            ),
            _section(
                "Ce que nous ne publions pas",
                _ul([
                    "les propos diffamatoires ou injurieux ;",
                    "les appels à la haine ou à la violence ;",
                    "les atteintes à la vie privée ;",
                    "les informations dont l'origine n'est pas identifiable.",
                ]),
            ),
            _section(
                "Données personnelles",
                _p("Nous collectons le minimum nécessaire. [À COMPLÉTER : finalités, durée de conservation, "
                   "droits des personnes, contact, au regard de la loi L/2016/037/AN.]"),
            ),
        ],
    },
    {
        "slug": "mentions-legales",
        "title": "Mentions légales",
        "introduction": "Brouillon : les champs marqués « À COMPLÉTER » doivent être renseignés par l'éditeur avant publication.",
        "body": [
            _section(
                "Éditeur du site",
                _p("Kaloum24. [À COMPLÉTER : nom ou raison sociale, statut juridique, adresse à Conakry.]"),
            ),
            _section(
                "Directeur de la publication",
                _p("[À COMPLÉTER : nom du directeur de la publication.]"),
            ),
            _section(
                "Contact",
                _p("[À COMPLÉTER : adresse électronique et téléphone de la rédaction.]"),
            ),
            _section(
                "Déclaration auprès des autorités",
                _p("[À COMPLÉTER : situation du site au regard de la déclaration auprès du procureur et de la "
                   "Haute Autorité de la Communication.]"),
            ),
            _section(
                "Hébergement",
                _p("Application hébergée par Render ; base de données et fichiers médias hébergés par Supabase. "
                   "[À COMPLÉTER : coordonnées légales des hébergeurs.]"),
            ),
            _section(
                "Propriété intellectuelle",
                _p("[À COMPLÉTER : conditions de reproduction des contenus, licences éventuelles.]"),
            ),
            _section(
                "Données personnelles",
                _p("Voir la charte éditoriale. [À COMPLÉTER : responsable du traitement et procédure d'exercice des droits.]"),
            ),
        ],
    },
    {
        "slug": "a-propos",
        "title": "À propos",
        "introduction": "L'actualité de Guinée et d'Afrique de l'Ouest, rédigée à Conakry.",
        "body": [
            _section(
                "Qui sommes-nous ?",
                _p("[À COMPLÉTER : présentation de l'équipe et de l'histoire de Kaloum24, rédigée par ses responsables.]"),
            ),
            _section(
                "Nous contacter",
                _p("[À COMPLÉTER : coordonnées, proposition d'article, signalement d'une erreur.]"),
            ),
        ],
    },
]
