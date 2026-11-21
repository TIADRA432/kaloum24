# Kaloum24 — Plan d'évolution (sprints)

> Rédigé le 2026-11-21. Complète `HANDOFF_AGENT.md` (état technique) et `GUIDE_REDACTION_WAGTAIL.md` (équipe).
> Règles du projet inchangées : aucun contenu inventé, « IA ≠ autorité linguistique », provenance obligatoire, aucun secret dans le code.

## 1. Point de départ (constat)

- **L'accueil est vide** : titre « Kaloum24 », une phrase d'accroche, un menu à deux entrées (Actualités, Dictionnaire pulaar), recherche, thème clair/sombre. Aucune une, aucun fil d'actualité, aucune rubrique (vérifié en ligne le 2026-11-21).
- **Contenu** : un seul article publié (alphabets latins, Pulaar). Le vrai goulot n'est pas le design mais **l'alimentation en contenu**.
- **Atouts déjà là** : rédaction structurée (blocs de presse, rôles Rédacteurs/Relecteurs, relecture), dictionnaire Pulaar, sitemap/robots, médias persistants, base sécurisée.

## 2. Ce que font les références

| | Guinéenews | Seneweb (Sénégal) |
|---|---|---|
| Accueil | « À la une », « Dernières nouvelles », un bloc par rubrique (Politique, Grands Dossiers, Économie, Faits divers, Société, Art & Culture, Régions, Interviews, Sport, Revue de presse, Monde) | Rubriques (Politique, Économie, Société, Faits-divers, Sport, Blogs, Afrique, People), « tags populaires », « le plus partagé », fil continu |
| Services | Annonces : offres d'emploi, nécrologie, petites annonces ; « mot du jour », « chiffre du jour » ; podcast ; publireportage | Petites annonces (immobilier, autos), forum, pétitions, podcasts, blogs, lecteur radio (6 flux), web TV, lien « In English » |
| Contribution | Interviews, rubrique Régions | Blogs, forum, pétitions, catégorie « Contribution », commentaires |
| Météo / langues locales / lecture vocale | **non vus** | **non vus** (météo absente ; une seule version anglaise) |

Limites de cette étude : l'accueil de Guinéenews a été lu tronqué (météo, sondage, « plus lus » peuvent exister plus bas) ; Africaguinee n'a pas pu être chargé ; les chiffres d'audience (Similarweb) sont indicatifs. « Cineweb » n'a pas été identifié : j'ai pris Seneweb comme référence sénégalaise.

**Conclusion** : les deux références sont des portails généralistes à forte pub et petites annonces. **Personne ne propose météo régionale, langues locales ni lecture vocale** : c'est là que Kaloum24 peut se démarquer, avec le dictionnaire Pulaar comme atout unique.

## 3. Contraintes locales qui orientent les choix

- **Peu de données, peu de débit** : ~3,96 M d'internautes en Guinée début 2025 ; Facebook ~2,6 M (début 2024) ; la donnée mobile est rationnée. → pages légères, images compressées, pas de scripts lourds, partage WhatsApp/Facebook, mode hors-ligne (PWA).
- **Cadre légal sensible** : la presse en ligne relève de la HAC et de la loi de 2010 sur la liberté de la presse ; la HAC a suspendu des sites en ligne (ex. 3 mois en avril 2025 après une plainte en diffamation) et a indiqué que les web médias défaillants relèveraient de la loi sur la cybersécurité (juillet 2025). → ouvrir à des contributeurs externes **suppose une charte, un directeur de publication identifié, une relecture avant toute mise en ligne et un droit de réponse**. Je ne suis pas juriste : à valider auprès d'un avocat guinéen / de la HAC.
- **Demande réelle en langues locales** : RFI a lancé un programme en fulfulde et doublé son temps d'antenne en mandenkan, 2 h/jour par langue, pour ~80 M de locuteurs.

## 4. Propositions, par thème

**A. Accueil vivant** — À la une (1 grand + 3), Dernières nouvelles, un bloc par rubrique, « En ce moment » (choix de la rédaction ; « Les plus lus » viendra avec un compteur), bandeau météo, **« Mot du jour en Pulaar » tiré du dictionnaire existant** (donnée réelle, sourcée), pied de page complet. Rubriques proposées : Politique, Économie, Société, Faits divers, Sport, Culture, Régions, Mines & Énergie, Afrique & Monde, Opinions & Tribunes, **Langues & Culture** (existe : Pulaar).

**B. Revue de presse automatique (licite)** — pour remplir l'accueil sans inventer : agrégateur RSS avec **extrait ≤ 400 caractères + lien vers la source** (règle du projet), sources guinéennes et régionales. Reprend l'idée de `collector.py` (V1) mais propre. Sans cela, l'accueil restera vide.

**C. Météo Afrique de l'Ouest** — Open-Meteo : sans clé, gratuit en **usage non commercial** (≈10 000 appels/jour, attribution CC BY 4.0) ; usage commercial = abonnement payant. Villes : Conakry, Labé, Kankan, Nzérékoré, Dakar, Bamako, Abidjan, Freetown, Bissau, Monrovia. Appels côté serveur, mis en cache (toutes les 3 h) → quelques dizaines d'appels/jour. **À trancher** : si le site vend de la publicité, prévoir l'abonnement ou l'auto-hébergement.

**D. Ouverture aux contributeurs** — compte contributeur, formulaire « Proposer un article » qui crée un **brouillon** (jamais de publication directe), types : Reportage, Tribune/Opinion, Témoignage, Communiqué ; **étiquette visible** « Rédaction » / « Contribution » / « Opinion » ; page auteur ; charte éditoriale ; droit de réponse ; signalement d'un contenu. La relecture Wagtail existante sert de filtre.

**E. Lecture vocale** — réaliste en trois paliers :
1. *Français / anglais* : bouton « Écouter » via l'API navigateur (Web Speech) : zéro coût, mais qualité et voix dépendent de l'appareil (Chrome bureau : voix en ligne seulement ; non pris en charge dans les WebView Android).
2. *Audio pré-généré* pour les articles clés (stocké dans le bucket) si la qualité du palier 1 déçoit.
3. *Pulaar, mandingue, soussou* : **pas de voix standard dans les navigateurs**. Des fournisseurs privés couvrent le fulfulde/wolof (ex. LAfricaMobile) et un modèle ouvert « Kiriku TTS » (wolof, pulaar, sérère) est en cours ; leur qualité n'est pas validée. → **audio enregistré par des locuteurs humains** d'abord ; voix synthétique seulement après validation par un locuteur, avec la mention « voix synthétique ».

**F. Multilingue** — champ « langue » sur chaque article, pages de liste par langue, interface bilingue FR/EN. **Anglais** : brouillon de traduction + relecture humaine, étiqueté. **Pulaar, maninka, soussou, wolof, mandinka** : contenus rédigés **directement** dans la langue par des locuteurs (pas de traduction automatique présentée comme fiable). Outil de traduction de pages Wagtail à évaluer en début de sprint (compatibilité Wagtail 7.4 non vérifiée). Alphabets non latins (N'Ko, Ajami) : plus tard.

**G. Distribution & légèreté** — PWA (installable, lecture hors-ligne), boutons de partage WhatsApp, chaîne WhatsApp, newsletter, flux RSS par rubrique, budget de poids de page, **sauvegarde automatique de la base hors Supabase** (c'est ainsi que la première base a été perdue).

**H. Widgets utiles (au choix, après le cœur)** — nécrologie / avis de décès et offres d'emploi (très présents chez les références), horaires de prière, sondage du jour, « chiffre du jour », taux de change GNF (source officielle à identifier), résultats sportifs.

## 5. Sprints (ordre proposé)

Chaque sprint = plan → construction → tests → déploiement → vérification en ligne → compte rendu court. Je m'arrête seulement pour ce qui exige vous (secret, décision légale, validation par un locuteur).

| Sprint | Contenu | Critère de réussite (vérifié en production) | Vous |
|---|---|---|---|
| **S0 — Cadre** (court) | Décisions §6, rubriques définitives, charte éditoriale (brouillon), mentions légales | Rubriques créées ; charte et mentions publiées en brouillon | Répondre aux 3 questions §6 |
| **S1 — Accueil vivant + sauvegarde** | Modèle d'accueil (une, derniers articles, blocs par rubrique, mot du jour pulaar, pied de page), menu des rubriques, sauvegarde `pg_dump` planifiée | Accueil rempli avec les articles existants ; 200 partout ; sauvegarde restaurable testée | Aucun |
| **S2 — Revue de presse** | Agrégateur RSS licite (extrait + lien), page « Revue de presse », bloc d'accueil | ≥ 5 sources, doublons évités, extraits ≤ 400 car., lien d'origine | Valider la liste de sources |
| **S3 — Météo** | Service + cache + bandeau d'accueil + page `/meteo/` | 10 villes affichées, attribution présente, panne API sans erreur 500 | Dire si monétisation prévue |
| **S4 — Contributeurs** | Comptes, formulaire → brouillon, étiquettes, page auteur, droit de réponse, signalement | Un contributeur de test soumet ; rien ne paraît avant relecture | Valider la charte (idéalement avocat) |
| **S5 — Écouter** | Bouton fr/en, lecteur accessible, mention de la limite | Fonctionne sur Chrome Android et un autre navigateur | Test sur votre téléphone |
| **S6 — Langues** | Champ langue, listes par langue, interface FR/EN, anglais étiqueté | Un article en anglais et un en pulaar (fourni par un locuteur) en ligne | Fournir/valider les textes locaux |
| **S7 — Distribution** | PWA, partage WhatsApp, newsletter, RSS par rubrique, budget de poids | Installable ; page d'accueil sous le budget fixé | Créer la chaîne WhatsApp |
| **S8 — Widgets** | Nécrologie, emplois, prière, sondage… selon vos priorités | Un widget à la fois, chacun sourcé | Choisir lesquels |

## 6. Décisions à prendre (valeurs par défaut si vous ne tranchez pas)

1. **Statut légal** : Kaloum24 est-il déclaré (procureur / HAC) et qui est le directeur de publication ? *Défaut : je prépare les mentions légales avec un champ à compléter, rien d'inventé.*
2. **Monétisation** (publicité, sponsors) prévue à court terme ? *Défaut : on suppose que oui, donc météo à prévoir en licence commerciale.*
3. **Ouverture externe** : *Défaut : seulement après S4 (charte + relecture), jamais de publication directe.*

## 7. Risques

- Accueil riche mais peu d'articles : atténué par S2 ; la production éditoriale reste humaine.
- Pression légale sur la presse en ligne : relecture systématique, charte, droit de réponse.
- Qualité des voix et traductions en langues locales : jamais présentées comme validées sans locuteur.
- Hébergement gratuit (veille, base) : sauvegarde en S1, passage payant à envisager quand l'audience grandit.

## Sources

- Structure d'accueil : guineenews.org et seneweb.com (lus le 2026-11-21) ; kaloum24.onrender.com (état actuel).
- Internet en Guinée : DataReportal, Digital 2025 Guinea ; Facebook : Digital 2024 Guinea.
- Cadre légal : RSF, page Guinée ; MFWA/Article 19 (suspension presseinvestigation.com, 2025) ; allAfrica, HAC et loi sur la cybersécurité (26 juillet 2025) ; Journal officiel, loi organique sur la liberté de la presse.
- RFI en fulfulde/mandenkan : France Médias Monde / ModernGhana (janvier lancement) ; Afri'Kibaaru (AFD).
- Open-Meteo : open-meteo.com (terms, pricing).
- Voix : Readium « SpeechSynthesis in browsers and OSes » ; caniuse SpeechSynthesis ; arXiv 2601.09716 (TTS langues sénégalaises) ; profil Kiriku TTS.
