"""Configuration des sources d'agrégation retenues.

Chaque source listée ici a été vérifiée avant intégration :
- présence d'un flux RSS/Atom public ;
- robots.txt ne l'interdit pas ;
- toutes créées INACTIVES par défaut malgré compliance_checked=True : le
  premier admin qui se connecte décide consciemment quand démarrer la
  collecte, plutôt que de la trouver déjà en marche.

Usage : flask seed-sources
"""
from datetime import datetime

from extensions import db
from models import Source

# (nom, site, flux, pays, confiance, fréquence en minutes)
SOURCES = [
    ("GuinéeNews", "https://guineenews.org", "https://guineenews.org/feed/",
     "Guinée", 75, 20),
    ("Africaguinée", "https://www.africaguinee.com", "https://www.africaguinee.com/feed/",
     "Guinée", 75, 20),
    ("Seneweb", "https://seneweb.com", "https://seneweb.com/feed/",
     "Sénégal", 70, 30),
    ("Dakaractu", "https://dakaractu.com", "https://dakaractu.com/xml/syndication.rss",
     "Sénégal", 70, 30),
    ("Le Soleil", "https://lesoleil.sn", "https://lesoleil.sn/feed/",
     "Sénégal", 75, 60),
    ("LeFaso.net", "https://lefaso.net", "https://lefaso.net/spip.php?page=backend",
     "Burkina Faso", 70, 60),
    # Fraternité Matin (fratmat.info) volontairement absente : son flux RSS
    # semblait valide lors de la vérification initiale (réponse contenant
    # "xml"), mais /rss, /feed/ et les variantes usuelles renvoient en
    # réalité une page HTML ou une 404 — vérifié via feed_client.fetch_feed(),
    # qui a levé ErreurFlux. Le site utilise un CMS maison (pas
    # WordPress/SPIP) sans URL de flux standard détectable.
    ("Malijet", "https://malijet.com", "https://malijet.com/feed/",
     "Mali", 65, 60),
    ("Togo First", "https://togofirst.com", "https://togofirst.com/?feed=rss2",
     "Togo", 65, 60),
    ("Bénin Web TV", "https://beninwebtv.bj", "https://beninwebtv.bj/feed/",
     "Bénin", 65, 60),
    ("Alwihda Info", "https://alwihdainfo.com", "https://alwihdainfo.com/feed/",
     "Tchad", 65, 90),
    ("WakatSéra", "https://wakatsera.com", "https://wakatsera.com/feed/",
     "Burkina Faso", 65, 90),
    ("Jeune Afrique", "https://jeuneafrique.com", "https://jeuneafrique.com/feed/",
     "Panafricain", 85, 60),
]

# Sources gouvernementales/institutionnelles vérifiées séparément : les
# portails officiels guinéens eux-mêmes (presidence.gov.gn, gouvernement.gov.gn,
# sgg.gov.gn, app.gov.gn) sont tous protégés par une vérification anti-robot
# (en-tête « sg-captcha: challenge », HTTP 202 systématique) — inutilisables
# pour une collecte automatisée, quel que soit le flux qu'ils proposeraient.
# Ces trois-là sont librement accessibles, robots.txt vérifié, aucune
# restriction. La Guinée est membre de la CEDEAO et de l'UA ; les
# communiqués OMS couvrent régulièrement des sujets de santé publique
# pertinents pour la sous-région.
#
# (nom, site, flux, pays, confiance, fréquence, offre_integral)
SOURCES_INSTITUTIONNELLES = [
    ("CEDEAO", "https://ecowas.int", "https://ecowas.int/feed/",
     "Régional (CEDEAO)", 85, 120, True),
    ("Union Africaine", "https://au.int", "https://au.int/en/rss.xml",
     "Continental (UA)", 85, 120, False),
    ("OMS", "https://who.int", "https://who.int/rss-feeds/news-english.xml",
     "International (ONU)", 90, 120, True),
]

# Justifications proposées pour le mode intégral — jamais appliquées
# automatiquement (content_mode reste "extrait" pour tout le monde à la
# création, voir plus bas). C'est à l'admin de les relire, les éditer si
# besoin, et de cocher lui-même le mode intégral depuis Sources → Modifier :
# la décision doit rester consciente, pas héritée d'un script.
JUSTIFICATIONS_SUGGEREES = {
    "CEDEAO": (
        "Communiqués officiels d'une organisation intergouvernementale "
        "régionale (dont la Guinée est un État membre), publiés pour "
        "diffusion large par la presse — pratique standard de "
        "communication institutionnelle. À confirmer/adapter avant "
        "d'activer le mode intégral."
    ),
    "OMS": (
        "Communiqués de presse d'une agence spécialisée des Nations Unies, "
        "publiés pour reprise large par les médias — pratique standard des "
        "agences onusiennes. À confirmer/adapter avant d'activer le mode "
        "intégral."
    ),
}


def run_seed_sources():
    db.create_all()
    total = 0

    for nom, site, flux, pays, confiance, frequence in SOURCES:
        if Source.query.filter_by(name=nom).first():
            continue
        db.session.add(Source(
            name=nom, site_url=site, feed_url=flux, country=pays,
            trust_level=confiance, fetch_frequency_minutes=frequence,
            source_category="media", content_mode="extrait",
            compliance_checked=True,
            compliance_notes=(
                "robots.txt vérifié : aucune restriction sur le flux, pas "
                "de crawl-delay. Voir PLAN_AGREGATEUR.md."
            ),
            is_active=False,   # activation = décision explicite d'un admin
        ))
        total += 1

    for nom, site, flux, pays, confiance, frequence, offre_integral in SOURCES_INSTITUTIONNELLES:
        if Source.query.filter_by(name=nom).first():
            continue
        notes = (
            "robots.txt vérifié : aucune restriction sur le flux. Source "
            "gouvernementale/institutionnelle."
        )
        if offre_integral:
            notes += (
                " Ce flux fournit du contenu intégral (champ content:encoded) "
                "— mode intégral NON activé par défaut : voir "
                "JUSTIFICATIONS_SUGGEREES dans ce fichier pour un texte de "
                "départ, à confirmer depuis Sources → Modifier avant "
                "d'activer content_mode=intégral."
            )
        db.session.add(Source(
            name=nom, site_url=site, feed_url=flux, country=pays,
            trust_level=confiance, fetch_frequency_minutes=frequence,
            source_category="institutionnel", content_mode="extrait",
            compliance_checked=True,
            compliance_notes=notes,
            is_active=False,
        ))
        total += 1

    db.session.commit()
    print(f"{total} source(s) vérifiée(s) — aucune activée automatiquement, "
         "toutes en mode extrait par défaut.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run_seed_sources()
