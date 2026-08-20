"""Peuple la base avec des catégories, un compte admin et des articles d'exemple.

Usage : flask seed-db   (voir README)
"""
from datetime import datetime, timedelta

from extensions import db
from models import User, Category, Article, Comment
from utils import slugify, text_to_paragraphs

CATEGORIES = ["Politique", "Économie", "Société", "Sport", "Culture", "Afrique", "Technologie"]

DEMO_ARTICLES = [
    {
        "title": "Le nouveau port en eau profonde entre en phase de test",
        "summary": "Les autorités portuaires annoncent le début des essais techniques avant une mise en service prévue pour la fin de l'année.",
        "content": (
            "Après plusieurs années de travaux, les installations du nouveau terminal "
            "entament leur phase de test grandeur nature. Les premiers navires-tests "
            "sont attendus dans les prochaines semaines.\n\n"
            "Selon les responsables du projet, cette étape doit permettre de valider "
            "les capacités de manutention avant l'ouverture officielle. Les opérateurs "
            "économiques locaux suivent le dossier de près, la nouvelle infrastructure "
            "devant réduire sensiblement les délais de dédouanement."
        ),
        "category": "Économie",
        "premium": False,
    },
    {
        "title": "Championnat national : coup d'envoi de la nouvelle saison ce week-end",
        "summary": "Seize clubs s'affrontent dès samedi pour la première journée d'un championnat annoncé comme le plus disputé depuis dix ans.",
        "content": (
            "La fédération a dévoilé le calendrier complet de la saison. Les rencontres "
            "phares de cette première journée opposeront les trois derniers champions.\n\n"
            "Plusieurs recrues attirent déjà l'attention des observateurs, dans un "
            "mercato marqué par le retour de plusieurs joueurs formés localement."
        ),
        "category": "Sport",
        "premium": False,
    },
    {
        "title": "Analyse : ce que change la réforme du Code des investissements",
        "summary": "Décryptage complet des nouvelles dispositions et de leurs conséquences pour les porteurs de projets, réservé aux abonnés.",
        "content": (
            "Le texte adopté modifie substantiellement les conditions d'exonération "
            "fiscale pour les nouveaux investisseurs. Notre rédaction a comparé "
            "l'ancien et le nouveau régime, article par article.\n\n"
            "Plusieurs juristes contactés estiment que la réforme devrait accélérer "
            "l'instruction des dossiers, jusqu'ici jugée trop lente par les "
            "chambres consulaires."
        ),
        "category": "Économie",
        "premium": True,
    },
    {
        "title": "Festival culturel : la programmation complète dévoilée",
        "summary": "Musique, cinéma et arts visuels au programme d'un événement qui prend de l'ampleur d'année en année.",
        "content": (
            "Les organisateurs ont présenté ce mardi le programme détaillé, avec "
            "une trentaine d'artistes attendus sur plusieurs scènes.\n\n"
            "La billetterie ouvre dès la semaine prochaine, avec un tarif préférentiel "
            "pour les étudiants."
        ),
        "category": "Culture",
        "premium": False,
    },
    {
        "title": "Startups : un nouveau fonds régional pour le numérique",
        "summary": "Doté de plusieurs millions de dollars, le fonds vise à soutenir une trentaine de jeunes entreprises technologiques.",
        "content": (
            "L'initiative régionale ambitionne de combler un manque de financement "
            "identifié par plusieurs incubateurs locaux.\n\n"
            "Les candidatures seront examinées par un comité mixte associant "
            "investisseurs privés et institutions publiques."
        ),
        "category": "Technologie",
        "premium": False,
    },
    {
        "title": "Sommet régional : les chefs d'État attendus la semaine prochaine",
        "summary": "La coopération énergétique transfrontalière figure en tête de l'ordre du jour de cette rencontre au sommet.",
        "content": (
            "Les préparatifs s'intensifient à l'approche de ce sommet qui réunira "
            "plusieurs chefs d'État de la sous-région.\n\n"
            "Les discussions porteront notamment sur l'interconnexion des réseaux "
            "électriques, un dossier suivi de près par les bailleurs internationaux."
        ),
        "category": "Afrique",
        "premium": False,
    },
    {
        "title": "Assemblée : le budget rectificatif adopté après huit heures de débats",
        "summary": "Les députés ont validé le texte à une large majorité, malgré des réserves sur le volet des dépenses courantes.",
        "content": (
            "La séance s'est achevée tard dans la nuit. Le rapporteur de la commission "
            "des finances a défendu un texte qu'il qualifie de « rigoureux ».\n\n"
            "Plusieurs élus de l'opposition ont regretté un calendrier d'examen trop "
            "resserré, jugeant impossible un travail de fond sur les annexes."
        ),
        "category": "Politique",
        "premium": False,
    },
    {
        "title": "Enseignement : la rentrée décalée d'une semaine dans trois régions",
        "summary": "Le ministère invoque des travaux de réhabilitation non achevés dans plusieurs établissements.",
        "content": (
            "La décision, annoncée mardi, concerne les établissements publics du "
            "primaire et du secondaire dans trois régions.\n\n"
            "Les syndicats d'enseignants demandent des garanties sur le rattrapage "
            "des heures perdues d'ici la fin du premier trimestre."
        ),
        "category": "Société",
        "premium": False,
    },
    {
        "title": "Fibre optique : le déploiement atteint quinze nouvelles communes",
        "summary": "L'opérateur historique annonce l'extension de son réseau, avec une mise en service progressive d'ici décembre.",
        "content": (
            "Le chantier, entamé il y a dix-huit mois, entre dans sa phase finale "
            "pour un premier lot de communes.\n\n"
            "Les tarifs de raccordement n'ont pas encore été communiqués, ce que "
            "regrettent plusieurs associations d'usagers."
        ),
        "category": "Technologie",
        "premium": False,
    },
    {
        "title": "Enquête : dans les coulisses du marché informel des devises",
        "summary": "Six semaines d'immersion auprès des changeurs de rue, de leurs clients et des autorités monétaires. Réservé aux abonnés.",
        "content": (
            "Chaque matin, le même ballet reprend aux abords du grand marché. "
            "Notre équipe a suivi pendant six semaines les circuits parallèles.\n\n"
            "Les écarts de taux avec le marché officiel se sont creusés, alimentant "
            "une économie de l'ombre que les autorités peinent à endiguer.\n\n"
            "Plusieurs opérateurs interrogés décrivent un système structuré, avec "
            "ses propres règles et ses hiérarchies."
        ),
        "category": "Économie",
        "premium": True,
    },
    {
        "title": "Athlétisme : deux records nationaux battus en une soirée",
        "summary": "Le meeting international a tenu ses promesses, avec des performances qui rapprochent deux athlètes des minima mondiaux.",
        "content": (
            "Le stade était comble pour cette soirée qui restera dans les annales "
            "de l'athlétisme national.\n\n"
            "Les deux performances doivent encore être homologuées par la "
            "fédération internationale."
        ),
        "category": "Sport",
        "premium": False,
    },
    {
        "title": "Cinéma : trois longs métrages nationaux sélectionnés à l'international",
        "summary": "Une reconnaissance inédite pour une production locale en pleine structuration.",
        "content": (
            "Les trois films retenus seront projetés en compétition officielle "
            "dans les prochaines semaines.\n\n"
            "Les réalisateurs saluent le rôle du fonds d'appui créé il y a trois ans, "
            "tout en appelant à en élargir la dotation."
        ),
        "category": "Culture",
        "premium": False,
    },
]


def run_seed():
    db.create_all()

    cat_objs = {}
    for name in CATEGORIES:
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            cat = Category(name=name, slug=slugify(name))
            db.session.add(cat)
        cat_objs[name] = cat
    db.session.commit()

    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@kaloum24.example", role="admin")
        admin.set_password("ChangeMoi123!")
        db.session.add(admin)

    lecteur = User.query.filter_by(username="lecteur").first()
    if not lecteur:
        lecteur = User(username="lecteur", email="lecteur@kaloum24.example", role="user")
        lecteur.set_password("Lecteur123!")
        db.session.add(lecteur)
    db.session.commit()

    for i, data in enumerate(DEMO_ARTICLES):
        if Article.query.filter_by(title=data["title"]).first():
            continue
        slug = slugify(data["title"])
        article = Article(
            title=data["title"],
            slug=slug,
            summary=data["summary"],
            content=text_to_paragraphs(data["content"]),
            category_id=cat_objs[data["category"]].id,
            author_id=admin.id,
            is_premium=data["premium"],
            status="publie",
            is_featured=(i == 0),
            views=(len(DEMO_ARTICLES) - i) * 137,
            created_at=datetime.utcnow() - timedelta(hours=i * 5),
        )
        db.session.add(article)
    db.session.commit()

    first_article = Article.query.order_by(Article.created_at.desc()).first()
    if first_article and not first_article.comments:
        db.session.add(
            Comment(
                content="Enfin une bonne nouvelle pour le secteur !",
                status="approuve",
                article_id=first_article.id,
                user_id=lecteur.id,
            )
        )
        db.session.add(
            Comment(
                content="Merci pour l'article, très clair.",
                status="en_attente",
                article_id=first_article.id,
                user_id=lecteur.id,
            )
        )
        db.session.commit()

    print("Comptes de démo : admin/ChangeMoi123!  et  lecteur/Lecteur123!")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run_seed()
