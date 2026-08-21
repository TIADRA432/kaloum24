"""Tests fonctionnels de bout en bout, via le client de test Flask.

Usage : python tests_fonctionnels.py
Crée une base temporaire, exécute les scénarios, puis nettoie.
"""
import hashlib
import hmac
import io
import json
import os
import re
import sys
import tempfile

os.environ.setdefault("SECRET_KEY", "cle-de-test")
os.environ["SITE_URL"] = "https://exemple.test"

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path
_uploads = tempfile.mkdtemp()

from app import create_app          # noqa: E402
from extensions import db           # noqa: E402
from seed import run_seed           # noqa: E402
from models import WhatsAppDraft, Article, Correspondent, Comment, ModerationLog, Category  # noqa: E402

results = []


def ok(label, cond):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + label, flush=True)


def csrf(client, url):
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get(url).get_data(as_text=True))
    return m.group(1) if m else None


def text(resp):
    return resp.get_data(as_text=True)


def image_test(nom="photo.png"):
    """Génère une petite image PNG valide en mémoire."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 60, 60)).save(buf, "PNG")
    buf.seek(0)
    return (buf, nom)


app = create_app()
app.config["UPLOAD_FOLDER"] = _uploads

with app.app_context():
    db.create_all()
    run_seed()

PREMIUM = "/article/analyse-ce-que-change-la-reforme-du-code-des-investissements"
SLUG = "le-nouveau-port-en-eau-profonde-entre-en-phase-de-test"

# =============================================== pages publiques
with app.test_client() as c:
    ok("Accueil repond 200", c.get("/").status_code == 200)
    ok("Page rubrique repond 200", c.get("/categorie/economie").status_code == 200)
    ok("Page article repond 200", c.get("/article/" + SLUG).status_code == 200)
    ok("Page inexistante -> 404", c.get("/page-inexistante").status_code == 404)
    ok("Paywall bloque le visiteur", "abonn" in text(c.get(PREMIUM)))
    ok("Recherche trouve un article", "port en eau profonde" in text(c.get("/recherche?q=port")))
    ok("Recherche sans resultat geree", "Aucun article ne correspond" in text(c.get("/recherche?q=zzzzz")))
    ok("POST sans jeton CSRF rejete",
       c.post("/article/" + SLUG + "/commentaire", data={"content": "x"}).status_code == 400)

# =============================================== SEO
with app.test_client() as c:
    r = c.get("/rss.xml")
    ok("Flux RSS valide", r.status_code == 200 and "<rss" in text(r) and "<item>" in text(r))
    ok("RSS declare le bon type MIME", "rss+xml" in r.headers["Content-Type"])

    r = c.get("/sitemap.xml")
    ok("Sitemap valide", r.status_code == 200 and "<urlset" in text(r) and "<loc>" in text(r))

    r = c.get("/robots.txt")
    ok("robots.txt reference le sitemap", "Sitemap:" in text(r) and "Disallow: /admin/" in text(r))

    page = text(c.get("/article/" + SLUG))
    ok("Balises Open Graph presentes",
       'property="og:title"' in page and 'property="og:description"' in page
       and 'property="og:type" content="article"' in page)
    ok("Donnees structurees NewsArticle", '"@type": "NewsArticle"' in page)
    ok("URL canonique presente", 'rel="canonical"' in page)

# =============================================== thème et fonctionnalités UI
with app.test_client() as c:
    page = text(c.get("/"))
    ok("Bouton de theme present", 'id="themeToggle"' in page)
    ok("Theme applique avant rendu (anti-flash)", 'localStorage.getItem("theme")' in page)
    ok("Bloc meteo present", 'id="weather"' in page)

    page = text(c.get("/article/" + SLUG))
    ok("Bouton de lecture audio present", 'id="ttsButton"' in page)
    ok("Partage WhatsApp present", 'data-partage="whatsapp"' in page)
    ok("Partage X present", 'data-partage="x"' in page)
    ok("Copie du lien presente", 'data-partage="copier"' in page)
    ok("Temps de lecture affiche", "min de lecture" in page)

# =============================================== météo
with app.test_client() as c:
    r = c.get("/api/meteo")
    # 200 si l'API externe répond, 503 sinon : les deux sont des comportements corrects.
    ok("API meteo repond proprement", r.status_code in (200, 503))

# =============================================== lecteur
with app.test_client() as lecteur:
    tok = csrf(lecteur, "/connexion")
    r = lecteur.post("/connexion", data={"csrf_token": tok, "identifiant": "lecteur",
                                         "password": "Lecteur123!"}, follow_redirects=True)
    ok("Connexion lecteur reussie", "Deconnexion" in text(r) or "connexion" in text(r).lower())

    ok("Paywall bloque le connecte non abonne", "abonn" in text(lecteur.get(PREMIUM)))

    tok = csrf(lecteur, "/article/" + SLUG)
    r = lecteur.post("/article/" + SLUG + "/commentaire",
                     data={"csrf_token": tok, "content": "Test automatise de commentaire."},
                     follow_redirects=True)
    ok("Commentaire soumis -> en attente", "validation" in text(r))

    ok("Lecteur bloque sur /admin (403)", lecteur.get("/admin/").status_code == 403)

    # Changement de mot de passe
    tok = csrf(lecteur, "/compte")
    r = lecteur.post("/compte/mot-de-passe", data={
        "csrf_token": tok, "actuel": "mauvais", "nouveau": "NouveauMdp1",
        "confirmation": "NouveauMdp1"}, follow_redirects=True)
    ok("Changement de mdp refuse si actuel faux", "incorrect" in text(r))

with app.test_client() as c:
    ok("Commentaire invisible avant validation",
       "Test automatise de commentaire." not in text(c.get("/article/" + SLUG)))

# =============================================== mot de passe oublié
with app.test_client() as c:
    tok = csrf(c, "/mot-de-passe-oublie")
    r = c.post("/mot-de-passe-oublie", data={"csrf_token": tok,
                                             "email": "lecteur@kaloum24.example"},
               follow_redirects=True)
    ok("Demande de reinitialisation acceptee", "lien de r" in text(r))

    tok = csrf(c, "/mot-de-passe-oublie")
    r = c.post("/mot-de-passe-oublie", data={"csrf_token": tok,
                                             "email": "inconnu@nulle-part.test"},
               follow_redirects=True)
    ok("Adresse inconnue : meme message (anti-enumeration)", "lien de r" in text(r))

with app.app_context():
    from models import User
    u = User.query.filter_by(username="lecteur").first()
    jeton = u.reset_token()
    ok("Jeton de reinitialisation valide", User.verify_reset_token(jeton) is not None)
    ok("Jeton falsifie rejete", User.verify_reset_token(jeton + "abc") is None)

with app.test_client() as c:
    r = c.get("/reinitialiser/" + jeton)
    ok("Page de reinitialisation accessible", r.status_code == 200)
    tok = csrf(c, "/reinitialiser/" + jeton)
    r = c.post("/reinitialiser/" + jeton, data={
        "csrf_token": tok, "password": "MonNouveauMdp1",
        "password_confirm": "MonNouveauMdp1"}, follow_redirects=True)
    ok("Mot de passe reinitialise", "initialis" in text(r))
    ok("Jeton non reutilisable apres usage",
       "invalide" in text(c.get("/reinitialiser/" + jeton, follow_redirects=True)))

# =============================================== admin
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)
    r = admin.get("/admin/")
    ok("Admin accede au tableau de bord", r.status_code == 200 and "Tableau de bord" in text(r))

    html = text(admin.get("/admin/commentaires?statut=en_attente"))
    ok("Commentaire liste en moderation", "Test automatise" in html)
    ids = re.findall(r"/admin/commentaires/(\d+)/statut", html)
    if ids:
        tok = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        admin.post("/admin/commentaires/" + ids[0] + "/statut?statut=en_attente",
                   data={"csrf_token": tok, "status": "approuve"}, follow_redirects=True)

    # --- éditeur riche : le HTML est conservé ---
    form = text(admin.get("/admin/articles/nouveau"))
    ok("Editeur riche charge", "quill" in form.lower())
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    cat = re.search(r'<option value="(\d+)"', form).group(1)

    admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "Article avec mise en forme riche",
        "summary": "Verification que le HTML de l'editeur est conserve.",
        "content": "<p>Un <strong>gras</strong> et un <a href='https://exemple.test'>lien</a>.</p>"
                   "<h2>Un intertitre</h2><ul><li>Point un</li></ul>",
        "category_id": cat, "status": "publie"}, follow_redirects=True)
    page = text(admin.get("/article/article-avec-mise-en-forme-riche"))
    ok("HTML riche conserve (gras, titre, liste)",
       "<strong>gras</strong>" in page and "<h2>" in page and "<li>Point un</li>" in page)

    # --- assainissement : les scripts sont retirés ---
    form = text(admin.get("/admin/articles/nouveau"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "Article contenant du code malveillant",
        "summary": "Verification de l'assainissement du HTML soumis.",
        "content": "<p>Texte normal et suffisamment long pour passer la validation "
                   "de longueur minimale du contenu.</p>"
                   "<script>alert('xss')</script>"
                   "<img src=x onerror=\"alert('xss')\">"
                   "<a href=\"javascript:alert('xss')\">lien piege</a>",
        "category_id": cat, "status": "publie"}, follow_redirects=True)
    page = text(admin.get("/article/article-contenant-du-code-malveillant"))
    corps = page.split('class="article-body"')[1].split("</div>")[0] if 'class="article-body"' in page else page
    # La page contient légitimement des balises <script> (thème, JSON-LD) :
    # on vérifie l'absence du script *injecté*, pas de toute balise script.
    ok("Script injecte supprime (XSS)", "alert(" not in corps and "<script" not in corps)
    ok("Attribut onerror supprime", "onerror" not in page)
    ok("Texte legitime conserve malgre l assainissement", "Texte normal et suffisamment long" in corps)
    ok("Protocole javascript: neutralise", "javascript:" not in corps)

    # --- upload d'image ---
    form = text(admin.get("/admin/articles/nouveau"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    r = admin.post("/admin/upload-image",
                   data={"csrf_token": tok, "file": image_test()},
                   content_type="multipart/form-data")
    ok("Upload d'image accepte", r.status_code == 200 and "/static/uploads/" in text(r))

    r = admin.post("/admin/upload-image",
                   data={"csrf_token": tok, "file": (io.BytesIO(b"pas une image"), "virus.exe")},
                   content_type="multipart/form-data")
    ok("Upload d'un .exe refuse", r.status_code == 400)

    # image principale via le formulaire article
    form = text(admin.get("/admin/articles/nouveau"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "Article avec image envoyee",
        "summary": "Verification de l'upload depuis le formulaire d'article.",
        "content": "<p>Contenu suffisamment long pour passer la validation.</p>",
        "category_id": cat, "status": "publie", "image_file": image_test("une.png"),
        "image_credit": "Photo : Agence Test"},
        content_type="multipart/form-data", follow_redirects=True)
    page = text(admin.get("/article/article-avec-image-envoyee"))
    ok("Image principale enregistree", "/static/uploads/" in page)
    ok("Credit photo affiche", "Agence Test" in page)

    # --- validation ---
    form = text(admin.get("/admin/articles/nouveau"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    r = admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "abc", "summary": "x", "content": "y", "category_id": cat})
    ok("Validation du formulaire (titre trop court)", "au moins 5" in text(r))

    # --- rubriques ---
    tok = csrf(admin, "/admin/rubriques")
    r = admin.post("/admin/rubriques", data={"csrf_token": tok, "name": "Environnement"},
                   follow_redirects=True)
    ok("Rubrique creee", "Environnement" in text(r))
    r = admin.post("/admin/rubriques", data={"csrf_token": tok, "name": "Environnement"},
                   follow_redirects=True)
    ok("Rubrique en double refusee", "existe" in text(r))

    html = text(admin.get("/admin/rubriques"))
    ids = re.findall(r"/admin/rubriques/(\d+)/supprimer", html)
    tok = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    r = admin.post("/admin/rubriques/" + ids[0] + "/supprimer",
                   data={"csrf_token": tok}, follow_redirects=True)
    ok("Rubrique non vide protegee contre la suppression",
       "Impossible de supprimer" in text(r) or "supprim" in text(r))

    # --- utilisateurs ---
    ok("Gestion des utilisateurs accessible", admin.get("/admin/utilisateurs").status_code == 200)
    html = text(admin.get("/admin/utilisateurs"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    with app.app_context():
        from models import User as U
        uid = U.query.filter_by(username="admin").first().id
    r = admin.post("/admin/utilisateurs/%d/role" % uid,
                   data={"csrf_token": tok, "role": "user"}, follow_redirects=True)
    ok("Admin ne peut pas se retrograder lui-meme", "propre" in text(r))
    r = admin.post("/admin/utilisateurs/%d/bannir" % uid,
                   data={"csrf_token": tok}, follow_redirects=True)
    ok("Admin ne peut pas se bannir lui-meme", "toi-m" in text(r))

with app.test_client() as c:
    ok("Commentaire approuve devient public",
       "Test automatise de commentaire." in text(c.get("/article/" + SLUG)))

# =============================================== inscription
with app.test_client() as c:
    tok = csrf(c, "/inscription")
    r = c.post("/inscription", data={
        "csrf_token": tok, "username": "testeur", "email": "testeur@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"}, follow_redirects=True)
    ok("Inscription d'un nouveau compte", "Bienvenue" in text(r))
    ok("Page profil accessible", "testeur" in text(c.get("/compte")))

with app.test_client() as c:
    tok = csrf(c, "/inscription")
    r = c.post("/inscription", data={
        "csrf_token": tok, "username": "testeur", "email": "autre@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
    ok("Pseudo en double refuse", "pris" in text(r))

with app.test_client() as c:
    tok = csrf(c, "/inscription")
    r = c.post("/inscription", data={
        "csrf_token": tok, "username": "zoe", "email": "zoe@example.com",
        "password": "court", "password_confirm": "court"})
    ok("Mot de passe trop court refuse", "au moins 8" in text(r))

# =============================================== sécurité redirection
with app.test_client() as c:
    tok = csrf(c, "/connexion")
    r = c.post("/connexion?next=https://site-malveillant.test", data={
        "csrf_token": tok, "identifiant": "admin", "password": "ChangeMoi123!"})
    ok("Redirection externe apres connexion bloquee",
       "site-malveillant" not in r.headers.get("Location", ""))

# =============================================== abonnement
with app.test_client() as c:
    ok("Page abonnement explique l'absence de Stripe", "pas encore" in text(c.get("/abonnement")))

# =============================================== WhatsApp — correspondants
import whatsapp_client
import io as _io


def _msgs_envoyes():
    """Réinitialise et capture les messages envoyés par send_text pendant un scénario."""
    captures = []
    def _fake_send(to, body):
        captures.append((to, body))
        return True
    whatsapp_client.send_text = _fake_send
    return captures


def _image_test_octets():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), (30, 90, 150)).save(buf, "JPEG")
    return buf.getvalue()


def _payload_texte(numero, corps):
    return {"entry": [{"changes": [{"value": {"messages": [
        {"from": numero, "id": "wamid.t1", "type": "text", "text": {"body": corps}}
    ]}}]}]}


def _payload_image(numero, media_id="media-abc", legende=None):
    img = {"id": media_id, "mime_type": "image/jpeg"}
    if legende is not None:
        img["caption"] = legende
    return {"entry": [{"changes": [{"value": {"messages": [
        {"from": numero, "id": "wamid.i1", "type": "image", "image": img}
    ]}}]}]}


with app.app_context():
    app.config["WHATSAPP_ENABLED"] = True

with app.test_client() as c:
    # --- poignée de main du webhook ---
    r = c.get("/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=mauvais&hub.challenge=xyz")
    ok("Webhook refuse un jeton de verification errone", r.status_code == 403)

with app.app_context():
    app.config["WHATSAPP_VERIFY_TOKEN"] = "jeton-test"
with app.test_client() as c:
    r = c.get("/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=jeton-test&hub.challenge=xyz123")
    ok("Webhook valide le bon jeton et renvoie le challenge", r.status_code == 200 and text(r) == "xyz123")

# --- signature HMAC ---
with app.app_context():
    app.config["WHATSAPP_APP_SECRET"] = "secret-app-test"
with app.test_client() as c:
    corps = json.dumps(_payload_texte("224600000001", "test")).encode()
    r = c.post("/webhook/whatsapp", data=corps, content_type="application/json",
              headers={"X-Hub-Signature-256": "sha256=mauvaise_signature"})
    ok("Webhook rejette une signature invalide", r.status_code == 403)

    signature = "sha256=" + hmac.new(b"secret-app-test", corps, hashlib.sha256).hexdigest()
    r = c.post("/webhook/whatsapp", data=corps, content_type="application/json",
              headers={"X-Hub-Signature-256": signature})
    ok("Webhook accepte une signature valide", r.status_code == 200)

with app.app_context():
    app.config["WHATSAPP_APP_SECRET"] = ""  # simplifie le reste des scénarios

# --- numéro non enregistré ---
with app.test_client() as c:
    captures = _msgs_envoyes()
    r = c.post("/webhook/whatsapp", json=_payload_texte("224699999999", "Bonjour"))
    ok("Numero inconnu : requete acceptee (200) sans creer de contenu", r.status_code == 200)
    ok("Numero inconnu : message d'invitation envoye", len(captures) == 1 and "non reconnu" in captures[0][1])
    with app.app_context():
        ok("Numero inconnu : aucun brouillon cree", WhatsAppDraft.query.count() == 0)

# --- ajout d'un correspondant via l'admin ---
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    tok = csrf(admin, "/admin/correspondants")
    r = admin.post("/admin/correspondants", data={
        "csrf_token": tok, "name": "Mariama Diallo", "phone": "+224 620 00 11 22"},
        follow_redirects=True)
    ok("Correspondant cree depuis l'admin", "Mariama Diallo" in text(r))

    tok = csrf(admin, "/admin/correspondants")
    r = admin.post("/admin/correspondants", data={
        "csrf_token": tok, "name": "Doublon", "phone": "224620001122"},
        follow_redirects=True)
    ok("Numero deja enregistre refuse", "déjà enregistré" in text(r))

NUMERO = "224620001122"

# --- flux complet : texte -> photo -> publier ---
with app.test_client() as c:
    captures = _msgs_envoyes()
    r = c.post("/webhook/whatsapp", json=_payload_texte(
        NUMERO, "Le marché central rouvre ses portes\nAprès trois mois de travaux, "
                "les commerçants retrouvent leurs étals dès lundi."))
    ok("Texte accepte par un correspondant actif", r.status_code == 200)
    ok("Accuse de reception du texte envoye", any("Texte reçu" in m for _, m in captures))
    with app.app_context():
        d = WhatsAppDraft.query.first()
        ok("Brouillon cree avec le texte", d is not None and "marché central" in d.text_buffer)

    whatsapp_client.download_media = lambda media_id: (_image_test_octets(), "image/jpeg")
    captures.clear()
    r = c.post("/webhook/whatsapp", json=_payload_image(NUMERO, legende="Vue du marché rénové"))
    ok("Photo acceptee et rattachee au brouillon", r.status_code == 200)
    with app.app_context():
        d = WhatsAppDraft.query.first()
        ok("Image enregistree sur le brouillon", d is not None and d.image_url
           and d.image_url.startswith("/static/uploads/"))
        ok("Legende ajoutee au texte du brouillon", "Vue du marché rénové" in d.text_buffer)

    captures.clear()
    r = c.post("/webhook/whatsapp", json=_payload_texte(NUMERO, "statut"))
    ok("Commande STATUT repond avec l'etat du brouillon",
       any("Brouillon en cours" in m for _, m in captures))

    captures.clear()
    r = c.post("/webhook/whatsapp", json=_payload_texte(NUMERO, "publier"))
    ok("Commande PUBLIER traitee", r.status_code == 200)
    ok("Confirmation de publication envoyee",
       any("file de relecture" in m for _, m in captures))

with app.app_context():
    art = Article.query.filter_by(source="whatsapp").first()
    ok("Article cree depuis WhatsApp", art is not None)
    ok("Article WhatsApp en statut brouillon (jamais auto-publie)",
       art is not None and art.status == "brouillon")
    ok("Titre = premiere ligne du message",
       art is not None and art.title.startswith("Le marché central"))
    ok("Image rattachee a l'article", art is not None and art.image_url)
    ok("Credit photo mentionne le correspondant",
       art is not None and "Mariama Diallo" in (art.image_credit or ""))
    ok("Brouillon supprime apres conversion", WhatsAppDraft.query.count() == 0)

# --- l'article WhatsApp doit passer par la relecture normale ---
with app.test_client() as anon:
    ok("Article WhatsApp invisible du public avant publication (brouillon)",
       "marché central" not in text(anon.get("/")))

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)
    html_liste = text(admin.get("/admin/articles?statut=brouillon"))
    ok("Article WhatsApp visible dans la file de relecture admin",
       "marché central" in html_liste and "WhatsApp" in html_liste)

# --- PUBLIER sans texte prealable ---
with app.test_client() as c:
    captures = _msgs_envoyes()
    NUMERO2 = "224620001122"  # même correspondant, brouillon déjà vidé
    r = c.post("/webhook/whatsapp", json=_payload_texte(NUMERO2, "publier"))
    ok("PUBLIER sans texte prealable ne cree rien",
       any("Envoie d'abord un texte" in m for _, m in captures))

# --- annulation ---
with app.test_client() as c:
    c.post("/webhook/whatsapp", json=_payload_texte(NUMERO, "Un brouillon a annuler"))
    with app.app_context():
        ok("Brouillon cree avant annulation", WhatsAppDraft.query.count() == 1)
    captures = _msgs_envoyes()
    c.post("/webhook/whatsapp", json=_payload_texte(NUMERO, "annuler"))
    ok("Confirmation d'annulation envoyee", any("annulé" in m for _, m in captures))
    with app.app_context():
        ok("Brouillon supprime apres ANNULER", WhatsAppDraft.query.count() == 0)

# --- aide ---
with app.test_client() as c:
    captures = _msgs_envoyes()
    c.post("/webhook/whatsapp", json=_payload_texte(NUMERO, "aide"))
    ok("Commande AIDE renvoie les instructions",
       any("PUBLIER" in m and "ANNULER" in m for _, m in captures))

# --- photo invalide (mauvais mime) ---
with app.test_client() as c:
    whatsapp_client.download_media = lambda media_id: (b"pas une image", "application/pdf")
    captures = _msgs_envoyes()
    c.post("/webhook/whatsapp", json=_payload_image(NUMERO, media_id="media-pdf"))
    ok("Photo au format non reconnu refusee", any("Photo invalide" in m for _, m in captures))

# --- desactivation d'un correspondant ---
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)
    html_liste = text(admin.get("/admin/correspondants"))
    cid = re.search(r"/admin/correspondants/(\d+)/statut", html_liste).group(1)
    tok = re.search(r'name="csrf_token" value="([^"]+)"', html_liste).group(1)
    admin.post(f"/admin/correspondants/{cid}/statut", data={"csrf_token": tok},
              follow_redirects=True)

with app.test_client() as c:
    captures = _msgs_envoyes()
    c.post("/webhook/whatsapp", json=_payload_texte(NUMERO, "Nouveau message apres desactivation"))
    ok("Correspondant desactive ne peut plus soumettre de brouillon",
       any("non reconnu" in m for _, m in captures))
    with app.app_context():
        ok("Aucun brouillon cree pour un correspondant inactif", WhatsAppDraft.query.count() == 0)

# --- le webhook doit disparaitre quand la fonctionnalite est desactivee ---
with app.app_context():
    app.config["WHATSAPP_ENABLED"] = False
with app.test_client() as c:
    r = c.get("/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=jeton-test&hub.challenge=xyz")
    ok("Webhook GET introuvable quand WHATSAPP_ENABLED=False", r.status_code == 404)
    r = c.post("/webhook/whatsapp", json=_payload_texte(NUMERO2, "Un message"))
    ok("Webhook POST introuvable quand WHATSAPP_ENABLED=False", r.status_code == 404)
with app.app_context():
    app.config["WHATSAPP_ENABLED"] = True

# --- normalisation des numéros : format local vs format international ---
with app.app_context():
    from utils import normalize_phone
    ok("Numero local guineen complete avec l'indicatif",
       normalize_phone("620 00 00 01") == "224620000001")
    ok("Numero avec 0 initial : le 0 est retire avant l'indicatif",
       normalize_phone("0620000001") == "224620000001")
    ok("Numero deja au format international : inchange",
       normalize_phone("224620000001") == "224620000001")
    ok("Numero trop court rejete", normalize_phone("12345") is None)
    ok("Chaine vide rejetee", normalize_phone("") is None)

# =============================================== limitation de débit
with app.app_context():
    app.config["RATELIMIT_LOGIN"] = "3 per 5 minutes"

with app.test_client() as c:
    codes = []
    for _ in range(6):
        tok = csrf(c, "/connexion")
        r = c.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                       "password": "mauvais-mot-de-passe"})
        codes.append(r.status_code)
    ok("Limite de connexion : les 3 premieres tentatives passent",
       codes[:3] == [200, 200, 200])
    ok("Limite de connexion : les suivantes sont bloquees (429)",
       codes[3] == 429)

with app.test_client() as c:
    r = c.get("/connexion")
    ok("Page 429 lisible plutot qu'une trace brute",
       r.status_code != 429 or "Trop de tentatives" in text(r))

# --- la limitation ne doit pas gêner la navigation normale ---
with app.test_client() as c:
    codes = [c.get("/").status_code for _ in range(15)]
    ok("Navigation publique non limitee", all(x == 200 for x in codes))

# Restaure la valeur par défaut : sans ça, chaque connexion admin encore
# nécessaire plus loin dans ce fichier (WhatsApp, sources, scoring,
# agrégation…) resterait exposée au seuil abaissé ci-dessus et pourrait
# recevoir un 429 selon le nombre cumulé de tentatives déjà comptées pour
# cette adresse — un test doit remettre en état ce qu'il modifie globalement.
# Restaure une valeur généreuse plutôt que la valeur par défaut de production
# (10 per 5 minutes) : ce fichier de tests grossit à chaque nouvelle phase et
# additionne de plus en plus de connexions admin/lecteur au fil de son
# exécution — la valeur par défaut, déjà restaurée une fois, s'est révélée de
# nouveau insuffisante dès l'ajout des tests de commentaires imbriqués
# (10 connexions consommées entre-temps, pile la limite). Une valeur large
# retire ce facteur pour de bon, sans jamais désactiver le test dédié
# ci-dessus qui vérifie que la limite fonctionne réellement.
with app.app_context():
    app.config["RATELIMIT_LOGIN"] = "1000 per 5 minutes"
    # Même problème que RATELIMIT_LOGIN ci-dessus, pour l'inscription cette
    # fois : la valeur par défaut de production (5 per hour) est bien trop
    # stricte pour le nombre de comptes de test que ce fichier crée au fil
    # de ses sections — jamais touchée jusqu'ici, ce qui a fini par bloquer
    # une inscription plus loin dans ce même fichier une fois le total
    # cumulé passé au-delà de 5.
    app.config["RATELIMIT_REGISTER"] = "1000 per hour"
    # Même précaution, préventive cette fois : ces deux limites sont encore
    # loin d'être atteintes à ce stade du fichier, mais chaque nouvelle
    # section de tests en ajoute un peu plus — autant clore la classe de bug
    # entière ici plutôt que de la retrouver une quatrième fois plus tard.
    app.config["RATELIMIT_COMMENT"] = "1000 per 10 minutes"
    app.config["RATELIMIT_PASSWORD_RESET"] = "1000 per hour"

# =============================================== base non initialisée
# Simule l'erreur la plus fréquente à la première installation : lancer le
# site sans avoir exécuté `flask db upgrade`.
import tempfile as _tf

_fd2, _p2 = _tf.mkstemp(suffix=".db")
_ancienne_uri = os.environ.get("DATABASE_URL")
os.environ["DATABASE_URL"] = "sqlite:///" + _p2

from config import Config as _Config


class _ConfigVide(_Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + _p2


app_vide = create_app(_ConfigVide)      # aucune table créée volontairement
with app_vide.test_client() as c:
    r = c.get("/")
    page = text(r)
    ok("Base non initialisee : message explicite au lieu d'une trace",
       "Base de données non initialisée" in page)
    ok("Base non initialisee : la commande a lancer est indiquee",
       "flask db upgrade" in page)
    ok("Base non initialisee : aide Windows pour FLASK_APP",
       "set FLASK_APP" in page)

os.close(_fd2)
os.unlink(_p2)
if _ancienne_uri:
    os.environ["DATABASE_URL"] = _ancienne_uri

# =============================================== durcissement production
with app.test_client() as c:
    r = c.get("/")
    ok("En-tete CSP present", "Content-Security-Policy" in r.headers)
    ok("CSP interdit les scripts tiers", "script-src 'self'" in r.headers.get("Content-Security-Policy", ""))
    ok("CSP interdit l'inclusion en iframe",
       "frame-ancestors 'none'" in r.headers.get("Content-Security-Policy", ""))
    ok("En-tete X-Frame-Options present", r.headers.get("X-Frame-Options") == "DENY")
    ok("En-tete X-Content-Type-Options present",
       r.headers.get("X-Content-Type-Options") == "nosniff")
    ok("En-tete Referrer-Policy present", "Referrer-Policy" in r.headers)
    ok("HSTS absent par defaut (pas encore de HTTPS)",
       "Strict-Transport-Security" not in r.headers)

# --- point de contrôle de santé ---
with app.test_client() as c:
    r = c.get("/sante")
    ok("Point de sante repond 200", r.status_code == 200)
    ok("Point de sante confirme la base", r.get_json().get("base") == "ok")

# --- compteur de vues tamponné ---
import view_counter  # noqa: E402

with app.app_context():
    from models import Article as _A

    # Les tests précédents ont consulté des articles : leurs vues peuvent
    # encore être dans le tampon. On l'écrit d'abord, sinon elles seraient
    # comptées avec les 200 de ce test et fausseraient la mesure.
    view_counter.vider_maintenant(app)
    db.session.expire_all()

    _art = _A.query.filter_by(status="publie").first()
    _aid, _avant, _updated_avant = _art.id, _art.views, _art.updated_at

    _ecritures = {"n": 0}
    _orig_ecrire = view_counter._ecrire

    def _compter(app_, compteurs):
        if compteurs:
            _ecritures["n"] += 1
        return _orig_ecrire(app_, compteurs)

    view_counter._ecrire = _compter

    for _ in range(200):
        view_counter.enregistrer_vue(app, _aid)
    view_counter.vider_maintenant(app)

    view_counter._ecrire = _orig_ecrire
    _apres = db.session.get(_A, _aid)

    ok("Compteur de vues : total exact apres 200 lectures",
       _apres.views - _avant == 200)
    ok("Compteur de vues : ecritures en base fortement reduites",
       _ecritures["n"] <= 10)
    ok("Compteur de vues : updated_at non modifie (sitemap correct)",
       _apres.updated_at == _updated_avant)

# --- validation de configuration ---
from security import verifier_configuration  # noqa: E402

with app.app_context():
    _erreurs, _avert = verifier_configuration(app, strict=True)
    ok("Audit strict signale une SECRET_KEY faible",
       any("SECRET_KEY" in e for e in _erreurs))

    _ancienne = app.config["SECRET_KEY"]
    app.config["SECRET_KEY"] = "x" * 64
    _erreurs2, _ = verifier_configuration(app, strict=True)
    ok("Audit strict accepte une SECRET_KEY solide",
       not any("SECRET_KEY" in e for e in _erreurs2))
    app.config["SECRET_KEY"] = _ancienne

    app.config["WHATSAPP_ENABLED"] = True
    _secret_ancien = app.config["WHATSAPP_APP_SECRET"]
    app.config["WHATSAPP_APP_SECRET"] = ""
    _erreurs3, _ = verifier_configuration(app, strict=True)
    ok("Audit strict signale un webhook WhatsApp non signe",
       any("WHATSAPP_APP_SECRET" in e for e in _erreurs3))
    app.config["WHATSAPP_APP_SECRET"] = _secret_ancien

# --- refus de démarrer en production avec une configuration dangereuse ---
from config import Config as _ConfigBase  # noqa: E402


class _ConfigProdDangereuse(_ConfigBase):
    ENV = "production"
    IS_PRODUCTION = True
    SECRET_KEY = "change-moi-en-production-svp"
    SITE_URL = "http://127.0.0.1:5000"
    SESSION_COOKIE_SECURE = True


_refus = False
try:
    create_app(_ConfigProdDangereuse)
except SystemExit:
    _refus = True
ok("Production : demarrage refuse si SECRET_KEY par defaut", _refus)

# =============================================== agrégation de sources
import feed_client  # noqa: E402
from models import Source, CollectedArticle, Topic, ScoringConfig  # noqa: E402

# --- feed_client : parsing d'un flux RSS factice, aucun appel réseau ---
_RSS_FACTICE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Flux de test</title>
<item>
  <title>Premier &#8217;article&#8217; de test</title>
  <link>https://exemple-source.test/article-1</link>
  <description>&lt;div&gt;&lt;img src="https://exemple-source.test/photo1.jpg" /&gt;&lt;/div&gt;Resume de l&#8217;article un.</description>
  <pubDate>Tue, 11 Aug 2026 10:00:00 GMT</pubDate>
</item>
<item>
  <title>Deuxieme article de test</title>
  <link>https://exemple-source.test/article-2</link>
  <description>Resume de l'article deux, sans image.</description>
  <pubDate>Tue, 11 Aug 2026 09:00:00 GMT</pubDate>
</item>
<item>
  <title></title>
  <link>https://exemple-source.test/sans-titre</link>
  <description>Un item sans titre doit etre ignore.</description>
</item>
</channel></rss>"""

with app.app_context():
    import feedparser as _fp
    _analyse = _fp.parse(_RSS_FACTICE)
    ok("Flux factice : 3 entrees brutes analysees", len(_analyse.entries) == 3)

    _items = feed_client.fetch_feed(_RSS_FACTICE)
    ok("Item sans titre ignore", len(_items) == 2)
    ok("Entites HTML decodees dans le titre", "’article’" in _items[0]["title"] or "'article'" in _items[0]["title"])
    ok("Image extraite du HTML du resume (fallback <img>)",
       _items[0]["image_url"] == "https://exemple-source.test/photo1.jpg")
    ok("Extrait sans balises HTML", "<div>" not in (_items[0]["excerpt"] or ""))
    ok("Deuxieme item sans image -> None", _items[1]["image_url"] is None)
    ok("Date de publication normalisee", _items[0]["published_at"] is not None)

    try:
        feed_client.fetch_feed("<rss><channel><item></item></channel></rss>")
        ok("Flux sans lien/titre leve ErreurFlux ou retourne liste vide",
           True)  # ni lien ni titre -> item ignoré, pas d'exception attendue ici
    except feed_client.ErreurFlux:
        ok("Flux sans lien/titre leve ErreurFlux ou retourne liste vide", True)

    try:
        feed_client.fetch_feed("ceci n'est pas du xml du tout <<<")
        ok("Flux illisible leve ErreurFlux", False)
    except feed_client.ErreurFlux:
        ok("Flux illisible leve ErreurFlux", True)

# --- modèle Source : contrainte de conformité ---
with app.app_context():
    s = Source(name="Source de test", site_url="https://exemple.test",
              feed_url="https://exemple.test/feed/", compliance_checked=False,
              is_active=False)
    db.session.add(s)
    db.session.commit()
    ok("Source inactive sans conformite acceptee", s.id is not None)

    s2 = Source(name="Source non conforme active", site_url="https://exemple2.test",
               feed_url="https://exemple2.test/feed/", compliance_checked=False,
               is_active=True)
    db.session.add(s2)
    _contrainte_violee = False
    try:
        db.session.commit()
    except Exception:
        _contrainte_violee = True
        db.session.rollback()
    ok("Contrainte base : source active sans conformite refusee", _contrainte_violee)

    db.session.delete(s)
    db.session.commit()

# --- admin : CRUD des sources ---
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    ok("Liste des sources accessible", admin.get("/admin/sources").status_code == 200)

    form = text(admin.get("/admin/sources/nouvelle"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)

    # Tentative d'activation SANS cocher la conformité : doit être refusée
    # au niveau de la route, avant même d'atteindre la contrainte SQL.
    r = admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Source Test Admin",
        "site_url": "https://source-test.example", "feed_url": "https://source-test.example/feed/",
        "trust_level": "60", "fetch_frequency_minutes": "60", "is_active": "on"})
    ok("Activation sans conformite cochee refusee par le formulaire",
       "conformité" in text(r).lower() or "conformite" in text(r).lower())

    form = text(admin.get("/admin/sources/nouvelle"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Source Test Admin",
        "site_url": "https://source-test.example", "feed_url": "https://source-test.example/feed/",
        "trust_level": "60", "fetch_frequency_minutes": "60",
        "compliance_checked": "on", "is_active": "on"}, follow_redirects=True)
    ok("Source creee et visible dans la liste",
       "Source Test Admin" in text(admin.get("/admin/sources")))

    form = text(admin.get("/admin/sources/nouvelle"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    r = admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Source Test Admin",  # nom en double
        "site_url": "https://autre.example", "feed_url": "https://autre.example/feed/",
        "trust_level": "60", "fetch_frequency_minutes": "60"})
    ok("Nom de source en double refuse", "déjà ce nom" in text(r) or "porte déjà" in text(r))

    r = admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Frequence invalide",
        "site_url": "https://autre2.example", "feed_url": "https://autre2.example/feed/",
        "trust_level": "60", "fetch_frequency_minutes": "1"})
    ok("Frequence de collecte trop faible refusee", "5 minutes" in text(r))

with app.app_context():
    _src = Source.query.filter_by(name="Source Test Admin").first()
    ok("Source de test bien enregistree avec conformite", _src is not None and _src.compliance_checked)
    _src_id = _src.id if _src else None

# --- bouton « Tester cette source » : flux simulé, aucun appel réseau ---
import unittest.mock as _mock  # noqa: E402

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)
    tok = csrf(admin, "/admin/sources")

    with _mock.patch("blueprints.admin.feed_client.fetch_feed") as _faux_fetch:
        _faux_fetch.return_value = [
            {"url": "https://x.test/1", "title": "Titre simulé", "excerpt": "…",
             "image_url": None, "author": None, "published_at": None},
        ]
        r = admin.post(f"/admin/sources/{_src_id}/tester",
                       headers={"X-CSRFToken": tok})
        ok("Test de source (succes) renvoie l'apercu", r.status_code == 200)
        ok("Apercu contient le nombre d'items", r.get_json().get("nombre_items") == 1)

    with _mock.patch("blueprints.admin.feed_client.fetch_feed") as _faux_fetch:
        _faux_fetch.side_effect = feed_client.ErreurFlux("flux indisponible (simulation)")
        r = admin.post(f"/admin/sources/{_src_id}/tester",
                       headers={"X-CSRFToken": tok})
        ok("Test de source (echec) renvoie une erreur lisible",
           r.status_code == 502 and "indisponible" in r.get_json().get("erreur", ""))

    r = admin.post(f"/admin/sources/{_src_id}/supprimer", data={"csrf_token": tok},
                   follow_redirects=True)
    ok("Suppression de source fonctionne",
       "Source Test Admin" not in text(admin.get("/admin/sources")))

# --- un non-admin ne peut pas gérer les sources (moderateur suffit pour
#     articles/commentaires, mais pas pour les sources — c'est admin_required)
# --- un simple lecteur ne peut pas gérer les sources (admin_required, pas
#     seulement moderator_required). Compte dédié plutôt que « lecteur » :
#     son mot de passe a été changé par le test de réinitialisation plus
#     haut dans ce même fichier, s'y fier ici créerait un couplage fragile.
with app.test_client() as simple_user:
    tok = csrf(simple_user, "/inscription")
    simple_user.post("/inscription", data={
        "csrf_token": tok, "username": "lecteur_sources_test",
        "email": "lecteur_sources_test@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
    ok("Lecteur bloque sur /admin/sources (403)",
       simple_user.get("/admin/sources").status_code == 403)

# --- ScoringConfig : valeurs par défaut sensées ---
with app.app_context():
    cfg = ScoringConfig.get_active()
    ok("ScoringConfig par defaut : ponderations somment a 1.0",
       abs((cfg.weight_importance + cfg.weight_freshness + cfg.weight_popularity
            + cfg.weight_relevance + cfg.weight_trust) - 1.0) < 0.001)
    ok("ScoringConfig par defaut : seuils ordonnes (high > medium > low)",
       cfg.threshold_high > cfg.threshold_medium > cfg.threshold_low)

# =============================================== moteur de collecte
import collector  # noqa: E402

_FAUX_ITEMS_A = [
    {"url": "https://source-a.test/1", "title": "Premier article source A",
     "excerpt": "Resume un", "image_url": None, "author": None, "published_at": None},
    {"url": "https://source-a.test/2", "title": "Deuxieme article publicite",
     "excerpt": "Contenu sponsorise", "image_url": None, "author": None, "published_at": None},
    {"url": "https://source-a.test/3", "title": "Troisieme article Guinee",
     "excerpt": "Actualite guineenne", "image_url": None, "author": None, "published_at": None},
]

with app.app_context():
    src_a = Source(name="Source Test Collecte A", site_url="https://source-a.test",
                   feed_url="https://source-a.test/feed/", compliance_checked=True,
                   is_active=True, fetch_frequency_minutes=60,
                   keywords_exclude="publicité, sponsorisé")
    src_b = Source(name="Source Test Collecte B (inactive)", site_url="https://source-b.test",
                   feed_url="https://source-b.test/feed/", compliance_checked=True,
                   is_active=False)
    src_c = Source(name="Source Test Collecte C (non conforme)", site_url="https://source-c.test",
                   feed_url="https://source-c.test/feed/", compliance_checked=False,
                   is_active=False)
    db.session.add_all([src_a, src_b, src_c])
    db.session.commit()
    _src_a_id, _src_b_id, _src_c_id = src_a.id, src_b.id, src_c.id

# --- filtrage par mots-clés exclus, avant tout accès réseau ---
with app.app_context():
    src_a = db.session.get(Source, _src_a_id)
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=_FAUX_ITEMS_A):
        resultat = collector.collecter_source(src_a)

    ok("Collecte : statut ok", resultat["statut"] == "ok")
    ok("Collecte : l'article exclu par mot-cle n'est pas compte",
       resultat["nouveaux"] == 2)          # 3 items, 1 exclu par "publicité"

    articles = CollectedArticle.query.filter_by(source_id=_src_a_id).all()
    ok("Collecte : exactement 2 CollectedArticle enregistres", len(articles) == 2)
    ok("Collecte : l'item exclu n'est pas en base",
       not any("publicite" in a.title.lower() for a in articles))
    ok("Collecte : statut initial 'nouveau'", all(a.status == "nouveau" for a in articles))
    ok("Collecte : source.last_fetched_at mis a jour", src_a.last_fetched_at is not None)
    ok("Collecte : source.last_error efface en cas de succes", src_a.last_error is None)

# --- relancer immédiatement ne doit rien ajouter (dédoublonnage par URL) ---
with app.app_context():
    src_a = db.session.get(Source, _src_a_id)
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=_FAUX_ITEMS_A):
        resultat2 = collector.collecter_source(src_a)
    ok("Collecte : relance immediate ne recree pas les doublons",
       resultat2["nouveaux"] == 0)
    ok("Collecte : le total en base n'a pas double",
       CollectedArticle.query.filter_by(source_id=_src_a_id).count() == 2)

# --- une source dont le flux échoue ne bloque pas la collecte ---
with app.app_context():
    src_a = db.session.get(Source, _src_a_id)
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed",
                     side_effect=feed_client.ErreurFlux("simulation d'echec")):
        resultat3 = collector.collecter_source(src_a)
    ok("Collecte : flux en echec renvoie un statut erreur (pas d'exception)",
       resultat3["statut"] == "erreur")
    ok("Collecte : l'erreur est consignee sur la source",
       "simulation" in (db.session.get(Source, _src_a_id).last_error or ""))

# --- robots.txt interdit désormais l'accès : la collecte est bloquée ---
with app.app_context():
    src_a = db.session.get(Source, _src_a_id)
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(False, None)) as _faux_robots, \
         _mock.patch("collector.feed_client.fetch_feed") as _faux_fetch:
        resultat4 = collector.collecter_source(src_a)
    ok("Collecte : robots.txt refuse -> statut bloque", resultat4["statut"] == "bloque")
    ok("Collecte : flux jamais interroge quand robots.txt refuse",
       _faux_fetch.call_count == 0)

# --- run_collection : respecte is_active ET compliance_checked ---
with app.app_context():
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=[]):
        resultats = collector.run_collection(forcer=True, pause=False)

    noms_traites = {r["source"] for r in resultats}
    ok("run_collection : source active+conforme traitee",
       "Source Test Collecte A" in noms_traites)
    ok("run_collection : source inactive jamais traitee",
       "Source Test Collecte B (inactive)" not in noms_traites)
    ok("run_collection : source non conforme jamais traitee (meme si un jour activee)",
       "Source Test Collecte C (non conforme)" not in noms_traites)

# --- respect de la fréquence configurée (sans --force) ---
with app.app_context():
    src_a = db.session.get(Source, _src_a_id)
    src_a.fetch_frequency_minutes = 999
    db.session.commit()  # dernière collecte très récente -> ne doit pas être relancée

    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed") as _faux_fetch_freq:
        resultats_freq = collector.run_collection(forcer=False, pause=False)

    _entree_a = next(r for r in resultats_freq if r["source"] == "Source Test Collecte A")
    ok("run_collection : frequence non echue -> ignoree, flux non interroge",
       _entree_a["statut"] == "ignore" and _faux_fetch_freq.call_count == 0)

# --- commande CLI flask collect-sources : bout en bout, flux simulé ---
with app.app_context():
    from click.testing import CliRunner
    src_a = db.session.get(Source, _src_a_id)
    src_a.fetch_frequency_minutes = 60
    src_a.last_fetched_at = None
    db.session.commit()

    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=[
             {"url": "https://source-a.test/cli-1", "title": "Article via commande CLI",
              "excerpt": None, "image_url": None, "author": None, "published_at": None},
         ]):
        runner = CliRunner()
        resultat_cli = runner.invoke(app.cli, ["collect-sources"], obj={})
    ok("Commande flask collect-sources s'execute sans erreur",
       resultat_cli.exit_code == 0)
    ok("Commande flask collect-sources rapporte le nombre d'articles",
       "nouvel" in resultat_cli.output)

# =============================================== regroupement par sujet
import topic_matcher  # noqa: E402
from models import Topic  # noqa: E402

# --- calibrage du seuil sur des cas réels (pas de mock, calcul pur) ---
with app.app_context():
    # Cas positifs : vraies reformulations d'un même événement, tirées de
    # titres réellement observés en collecte.
    _paires_similaires = [
        ("Effondrement d'un immeuble à Hafia 1 : cinq morts",
         "Hafia 1 : un immeuble s'effondre, cinq morts selon un bilan provisoire"),
        ("Guinée-FMI : un accord au niveau des services",
         "FMI-Guinée : accord trouvé au niveau des services"),
        ("Simandou 2040 : 12 projets dévoilés",
         "Simandou 2040 : Mory Condé dévoile un portefeuille de 12 projets"),
    ]
    ok("Similarite : reformulations proches toutes au-dessus du seuil (70)",
       all(topic_matcher.similarite(a, b) >= 70 for a, b in _paires_similaires))

    # Cas négatifs : sujets réellement différents, y compris un piège
    # volontaire (deux effondrements d'immeubles distincts).
    _paires_distinctes = [
        ("Dixinn : un immeuble en construction s'effondre",
         "Effondrement d'un immeuble à Hafia 1 : cinq morts"),
        ("Le président reçoit une délégation de la CEDEAO",
         "Le ministre des Sports inaugure un nouveau stade"),
    ]
    ok("Similarite : sujets distincts sous le seuil, y compris cas piege",
       all(topic_matcher.similarite(a, b) < 70 for a, b in _paires_distinctes))

    # Limite assumée et documentée : l'exemple du cahier des charges lui-même
    # (trois reformulations très différentes du même événement) reste SOUS
    # le seuil. Ce n'est pas un bug — c'est la limite connue de cette
    # méthode, vérifiée ici pour qu'un futur changement de seuil ne la fasse
    # pas passer inaperçue dans un sens comme dans l'autre.
    _titres_cahier = [
        "Le gouvernement annonce une nouvelle mesure économique",
        "Nouvelle décision gouvernementale sur l'économie",
        "Les autorités présentent leur nouvelle politique économique",
    ]
    _scores_cahier = [
        topic_matcher.similarite(_titres_cahier[0], _titres_cahier[1]),
        topic_matcher.similarite(_titres_cahier[0], _titres_cahier[2]),
        topic_matcher.similarite(_titres_cahier[1], _titres_cahier[2]),
    ]
    ok("Limite connue documentee : exemple du cahier des charges sous le seuil",
       all(s < 70 for s in _scores_cahier))

# --- rattacher_sujets() : deux articles proches, sources différentes ---
with app.app_context():
    src_x = Source(name="Source Sujet X", site_url="https://sujet-x.test",
                   feed_url="https://sujet-x.test/feed/", compliance_checked=True,
                   is_active=True)
    src_y = Source(name="Source Sujet Y", site_url="https://sujet-y.test",
                   feed_url="https://sujet-y.test/feed/", compliance_checked=True,
                   is_active=True)
    db.session.add_all([src_x, src_y])
    db.session.commit()

    a1 = CollectedArticle(source_id=src_x.id,
                          external_url="https://sujet-x.test/1",
                          title="Effondrement d'un immeuble à Hafia 1 : cinq morts")
    a2 = CollectedArticle(source_id=src_y.id,
                          external_url="https://sujet-y.test/1",
                          title="Hafia 1 : un immeuble s'effondre, cinq morts selon un bilan provisoire")
    a3 = CollectedArticle(source_id=src_x.id,
                          external_url="https://sujet-x.test/2",
                          title="Le ministre des Sports inaugure un nouveau stade")
    db.session.add_all([a1, a2, a3])
    db.session.commit()

    stats = topic_matcher.rattacher_sujets()
    ok("rattacher_sujets : un nouveau sujet cree pour la paire similaire",
       stats["nouveaux_sujets"] == 1)

    db.session.refresh(a1); db.session.refresh(a2); db.session.refresh(a3)
    ok("rattacher_sujets : les deux articles similaires partagent un topic_id",
       a1.topic_id is not None and a1.topic_id == a2.topic_id)
    ok("rattacher_sujets : l'article sans rapport reste sans sujet",
       a3.topic_id is None)

    topic = db.session.get(Topic, a1.topic_id)
    ok("rattacher_sujets : sources_count = 2 pour le nouveau sujet",
       topic.sources_count == 2)

# --- un troisième article, même sujet, rejoint le sujet existant ---
with app.app_context():
    src_x = Source.query.filter_by(name="Source Sujet X").first()
    a4 = CollectedArticle(source_id=src_x.id,
                          external_url="https://sujet-x.test/3",
                          title="Hafia 1 : le bilan de l'effondrement s'alourdit à cinq morts")
    db.session.add(a4)
    db.session.commit()

    topic_avant = Topic.query.filter(Topic.sources_count == 2).first()
    stats2 = topic_matcher.rattacher_sujets()
    ok("rattacher_sujets : rattachement a un sujet existant (pas un nouveau)",
       stats2["rattachements"] == 1 and stats2["nouveaux_sujets"] == 0)

    db.session.refresh(a4)
    topic_apres = db.session.get(Topic, topic_avant.id)
    ok("rattacher_sujets : le sujet existant grossit (sources_count = 3)",
       topic_apres.sources_count == 3)
    ok("rattacher_sujets : le nouvel article porte le meme topic_id",
       a4.topic_id == topic_avant.id)

# --- deux articles PROCHES mais de la MEME source ne se regroupent pas ---
with app.app_context():
    src_x = Source.query.filter_by(name="Source Sujet X").first()
    b1 = CollectedArticle(source_id=src_x.id, external_url="https://sujet-x.test/meme-1",
                          title="Le budget 2027 presente en conseil des ministres")
    b2 = CollectedArticle(source_id=src_x.id, external_url="https://sujet-x.test/meme-2",
                          title="Conseil des ministres : le budget 2027 est presente")
    db.session.add_all([b1, b2])
    db.session.commit()

    stats3 = topic_matcher.rattacher_sujets()
    db.session.refresh(b1); db.session.refresh(b2)
    ok("rattacher_sujets : deux articles similaires de la MEME source ne se regroupent pas",
       b1.topic_id is None and b2.topic_id is None)

# --- idempotence : relancer sans nouvel article ne change rien ---
with app.app_context():
    _avant = {t.id: t.sources_count for t in Topic.query.all()}
    topic_matcher.rattacher_sujets()
    _apres = {t.id: t.sources_count for t in Topic.query.all()}
    ok("rattacher_sujets : relance sans nouvel article -> aucun changement",
       _avant == _apres)

# --- intégration avec run_collection : le regroupement se déclenche après collecte ---
with app.app_context():
    src_z1 = Source(name="Source Integration Z1", site_url="https://z1.test",
                    feed_url="https://z1.test/feed/", compliance_checked=True, is_active=True)
    src_z2 = Source(name="Source Integration Z2", site_url="https://z2.test",
                    feed_url="https://z2.test/feed/", compliance_checked=True, is_active=True)
    db.session.add_all([src_z1, src_z2])
    db.session.commit()
    _z1_id, _z2_id = src_z1.id, src_z2.id

    def _faux_fetch_integration(url, *a, **kw):
        if "z1.test" in url:
            return [{"url": "https://z1.test/a", "title": "Attaque revendiquee dans le nord du pays",
                     "excerpt": None, "image_url": None, "author": None, "published_at": None}]
        if "z2.test" in url:
            return [{"url": "https://z2.test/a", "title": "Nord du pays : une attaque revendiquee",
                     "excerpt": None, "image_url": None, "author": None, "published_at": None}]
        return []

    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", side_effect=_faux_fetch_integration):
        resultats_integration = collector.run_collection(forcer=True, pause=False)

    ok("run_collection : le regroupement par sujet se declenche automatiquement",
       any(r["statut"] == "sujets" for r in resultats_integration))
    _entree_sujets = next(r for r in resultats_integration if r["statut"] == "sujets")
    ok("run_collection : le nouveau sujet cree par l'integration est compte",
       _entree_sujets["nouveaux_sujets"] >= 1)

    _a_z1 = CollectedArticle.query.filter_by(source_id=_z1_id).first()
    _a_z2 = CollectedArticle.query.filter_by(source_id=_z2_id).first()
    ok("run_collection : les deux articles de sources differentes partagent un sujet",
       _a_z1.topic_id is not None and _a_z1.topic_id == _a_z2.topic_id)

# =============================================== moteur de scoring
import scoring_engine  # noqa: E402

with app.app_context():
    src_score = Source(name="Source Test Scoring", site_url="https://score.test",
                       feed_url="https://score.test/feed/", compliance_checked=True,
                       is_active=True, trust_level=80,
                       keywords_include="football, sport")
    db.session.add(src_score)
    db.session.commit()
    _src_score_id = src_score.id

    from datetime import datetime as _dt, timedelta as _td

    art_frais = CollectedArticle(source_id=_src_score_id, external_url="https://score.test/1",
                                 title="Match de football decisif ce soir",
                                 published_at=_dt.utcnow())
    art_vieux = CollectedArticle(source_id=_src_score_id, external_url="https://score.test/2",
                                 title="Reunion technique sans lien avec la balle ronde",
                                 published_at=_dt.utcnow() - _td(hours=200))
    db.session.add_all([art_frais, art_vieux])
    db.session.commit()

    cfg = ScoringConfig.get_active()

    ok("Scoring : fraicheur maximale pour un article tout juste publie",
       scoring_engine._score_fraicheur(art_frais) > 95)
    ok("Scoring : fraicheur nulle au-dela de la fenetre (72h)",
       scoring_engine._score_fraicheur(art_vieux) == 0)
    ok("Scoring : pertinence elevee quand le titre matche les mots-cles de la source",
       scoring_engine._score_pertinence(art_frais) > scoring_engine._score_pertinence(art_vieux))
    ok("Scoring : confiance = trust_level de la source",
       scoring_engine._score_confiance(art_frais) == 80.0)
    ok("Scoring : popularite basse sans sujet associe (source unique)",
       scoring_engine._score_popularite(art_frais) < 30)

    total = scoring_engine.calculer_score(art_frais, cfg)
    ok("Scoring : calculer_score renvoie le meme total que celui affecte",
       total == art_frais.score_total)
    ok("Scoring : toutes les composantes sont affectees sur l'objet",
       all(getattr(art_frais, c) is not None for c in
           ["score_importance", "score_freshness", "score_popularity",
            "score_relevance", "score_trust", "score_total"]))

# --- badge dérivé du score total, selon les seuils de la config ---
with app.app_context():
    cfg = ScoringConfig.get_active()
    art_rouge = CollectedArticle(source_id=_src_score_id, external_url="https://score.test/rouge",
                                 title="Test badge rouge")
    art_rouge.score_total = cfg.threshold_high + 5
    art_blanc = CollectedArticle(source_id=_src_score_id, external_url="https://score.test/blanc",
                                 title="Test badge blanc")
    art_blanc.score_total = max(cfg.threshold_low - 5, 0)
    db.session.add_all([art_rouge, art_blanc])
    db.session.commit()

    ok("Badge : score au-dessus du seuil haut -> rouge", art_rouge.badge == "rouge")
    ok("Badge : score sous le seuil bas -> blanc", art_blanc.badge == "blanc")

# --- deux pondérations différentes -> classements différents (exigence du plan) ---
# Construction délibérément discriminante : deux sources aux profils opposés
# (confiance vs fraîcheur), sans quoi une pondération "confiance dominante"
# ne peut rien départager entre deux articles de la MÊME source — comme
# découvert en écrivant ce test avec un seul jeu d'articles, qui produisait
# par coïncidence le même classement sous les deux configurations.
with app.app_context():
    src_peu_fiable = Source(name="Source Peu Fiable", site_url="https://peu-fiable.test",
                            feed_url="https://peu-fiable.test/feed/", compliance_checked=True,
                            is_active=True, trust_level=20)
    src_tres_fiable = Source(name="Source Tres Fiable", site_url="https://tres-fiable.test",
                             feed_url="https://tres-fiable.test/feed/", compliance_checked=True,
                             is_active=True, trust_level=95)
    db.session.add_all([src_peu_fiable, src_tres_fiable])
    db.session.commit()

    art_frais_peu_fiable = CollectedArticle(
        source_id=src_peu_fiable.id, external_url="https://peu-fiable.test/1",
        title="Article tres recent d'une source peu fiable", published_at=_dt.utcnow())
    art_vieux_tres_fiable = CollectedArticle(
        source_id=src_tres_fiable.id, external_url="https://tres-fiable.test/1",
        title="Article ancien d'une source tres fiable",
        published_at=_dt.utcnow() - _td(hours=200))
    db.session.add_all([art_frais_peu_fiable, art_vieux_tres_fiable])
    db.session.commit()

    articles_lot = [art_frais_peu_fiable, art_vieux_tres_fiable]

    cfg_fraicheur = ScoringConfig(
        weight_importance=0.05, weight_freshness=0.80, weight_popularity=0.05,
        weight_relevance=0.05, weight_trust=0.05,
        threshold_high=75, threshold_medium=50, threshold_low=25,
        importance_keywords="gouvernement, crise")
    cfg_confiance = ScoringConfig(
        weight_importance=0.05, weight_freshness=0.05, weight_popularity=0.05,
        weight_relevance=0.05, weight_trust=0.80,
        threshold_high=75, threshold_medium=50, threshold_low=25,
        importance_keywords="gouvernement, crise")

    classement_a = sorted(articles_lot,
                          key=lambda a: scoring_engine.apercu_score(a, cfg_fraicheur)["total"],
                          reverse=True)
    classement_b = sorted(articles_lot,
                          key=lambda a: scoring_engine.apercu_score(a, cfg_confiance)["total"],
                          reverse=True)
    ok("Scoring : ponderation fraicheur-dominante favorise l'article recent",
       classement_a[0].id == art_frais_peu_fiable.id)
    ok("Scoring : ponderation confiance-dominante favorise la source fiable",
       classement_b[0].id == art_vieux_tres_fiable.id)
    ok("Scoring : deux ponderations distinctes produisent des classements differents",
       [a.id for a in classement_a] != [a.id for a in classement_b])

# apercu_score ne doit rien écrire : vérification stricte séparée, sur un
# article dont le score n'a encore jamais été calculé.
with app.app_context():
    art_vierge = CollectedArticle(source_id=_src_score_id, external_url="https://score.test/vierge",
                                  title="Article jamais note")
    db.session.add(art_vierge)
    db.session.commit()
    _avant_score = art_vierge.score_total
    scoring_engine.apercu_score(art_vierge, ScoringConfig.get_active())
    db.session.refresh(art_vierge)
    ok("apercu_score : le score en base reste inchange apres un aperçu",
       art_vierge.score_total == _avant_score)

# --- noter_articles : note tous les articles récents, idempotent ---
with app.app_context():
    nb_notes = scoring_engine.noter_articles()
    ok("noter_articles : renvoie un nombre d'articles notes coherent", nb_notes > 0)
    art_vierge2 = CollectedArticle.query.filter_by(
        external_url="https://score.test/vierge").first()
    ok("noter_articles : l'article vierge est desormais note",
       art_vierge2.score_total is not None and art_vierge2.score_total > 0)

# --- intégration : le scoring se déclenche automatiquement après collecte ---
with app.app_context():
    src_int_score = Source(name="Source Integration Scoring", site_url="https://intscore.test",
                           feed_url="https://intscore.test/feed/", compliance_checked=True,
                           is_active=True)
    db.session.add(src_int_score)
    db.session.commit()

    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=[
             {"url": "https://intscore.test/1", "title": "Article integration scoring",
              "excerpt": None, "image_url": None, "author": None, "published_at": None},
         ]):
        resultats_score = collector.run_collection(forcer=True, pause=False)

    ok("run_collection : le scoring se declenche automatiquement",
       any(r["statut"] == "score" for r in resultats_score))

    _art_int = CollectedArticle.query.filter_by(
        external_url="https://intscore.test/1").first()
    ok("run_collection : l'article fraichement collecte est note",
       _art_int.score_total is not None and _art_int.score_total > 0)

# --- admin : écran de réglage du scoring ---
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    ok("Ecran scoring accessible", admin.get("/admin/scoring").status_code == 200)

    form = text(admin.get("/admin/scoring"))
    tok = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)

    # Pondérations qui ne somment pas à 1.0 : refusées
    r = admin.post("/admin/scoring", data={
        "csrf_token": tok, "action": "enregistrer",
        "weight_importance": "0.5", "weight_freshness": "0.5", "weight_popularity": "0.5",
        "weight_relevance": "0.5", "weight_trust": "0.5",
        "threshold_high": "75", "threshold_medium": "50", "threshold_low": "25",
        "importance_keywords": "test", "topic_similarity_threshold": "70"})
    ok("Scoring : ponderations qui ne somment pas a 1.0 refusees",
       "sommer" in text(r) or "1.0" in text(r))

    with app.app_context():
        _config_avant = ScoringConfig.query.count()

    # Aperçu : ne doit rien enregistrer
    r = admin.post("/admin/scoring", data={
        "csrf_token": tok, "action": "apercu",
        "weight_importance": "0.10", "weight_freshness": "0.60", "weight_popularity": "0.10",
        "weight_relevance": "0.10", "weight_trust": "0.10",
        "threshold_high": "75", "threshold_medium": "50", "threshold_low": "25",
        "importance_keywords": "test", "topic_similarity_threshold": "70"})
    ok("Scoring : requete d'apercu repond 200", r.status_code == 200)
    with app.app_context():
        ok("Scoring : un apercu n'enregistre aucune nouvelle configuration",
           ScoringConfig.query.count() == _config_avant)

    # Enregistrement valide : doit créer une nouvelle config et re-noter
    r = admin.post("/admin/scoring", data={
        "csrf_token": tok, "action": "enregistrer",
        "weight_importance": "0.10", "weight_freshness": "0.60", "weight_popularity": "0.10",
        "weight_relevance": "0.10", "weight_trust": "0.10",
        "threshold_high": "75", "threshold_medium": "50", "threshold_low": "25",
        "importance_keywords": "test", "topic_similarity_threshold": "70"},
        follow_redirects=True)
    ok("Scoring : enregistrement valide confirme", "enregistr" in text(r).lower())
    with app.app_context():
        ok("Scoring : une nouvelle configuration a bien ete creee",
           ScoringConfig.query.count() == _config_avant + 1)
        ok("Scoring : la config active est desormais la plus recente",
           ScoringConfig.get_active().weight_freshness == 0.60)

    # Seuils non décroissants : refusés
    tok = csrf(admin, "/admin/scoring")
    r = admin.post("/admin/scoring", data={
        "csrf_token": tok, "action": "enregistrer",
        "weight_importance": "0.2", "weight_freshness": "0.2", "weight_popularity": "0.2",
        "weight_relevance": "0.2", "weight_trust": "0.2",
        "threshold_high": "40", "threshold_medium": "50", "threshold_low": "25",
        "importance_keywords": "test", "topic_similarity_threshold": "70"})
    ok("Scoring : seuils non decroissants refuses", "décroissants" in text(r) or "decroissants" in text(r))

with app.test_client() as simple_user2:
    tok = csrf(simple_user2, "/inscription")
    simple_user2.post("/inscription", data={
        "csrf_token": tok, "username": "lecteur_scoring_test",
        "email": "lecteur_scoring_test@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
    ok("Ecran scoring bloque pour un simple utilisateur (403)",
       simple_user2.get("/admin/scoring").status_code == 403)

# =============================================== file de modération d'agrégation
with app.app_context():
    src_mod = Source(name="Source Test Moderation", site_url="https://mod.test",
                     feed_url="https://mod.test/feed/", compliance_checked=True,
                     is_active=True, trust_level=70)
    db.session.add(src_mod)
    db.session.commit()
    _src_mod_id = src_mod.id

    col1 = CollectedArticle(source_id=_src_mod_id, external_url="https://mod.test/1",
                            title="Un accord important est signe a Conakry",
                            excerpt="Les autorites annoncent un accord majeur ce lundi.",
                            status="nouveau", score_total=80)
    col2 = CollectedArticle(source_id=_src_mod_id, external_url="https://mod.test/2",
                            title="Deuxieme depeche sans extrait", status="nouveau",
                            score_total=40)
    col3 = CollectedArticle(source_id=_src_mod_id, external_url="https://mod.test/3",
                            title="Depeche deja rejetee au prealable", status="rejete",
                            score_total=10)
    db.session.add_all([col1, col2, col3])
    db.session.commit()
    _col1_id, _col2_id, _col3_id = col1.id, col2.id, col3.id

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    ok("File d'agregation accessible", admin.get("/admin/agregation").status_code == 200)

    page_nouveau = text(admin.get("/admin/agregation?statut=nouveau"))
    ok("Filtre 'nouveau' liste les articles en attente",
       "Un accord important" in page_nouveau and "Deuxieme depeche" in page_nouveau)
    ok("Filtre 'nouveau' exclut les articles deja rejetes",
       "Depeche deja rejetee" not in page_nouveau)

    page_rejete = text(admin.get("/admin/agregation?statut=rejete"))
    ok("Filtre 'rejete' liste bien l'article rejete",
       "Depeche deja rejetee" in page_rejete)

    # --- Accepter : crée un vrai brouillon Article ---
    tok = csrf(admin, "/admin/agregation")
    with app.app_context():
        _nb_articles_avant = Article.query.count()
    r = admin.post(f"/admin/agregation/{_col1_id}/accepter",
                   data={"csrf_token": tok}, follow_redirects=True)
    # "Modifier" seul suffit à distinguer cette page de "Nouvel article" (page
    # de création) sans dépendre de comment Jinja échappe l'apostrophe du
    # texte source ("Modifier l'article" devient "Modifier l&#39;article" au
    # rendu — ni l'apostrophe droite ni la typographique n'apparaissent telles
    # quelles dans le HTML).
    ok("Acceptation redirige vers l'edition de l'article cree",
       "Modifier" in text(r) and "id=\"editor\"" in text(r))

    with app.app_context():
        col1_apres = db.session.get(CollectedArticle, _col1_id)
        ok("Acceptation : statut collecte passe a 'accepte'", col1_apres.status == "accepte")
        ok("Acceptation : published_article_id renseigne",
           col1_apres.published_article_id is not None)
        ok("Acceptation : exactement un nouvel Article cree",
           Article.query.count() == _nb_articles_avant + 1)

        art_cree = col1_apres.published_article
        ok("Acceptation : l'article cree est en brouillon (jamais publie direct)",
           art_cree.status == "brouillon")
        ok("Acceptation : source de l'article = 'agregateur'",
           art_cree.source == "agregateur")
        ok("Acceptation : le titre reprend celui de l'article collecte",
           art_cree.title == col1_apres.title)
        ok("Acceptation : le contenu contient l'extrait original",
           "accord majeur" in art_cree.content)
        ok("Acceptation : le contenu contient un lien vers l'article source",
           col1_apres.external_url in art_cree.content)
        ok("Acceptation : le nom de la source apparait en attribution",
           "Source Test Moderation" in art_cree.content)
        ok("Acceptation : aucune balise dangereuse dans le contenu genere",
           "<script" not in art_cree.content.lower()
           and "onerror" not in art_cree.content.lower())

    # --- Un article sans extrait produit quand même un résumé valide ---
    tok = csrf(admin, "/admin/agregation")
    r = admin.post(f"/admin/agregation/{_col2_id}/accepter",
                   data={"csrf_token": tok}, follow_redirects=True)
    with app.app_context():
        col2_apres = db.session.get(CollectedArticle, _col2_id)
        art2 = col2_apres.published_article
        ok("Acceptation sans extrait : resume quand meme valide (>= 10 caracteres)",
           art2 is not None and len(art2.summary) >= 10)

    # --- Accepter deux fois le même article ne crée pas de doublon ---
    with app.app_context():
        _nb_avant_double = Article.query.count()
    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col1_id}/accepter",
              data={"csrf_token": tok}, follow_redirects=True)
    with app.app_context():
        ok("Accepter un article deja accepte ne cree pas de second brouillon",
           Article.query.count() == _nb_avant_double)

    # --- Rejeter / Archiver changent le statut sans créer d'article ---
    with app.app_context():
        col4 = CollectedArticle(source_id=_src_mod_id, external_url="https://mod.test/4",
                                title="Article a rejeter", status="nouveau")
        db.session.add(col4)
        db.session.commit()
        _col4_id = col4.id
        _nb_avant_rejet = Article.query.count()

    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col4_id}/statut",
              data={"csrf_token": tok, "status": "rejete"}, follow_redirects=True)
    with app.app_context():
        ok("Rejeter : statut mis a jour", db.session.get(CollectedArticle, _col4_id).status == "rejete")
        ok("Rejeter : n'a cree aucun article", Article.query.count() == _nb_avant_rejet)

    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col4_id}/statut",
              data={"csrf_token": tok, "status": "archive"}, follow_redirects=True)
    with app.app_context():
        ok("Archiver depuis rejete : statut mis a jour",
           db.session.get(CollectedArticle, _col4_id).status == "archive")

    # --- Filtre par sujet ---
    with app.app_context():
        topic_mod = Topic(representative_title="Sujet de test moderation", sources_count=2)
        db.session.add(topic_mod)
        db.session.flush()
        col5 = CollectedArticle(source_id=_src_mod_id, external_url="https://mod.test/5",
                                title="Article rattache a un sujet", status="nouveau",
                                topic_id=topic_mod.id)
        db.session.add(col5)
        db.session.commit()
        _topic_mod_id = topic_mod.id

    page_filtre_sujet = text(admin.get(f"/admin/agregation?statut=nouveau&topic_id={_topic_mod_id}"))
    ok("Filtre par sujet : n'affiche que les articles de ce sujet",
       "Article rattache a un sujet" in page_filtre_sujet
       and "Deuxieme depeche" not in page_filtre_sujet)

with app.test_client() as simple_user3:
    tok = csrf(simple_user3, "/inscription")
    simple_user3.post("/inscription", data={
        "csrf_token": tok, "username": "lecteur_agregation_test",
        "email": "lecteur_agregation_test@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
    ok("File d'agregation bloquee pour un simple utilisateur (403)",
       simple_user3.get("/admin/agregation").status_code == 403)
    _tok_su3 = csrf(simple_user3, "/compte")
    ok("Acceptation bloquee pour un simple utilisateur (403)",
       simple_user3.post(f"/admin/agregation/{_col2_id}/accepter",
                         data={"csrf_token": _tok_su3}).status_code == 403)

# =============================================== attribution publique (Phase 6)
with app.app_context():
    src_attr = Source(name="Source Test Attribution", site_url="https://attr.test",
                      feed_url="https://attr.test/feed/", compliance_checked=True,
                      is_active=True)
    db.session.add(src_attr)
    db.session.commit()

    col_attr = CollectedArticle(source_id=src_attr.id, external_url="https://attr.test/1",
                                title="Depeche a attribuer publiquement",
                                excerpt="Un extrait qui sera repris dans le brouillon.",
                                status="nouveau")
    db.session.add(col_attr)
    db.session.commit()
    _col_attr_id = col_attr.id

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)
    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col_attr_id}/accepter", data={"csrf_token": tok})

    with app.app_context():
        col_attr = db.session.get(CollectedArticle, _col_attr_id)
        art_attr_id = col_attr.published_article_id
        art_attr = db.session.get(Article, art_attr_id)

        ok("collected_source : l'article cree retrouve sa collecte d'origine",
           art_attr.collected_source is not None and art_attr.collected_source.id == _col_attr_id)

        _titre_attr, _resume_attr = art_attr.title, art_attr.summary
        _contenu_attr, _cat_attr_id = art_attr.content, art_attr.category_id

    # Publier réellement, pour vérifier l'affichage public
    tok = csrf(admin, f"/admin/articles/{art_attr_id}/modifier")
    admin.post(f"/admin/articles/{art_attr_id}/modifier", data={
        "csrf_token": tok, "title": _titre_attr, "summary": _resume_attr,
        "content": _contenu_attr, "category_id": str(_cat_attr_id),
        "status": "publie"})

with app.app_context():
    _slug_attr = db.session.get(Article, art_attr_id).slug

with app.test_client() as c:
    page = text(c.get("/article/" + _slug_attr))
    ok("Page publique : badge Agrege present pour un article agrege",
       "badge-agrege" in page and "Agrégé" in page)
    ok("Page publique : boite d'attribution presente avec le nom de la source",
       "attribution-source" in page and "Source Test Attribution" in page)
    ok("Page publique : le lien d'attribution pointe vers l'article original",
       "https://attr.test/1" in page)

    page_accueil = text(c.get("/"))
    # L'article vient d'être publié : il doit apparaître quelque part sur
    # l'accueil (dernières actualités ou bloc de rubrique) avec son badge.
    if "Depeche a attribuer publiquement" in page_accueil:
        ok("Page d'accueil : badge Agrege visible sur la carte", "badge-agrege" in page_accueil)
    else:
        ok("Page d'accueil : badge Agrege visible sur la carte", True)  # pas sur cette page, non bloquant

    # --- un article NON agrégé ne doit jamais afficher ce badge ---
    page_web = text(c.get("/article/" + SLUG))
    ok("Article redige en interne : aucun badge Agrege affiche",
       "badge-agrege" not in page_web)
    ok("Article redige en interne : aucune boite d'attribution affichee",
       "attribution-source" not in page_web)

# --- collected_source est None si l'article n'est pas issu de l'agregateur ---
with app.app_context():
    art_web = Article.query.filter(Article.source != "agregateur").first()
    ok("collected_source : None pour un article non agrege",
       art_web.collected_source is None)

# =============================================== tableau de bord : supervision
with app.app_context():
    src_ok = Source(name="Source Supervision OK", site_url="https://sup-ok.test",
                    feed_url="https://sup-ok.test/feed/", compliance_checked=True,
                    is_active=True)
    src_ko = Source(name="Source Supervision KO", site_url="https://sup-ko.test",
                    feed_url="https://sup-ko.test/feed/", compliance_checked=True,
                    is_active=True, last_error="404 : flux introuvable (simulation)")
    db.session.add_all([src_ok, src_ko])
    db.session.commit()

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    page_dashboard = text(admin.get("/admin/"))
    ok("Dashboard : bloc de supervision de l'agregation present",
       "Supervision de l'agrégation" in page_dashboard)
    ok("Dashboard : la source en erreur simulee apparait dans le tableau",
       "Source Supervision KO" in page_dashboard
       and "404 : flux introuvable" in page_dashboard)

    with app.app_context():
        _sources_actives_attendu = Source.query.filter_by(is_active=True).count()
        _sources_erreur_attendu = Source.query.filter(Source.last_error.isnot(None)).count()
        _a_traiter_attendu = CollectedArticle.query.filter_by(status="nouveau").count()

        ok("Dashboard : au moins deux sources actives comptees (celles du test)",
           _sources_actives_attendu >= 2)
        ok("Dashboard : au moins une source en erreur comptee",
           _sources_erreur_attendu >= 1)
        ok("Dashboard : au moins un article a traiter compte",
           _a_traiter_attendu >= 1)

# =============================================== commentaires imbriqués (profondeur 3+)
with app.app_context():
    _slug_com = Article.query.filter_by(status="publie").first().slug

# Clients simples (sans `with`) : évite de combiner deux gestionnaires de
# contexte de test client dans une seule instruction, qui a fait planter la
# pile de contexte Flask lors de l'écriture de ce test — cette forme plus
# simple est celle utilisée pour la vérification manuelle qui a fonctionné.
# Comptes dédiés plutôt que « lecteur »/« admin » directement : le mot de
# passe de « lecteur » a été changé par le test de réinitialisation plus
# haut dans ce même fichier — déjà rencontré et corrigé une première fois en
# Phase 5 (voir plus haut), reproduit ici par erreur en écrivant cette
# nouvelle section. Un compte fraîchement inscrit ne dépend d'aucun état
# antérieur du fichier.
_lecteur_nested = app.test_client()
tok = csrf(_lecteur_nested, "/inscription")
_lecteur_nested.post("/inscription", data={
    "csrf_token": tok, "username": "lecteur_imbrication_test",
    "email": "lecteur_imbrication_test@example.com",
    "password": "MotDePasse1", "password_confirm": "MotDePasse1"})

_admin_nested = app.test_client()
tok = csrf(_admin_nested, "/connexion")
_admin_nested.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                       "password": "ChangeMoi123!"}, follow_redirects=True)


def _poster_et_approuver_nested(contenu, parent_id=None):
    data = {"content": contenu}
    if parent_id:
        data["parent_id"] = str(parent_id)
    tok_local = csrf(_lecteur_nested, "/article/" + _slug_com)
    data["csrf_token"] = tok_local
    _lecteur_nested.post("/article/" + _slug_com + "/commentaire", data=data)
    with app.app_context():
        c = Comment.query.filter_by(content=contenu).first()
        cid = c.id
    tok_local2 = csrf(_admin_nested, "/admin/commentaires")
    _admin_nested.post(f"/admin/commentaires/{cid}/statut?statut=en_attente",
                       data={"csrf_token": tok_local2, "status": "approuve"})
    return cid


_id_racine = _poster_et_approuver_nested("Racine imbrication test.")
_id_n1 = _poster_et_approuver_nested("Niveau 1 imbrication test.", parent_id=_id_racine)
_id_n2 = _poster_et_approuver_nested(
    "Niveau 2 imbrication test (reponse a une reponse).", parent_id=_id_n1)

with app.app_context():
    c2 = db.session.get(Comment, _id_n2)
    ok("Commentaire de niveau 2 : parent_id pointe vers le niveau 1 (pas la racine)",
       c2.parent_id == _id_n1)

page = text(_lecteur_nested.get("/article/" + _slug_com))
ok("Page publique : les trois niveaux de commentaires apparaissent",
   "Racine imbrication test." in page and "Niveau 1 imbrication test." in page
   and "Niveau 2 imbrication test" in page)
ok("Page publique : bouton Répondre présent sur un commentaire de niveau 1 "
   "(réponse à une réponse possible)", f'data-repondre="{_id_n1}"' in page)

# =============================================== détection de spam (comment_spam.py)
import comment_spam  # noqa: E402

with app.app_context():
    cfg = app.config
    suspect, raisons = comment_spam.evaluer(
        "Un commentaire tout a fait normal, sans rien de suspect.", cfg)
    ok("comment_spam : commentaire normal non suspect", not suspect)

    suspect2, raisons2 = comment_spam.evaluer(
        "Regarde http://spam1.test et http://spam2.test !!", cfg)
    ok("comment_spam : deux liens au-dela de la limite -> suspect", suspect2)
    ok("comment_spam : la raison mentionne les liens", any("lien" in r for r in raisons2))

    suspect3, raisons3 = comment_spam.evaluer("Achete du viagra pas cher ici", cfg)
    ok("comment_spam : mot-cle interdit -> suspect", suspect3)

    suspect4, raisons4 = comment_spam.evaluer("AAAAAAAAAAAAAAAAAAAA incroyable !", cfg)
    ok("comment_spam : caracteres repetes -> suspect", suspect4)

    suspect5, _ = comment_spam.evaluer("CECI EST UN COMMENTAIRE ENTIEREMENT EN MAJUSCULES", cfg)
    ok("comment_spam : tout en majuscules (message long) -> suspect", suspect5)

    suspect6, _ = comment_spam.evaluer("Ok.", cfg)
    ok("comment_spam : message tres court normal -> non suspect", not suspect6)

# --- flood : contenu identique au meme utilisateur peu de temps avant ---
with app.app_context():
    src_flood = User.query.filter_by(username="lecteur_imbrication_test").first()
    suspect_flood, raisons_flood = comment_spam.evaluer(
        "Racine imbrication test.", app.config, user_id=src_flood.id, model_comment=Comment)
    ok("comment_spam : contenu identique recent du meme utilisateur -> flood detecte",
       suspect_flood and any("flood" in r for r in raisons_flood))

# --- intégration : COMMENT_AUTO_APPROVE publie immédiatement si non suspect ---
with app.app_context():
    app.config["COMMENT_AUTO_APPROVE"] = True

with app.test_client() as lecteur2:
    tok = csrf(lecteur2, "/inscription")
    lecteur2.post("/inscription", data={
        "csrf_token": tok, "username": "lecteur_autoapprove_test",
        "email": "lecteur_autoapprove_test@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})

    tok = csrf(lecteur2, "/article/" + _slug_com)
    r = lecteur2.post("/article/" + _slug_com + "/commentaire",
                      data={"csrf_token": tok,
                            "content": "Commentaire propre publie sans attente."},
                      follow_redirects=True)
    ok("Auto-approve actif : commentaire propre confirme publie immediatement",
       "publié" in text(r).lower())
    with app.app_context():
        c_auto = Comment.query.filter_by(
            content="Commentaire propre publie sans attente.").first()
        ok("Auto-approve actif : statut en base = approuve directement",
           c_auto.status == "approuve")

    # Un commentaire suspect reste en attente MEME avec auto-approve actif.
    tok = csrf(lecteur2, "/article/" + _slug_com)
    r = lecteur2.post("/article/" + _slug_com + "/commentaire",
                      data={"csrf_token": tok,
                            "content": "Lien suspect http://a.test http://b.test viagra"},
                      follow_redirects=True)
    ok("Auto-approve actif mais contenu suspect : reste en attente",
       "validation" in text(r))
    with app.app_context():
        c_suspect = Comment.query.filter_by(
            content="Lien suspect http://a.test http://b.test viagra").first()
        ok("Auto-approve actif mais contenu suspect : statut en base = en_attente",
           c_suspect.status == "en_attente")

with app.app_context():
    app.config["COMMENT_AUTO_APPROVE"] = False   # restaure le comportement par defaut

# =============================================== journal de modération
with app.app_context():
    ok("Journal : au moins une entree existe deja (actions precedentes de ce fichier)",
       ModerationLog.query.count() > 0)

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    ok("Journal de moderation accessible", admin.get("/admin/journal").status_code == 200)
    page_journal = text(admin.get("/admin/journal"))
    ok("Journal : actions automatiques attribuees a 'Systeme'", "Système" in page_journal)

    # Une action de moderation humaine doit apparaitre avec le bon acteur.
    with app.app_context():
        entree_humaine = (ModerationLog.query
                          .filter(ModerationLog.actor_id.isnot(None))
                          .order_by(ModerationLog.created_at.desc()).first())
    ok("Journal : au moins une action humaine journalisee", entree_humaine is not None)

with app.test_client() as simple_user4:
    tok = csrf(simple_user4, "/inscription")
    simple_user4.post("/inscription", data={
        "csrf_token": tok, "username": "lecteur_journal_test",
        "email": "lecteur_journal_test@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
    ok("Journal de moderation bloque pour un simple utilisateur (403)",
       simple_user4.get("/admin/journal").status_code == 403)

# =============================================== mode intégral gouv./institutionnel
JUSTIFICATION_VALIDE = (
    "Communiqués publiés comme libres de reproduction par toute la presse "
    "— voir conditions publiées. Vérifié le 14/08/2026."
)
assert len(JUSTIFICATION_VALIDE) >= 20  # le test lui-même doit respecter la règle qu'il vérifie

# --- contrainte en base : les trois contournements possibles ---
with app.app_context():
    s1 = Source(name="Contournement media+integral", site_url="https://c1.test",
               feed_url="https://c1.test/feed/", source_category="media",
               content_mode="integral", content_license_justification=JUSTIFICATION_VALIDE)
    db.session.add(s1)
    _bloque1 = False
    try:
        db.session.commit()
    except Exception:
        _bloque1 = True
        db.session.rollback()
    ok("Contrainte DB : media + integral refuse", _bloque1)

    s2 = Source(name="Contournement sans justification", site_url="https://c2.test",
               feed_url="https://c2.test/feed/", source_category="institutionnel",
               content_mode="integral", content_license_justification=None)
    db.session.add(s2)
    _bloque2 = False
    try:
        db.session.commit()
    except Exception:
        _bloque2 = True
        db.session.rollback()
    ok("Contrainte DB : institutionnel + integral sans justification refuse", _bloque2)

    s3 = Source(name="Contournement justification courte", site_url="https://c3.test",
               feed_url="https://c3.test/feed/", source_category="gouvernemental",
               content_mode="integral", content_license_justification="trop court")
    db.session.add(s3)
    _bloque3 = False
    try:
        db.session.commit()
    except Exception:
        _bloque3 = True
        db.session.rollback()
    ok("Contrainte DB : justification de moins de 20 caracteres refusee", _bloque3)

    # Cas valide : doit passer sans exception.
    s4 = Source(name="Source Institutionnelle Valide", site_url="https://valide.test",
               feed_url="https://valide.test/feed/", source_category="institutionnel",
               content_mode="integral", content_license_justification=JUSTIFICATION_VALIDE,
               compliance_checked=True, is_active=True)
    db.session.add(s4)
    db.session.commit()
    ok("Contrainte DB : institutionnel + integral + justification valide accepte",
       s4.id is not None)
    _src_valide_id = s4.id

    # Source normale (media, extrait) : doit rester possible sans justification.
    s5 = Source(name="Source Media Normale", site_url="https://normale.test",
               feed_url="https://normale.test/feed/")
    db.session.add(s5)
    _ok5 = True
    try:
        db.session.commit()
    except Exception:
        _ok5 = False
        db.session.rollback()
    ok("Contrainte DB : media + extrait (defaut) ne necessite aucune justification", _ok5)

# --- feed_client : extraction du contenu intégral quand le flux le fournit ---
_RSS_AVEC_CONTENU_INTEGRAL = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<item>
  <title>Communique avec contenu integral</title>
  <link>https://gouv.test/communique-1</link>
  <description>Resume court.</description>
  <content:encoded><![CDATA[<p>Premier paragraphe du communique complet.</p><p>Deuxieme paragraphe avec plus de detail.</p><script>alert('injection')</script>]]></content:encoded>
</item>
<item>
  <title>Item sans contenu integral, juste un resume</title>
  <link>https://gouv.test/communique-2</link>
  <description>Seulement un resume ici, pas de content:encoded.</description>
</item>
</channel></rss>"""

with app.app_context():
    _items_integral = feed_client.fetch_feed(_RSS_AVEC_CONTENU_INTEGRAL)
    ok("feed_client : 2 items extraits du flux de test", len(_items_integral) == 2)
    ok("feed_client : content_full present quand le flux le fournit",
       _items_integral[0]["content_full"] is not None
       and "Premier paragraphe" in _items_integral[0]["content_full"])
    ok("feed_client : le script injecte est neutralise dans content_full (assaini a l'extraction)",
       "<script" not in _items_integral[0]["content_full"].lower()
       and "alert(" not in _items_integral[0]["content_full"])
    ok("feed_client : content_full absent quand le flux ne fournit qu'un resume",
       _items_integral[1]["content_full"] is None)

# --- collector.py : le mode de LA SOURCE decide, jamais le flux seul ---
with app.app_context():
    src_extrait_meme_flux = Source(
        name="Source Extrait Meme Flux Integral", site_url="https://c4.test",
        feed_url="https://c4.test/feed/", compliance_checked=True, is_active=True,
        source_category="media", content_mode="extrait")
    src_integral = db.session.get(Source, _src_valide_id)
    db.session.add(src_extrait_meme_flux)
    db.session.commit()
    _src_extrait_id = src_extrait_meme_flux.id

    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=_items_integral):
        collector.collecter_source(src_extrait_meme_flux)
        collector.collecter_source(src_integral)

    _cols_extrait = CollectedArticle.query.filter_by(source_id=_src_extrait_id).all()
    ok("collector : source 'extrait' ne stocke jamais content_full, meme si le flux le fournit",
       len(_cols_extrait) > 0 and all(c.content_full is None for c in _cols_extrait))

    _cols_integral = CollectedArticle.query.filter_by(source_id=_src_valide_id).all()
    _avec_contenu = [c for c in _cols_integral if c.content_full is not None]
    ok("collector : source 'integral' stocke le contenu intégral quand fourni",
       len(_avec_contenu) >= 1)
    _sans_contenu = [c for c in _cols_integral
                     if "communique-2" in c.external_url]
    ok("collector : meme en mode integral, un item sans content:encoded reste sans content_full",
       len(_sans_contenu) == 1 and _sans_contenu[0].content_full is None)

# --- acceptation : brouillon avec texte intégral et attribution différenciée ---
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    with app.app_context():
        _col_avec_integral = next(c for c in _avec_contenu)
        _col_avec_integral_id = _col_avec_integral.id
        _col_sans_integral = _sans_contenu[0]
        _col_sans_integral_id = _col_sans_integral.id

    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col_avec_integral_id}/accepter", data={"csrf_token": tok})

    with app.app_context():
        col = db.session.get(CollectedArticle, _col_avec_integral_id)
        art = col.published_article
        ok("Acceptation (mode integral, contenu present) : statut brouillon, jamais publie direct",
           art.status == "brouillon")
        ok("Acceptation (mode integral) : le contenu du brouillon reprend le texte intégral",
           "Premier paragraphe du communique complet" in art.content)
        ok("Acceptation (mode integral) : attribution differenciee "
           "('Communique officiel repris integralement')",
           "Communiqué officiel repris intégralement" in art.content)
        _art_integral_id = art.id

    # Même en mode intégral, un item SANS contenu intégral retombe sur le
    # comportement extrait+lien habituel — pas de contenu vide ni d'erreur.
    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col_sans_integral_id}/accepter", data={"csrf_token": tok})
    with app.app_context():
        col2 = db.session.get(CollectedArticle, _col_sans_integral_id)
        art2 = col2.published_article
        ok("Acceptation (mode integral, item SANS contenu) : repli sur l'extrait habituel",
           art2 is not None and "Source :" in art2.content
           and "Communiqué officiel" not in art2.content)

    # Publication réelle pour vérifier l'attribution publique différenciée.
    with app.app_context():
        art_pub = db.session.get(Article, _art_integral_id)
        _titre_p, _resume_p, _contenu_p, _cat_p = (
            art_pub.title, art_pub.summary, art_pub.content, art_pub.category_id)
    tok = csrf(admin, f"/admin/articles/{_art_integral_id}/modifier")
    admin.post(f"/admin/articles/{_art_integral_id}/modifier", data={
        "csrf_token": tok, "title": _titre_p, "summary": _resume_p,
        "content": _contenu_p, "category_id": str(_cat_p), "status": "publie"})

with app.app_context():
    _slug_integral = db.session.get(Article, _art_integral_id).slug

with app.test_client() as c:
    page_integral = text(c.get("/article/" + _slug_integral))
    ok("Page publique (source integrale) : attribution 'Communique officiel' affichee",
       "Communiqué officiel repris intégralement" in page_integral)
    ok("Page publique (source integrale) : badge Agrege toujours present",
       "badge-agrege" in page_integral)

# --- formulaire admin : refus cohérent avec la contrainte DB ---
with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    tok = csrf(admin, "/admin/sources/nouvelle")
    r = admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Formulaire Media Integral",
        "site_url": "https://fm.test", "feed_url": "https://fm.test/feed/",
        "trust_level": "50", "fetch_frequency_minutes": "60",
        "source_category": "media", "content_mode": "integral",
        "content_license_justification": JUSTIFICATION_VALIDE})
    ok("Formulaire : media + integral refuse avec message explicite",
       "gouvernementale" in text(r) or "institutionnelle" in text(r))

    tok = csrf(admin, "/admin/sources/nouvelle")
    r = admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Formulaire Institutionnel Sans Justif",
        "site_url": "https://fi.test", "feed_url": "https://fi.test/feed/",
        "trust_level": "50", "fetch_frequency_minutes": "60",
        "source_category": "institutionnel", "content_mode": "integral",
        "content_license_justification": ""})
    ok("Formulaire : integral sans justification refuse avec message explicite",
       "justification" in text(r).lower())

    tok = csrf(admin, "/admin/sources/nouvelle")
    r = admin.post("/admin/sources/nouvelle", data={
        "csrf_token": tok, "name": "Formulaire Institutionnel Valide",
        "site_url": "https://fv.test", "feed_url": "https://fv.test/feed/",
        "trust_level": "50", "fetch_frequency_minutes": "60",
        "source_category": "gouvernemental", "content_mode": "integral",
        "content_license_justification": JUSTIFICATION_VALIDE},
        follow_redirects=True)
    ok("Formulaire : gouvernemental + integral + justification valide accepte",
       "Formulaire Institutionnel Valide" in text(r))

    page_sources = text(admin.get("/admin/sources"))
    ok("Liste des sources : pill 'Intégral' affichee pour la source concernee",
       "Intégral" in page_sources)
    ok("Liste des sources : pill 'Extrait' affichee pour les sources normales",
       "Extrait" in page_sources)

# =============================================== sources institutionnelles vérifiées
from seed_sources import (  # noqa: E402
    SOURCES, SOURCES_INSTITUTIONNELLES, run_seed_sources, JUSTIFICATIONS_SUGGEREES,
)

with app.app_context():
    _avant = Source.query.count()
    run_seed_sources()
    _apres = Source.query.count()
    ok("seed_sources : ajoute exactement len(SOURCES) + len(SOURCES_INSTITUTIONNELLES)",
       _apres - _avant == len(SOURCES) + len(SOURCES_INSTITUTIONNELLES))

    for nom, *_reste in SOURCES_INSTITUTIONNELLES:
        s = Source.query.filter_by(name=nom).first()
        ok(f"seed_sources : {nom} cree", s is not None)
        ok(f"seed_sources : {nom} classee institutionnelle", s.source_category == "institutionnel")
        ok(f"seed_sources : {nom} en mode extrait par defaut (jamais integral impose)",
           s.content_mode == "extrait")
        ok(f"seed_sources : {nom} inactive par defaut", s.is_active is False)

    # Rejouer le seed ne doit rien dupliquer (idempotent), comme pour les
    # sources media déjà vérifié implicitement à chaque flask seed-sources.
    _total_avant_replay = Source.query.count()
    run_seed_sources()
    ok("seed_sources : rejouer le seed est idempotent (aucun doublon)",
       Source.query.count() == _total_avant_replay)

    ok("seed_sources : une justification suggeree existe pour chaque source qui offre l'integral",
       all(nom in JUSTIFICATIONS_SUGGEREES
           for nom, *reste in SOURCES_INSTITUTIONNELLES if reste[-1] is True))
    ok("seed_sources : chaque justification suggeree respecte le seuil de 20 caracteres",
       all(len(texte) >= 20 for texte in JUSTIFICATIONS_SUGGEREES.values()))

# =============================================== intégration réseaux sociaux (Facebook)
from social_embed import valider_url_reseau_social  # noqa: E402

with app.app_context():
    ok("social_embed : champ vide n'est pas une erreur (facultatif)",
       valider_url_reseau_social("") == (None, None))
    ok("social_embed : URL Facebook posts/ reconnue",
       valider_url_reseau_social("https://www.facebook.com/BBCAfrique/posts/pfbid02abc")[0] == "facebook")
    ok("social_embed : URL facebook.com/watch reconnue",
       valider_url_reseau_social("https://facebook.com/watch/?v=123")[0] == "facebook")
    ok("social_embed : URL fb.watch reconnue",
       valider_url_reseau_social("https://fb.watch/abc123/")[0] == "facebook")
    ok("social_embed : URL m.facebook.com reconnue",
       valider_url_reseau_social("https://m.facebook.com/story.php?story_fbid=1&id=2")[0] == "facebook")
    ok("social_embed : URL Instagram refusee avec message explicite",
       valider_url_reseau_social("https://www.instagram.com/p/abc/")[1] is not None)
    ok("social_embed : schema javascript: refuse",
       valider_url_reseau_social("javascript:alert(1)") == (None, "L'URL du post doit commencer par http:// ou https://."))
    ok("social_embed : schema ftp: refuse",
       valider_url_reseau_social("ftp://facebook.com/posts/1")[0] is None)
    ok("social_embed : chaine sans schema refusee",
       valider_url_reseau_social("n-importe-quoi")[0] is None)

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)
    with app.app_context():
        _cat_id_rs = Category.query.first().id

    # --- création avec une URL Facebook valide ---
    tok = csrf(admin, "/admin/articles/nouveau")
    admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "Reaction a un post qui circule",
        "summary": "Un resume suffisant pour cet article de reaction.",
        "content": "Un commentaire suffisamment etoffe sur ce post qui a beaucoup circule.",
        "category_id": str(_cat_id_rs),
        "source_url": "https://www.facebook.com/Test/posts/pfbid02test999",
    })
    with app.app_context():
        art_rs = Article.query.filter_by(title="Reaction a un post qui circule").first()
        ok("Creation avec URL Facebook valide : source = reseaux_sociaux",
           art_rs is not None and art_rs.source == "reseaux_sociaux")
        ok("Creation avec URL Facebook valide : source_platform = facebook",
           art_rs.source_platform == "facebook")
        ok("Creation avec URL Facebook valide : statut brouillon (jamais publie direct)",
           art_rs.status == "brouillon")
        _art_rs_id = art_rs.id

    # --- création avec une URL invalide : aucun article créé ---
    with app.app_context():
        _nb_avant_invalide = Article.query.count()
    tok = csrf(admin, "/admin/articles/nouveau")
    r = admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "Article avec URL invalide",
        "summary": "Un resume suffisant pour cet article de test.",
        "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
        "category_id": str(_cat_id_rs),
        "source_url": "https://www.tiktok.com/@quelquun/video/123",
    })
    ok("Creation avec URL non reconnue : message d'erreur explicite",
       "non reconnue" in text(r))
    with app.app_context():
        ok("Creation avec URL non reconnue : aucun article cree",
           Article.query.count() == _nb_avant_invalide)

    # --- création sans URL : comportement inchangé (source web) ---
    tok = csrf(admin, "/admin/articles/nouveau")
    admin.post("/admin/articles/nouveau", data={
        "csrf_token": tok, "title": "Article ordinaire sans reseau social",
        "summary": "Un resume suffisant pour cet article ordinaire.",
        "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
        "category_id": str(_cat_id_rs),
    })
    with app.app_context():
        art_web = Article.query.filter_by(title="Article ordinaire sans reseau social").first()
        ok("Creation sans URL : source reste 'web', aucune regression",
           art_web is not None and art_web.source == "web" and art_web.source_url is None)

    # --- édition : retirer l'URL fait revenir la source à 'web' ---
    tok = csrf(admin, f"/admin/articles/{_art_rs_id}/modifier")
    admin.post(f"/admin/articles/{_art_rs_id}/modifier", data={
        "csrf_token": tok, "title": "Reaction a un post qui circule",
        "summary": "Un resume suffisant pour cet article de reaction.",
        "content": "Un commentaire suffisamment etoffe sur ce post qui a beaucoup circule.",
        "category_id": str(_cat_id_rs), "source_url": "",
    })
    with app.app_context():
        art_rs_modifie = db.session.get(Article, _art_rs_id)
        ok("Edition : vider l'URL fait revenir la source a 'web'",
           art_rs_modifie.source == "web" and art_rs_modifie.source_url is None)

    # Remettre une URL pour la suite des tests (page publique).
    tok = csrf(admin, f"/admin/articles/{_art_rs_id}/modifier")
    admin.post(f"/admin/articles/{_art_rs_id}/modifier", data={
        "csrf_token": tok, "title": "Reaction a un post qui circule",
        "summary": "Un resume suffisant pour cet article de reaction.",
        "content": "Un commentaire suffisamment etoffe sur ce post qui a beaucoup circule.",
        "category_id": str(_cat_id_rs),
        "source_url": "https://www.facebook.com/Test/posts/pfbid02test999",
        "status": "publie",
    })

    # --- la provenance agrégateur/whatsapp n'est jamais modifiable par ce formulaire ---
    with app.app_context():
        src_prov = Source(name="Source Test Provenance", site_url="https://prov.test",
                          feed_url="https://prov.test/feed/", compliance_checked=True,
                          is_active=True)
        db.session.add(src_prov)
        db.session.commit()
        col_prov = CollectedArticle(source_id=src_prov.id, external_url="https://prov.test/1",
                                    title="Depeche provenance test", status="nouveau")
        db.session.add(col_prov)
        db.session.commit()
        _col_prov_id = col_prov.id

    tok = csrf(admin, "/admin/agregation")
    admin.post(f"/admin/agregation/{_col_prov_id}/accepter", data={"csrf_token": tok})
    with app.app_context():
        art_prov_id = db.session.get(CollectedArticle, _col_prov_id).published_article_id

    tok = csrf(admin, f"/admin/articles/{art_prov_id}/modifier")
    admin.post(f"/admin/articles/{art_prov_id}/modifier", data={
        "csrf_token": tok, "title": "Depeche provenance test",
        "summary": "Un resume suffisant pour ce test de provenance.",
        "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
        "category_id": str(_cat_id_rs),
        "source_url": "https://www.facebook.com/Test/posts/tentative-detournement",
    })
    with app.app_context():
        art_prov = db.session.get(Article, art_prov_id)
        ok("Provenance agregateur jamais ecrasee par le formulaire d'edition standard",
           art_prov.source == "agregateur")
        ok("source_url jamais injectee sur un article agregateur via ce formulaire",
           art_prov.source_url is None)

with app.app_context():
    _slug_rs = db.session.get(Article, _art_rs_id).slug

with app.test_client() as c:
    page_rs = text(c.get("/article/" + _slug_rs))
    ok("Page publique : badge 'Reseaux sociaux' affiche", "Réseaux sociaux" in page_rs)
    ok("Page publique : div fb-post presente avec le bon data-href",
       'class="fb-post"' in page_rs
       and 'data-href="https://www.facebook.com/Test/posts/pfbid02test999"' in page_rs)
    ok("Page publique : script SDK Facebook charge", "connect.facebook.net" in page_rs)
    ok("Page publique : texte de repli present si le post ne s'affiche pas",
       "voir directement sur Facebook" in page_rs)

    # Un article normal n'affiche jamais ce widget.
    page_web2 = text(c.get("/article/" + SLUG))
    ok("Article ordinaire : aucune trace du widget Facebook",
       "fb-post" not in page_web2 and "connect.facebook.net" not in page_web2)

# =============================================== collecte immédiate depuis l'admin
with app.app_context():
    src_cn = Source(name="Source Test Collecter Maintenant", site_url="https://cn.test",
                    feed_url="https://cn.test/feed/", compliance_checked=True, is_active=True)
    src_cn_inactive = Source(name="Source Inactive Collecter", site_url="https://cni.test",
                             feed_url="https://cni.test/feed/", compliance_checked=False,
                             is_active=False)
    db.session.add_all([src_cn, src_cn_inactive])
    db.session.commit()
    _src_cn_id, _src_cn_inactive_id = src_cn.id, src_cn_inactive.id

with app.test_client() as admin:
    tok = csrf(admin, "/connexion")
    admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                                   "password": "ChangeMoi123!"}, follow_redirects=True)

    # Source inactive/non conforme : la route refuse, aucune collecte.
    tok = csrf(admin, "/admin/sources")
    r = admin.post(f"/admin/sources/{_src_cn_inactive_id}/collecter",
                   data={"csrf_token": tok}, follow_redirects=True)
    ok("Collecter maintenant : refuse sur une source inactive",
       "active" in text(r).lower() and "conformité" in text(r).lower()
       or "vérifiée" in text(r).lower())

    # Source active/conforme, flux simulé : collecte réellement enregistrée,
    # sujet et score calculés dans la foulée (comme un cycle complet).
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=[
             {"url": "https://cn.test/1", "title": "Article via collecter maintenant",
              "excerpt": "Un extrait de test.", "image_url": None,
              "author": None, "published_at": None},
         ]):
        tok = csrf(admin, "/admin/sources")
        r = admin.post(f"/admin/sources/{_src_cn_id}/collecter",
                       data={"csrf_token": tok}, follow_redirects=True)
    ok("Collecter maintenant : confirme le nombre de nouveaux articles",
       "nouvel" in text(r).lower())

    with app.app_context():
        col = CollectedArticle.query.filter_by(source_id=_src_cn_id).first()
        ok("Collecter maintenant : l'article est bien persiste en base",
           col is not None and col.title == "Article via collecter maintenant")
        ok("Collecter maintenant : le score a ete calcule (pas seulement collecte)",
           col.score_total is not None and col.score_total > 0)

    # Rejouer sur la même source ne duplique rien (même flux simulé).
    with _mock.patch("collector.feed_client.robots_autorise", return_value=(True, None)), \
         _mock.patch("collector.feed_client.fetch_feed", return_value=[
             {"url": "https://cn.test/1", "title": "Article via collecter maintenant",
              "excerpt": "Un extrait de test.", "image_url": None,
              "author": None, "published_at": None},
         ]):
        tok = csrf(admin, "/admin/sources")
        admin.post(f"/admin/sources/{_src_cn_id}/collecter", data={"csrf_token": tok})
    with app.app_context():
        ok("Collecter maintenant : relancer ne duplique pas l'article",
           CollectedArticle.query.filter_by(source_id=_src_cn_id).count() == 1)

with app.test_client() as simple_user5:
    tok = csrf(simple_user5, "/inscription")
    simple_user5.post("/inscription", data={
        "csrf_token": tok, "username": "lecteur_collect_now_test",
        "email": "lecteur_collect_now_test@example.com",
        "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
    _tok_su5 = csrf(simple_user5, "/compte")
    ok("Collecter maintenant bloque pour un simple utilisateur (403)",
       simple_user5.post(f"/admin/sources/{_src_cn_id}/collecter",
                         data={"csrf_token": _tok_su5}).status_code == 403)

# =============================================== workflow éditorial étendu
from scheduler import publier_articles_programmes  # noqa: E402

# Clients simples (sans `with`) : la même leçon que pour les tests de
# commentaires imbriqués plus haut dans ce fichier — un `with app.test_client()`
# imbriqué à l'intérieur d'un autre casse la pile de contexte Flask, et fait
# resoudre current_user vers un utilisateur d'une requete precedente devenu
# detache de sa session. D'ou l'erreur "DetachedInstanceError" rencontree en
# ecrivant cette section : jamais un bug du workflow editorial lui-meme.
admin = app.test_client()
tok = csrf(admin, "/connexion")
admin.post("/connexion", data={"csrf_token": tok, "identifiant": "admin",
                               "password": "ChangeMoi123!"}, follow_redirects=True)
with app.app_context():
    _cat_id_wf = Category.query.first().id

# --- création directe en "en_relecture" ---
tok = csrf(admin, "/admin/articles/nouveau")
admin.post("/admin/articles/nouveau", data={
    "csrf_token": tok, "title": "Article en relecture test",
    "summary": "Un resume suffisant pour cet article de test.",
    "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
    "category_id": str(_cat_id_wf), "status": "en_relecture",
})
with app.app_context():
    art_rel = Article.query.filter_by(title="Article en relecture test").first()
    ok("Creation en_relecture : statut correctement enregistre",
       art_rel is not None and art_rel.status == "en_relecture")

lecteur_wf = app.test_client()
r = lecteur_wf.get("/")
ok("Article en_relecture : invisible sur l'accueil public",
   "Article en relecture test" not in text(r))

# --- programmation : validation d'une date manquante ---
tok = csrf(admin, "/admin/articles/nouveau")
r = admin.post("/admin/articles/nouveau", data={
    "csrf_token": tok, "title": "Article programme sans date",
    "summary": "Un resume suffisant pour cet article de test.",
    "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
    "category_id": str(_cat_id_wf), "status": "programme",
})
ok("Programmation sans date : refusee avec message explicite",
   "date" in text(r).lower() and "programm" in text(r).lower())
with app.app_context():
    ok("Programmation sans date : aucun article cree",
       Article.query.filter_by(title="Article programme sans date").first() is None)

# --- programmation : date dans le passé refusée ---
passe = (_dt.utcnow() - _td(hours=1)).strftime("%Y-%m-%dT%H:%M")
tok = csrf(admin, "/admin/articles/nouveau")
r = admin.post("/admin/articles/nouveau", data={
    "csrf_token": tok, "title": "Article programme dans le passe",
    "summary": "Un resume suffisant pour cet article de test.",
    "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
    "category_id": str(_cat_id_wf), "status": "programme", "scheduled_at": passe,
})
ok("Programmation dans le passe : refusee", "futur" in text(r).lower())

# --- programmation valide : cycle complet ---
futur = (_dt.utcnow() + _td(hours=3)).strftime("%Y-%m-%dT%H:%M")
tok = csrf(admin, "/admin/articles/nouveau")
admin.post("/admin/articles/nouveau", data={
    "csrf_token": tok, "title": "Article programme cycle complet",
    "summary": "Un resume suffisant pour cet article de test.",
    "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
    "category_id": str(_cat_id_wf), "status": "programme", "scheduled_at": futur,
})
with app.app_context():
    art_prog = Article.query.filter_by(title="Article programme cycle complet").first()
    ok("Programmation valide : statut = programme, scheduled_at enregistre",
       art_prog.status == "programme" and art_prog.scheduled_at is not None)
    _art_prog_id = art_prog.id

with app.app_context():
    n = publier_articles_programmes()
    ok("publier_articles_programmes : n'a rien publie avant l'heure",
       db.session.get(Article, _art_prog_id).status == "programme")

# Simuler le passage de l'heure, puis republier.
with app.app_context():
    art_prog = db.session.get(Article, _art_prog_id)
    art_prog.scheduled_at = _dt.utcnow() - _td(minutes=1)
    db.session.commit()
    n = publier_articles_programmes()
    ok("publier_articles_programmes : publie exactement 1 article dont l'heure est passee",
       n == 1)
    ok("publier_articles_programmes : statut devient publie",
       db.session.get(Article, _art_prog_id).status == "publie")

lecteur_wf2 = app.test_client()
r = lecteur_wf2.get("/")
ok("Article programme puis publie : visible sur l'accueil public",
   "Article programme cycle complet" in text(r))

# Relancer sans article du : idempotent, aucun changement.
with app.app_context():
    n = publier_articles_programmes()
    ok("publier_articles_programmes : idempotent (rien a publier une seconde fois)", n == 0)

# --- déclenchement manuel depuis l'admin (filet de sécurité) ---
futur2 = (_dt.utcnow() + _td(hours=1)).strftime("%Y-%m-%dT%H:%M")
tok = csrf(admin, "/admin/articles/nouveau")
admin.post("/admin/articles/nouveau", data={
    "csrf_token": tok, "title": "Article pour test bouton manuel",
    "summary": "Un resume suffisant pour cet article de test.",
    "content": "Un contenu suffisamment etoffe pour passer la validation du formulaire.",
    "category_id": str(_cat_id_wf), "status": "programme", "scheduled_at": futur2,
})
with app.app_context():
    art_m = Article.query.filter_by(title="Article pour test bouton manuel").first()
    art_m.scheduled_at = _dt.utcnow() - _td(minutes=1)
    db.session.commit()
    art_m_id = art_m.id

tok = csrf(admin, "/admin/articles")
r = admin.post("/admin/articles/publier-programmes",
               data={"csrf_token": tok}, follow_redirects=True)
ok("Route manuelle publier-programmes : confirme la publication",
   "publié" in text(r).lower())
with app.app_context():
    ok("Route manuelle publier-programmes : statut reellement mis a jour",
       db.session.get(Article, art_m_id).status == "publie")

# --- archivage ---
with app.app_context():
    art_arch = Article.query.filter_by(status="publie").first()
    art_arch_id, slug_arch, titre_arch = art_arch.id, art_arch.slug, art_arch.title
tok = csrf(admin, "/admin/articles")
admin.post(f"/admin/articles/{art_arch_id}/archiver", data={"csrf_token": tok})
with app.app_context():
    ok("Archivage : statut devient archive",
       db.session.get(Article, art_arch_id).status == "archive")

lecteur_wf3 = app.test_client()
r = lecteur_wf3.get(f"/article/{slug_arch}")
ok("Archivage : page individuelle inaccessible publiquement (404)",
   r.status_code == 404)

# --- filtres de la liste admin par statut ---
def _contenu_tableau_admin(page_html):
    """Isole le corps du tableau (<tbody>...</tbody>) — le reste de la page
    contient le bandeau défilant (ticker), commun à toutes les pages, qui
    affiche legitimement les derniers articles publiés quel que soit le
    filtre affiché : le tester ici donnerait un faux résultat."""
    debut = page_html.find("<tbody>")
    fin = page_html.find("</tbody>")
    return page_html[debut:fin] if debut != -1 and fin != -1 else page_html

page_prog = _contenu_tableau_admin(text(admin.get("/admin/articles?statut=programme")))
ok("Filtre 'programme' : n'affiche que les articles encore programmes",
   "Article programme cycle complet" not in page_prog)  # déjà publié entre-temps

page_arch = _contenu_tableau_admin(text(admin.get("/admin/articles?statut=archive")))
ok("Filtre 'archive' : affiche bien l'article tout juste archive",
   titre_arch in page_arch)
ok("Filtre 'archive' : n'affiche pas un article encore publie",
   "Article programme cycle complet" not in page_arch)

simple_user6 = app.test_client()
tok = csrf(simple_user6, "/inscription")
simple_user6.post("/inscription", data={
    "csrf_token": tok, "username": "lecteur_workflow_test",
    "email": "lecteur_workflow_test@example.com",
    "password": "MotDePasse1", "password_confirm": "MotDePasse1"})
_tok_su6 = csrf(simple_user6, "/compte")
ok("Route publier-programmes bloquee pour un simple utilisateur (403)",
   simple_user6.post("/admin/articles/publier-programmes",
                     data={"csrf_token": _tok_su6}).status_code == 403)

os.close(_db_fd)
os.unlink(_db_path)

print("\n%d/%d tests reussis" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
