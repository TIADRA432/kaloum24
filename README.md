# Kaloum24 — portail d'actualités

Site de médias full-stack, prêt à être adapté et revendu : publication
d'articles avec éditeur riche, comptes lecteurs, commentaires modérés, articles
réservés aux abonnés, paiement récurrent, lecture audio, mode sombre et
optimisations SEO.

Stack : **Flask 3 · SQLite · Jinja2**. Pas de build front, pas de Node, aucune
ressource externe au chargement.

---

## 1. Installation

```bash
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# → génère une SECRET_KEY :
#   python -c "import secrets; print(secrets.token_hex(32))"

export FLASK_APP=app.py           # Windows : set FLASK_APP=app.py
flask db upgrade                  # crée la base via les migrations
flask seed-db                     # optionnel : contenu de démonstration

flask run
```

Site sur **http://127.0.0.1:5000**

### Comptes de démonstration

Créés par `flask seed-db`. **À supprimer avant toute mise en ligne.**

| Compte    | Mot de passe    | Rôle  |
| --------- | --------------- | ----- |
| `admin`   | `ChangeMoi123!` | admin |
| `lecteur` | `Lecteur123!`   | user  |

Pour un vrai compte administrateur : `flask create-admin`

---

## 2. Fonctionnalités

### Lecture
- Une, articles secondaires, dernières actualités, blocs par rubrique, plus lus
- Pages par rubrique avec pagination, recherche plein texte
- **Mode sombre / clair** — mémorisé, suit la préférence système par défaut
- **Lecture audio** des articles (voir §4)
- **Partage** WhatsApp, X, Facebook et copie du lien sur chaque article
- **Météo** dans l'en-tête (Open-Meteo, gratuit, sans clé)
- Temps de lecture estimé, crédit photo, articles similaires

### Comptes et commentaires
- Inscription, connexion, profil, changement de mot de passe
- **Réinitialisation par e-mail** avec jeton signé valable 1 heure
- Commentaires avec **réponses imbriquées**, **signalement** par les lecteurs,
  et modération obligatoire avant publication
- Bannissement d'un compte sans suppression

### Espace rédaction
- **Éditeur riche** (gras, italique, intertitres, listes, citations, liens,
  images dans le texte)
- **Upload d'images** avec redimensionnement et compression automatiques
- **Publication par WhatsApp** — un correspondant rédige et envoie sa photo
  entièrement depuis WhatsApp, l'article arrive en brouillon (voir §5)
- Brouillons, mise à la une, articles réservés aux abonnés, crédit photo
- File de modération, filtre des commentaires signalés, approbation groupée
- Gestion des rubriques, des rôles, des correspondants et des bannissements
- Tableau de bord : lectures, articles, abonnés, brouillons WhatsApp

### SEO et partage
- **Open Graph et Twitter Card** — aperçu correct sur WhatsApp et Facebook
- **Flux RSS** (`/rss.xml`), **sitemap** (`/sitemap.xml`), **robots.txt**
- **Données structurées** `NewsArticle` (schema.org)
- URL canoniques, slugs lisibles

### Abonnements
- Paywall sur les articles premium
- Stripe Checkout + webhook d'activation (voir §6)

---

## 3. Performance

Mesurée sur ce projet avec `python mesure_poids.py` :

| Page | Poids transféré | Requêtes | Ressources tierces |
| ---- | --------------- | -------- | ------------------ |
| Accueil (1re visite) | ~196 Ko | 8 | **0** |
| Article (1re visite) | ~193 Ko | 8 | **0** |
| Page suivante (cache actif) | ~98 Ko | 8 | **0** |

Ces chiffres sont ceux de la structure de page, **hors photos d'articles** :
ajoute le poids réel de tes images. Une grande partie de la première visite
correspond aux polices, mises en cache ensuite.

**Pourquoi zéro ressource tierce.** Les polices et l'éditeur sont servis depuis
le serveur du site, pas depuis Google Fonts ou un CDN. Concrètement : une
connexion de moins à négocier (DNS + TLS, coûteux sur mobile lent), et le site
reste complet même si le CDN est inaccessible.

À titre de comparaison, un site d'actualités sous WordPress avec un thème du
commerce dépasse fréquemment 3 Mo et 80 requêtes sur la page d'accueil. Sur une
connexion 3G et avec des forfaits data facturés au mégaoctet, l'écart est
directement perceptible par le lecteur.

**Vérifie toi-même avant de l'affirmer à un client :** mesure ce site *et* deux
ou trois sites concurrents avec PageSpeed Insights ou l'onglet Réseau du
navigateur, et cite tes propres chiffres.

---

## 4. Lecture audio des articles

Le bouton **Écouter** utilise l'API de synthèse vocale intégrée au navigateur
(`speechSynthesis`).

**Pourquoi ce choix plutôt que Google Cloud TTS :**

| | API du navigateur | Google Cloud TTS |
| --- | --- | --- |
| Coût | Gratuit, illimité | Facturé au caractère |
| Clé API | Aucune | Une par client, à gérer |
| Qualité | Correcte à bonne | Meilleure |
| Fonctionne hors ligne | Oui | Non |

Sur Chrome et Android, les voix utilisées sont celles de Google. Pour un site
revendu à des clients, l'absence de coût récurrent et de clé à administrer pèse
plus lourd que le gain de qualité.

**Limites à connaître :** la qualité et la disponibilité des voix françaises
dépendent de l'appareil du lecteur. Sur un appareil sans voix française
installée, la lecture peut sonner artificielle. Le bouton se masque
automatiquement si le navigateur ne gère pas la fonctionnalité.

Désactivation : `TTS_ENABLED=0` dans `.env`.

---

## 5. Agrégation de sources externes

Kaloum24 peut surveiller des sites d'actualité tiers via leur flux RSS/Atom
et faire remonter leurs titres dans l'espace rédaction — jamais publiés
automatiquement, jamais avec le contenu intégral. Le détail complet du
principe, du modèle de données et du plan d'implémentation par phases est
dans **`PLAN_AGREGATEUR.md`**, à la racine du projet.

### Ce qui est livré à ce stade (Phase 0-1 du plan)

- Gestion des sources depuis **Sources** dans l'espace rédaction : CRUD
  complet, niveau de confiance, fréquence de collecte, mots-clés à
  privilégier/exclure, rubrique par défaut.
- Bouton **Tester** : lit les premiers items du flux sans rien enregistrer,
  pour valider la configuration avant d'activer la collecte pour de bon.
- **Une source ne peut pas être activée sans avoir coché la vérification de
  conformité** (`robots.txt` / CGU) — appliqué à la fois côté formulaire et
  par une contrainte en base de données, pas seulement documenté.
- `flask seed-sources` enregistre 15 sources vérifiées (flux RSS confirmé,
  `robots.txt` sans restriction) — 12 médias ouest-africains et 3
  institutionnelles (CEDEAO, Union Africaine, OMS), **toutes inactives par
  défaut** et **toutes en mode extrait** — l'activation et le passage
  éventuel en mode intégral (voir plus bas) restent un choix explicite de
  l'admin, jamais hérité du script de seed.

### Le moteur de collecte (Phase 2)

```bash
flask collect-sources          # collecte les sources actives dont la fréquence est échue
flask collect-sources --force  # ignore la fréquence, collecte tout de suite
```

À lancer périodiquement via cron (voir `deploiement/`) — même principe que
les sauvegardes. Chaque exécution :

- **revérifie `robots.txt` en direct** avant de lire un flux, pas seulement
  au moment où l'admin a coché la conformité — un site peut changer sa
  politique après coup ;
- respecte le `crawl-delay` du site s'il en réclame un, et espace ses
  requêtes d'au moins 2 secondes entre chaque source par politesse ;
- ignore les articles déjà connus (contrainte d'unicité source + URL) ;
- applique le filtrage par mots-clés inclus/exclus défini sur la source,
  insensible aux accents (« guinee » retrouve « Guinée ») ;
- consigne l'erreur sur la source et **continue avec les suivantes** si un
  flux est indisponible — une source en panne n'interrompt jamais les
  autres.

Le nombre d'articles collectés par source est visible dans la colonne
**Collectés** de la liste des sources.

### Détection de doublons et regroupement par sujet (Phase 3)

Après chaque collecte, les articles fraîchement récupérés sont automatiquement
comparés entre eux (`topic_matcher.py`) : deux titres suffisamment proches,
venant de **sources différentes**, rejoignent le même `Topic`. Une source ne
« confirme » jamais son propre sujet — il en faut au moins deux.

Méthode : similarité textuelle sur les titres (`rapidfuzz`), pas de modèle
sémantique. **Limite assumée et vérifiée par un test dédié** : les trois
titres donnés en exemple dans le cahier des charges (des reformulations très
éloignées lexicalement du même événement) scorent entre 49 et 67 sur 100 —
sous le seuil retenu de 70. Un seuil assez bas pour les regrouper créerait
des faux positifs massifs entre articles sans rapport. Sur des reformulations
plus proches (le cas le plus fréquent en pratique), la méthode fonctionne
bien — vérifié sur cinq cas réels, cinq corrects, dont un piège volontaire
(deux effondrements d'immeubles différents, correctement séparés).

Le seuil (`ScoringConfig.topic_similarity_threshold`, 70 par défaut) est
réglable depuis **Scoring** dans l'espace rédaction, avec le reste des
pondérations — voir la section suivante.

### Scoring configurable (Phase 4)

Après chaque collecte et regroupement, chaque article reçoit un score sur
cinq composantes indépendantes (`scoring_engine.py`), combinées selon les
pondérations de `ScoringConfig` :

| Composante | Calcul |
| --- | --- |
| Fraîcheur | Décroît linéairement sur 72 h depuis la publication |
| Popularité | Dérivée du nombre de sources sur le même sujet (Phase 3) |
| Fiabilité source | `Source.trust_level`, réglé à la création de la source |
| Pertinence | Correspondance avec les mots-clés propres à la source |
| Importance | Correspondance avec un vocabulaire d'alerte global, réglable |

Chaque article reçoit ensuite un badge — 🔴 très important, 🟠 important,
🟡 à surveiller, ⚪ faible priorité — selon des seuils eux aussi réglables.

**Écran admin → Scoring** : ajuste les pondérations, clique sur **Aperçu**
pour voir l'effet sur les 15 derniers articles collectés sans rien
enregistrer, puis **Enregistrer** pour appliquer pour de bon — tous les
articles récents sont alors re-notés. Vérifié avec deux jeux de pondérations
opposés (fraîcheur dominante vs fiabilité dominante) sur les mêmes articles :
les classements obtenus diffèrent, comme attendu.

### File de modération éditoriale (Phase 5)

**Écran admin → Agrégation** : les articles collectés, regroupés et notés
apparaissent triés par score décroissant, avec leur badge, leur source et,
s'ils font partie d'un sujet suivi par plusieurs sources, un lien pour voir
les autres articles du même sujet.

Trois actions, jamais automatiques :

- **Accepter** crée un vrai brouillon `Article` Kaloum24 — jamais publié
  directement — pré-rempli avec le titre, la rubrique héritée de la source,
  et un contenu qui contient toujours l'extrait **suivi d'une attribution
  explicite avec lien cliquable vers l'article original**. L'admin est
  redirigé droit vers l'édition du brouillon pour le compléter avant de
  publier, exactement comme pour un article WhatsApp.
- **Rejeter** et **Archiver** changent le statut sans jamais créer d'article.

Accepter deux fois le même article collecté ne crée pas de second brouillon.
Un article sans extrait produit quand même un résumé valide plutôt que de
bloquer l'acceptation.

### Attribution publique et supervision (Phase 6)

Un article publié à partir de l'agrégateur (`Article.source == "agregateur"`)
porte désormais, côté public :

- un badge **Agrégé** (contour, distinct du badge doré « Abonnés ») sur
  toutes les cartes où il apparaît — accueil, rubrique, recherche ;
- sur sa page, une boîte d'attribution dédiée juste avant le corps du
  texte : « Contenu agrégé — article original sur *NomSource* ↗ », avec un
  lien direct vers l'article d'origine.

Cette boîte est générée depuis un lien structurel (`Article.collected_source`,
qui retrouve la `CollectedArticle` d'origine) — elle reste donc affichée même
si l'admin réécrit entièrement le corps du brouillon après acceptation.
Un article rédigé en interne ou reçu par WhatsApp n'affiche jamais ce badge
ni cette boîte.

**Tableau de bord → Supervision de l'agrégation** : sources actives, sources
en erreur (avec le détail de la dernière erreur et de la dernière tentative
pour chacune), articles collectés sur 24 h et sur 7 jours, articles en
attente de traitement, articles acceptés.

### Contenu intégral — exception encadrée, gouvernemental/institutionnel uniquement

Pour toute **source de presse** (« media », la classification par défaut),
rien ne change : Mode 1 uniquement — titre, extrait, lien vers l'original.
Ça reste la règle, sans exception, quoi que le flux propose techniquement.

Une source explicitement classée **gouvernementale** ou **institutionnelle**
(un ministère, une agence onusienne, la CEDEAO…) peut passer en mode
**intégral** — mais seulement si les trois conditions suivantes sont
réunies, appliquées à la fois par le formulaire et par une **contrainte en
base de données** (défense en profondeur, comme pour `robots.txt` en
Phase 0) :

1. la source est classée gouvernementale ou institutionnelle (jamais media) ;
2. une **justification écrite d'au moins 20 caractères** est enregistrée :
   accord, conditions de syndication publiées par la source elle-même, ou
   communiqué qui se déclare lui-même libre de reproduction ;
3. le flux fournit effectivement du contenu intégral pour cet item précis
   (`content:encoded` en RSS, `content` en Atom) — sinon, repli automatique
   sur extrait + lien, même pour une source en mode intégral.

Un article accepté depuis une source intégrale porte une attribution
distincte, aussi bien dans le brouillon que sur la page publique :
« Communiqué officiel repris intégralement — source : *nom* », plutôt que
« Contenu agrégé — article original sur *nom* ».

**Ce qui ne change jamais, quel que soit le mode** : tout reste un
brouillon, jamais publié automatiquement. Le contenu intégral vient d'un
flux RSS externe, donc d'une source non fiable par principe — il est
assaini deux fois (à l'extraction dans `feed_client.py`, puis de nouveau à
la construction du brouillon) avant de toucher la base de données.

#### Candidats déjà vérifiés parmi les 15 sources

Les portails gouvernementaux guinéens eux-mêmes (`presidence.gov.gn`,
`gouvernement.gov.gn`, `sgg.gov.gn`, `app.gov.gn`) sont tous protégés par
une vérification anti-robot (en-tête `sg-captcha: challenge`, HTTP 202
systématique) — **inutilisables pour une collecte automatisée**, quel que
soit le flux qu'ils proposeraient. Aucun n'est dans la liste.

Trois sources institutionnelles librement accessibles ont été ajoutées à
`flask seed-sources`, toutes en mode extrait par défaut :

| Source | Flux fournit du contenu intégral ? |
| --- | --- |
| CEDEAO | Oui — un texte de justification suggéré existe dans `seed_sources.py` (`JUSTIFICATIONS_SUGGEREES`), à relire et confirmer avant d'activer |
| OMS | Oui — idem |
| Union Africaine | Non, résumé seulement — reste en extrait quel que soit le mode choisi, rien à gagner à l'intégral |

Le texte de justification suggéré n'est **jamais appliqué automatiquement** —
`content_mode` reste `extrait` pour ces trois sources à la création, comme
pour toutes les autres. C'est à l'admin de le relire, l'éditer si besoin, et
de cocher lui-même le mode intégral depuis **Sources → Modifier**.

---

## 6. Commentaires : imbrication et modération automatisée

Les réponses ne s'arrêtent plus à un niveau : un lecteur peut répondre à une
réponse, et ainsi de suite sans limite technique de profondeur (limite
purement visuelle au-delà de 4 niveaux d'indentation, pour rester lisible
sur mobile).

### Pré-modération ou post-modération, au choix

Par défaut, **tout commentaire attend une validation humaine** avant d'être
visible — le comportement le plus prudent, en place depuis le début de ce
projet. `COMMENT_AUTO_APPROVE=1` bascule vers une post-modération : un
commentaire qui passe les filtres automatiques ci-dessous s'affiche
immédiatement ; un commentaire jugé suspect part quand même en file
d'attente, quel que soit ce réglage — le filtre ne rejette jamais
silencieusement, il ralentit seulement ce qui a l'air suspect.

### Détection automatique (`comment_spam.py`)

Volontairement des règles lisibles plutôt qu'un modèle de classification :

- trop de liens dans un même message (`COMMENT_MAX_LIENS`, 1 par défaut) ;
- vocabulaire suspect, liste réglable (`COMMENT_SPAM_KEYWORDS`) ;
- caractères répétés de façon excessive ;
- message entièrement en majuscules ;
- contenu identique à un commentaire récent du même compte (flood).

### Journal de modération

**Écran admin → Journal** : les 200 dernières actions de modération,
humaines et automatiques — approbation, rejet, suppression, signalement,
bannissement. Une action sans auteur vient d'un filtre automatique, pas
d'un administrateur.

---

## 7. Réseaux sociaux — intégration officielle Facebook

Un rédacteur peut coller l'URL d'un post Facebook **public** dans le champ
« URL d'un post Facebook à intégrer » du formulaire d'article. Le post
s'affiche alors tel qu'il est sur Facebook — largeur, mentions J'aime et
commentaires réels, lien vers l'original — via le widget officiel de Meta
(*Embedded Posts*). Autour, le rédacteur écrit son propre commentaire,
son analyse, son ton — clairement distinct du post lui-même.

### Ce que ce n'est pas

**Jamais de récupération de contenu côté serveur.** Le texte du post n'est
ni copié, ni réécrit, ni stocké — seule son URL l'est. C'est Facebook qui
héberge et rend le post, à chaque chargement de la page. Si l'auteur du
post le supprime ou le repasse en privé, l'intégration s'efface d'elle-même
chez le lecteur (comportement prévu par Meta, pas un bug à corriger ici) —
un texte affiché depuis le lien de repli renvoie alors directement vers
Facebook.

**Jamais de surveillance automatique.** Il n'existe pas de mécanisme pour
détecter tout seul qu'un compte vient de publier — un rédacteur choisit
chaque post à intégrer, un par un. Une automatisation complète demanderait
soit que le compte source accorde un accès (comme une vraie source
institutionnelle), soit une application Meta approuvée pour un accès API
élargi — une démarche externe, pas une fonctionnalité de ce projet.

**Seul Facebook est pris en charge.** `social_embed.py` valide uniquement
les URL `facebook.com`, `m.facebook.com`, `web.facebook.com` et
`fb.watch` — une URL Instagram, X ou TikTok est refusée avec un message
explicite. D'autres plateformes pourraient s'ajouter sur le même principe
(une fonction de validation dédiée par plateforme), mais aucune ne l'est
pour l'instant.

### Ce qui est vérifié, pas seulement documenté

- La validation ne porte que sur la **forme** de l'URL (domaine, schéma) —
  jamais une tentative de vérifier côté serveur si le post est réellement
  public, ce qui n'est de toute façon pas possible sans application Meta
  approuvée. C'est le widget, côté navigateur, qui décide de l'affichage.
- Un article dont la provenance est `agregateur` ou `whatsapp` ne peut
  jamais se faire attribuer une URL de réseau social par ce formulaire —
  la provenance d'un article ne change jamais après coup, quel que soit ce
  qui est soumis.
- Tout article avec un post intégré reste un **brouillon** tant qu'un
  humain ne l'a pas publié — comme partout ailleurs dans ce projet.

---

## 8. Publication par WhatsApp

Un correspondant enregistré (journaliste local, pigiste) peut rédiger un
article entièrement depuis WhatsApp, sans jamais ouvrir le site :

1. Il envoie son texte — la première ligne devient le titre.
2. Il envoie une photo si besoin (facultatif).
3. Il écrit **PUBLIER**.

L'article arrive alors en **brouillon** dans l'espace rédaction — jamais
publié automatiquement. Un responsable relit et publie normalement, comme
n'importe quel autre article. Le correspondant peut aussi écrire `ANNULER`
(efface le brouillon en cours), `STATUT` (rappelle où il en est) ou `AIDE`.

**Pourquoi ça compte commercialement.** Beaucoup de correspondants locaux et
de pigistes en région n'ouvriront jamais un panneau d'administration web sur
une connexion instable. WhatsApp, si. C'est une fonctionnalité qu'aucun
concurrent WordPress générique ne propose.

### Sécurité du dispositif

- Seuls les numéros explicitement enregistrés par un administrateur
  (**Correspondants** dans l'espace rédaction) peuvent créer du contenu. Un
  numéro inconnu reçoit un message l'invitant à contacter la rédaction et ne
  peut rien soumettre.
- Le webhook vérifie la **signature HMAC** envoyée par Meta
  (`WHATSAPP_APP_SECRET`) pour écarter toute requête forgée. Un avertissement
  s'affiche au démarrage si un jeton d'accès est configuré sans ce secret.
- Le point d'entrée du webhook répond **404** tant que
  `WHATSAPP_ENABLED=1` n'est pas explicitement activé — rien n'est exposé par
  défaut.
- Tout part en brouillon. Même un envoi malencontreux, ou un correspondant
  dont le compte serait compromis, ne peut pas mettre un texte en ligne sans
  relecture humaine.

### Configuration

Nécessite un compte Meta Business avec l'API Cloud WhatsApp activée
(gratuite jusqu'à un volume de conversations largement suffisant pour un flux
de rédaction interne).

1. Dans le dashboard Meta for Developers, crée une app, ajoute le produit
   **WhatsApp**, et récupère un jeton d'accès (un jeton système longue durée
   pour la production — le jeton de test par défaut expire au bout de 24 h).
2. Renseigne `.env` :
   ```
   WHATSAPP_ENABLED=1
   WHATSAPP_VERIFY_TOKEN=choisis-une-phrase-secrete
   WHATSAPP_ACCESS_TOKEN=le-jeton-recupere-chez-meta
   WHATSAPP_PHONE_NUMBER_ID=identifiant-du-numero-meta
   WHATSAPP_APP_SECRET=le-secret-de-l-app-meta
   WHATSAPP_COUNTRY_CODE=224
   ```
3. Dans le dashboard Meta, configuration du webhook :
   - URL : `https://tondomaine.com/webhook/whatsapp`
   - Jeton de vérification : la même valeur que `WHATSAPP_VERIFY_TOKEN`
   - Abonne le webhook aux événements `messages`
4. Depuis **Correspondants** dans l'espace rédaction, enregistre un nom et un
   numéro pour chaque contributeur autorisé. Le numéro peut être tapé au
   format local (`620 00 00 01`) — il est automatiquement complété avec
   l'indicatif pays configuré.

> **Numéros au format local vs international.** Un administrateur tape
> naturellement un numéro comme on le lit sur place, alors que l'API WhatsApp
> envoie et attend le format international complet. `WHATSAPP_COUNTRY_CODE`
> (224 = Guinée) sert à faire cette conversion automatiquement. Pour un
> déploiement dans un autre pays, adapte cette valeur — la détection reste une
> heuristique simple (préfixe), pas une validation complète de numéro.

### Limites connues

- Un seul brouillon actif à la fois par correspondant : un deuxième texte
  envoyé avant `PUBLIER` s'ajoute à la suite du premier plutôt que d'ouvrir un
  second brouillon.
- Pas de choix de rubrique par message — tous les articles WhatsApp arrivent
  dans la rubrique par défaut (`WHATSAPP_DEFAULT_CATEGORY`) ; la rédaction la
  corrige si besoin avant publication.
- Aucune limitation de débit sur le webhook — un numéro (même inconnu) peut en
  théorie déclencher un grand nombre de messages de réponse. À surveiller si
  le webhook est exposé publiquement sur la durée.

---

## 9. Configuration de Stripe

Sans clés, le site fonctionne normalement et la page d'abonnement affiche un
message explicatif.

1. Dans le dashboard Stripe : crée un produit avec un **prix récurrent
   mensuel**. Note l'identifiant `price_xxxxx`.

2. Renseigne `.env` :
   ```
   STRIPE_SECRET_KEY=sk_test_xxxxx
   STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
   STRIPE_PRICE_ID=price_xxxxx
   SUBSCRIPTION_PRICE_LABEL=15 000 GNF / mois
   ```

3. **Configure le webhook** — c'est lui qui active l'abonnement en base après
   paiement. Sans lui, le client paie mais ne devient jamais abonné.

   En local :
   ```bash
   stripe listen --forward-to localhost:5000/webhook/stripe
   ```
   La commande affiche un secret `whsec_xxxxx` → dans `.env` sous
   `STRIPE_WEBHOOK_SECRET`.

   En production : Développeurs → Webhooks → `https://tondomaine.com/webhook/stripe`
   avec les événements `checkout.session.completed`,
   `customer.subscription.updated`, `customer.subscription.deleted`.

4. Teste avec la carte `4242 4242 4242 4242`.

> ### Mobile money : le point à traiter en priorité
>
> Stripe ne gère pas Orange Money ni MTN MoMo, qui sont les moyens de paiement
> dominants en Guinée. Pour un site destiné à ce marché, un paywall en carte
> bancaire ne convertira quasiment personne.
>
> L'architecture est prête pour un autre fournisseur : toute la logique
> d'abonnement est isolée dans `blueprints/payments.py`, et le seul effet à
> reproduire côté base est de passer `user.is_subscriber` à `True` (plus la
> mise à jour de `Subscription`). Il faut brancher un agrégateur local
> (PayDunya, CinetPay, Hub2 ou l'API opérateur directement) — c'est un vrai
> chantier, pas une case à cocher.

---

## 10. Sauvegardes

```bash
python scripts/sauvegarde.py                    # archive base + images
python scripts/restaurer.py sauvegardes/kaloum24-AAAAMMJJ-HHMMSS.tar.gz
```

La sauvegarde utilise l'API de SQLite plutôt qu'une simple copie de fichier :
copier une base en cours d'écriture avec `cp` peut produire une archive
corrompue.

Automatisation quotidienne (crontab) :
```
0 3 * * * cd /chemin/vers/kaloum24 && venv/bin/python scripts/sauvegarde.py
```

Les archives de plus de 30 jours sont supprimées automatiquement.
**Copie-les hors du serveur** — une sauvegarde qui vit sur la machine qu'elle
protège ne protège de rien.

---

## 11. Migrations de base de données

Le schéma est géré par Flask-Migrate (Alembic). Après toute modification de
`models.py` :

```bash
flask db migrate -m "description du changement"
flask db upgrade
```

Relis toujours le fichier généré dans `migrations/versions/` avant de
l'appliquer en production : Alembic détecte mal certains changements sur
SQLite, notamment les renommages de colonnes.

---

## 12. Structure du projet

```
kaloum24/
├── app.py                  # application factory, filtres, commandes CLI
├── config.py               # configuration (variables d'environnement)
├── extensions.py           # db, login, csrf, migrate
├── models.py               # User, Category, Article, Comment, Subscription,
│                           # Correspondent, WhatsAppDraft
├── utils.py                # rôles, slugs, assainissement HTML, images, dates,
│                           # normalisation des numéros de téléphone et du texte
│                           # (accents) partagée par le sous-système d'agrégation
├── mailer.py               # envoi SMTP (console si non configuré)
├── security.py             # en-têtes HTTP, audit de config, journalisation
├── view_counter.py         # comptage des lectures, tamponné en mémoire
├── whatsapp_client.py      # client API WhatsApp Cloud (Meta) — envoi, médias
├── feed_client.py          # lecture des flux RSS/Atom + verification robots.txt
├── collector.py            # moteur de collecte periodique (flask collect-sources)
├── topic_matcher.py        # detection de doublons, regroupement par sujet
├── scoring_engine.py       # calcul du score, 5 composantes ponderees
├── comment_spam.py         # heuristiques de detection de spam sur les commentaires
├── social_embed.py         # validation des URL de reseaux sociaux (Facebook)
├── seed_sources.py         # configuration des 15 sources d'agrégation vérifiées
├── seed.py                 # contenu de démonstration
├── tests_fonctionnels.py   # 354 tests de bout en bout
├── mesure_poids.py         # mesure du poids des pages
├── blueprints/
│   ├── main.py             # accueil, rubriques, article, commentaires, RSS, météo
│   ├── auth.py             # comptes, mot de passe oublié
│   ├── admin.py            # espace rédaction, sources, scoring, agrégation, correspondants
│   ├── payments.py         # abonnement Stripe + webhook
│   └── whatsapp.py         # réception et traitement des messages WhatsApp
├── scripts/
│   ├── sauvegarde.py
│   └── restaurer.py
├── deploiement/            # gunicorn, Nginx, systemd, cron (sauvegarde + collecte)
├── templates/
├── static/
│   ├── css/style.css       # tout le style, thèmes clair et sombre
│   ├── css/fonts.css       # polices auto-hébergées
│   ├── fonts/              # fichiers woff2 (SIL Open Font License)
│   ├── vendor/quill/       # éditeur riche (BSD)
│   └── uploads/            # images envoyées par la rédaction et par WhatsApp
├── migrations/             # historique Alembic
├── GUIDE_REDACTION.md      # guide destiné au client
└── README.md
```

---

## 13. Tests

```bash
python tests_fonctionnels.py
```

354 tests couvrant : pages publiques, paywall, cycle de vie des commentaires,
rôles et permissions, protection CSRF, **assainissement XSS**, upload d'images
(y compris le rejet des fichiers non-images), réinitialisation de mot de passe,
flux RSS et sitemap, balises Open Graph, redirection ouverte, validation des
formulaires, **publication par WhatsApp** (signature HMAC, numéro non reconnu,
cycle texte → photo → PUBLIER, normalisation des numéros locaux/internationaux,
webhook désactivé par défaut), **limitation de débit**, et page d'aide quand
la base n'est pas initialisée, **en-têtes de sécurité**, **compteur de vues
tamponné**, refus de démarrage en production sur configuration dangereuse,
et **agrégation de sources** (contrainte de conformité, parsing de flux RSS
simulé, décodage d'entités HTML, extraction d'image, moteur de collecte —
dédoublonnage, filtrage par mots-clés, gestion des pannes, respect de
robots.txt et de la fréquence configurée, regroupement par sujet avec la
limite connue vérifiée explicitement plutôt que passée sous silence, moteur
de scoring — cinq composantes, badges, écran de réglage avec aperçu, et
vérification que deux pondérations opposées produisent des classements
différents sur les mêmes articles, file de modération — acceptation crée un
brouillon avec attribution vérifiable, rejet/archivage, protection contre le
doublon d'acceptation, attribution publique — badge visible uniquement sur le
contenu agrégé, boîte d'attribution reliée structurellement à sa source,
tableau de supervision, commentaires imbriqués sur plusieurs niveaux,
détection de spam, post-modération optionnelle, journal de modération,
mode intégral gouvernemental/institutionnel — contrainte en base testée sur
les trois contournements possibles, migration vérifiée sur une source déjà
existante en base, extraction contre un vrai flux institutionnel, seed idempotent des 3
sources institutionnelles vérifiées, intégration Facebook — validation
d'URL, provenance jamais écrasée sur un article agrégateur/WhatsApp,
widget officiel absent de tout article ordinaire, workflow éditorial étendu
— en relecture, programmation avec cycle complet vérifié, archivage,
idempotence).

Base temporaire : tes données ne sont pas touchées.

---

## 14. Sécurité — ce qui est en place

- Mots de passe hachés (Werkzeug/PBKDF2)
- Protection CSRF sur tous les formulaires
- **Assainissement du HTML** des articles : `<script>`, `<iframe>`, `<style>`,
  attributs `onerror`/`onclick` et URL `javascript:` sont supprimés
- Validation des images à l'ouverture réelle du fichier (pas seulement
  l'extension) et renommage aléatoire
- Limite de 8 Mo par requête
- Redirection après connexion restreinte aux URL internes
- Messages identiques que l'adresse existe ou non lors d'une demande de
  réinitialisation, pour empêcher l'énumération des comptes
- Un administrateur ne peut ni se rétrograder ni se bannir lui-même
- Webhook WhatsApp : signature HMAC vérifiée, désactivé (404) tant que
  `WHATSAPP_ENABLED` n'est pas explicitement activé, seuls les numéros
  enregistrés comme correspondants actifs peuvent créer du contenu
- **Limitation de débit** sur la connexion, l'inscription, les commentaires,
  la réinitialisation de mot de passe et le webhook WhatsApp — réglable par
  variables d'environnement (voir `.env.example`)
- Pages d'erreur propres (403, 404, 413, 429, 500) : aucune trace technique
  n'est exposée au visiteur
- **En-têtes de sécurité** : CSP (bloque les scripts tiers), X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy, Permissions-Policy, HSTS optionnel
- **Cookies de session** : HttpOnly, SameSite=Lax, et réservés à HTTPS dès que
  `ENV=production`
- **Refus de démarrer en production** si la configuration est dangereuse
  (clé par défaut, SITE_URL locale, webhook non signé) — voir `flask check-prod`
- **Journalisation** dans des fichiers avec rotation (`LOG_TO_FILE=1`)

### Ce qui n'est pas en place

- **Vérification de l'adresse e-mail** à l'inscription
- **Anti-spam automatique** sur les commentaires (au-delà de la modération)
- **Journalisation détaillée des actions d'administration** (qui a supprimé
  quel article, et quand)
- **Compteurs de débit partagés entre processus** — le stockage par défaut est
  en mémoire, donc propre à chaque worker. Avec plusieurs workers gunicorn, la
  limite réelle est multipliée par leur nombre. Configure
  `RATELIMIT_STORAGE_URI` vers Redis pour un décompte exact.

---

## 15. Mise en production

`flask run` est un serveur de développement : ni performant, ni sûr pour une
exposition publique.

### L'audit automatique

```bash
export ENV=production
flask check-prod
```

La commande liste ce qui bloque, ce qui mérite attention, et rappelle les
points qui ne se vérifient pas depuis la configuration (comptes de démo,
restauration testée, surveillance).

Avec `ENV=production`, l'application **refuse de démarrer** si la
configuration est dangereuse : clé secrète par défaut, `SITE_URL` locale,
webhook WhatsApp non signé, cookies non restreints à HTTPS. C'est volontaire —
un service qui ne part pas avec un message clair vaut mieux qu'un site en
ligne avec une faille silencieuse.

### Procédure

```bash
# 1. Déposer le code
sudo mkdir -p /var/www/kaloum24 && cd /var/www/kaloum24
# (git clone, rsync ou décompression de l'archive ici)

# 2. Environnement
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY
# Dans .env : ENV=production, SITE_URL=https://tondomaine.com, PROXY_COUNT=1,
#             LOG_TO_FILE=1
nano .env

# 4. Base de données
export FLASK_APP=app.py
flask db upgrade
flask create-admin          # compte réel ; ne pas utiliser flask seed-db

# 5. Vérifier avant d'exposer
flask check-prod

# 6. Service
sudo cp deploiement/kaloum24.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now kaloum24

# 7. Nginx + HTTPS
sudo cp deploiement/nginx.conf.exemple /etc/nginx/sites-available/kaloum24
sudo nano /etc/nginx/sites-available/kaloum24     # adapter le domaine
sudo ln -s /etc/nginx/sites-available/kaloum24 /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d tondomaine.com

# 8. Une fois HTTPS en place : HSTS_ENABLED=1 dans .env, puis
sudo systemctl restart kaloum24

# 9. Sauvegardes automatiques
sudo cp deploiement/sauvegarde.cron /etc/cron.d/kaloum24

# 10. Collecte des sources d'agrégation (si des sources sont activées)
sudo cp deploiement/collecte-sources.cron /etc/cron.d/kaloum24-sources
```

Le dossier `deploiement/` contient les fichiers prêts à adapter : configuration
gunicorn, exemple Nginx (avec cache des fichiers statiques, compression et
limitation de débit), unité systemd (avec cloisonnement du service) et tâche
cron de sauvegarde.

### Surveillance

Le point de contrôle `/sante` renvoie 200 si l'application **et** la base
répondent, 503 sinon. Branche-le sur un service de surveillance gratuit
(UptimeRobot, Better Stack) qui alerte par e-mail ou SMS. Sans cela, une panne
à 3 h du matin n'est découverte que par un lecteur mécontent.

### Ce qui a été mesuré

Test de charge sur ce projet, sous gunicorn (3 workers, gthread) :

| Simultanés | Requêtes | Échecs | Débit | Médiane | p95 |
| ---------- | -------- | ------ | ----- | ------- | --- |
| 10 | 100 | 0 | 38 req/s | 156 ms | 1094 ms |
| 30 | 300 | 0 | 79 req/s | 254 ms | 883 ms |
| 50 | 500 | 0 | 84 req/s | 421 ms | 1324 ms |

Aucune erreur de verrouillage SQLite, y compris sur les pages d'article qui
incrémentent le compteur de lectures.

**À lire avec prudence :** mesures faites dans un conteneur de développement,
sans Nginx devant (qui servirait les fichiers statiques et déchargerait
d'autant), et sur une base de démonstration d'une douzaine d'articles.
Refais la mesure sur ton serveur réel avant d'annoncer un chiffre à un client.
L'ordre de grandeur — quelques dizaines de requêtes par seconde — convient
largement à un site d'actualités régional.

### Hébergement

Render, Railway et Fly.io déploient ce projet depuis un dépôt Git.

**Attention au système de fichiers éphémère.** Sur ces plateformes, la base
SQLite *et les images envoyées* sont effacées à chaque redéploiement. Il faut
soit un volume persistant, soit PostgreSQL + un stockage objet (S3, Cloudinary)
pour les images. C'est le piège le plus courant sur ce type de projet.

Passage à PostgreSQL : change `DATABASE_URL`, les modèles sont inchangés.

---

## 16. Limites connues

- Les images sont stockées sur le disque local — inadapté à un déploiement
  multi-serveurs ou à un hébergement éphémère
- Pas de gestion de médiathèque : les images envoyées ne sont pas listées ni
  réutilisables depuis l'interface
- Recherche par `LIKE` SQL : suffisante jusqu'à quelques milliers d'articles,
  au-delà il faut un index plein texte
- Pas de cache : sous forte charge, la page d'accueil recalcule tout à chaque
  visite
- Pas de gestion multi-auteurs avancée (workflow de relecture, planification de
  publication à une date future)
- Newsletter : le formulaire est décoratif, aucune adresse n'est enregistrée
- **Agrégation** : les six phases du plan MVP (`PLAN_AGREGATEUR.md`) sont
  livrées — sources, collecte, doublons, scoring, modération, attribution
  publique et supervision. Une exception encadrée au Mode 1 existe
  désormais pour les sources gouvernementales/institutionnelles justifiées
  (voir §5) — à ne pas confondre avec le **Mode 2 général** (importation
  autorisée pour une source de presse quelconque), qui reste hors MVP : il
  demande un vrai accord bilatéral par source, pas seulement une
  classification et un texte de justification. Restent aussi hors MVP : le
  Mode 3 (synthèse par IA), un dédoublonnage sémantique par embeddings, et
  la publication automatique sans validation humaine — qui ne s'applique à
  aucune source, intégrale ou non. Le regroupement par sujet est en O(n²)
  sur les articles non groupés de la fenêtre récente — non bloquant à
  l'échelle d'une dizaine de sources, à revoir si ce nombre grossit
  nettement (voir `topic_matcher.py`)

---

## 17. Dépannage

### « no such table: articles » au démarrage

La base n'est pas initialisée. Le site affiche désormais une page explicative
plutôt qu'une trace technique. Lance :

```bash
export FLASK_APP=app.py     # Windows cmd : set FLASK_APP=app.py
flask db upgrade
```

### « Error: No such command 'db' »

`FLASK_APP` n'est pas défini dans le terminal courant. La syntaxe dépend du
système :

| Terminal | Commande |
| -------- | -------- |
| Linux / macOS | `export FLASK_APP=app.py` |
| Windows (cmd) | `set FLASK_APP=app.py` |
| Windows (PowerShell) | `$env:FLASK_APP="app.py"` |

La variable disparaît à la fermeture du terminal : il faut la redéfinir à
chaque nouvelle session, ou la placer dans `.env`.

### L'environnement virtuel ne correspond pas au projet

Si tu as plusieurs copies du projet, vérifie que le `venv` activé est bien
celui du dossier courant — la trace d'erreur affiche le chemin des paquets
utilisés, et un décalage y est visible. Pour connaître la base réellement
utilisée :

```bash
python -c "from app import create_app; print(create_app().config['SQLALCHEMY_DATABASE_URI'])"
```

### Un correspondant WhatsApp n'est pas reconnu

Vérifie dans **Correspondants** que son numéro est **Actif**. Si le numéro a
été saisi avec un indicatif d'un autre pays, corrige `WHATSAPP_COUNTRY_CODE`
puis ré-enregistre-le.

### « Trop de tentatives » (erreur 429)

La limitation de débit s'est déclenchée. Attends quelques minutes, ou ajuste
les valeurs `RATELIMIT_*` dans `.env` si elles sont trop strictes pour ton
usage.

### Une source reste bloquée sur « Erreur » après activation

1. Ouvre **Sources**, clique sur **Tester** pour cette source : le message
   d'erreur exact s'affiche (flux introuvable, format illisible, 404…).
   C'est le même diagnostic qu'utilise `flask collect-sources`.
2. Si le test réussit mais que la collecte automatique échoue quand même,
   vérifie que la case « J'ai vérifié robots.txt… » est cochée — sans elle,
   la source ne peut pas être active (contrainte appliquée en base, pas
   seulement dans le formulaire).
3. Un flux qui répondait au moment de l'ajout peut cesser de fonctionner
   plus tard (site refondu, flux déplacé) — c'est justement ce que le
   bouton **Tester** permet de vérifier sans attendre le prochain cycle cron.

### `flask collect-sources` ne ramène aucun article

- Vérifie qu'au moins une source est **Active** dans la liste.
- Une source dont la fréquence n'est pas encore échue est ignorée en
  silence (colonne « Dernière collecte ») — utilise `--force` pour forcer
  une collecte immédiate en test.
- Si `robots.txt` a changé depuis l'activation de la source, la collecte se
  bloque d'elle-même (voir §5) — le message d'erreur de la source l'indique.

---

## 18. Personnalisation

- **Nom, description, réseaux sociaux, ville météo** : `.env`
- **Couleurs et polices** : variables en haut de `static/css/style.css`
  (`--ink`, `--paper`, `--signal`, `--gold`, `--wire`). Le thème sombre est
  défini juste en dessous, dans le bloc `[data-theme="dark"]`.
- **Rubriques** : depuis l'espace d'administration, ou `CATEGORIES` dans `seed.py`

---

## 19. Licences des composants

| Composant | Licence |
| --------- | ------- |
| Flask, SQLAlchemy, Werkzeug | BSD |
| Quill | BSD |
| Fraunces, IBM Plex Sans, IBM Plex Mono | SIL Open Font License 1.1 |
| bleach, Pillow | Apache 2.0 / HPND |

Toutes permettent un usage commercial, y compris la revente d'un site construit
avec. Conserve les fichiers de licence si tu redistribues le code source.
