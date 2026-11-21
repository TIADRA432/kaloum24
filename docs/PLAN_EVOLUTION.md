# Kaloum24 — Plan d'évolution (sprints)

> Rédigé le 2026-11-21, enrichi le même jour (volet Prix, backlog unifié §5 bis). Complète `HANDOFF_AGENT.md` (état technique), `GUIDE_REDACTION_WAGTAIL.md` (équipe) et `PLAN_OBSERVATOIRE_PRIX.md` (volet Prix) et `PLAN_COMMUNAUTE.md` (commentaires, comptes, forum).
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

**A. Accueil vivant** — À la une (1 grand + 3), Dernières nouvelles, un bloc par rubrique, **colonne « Flash info / Brèves »** (2–3 lignes horodatées, lieu de retour plusieurs fois par jour), « En ce moment » (choix de la rédaction ; « Les plus lus » viendra avec un compteur), bandeau météo, **« Mot du jour en Pulaar » tiré du dictionnaire existant** (donnée réelle, sourcée), pied de page complet. Rubriques proposées : Politique, Économie, Société, Faits divers, Sport, Culture, Régions, Mines & Énergie, Afrique & Monde, Opinions & Tribunes, **Langues & Culture** (existe : Pulaar).

**B. Revue de presse automatique (licite)** — pour remplir l'accueil sans inventer : agrégateur RSS avec **extrait ≤ 400 caractères + lien vers la source** (règle du projet), sources guinéennes et régionales. Reprend l'idée de `collector.py` (V1) mais propre. Sans cela, l'accueil restera vide.

**C. Météo Afrique de l'Ouest** — *(mise à jour 2026-11-21 : en production, Open-Meteo répond « 429 Too Many Requests » à l'IP partagée de Render ; le site utilise désormais l'API MET Norway, gratuite, usage commercial compris, CC BY 4.0, attribution obligatoire. La décision « monétisation » n'est donc plus bloquante pour la météo. Détail ci-dessous = analyse initiale sur Open-Meteo.)* Open-Meteo : sans clé, gratuit en **usage non commercial** (≈10 000 appels/jour, attribution CC BY 4.0) ; usage commercial = abonnement payant. Villes : Conakry, Labé, Kankan, Nzérékoré, Dakar, Bamako, Abidjan, Freetown, Bissau, Monrovia. Appels côté serveur, mis en cache (toutes les 3 h) → quelques dizaines d'appels/jour. **À trancher** : si le site vend de la publicité, prévoir l'abonnement ou l'auto-hébergement.

**D. Ouverture aux contributeurs** — compte contributeur, formulaire « Proposer un article » qui crée un **brouillon** (jamais de publication directe), types : Reportage, Tribune/Opinion, Témoignage, Communiqué ; **étiquette visible** « Rédaction » / « Contribution » / « Opinion » ; page auteur ; charte éditoriale ; droit de réponse ; signalement d'un contenu. La relecture Wagtail existante sert de filtre.

**E. Lecture vocale** — réaliste en trois paliers :
1. *Français / anglais* : bouton « Écouter » via l'API navigateur (Web Speech) : zéro coût, mais qualité et voix dépendent de l'appareil (Chrome bureau : voix en ligne seulement ; non pris en charge dans les WebView Android).
2. *Audio pré-généré* pour les articles clés (stocké dans le bucket) si la qualité du palier 1 déçoit. **Voies à écarter ou à encadrer** : Edge-TTS est une bibliothèque **non officielle** qui appelle le service vocal du navigateur Edge (Microsoft n'a pas déclaré son usage interdit, mais ce n'est pas une API prévue pour cela et elle peut cesser de fonctionner) ; préférer un service officiel payant si on automatise. Les modèles Meta MMS-TTS (1 107 langues) sont publiés sous licence **CC-BY-NC 4.0, donc non commerciale** : à écarter si le site vend de la publicité ou des sponsors.
   - **Champ « Version audio »** (ajout issu de l'analyse Gemini) : l'auteur ou un lecteur enregistre l'article au téléphone, le fichier est envoyé dans l'admin (compression en Opus/MP3 léger), et un mini-lecteur façon note vocale s'affiche en haut de l'article. C'est la voie **la plus réaliste en langues locales** et elle est peu coûteuse à construire.
3. *Pulaar, mandingue, soussou* : **pas de voix standard dans les navigateurs**. Des fournisseurs privés couvrent le fulfulde/wolof (ex. LAfricaMobile) et un modèle ouvert « Kiriku TTS » (wolof, pulaar, sérère) est en cours ; leur qualité n'est pas validée. → **audio enregistré par des locuteurs humains** d'abord ; voix synthétique seulement après validation par un locuteur, avec la mention « voix synthétique ».

**F. Multilingue** — champ « langue » sur chaque article, pages de liste par langue, interface bilingue FR/EN. **Anglais** : brouillon de traduction + relecture humaine, étiqueté. **Pulaar, maninka, soussou, wolof, mandinka** : contenus rédigés **directement** dans la langue par des locuteurs (pas de traduction automatique présentée comme fiable). Outil de traduction de pages Wagtail à évaluer en début de sprint (compatibilité Wagtail 7.4 non vérifiée). **Liens entre traductions** : un article peut renvoyer à ses versions dans d'autres langues, avec un sélecteur « Lire cet article en : Pulaar | English » en haut de page. **Adlam** (ajout, j'avais omis cet alphabet) : écriture du pulaar créée en Guinée à la fin des années 1980, intégrée à Unicode 9.0 en 2016, écrite de droite à gauche ; la police libre Noto Sans Adlam (licence OFL) existe. À prévoir : prise en charge du sens d'écriture, choix de l'orthographe et du dialecte (décision d'un locuteur), et **aucune conversion automatique latin↔adlam présentée comme fiable**. N'Ko et Ajami : plus tard.

**G. Distribution & légèreté** — PWA (installable, lecture hors-ligne), boutons de partage WhatsApp, chaîne WhatsApp, newsletter, flux RSS par rubrique, budget de poids de page, **sauvegarde automatique de la base hors Supabase** (c'est ainsi que la première base a été perdue).

**I. Baromètre des prix** — prix réels du marché guinéen (moto, riz, carburant, transport, loyers, bétail…), officiels et citoyens, avec contrôle qualité. Voir `PLAN_OBSERVATOIRE_PRIX.md` (sprints P1–P4).

**K. Communauté** — comptes lecteurs, commentaires modérés, réactions (C1), forum à sections (C2), blogs écartés pour l'instant (C3). Voir `PLAN_COMMUNAUTE.md`.

**J. Appels d'offres et marchés publics** — rubrique de service (sprint M1).

**H. Widgets utiles (au choix, après le cœur)** — nécrologie / avis de décès et offres d'emploi (très présents chez les références), horaires de prière, sondage du jour, « chiffre du jour », taux de change GNF (source officielle à identifier), résultats sportifs.

## 5. Sprints (ordre proposé)

Chaque sprint = plan → construction → tests → déploiement → vérification en ligne → compte rendu court. Je m'arrête seulement pour ce qui exige vous (secret, décision légale, validation par un locuteur).

| Sprint | Contenu | Critère de réussite (vérifié en production) | Vous |
|---|---|---|---|
| **S0 — Cadre** (court) | Décisions §6, rubriques définitives, charte éditoriale (brouillon), mentions légales | Rubriques créées ; charte et mentions publiées en brouillon | Répondre aux 3 questions §6 |
| **S0b — Charte graphique** | Audit du visuel actuel, palette, polices, logo, composants (boutons, cartes, bandeau, étiquettes), ton, règles d'accessibilité ; page interne « Charte graphique » + variables CSS uniques ; application à l'accueil, au bandeau et aux articles | Un seul jeu de variables CSS ; contraste AA vérifié ; accueil, article et bandeau conformes ; document de charte publié dans le dépôt | Choisir parmi 2–3 propositions ; fournir un logo s'il existe |
| **S1 — Accueil vivant + sauvegarde** | Modèle d'accueil (une, **brèves / flash info**, derniers articles, blocs par rubrique, mot du jour pulaar, pied de page), menu des rubriques, images en WebP avec chargement différé, sauvegarde `pg_dump` planifiée | Accueil rempli avec les articles existants ; 200 partout ; sauvegarde restaurable testée | Aucun |
| **S2 — Revue de presse** | Agrégateur RSS licite (extrait + lien), page « Revue de presse », bloc d'accueil | ≥ 5 sources, doublons évités, extraits ≤ 400 car., lien d'origine | Valider la liste de sources |
| **S3 — Météo** | Service + cache + bandeau d'accueil + page `/meteo/` | 10 villes affichées, attribution présente, panne API sans erreur 500 | Dire si monétisation prévue |
| **S4 — Contributeurs** | Comptes, formulaire → brouillon, étiquettes (**Rédaction / Tribune / Contribution / Décryptage**), **fiche auteur** (photo, courte bio, spécialité, lien vers tous ses articles), droit de réponse, signalement | Un contributeur de test soumet ; rien ne paraît avant relecture | Valider la charte (idéalement avocat) |
| **S5 — Écouter** | Bouton fr/en (voix de l'appareil), **champ « Version audio » + mini-lecteur** (enregistrement humain, tous langages), mention de la limite | Fonctionne sur Chrome Android et un autre navigateur | Test sur votre téléphone |
| **S6 — Langues** | Champ langue, **liens entre traductions et sélecteur « Lire en… »**, listes par langue, interface FR/EN, anglais étiqueté, **police et sens d'écriture Adlam (optionnel)** | Un article en anglais et un en pulaar (fourni par un locuteur) en ligne | Fournir/valider les textes locaux |
| **S7 — Distribution** | PWA, partage WhatsApp **avec aperçu soigné (OpenGraph : miniature + titre)**, newsletter, RSS par rubrique, budget de poids | Installable ; page d'accueil sous le budget fixé | Créer la chaîne WhatsApp |
| **S8 — Widgets** | Nécrologie, emplois, prière, sondage… selon vos priorités | Un widget à la fois, chacun sourcé | Choisir lesquels |

## 5 ter. Charte graphique (ajout du 2026-11-21, à faire tôt)

Demande du propriétaire : définir une vraie identité visuelle (polices, couleurs, logo…) comme **base** du visuel. Le logo actuel (le nom « KALOUM24 » en texte) est **conservé** pour l'instant ; la charte peut le faire évoluer plus tard.

**Constat (code au 2026-11-21)** : palette héritée du modèle Wagtail « news-template » (bleu-vert *mackerel* `#26899E`, `#96D7E5`, `#1A2A2E`, gris), polices Source Serif 4 (titres), Source Sans 3, Source Code Pro. Ce n'est donc **pas** une identité Kaloum24, c'est celle du gabarit. Ajouts récents provisoires : rouge `#c8102e` de l'étiquette « Flash info », reflet du logo, couleurs héritées (`currentColor`). La charte Tiadra Consortium (bordeaux/or, Roboto Slab/Montserrat) reste **cantonnée à `/pulaar/`** et n'est pas reprise.

**Contenu de la charte** :
1. **Principes** : sérieux et lisible d'abord (c'est un média), chaleureux ensuite ; lisible sur petit écran et faible débit ; identité guinéenne sans cliché.
2. **Couleurs** : 1 couleur de marque, 1 d'accent, 1 couleur « urgence » (flash info), neutres, états (succès/erreur) ; versions clair et sombre ; contraste **WCAG AA** vérifié.
3. **Typographie** : 1 police de titres, 1 de texte, 1 de chiffres si besoin ; polices libres, auto-hébergées (poids de page) ; prise en charge des lettres ɓ ɗ ŋ ƴ (obligatoire) et, plus tard, de l'Adlam (Noto Sans Adlam).
4. **Logo** : garder le texte actuel ; décliner : version horizontale, icône carrée (favicon, WhatsApp, PWA), version monochrome ; zones de protection ; usages interdits.
5. **Composants** : bandeau d'info, cartes d'article, étiquettes (Rédaction/Tribune/Contribution/Décryptage), boutons, formulaires, alertes.
6. **Mouvement** : ce qui peut bouger (flash info, reflet, apparitions), durées, et la règle « mouvement réduit ».
7. **Ton** : voix éditoriale, exemples de titres, vocabulaire (« Flash info », « À la une »…).
8. **Mise en œuvre** : un seul fichier de variables CSS (`--k24-*`), remplacement des couleurs en dur, page interne `/charte-graphique/` réservée à l'équipe, document `docs/CHARTE_GRAPHIQUE.md`.

**Méthode** : je propose **2 ou 3 directions** (palette + polices + exemples réels d'écran), tu choisis, puis j'applique et je vérifie en production. Je n'invente ni logo ni marque : un logo/pictogramme n'est conçu que sur ta demande, et tout logo existant est repris tel quel.

**À fournir si tu l'as** : couleurs ou logos déjà utilisés (Facebook, WhatsApp, cartes), préférences (sobre/vif, couleurs du drapeau ou non), exemples de sites que tu aimes.

## 5 bis. Backlog unifié et priorisé (mis à jour le 2026-11-21)

Le volet **Prix** (détails dans `PLAN_OBSERVATOIRE_PRIX.md`) et deux nouvelles pistes s'ajoutent aux sprints S0–S8. Taille : **S** = 1 cycle « go », **M** = 2–3, **L** = 4 ou plus. Valeurs : H = élevée, M = moyenne, B = basse.

| Ordre | Id | Chantier | Valeur audience | Différenciation | Taille | Risque | Dépend de |
|---|---|---|---|---|---|---|---|
| 1 | S0 | Cadre, rubriques, charte (+ charte de la communauté) | M | B | S | légal | vos réponses §6 |
| 2 | S0b | **Charte graphique** (couleurs, polices, logo, composants, ton) : base de tout le visuel | H | H | M | faible (décisions de goût) | S0 |
| 3 | S1 | Accueil vivant + brèves + sauvegarde base | H | M | M | faible | S0 |
| 4 | S2 | Revue de presse licite | H | B | M | licences sources | S1 |
| 5 | P1 | Prix : fondations + données officielles + « Chiffres du jour » | H | H | M | extraction PDF | S1 |
| 6 | S3 | Météo Afrique de l'Ouest | H | H | S | licence si pub | S1 |
| 7 | S4 | Contributeurs (brouillons, étiquettes, fiche auteur) | M | H | M | **légal élevé** | S0 (charte) |
| 8 | C1 | Communauté : comptes lecteurs, commentaires modérés, réactions | H | M | M | **modération, données perso** | S4 |
| 9 | P2 | Prix : contributions citoyennes + contrôle qualité | H | **très H** | L | qualité des données, légal | P1, C1 |
| 10 | S7 | Distribution : PWA, WhatsApp, newsletter, RSS | H | M | M | faible | S1 |
| 11 | S5 | « Écouter » fr/en + champ « Version audio » | M | H | S | faible | — |
| 12 | P3 | Prix : graphiques dans articles, « Panier de la ménagère », données ouvertes | H | H | M | faible | P2 |
| 13 | S6 | Langues (anglais, puis langues locales, liens de traduction, Adlam) | M | **très H** | L | validation humaine | locuteurs |
| 14 | C2 | **Forum** (sections, sujets, messages, modération par section) | H | H | L | **modération lourde, légal** | C1, S7, audience |
| 15 | M1 | Appels d'offres et marchés publics | M | H | M | sources/licences | S2 |
| 16 | S8 | Widgets : nécrologie, emplois, prière, sondage | M | B | M | faible | S1 |
| 17 | P4 | Signalements sur carte (carburant, embouteillages, électricité) | M | H | L | **modération, rumeurs** | P2 |
| 18 | M2 | Cours des matières premières minières | B | M | S | licence données | P1 |
| 19 | C3 | Blogs d'utilisateurs (non planifié ; profil public d'abord) | B | M | L | modération | C2 |

**Nouveau (communauté)** : détails dans `PLAN_COMMUNAUTE.md`. Les commentaires (C1) viennent juste après les contributeurs, car ils reposent sur la même charte et la même modération ; le forum (C2) attend une audience et des modérateurs formés.

**Pourquoi cet ordre** : l'accueil et la revue de presse règlent d'abord le « site vide ». Les prix officiels (P1) donnent vite des chiffres crédibles sans dépendre de personne. Les contributions externes (S4, P2) viennent ensuite, car elles exigent la charte et la modération. Les langues locales (S6) avancent **en parallèle** dès que des locuteurs sont disponibles, car elles ne dépendent pas de moi.

**Deux pistes** : *Technique* (moi, en cycles « go ») et *Humaine* (vous : charte à valider par un juriste, liste de sources, locuteurs pulaar/maninka/soussou, premiers contributeurs de prix, chaîne WhatsApp).

**Règle de fonctionnement** : un sprint à la fois ; critère de réussite vérifié en production avant de passer au suivant ; compte rendu court ; mise à jour de `HANDOFF_AGENT.md` à la fin de chaque sprint.

## 6. Décisions à prendre (valeurs par défaut si vous ne tranchez pas)

1. **Statut légal** : Kaloum24 est-il déclaré (procureur / HAC) et qui est le directeur de publication ? *Défaut : je prépare les mentions légales avec un champ à compléter, rien d'inventé.*
2. **Monétisation** (publicité, sponsors) prévue à court terme ? *Défaut : on suppose que oui, donc météo à prévoir en licence commerciale.*
3. **Ouverture externe** : *Défaut : seulement après S4 (charte + relecture), jamais de publication directe.*
4. **Communauté** (voir `PLAN_COMMUNAUTE.md` §8) : modération préalable des commentaires au début, qui modère, anonymat des invités. *Défaut : modération préalable, vous + une personne, e-mail vérifié exigé pour les comptes.*
5. **Volet Prix** (voir `PLAN_OBSERVATOIRE_PRIX.md` §12) : nom (*défaut : « Baromètre des prix », pas « Bourse »*), sens de « fréquentation de zones », produits de départ, qui valide les relevés (*défaut : vous*), partenariat éventuel avec SIMPRIX.

6. **Charte graphique** (§5 ter) : direction (sobre / chaleureuse / vive), usage ou non des couleurs du drapeau guinéen, logo à conserver ou à décliner. *Défaut : 3 propositions présentées avant tout changement, logo textuel actuel conservé.*

## 6 bis. Intégration de l'analyse de Gemini (2026-11-21)

Votre prompt a aussi été soumis à Gemini. Comparaison avec ce plan, après vérification des points techniques :

**Retenu et ajouté** : colonne « Flash info / Brèves » (S1) ; étiquette « Décryptage » et fiche auteur détaillée (S4) ; liens entre traductions + sélecteur « Lire cet article en » (S6) ; **alphabet Adlam** (S6) ; champ « Version audio » téléversé par l'auteur (S5) ; réactions rapides et commentaires modérés (C1) ; aperçu WhatsApp (OpenGraph), images WebP, chargement différé (S1/S7).

**Déjà présent chez nous** : badges Rédaction / Contribution / Opinion, workflow brouillon → relecture → publication (déjà dans Wagtail), météo mise en cache, taux de change (P1), lecture vocale du navigateur, multilingue par article plutôt que traduction automatique, pages légères.

**Corrigé ou mis en garde** :
- *Meta MMS-TTS* pour le pulaar : licence **non commerciale** (CC-BY-NC 4.0) ; la couverture exacte du fulfulde n'a pas été vérifiée ; qualité non validée par un locuteur.
- *Edge-TTS* : bibliothèque non officielle, usage non garanti ; ne pas bâtir la production dessus.
- *Taux de change « en direct »* : la BCRG publie un cours de référence **quotidien** (PDF), pas un flux en direct ; on affichera « cours du jour » avec sa date.
- *Alerte Harmattan* dans la météo : idée à étudier (poussière/visibilité) ; non vérifiée comme disponible dans la source météo.
- Affirmations de Gemini sur la concurrence (« forums non modérés », « 100 % français ») : **non vérifiées** ; Seneweb propose par exemple un lien « In English ».
- Absents de son plan : le **cadre légal** (HAC, diffamation), le **manque de contenu** (revue de presse), la **licence de la météo** si le site vend de la publicité, la règle « IA ≠ autorité linguistique », et tout le volet **Prix**. Je les garde en priorité.

**Ordre** : Gemini place langues et audio avant les widgets. Je maintiens l'ordre du backlog (accueil et contenu d'abord, contributions après la charte), mais le champ « Version audio » (taille S) peut être avancé si vous le souhaitez.

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
- Licence MMS-TTS (CC-BY-NC 4.0) : Hugging Face, facebook/mms-tts ; Edge-TTS : PyPI/GitHub rany2/edge-tts et Microsoft Q&A « Unofficial Edge TTS API » ; Adlam : Unicode 9.0, Noto Sans Adlam (Google Fonts, OFL), W3C « Adlam Script Resources ».
- Voix : Readium « SpeechSynthesis in browsers and OSes » ; caniuse SpeechSynthesis ; arXiv 2601.09716 (TTS langues sénégalaises) ; profil Kiriku TTS.
