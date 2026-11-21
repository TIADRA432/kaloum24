# Kaloum24 Prix — observatoire des prix et des indicateurs du quotidien

> Conception du 2026-11-21. **Rien n'est construit.** Complète `PLAN_EVOLUTION.md` (le backlog unifié et l'ordre des sprints y sont).
> Règles du projet : aucune donnée inventée, provenance visible pour chaque chiffre, aucun secret dans le code.

## 1. L'idée

Le « prix réel, aujourd'hui, près de chez vous » : la moto TVS dont on dit qu'elle est passée de 10 à 8 millions, le sac de riz, le litre d'essence au marché noir, le loyer, le mouton avant la fête. Un site de presse qui publie des **chiffres vérifiables et leur évolution** devient une référence que les gens consultent chaque semaine, pas seulement quand il y a une actualité. C'est aussi un excellent sujet d'articles (« Panier de la ménagère »).

## 2. Le nom : attention au mot « Bourse »

« Bourse » évoque un marché financier réglementé avec des cotations garanties. Un prix recueilli auprès de citoyens est un **indicateur**, pas une cotation. Je propose **« Baromètre des prix Kaloum24 »** (ou « Le prix du jour »). On peut garder « bourse » comme surnom interne. À décider (§12).

## 3. Ce qui existe déjà (et ce qui manque)

| Source | Ce qu'elle apporte | Limites / à vérifier |
|---|---|---|
| **SIMPRIX** (ministère du Commerce, DNCIC) | Plateforme officielle de suivi des prix des denrées de base et des produits de grande consommation, lancée le 31 juillet 2024 avec 4 portails (public, collecteurs, superviseurs, décideurs), étendue en juillet 2025 aux 8 régions ; objectif affiché : informer sur les **prix plafonds** | L'article ne dit pas si les prix observés sont publiés, ni s'il existe un signalement citoyen ou des données ouvertes. **À vérifier sur simprix.gov.gn** |
| **Prix plafonds** (protocole du 16 février 2026, Ramadan) | Grille officielle ; prix différents à Conakry et à l'intérieur (coût du transport) | Valable sur une période ; à republier avec sa date |
| **INS — IHPC** | Indice mensuel des prix, avec un tableau des « prix moyens de quelques produits essentiels à Conakry » | PDF ; les bulletins retrouvés datent de 2016–2020, **récence à vérifier** |
| **PAM / HDX — Guinea Food Prices** | Jeu de données ouvert (sources : FPMA/FAO, INS, SIPAG) | Denrées alimentaires seulement ; licence à confirmer |
| **Banque mondiale — Real Time Prices** | Estimations mensuelles par produit et par marché, **20 marchés en Guinée, jusqu'à octobre 2026**, données ouvertes | Ce sont des **estimations** (modèle + mesures), à étiqueter comme telles |
| **BCRG — cours de référence** | Cours officiels des devises contre le GNF, publiés par jour | **PDF**, pas d'interface de données trouvée → extraction à prévoir |
| **Carburant** | Prix officiel à la pompe : 12 000 GNF le litre (agrégateur tiers, 2026) ; l'Union des Consommateurs évoquait 15 000 GNF au marché noir, et la presse 25 000–30 000 à Kindia en pénurie (date non vérifiée) | L'écart officiel / réel est exactement ce qu'un baromètre citoyen peut montrer |
| **Presse** | « Panier de la ménagère » (ex. sac de riz Bangladesh de 50 kg à 315 000 GNF en mars 2025, contre 350 000 un an plus tôt) | Ponctuel, manuel, sans historique |

**Ce qui n'est nulle part** (d'après mes recherches) : les prix des **biens durables et services** (moto, téléphone, pièces, ciment, fer, loyers, transport, bétail), l'**écart entre prix plafond et prix réellement payé**, et un **historique lisible** par produit et par ville. Je n'ai trouvé **aucune donnée publique** sur le prix des motos TVS en Guinée : pour ce cas, la contribution des gens est la seule source possible, ce qui en fait la valeur du service.

## 4. Catalogue de prix proposé

**Niveau 1 — données officielles disponibles (démarrage rapide)**
- Carburant (prix officiel), taux de change BCRG (USD, EUR, XOF), prix plafonds des denrées de base, inflation INS, riz/huile/sucre/oignon (PAM, Banque mondiale).

**Niveau 2 — contributions citoyennes (le cœur du projet)**
- Riz, huile, sucre, oignon, pain, poisson au marché (prix réel vs plafond).
- Carburant réellement payé (station / hors station), recharge de gaz.
- Transport : taxi-moto, minibus, interurbain.
- Motos (neuves / occasion : TVS HLX 125, etc.), téléphones.
- Construction : ciment, fer à béton, tôles.
- Loyers par commune.
- Bétail (mouton, bœuf) avant les fêtes.

**Niveau 3 — à étudier**
- Forfaits data et frais Orange Money / autres opérateurs (comparateur).
- Matières premières minières (or, bauxite, minerai de fer) : cours internationaux ; source libre et licence à vérifier.
- Taux de change « de rue » : **sensible**, à valider juridiquement avant tout.

## 5. Fonctionnement côté lecteur

- **Fiche produit** : prix typique (médiane), fourchette (min–max), nombre de relevés, date de la dernière mise à jour, courbe sur 12 mois, comparaison entre villes, mention « officiel / citoyen / estimation ».
- **« Signaler un prix »** en moins de 20 secondes : produit, prix, ville/marché, date (automatique), état (neuf/occasion), photo facultative. Fonctionne sur téléphone d'entrée de gamme.
- **Alertes** de variation notable (« la moto X a baissé de 12 % en 3 mois à Conakry »), qui alimentent les articles.
- **Accueil** : bloc « Chiffres du jour » (carburant, dollar, riz, moto…).

## 6. Qualité des données (le point décisif)

Des études (JRC/Commission européenne, Nature Scientific Data, Banque mondiale/PLOS) montrent que le recueil citoyen peut égaler les enquêtes classiques **à condition d'un contrôle qualité automatique**. Méthode retenue :

1. **Spécification stricte du produit** (ex. « riz importé étuvé, sac de 50 kg » ; « TVS HLX 125 neuve, concessionnaire »). Sans cela, on compare des choses différentes.
2. **Médiane**, jamais la moyenne ; publication d'une valeur **seulement à partir d'un nombre minimum de relevés indépendants** sur la période (seuil à calibrer sur données réelles).
3. **Filtre des valeurs aberrantes** et détection des prix « figés » ou répétés par le même contributeur.
4. **Prix demandé ≠ prix payé** : on les distingue. Un témoignage isolé (« le gars m'a dit 8 millions ») entre en file « à confirmer » et **ne déplace pas la courbe** tant qu'il n'est pas recoupé.
5. **Limites par contributeur** (nombre de relevés/jour), score de confiance, modération dans l'admin Wagtail.
6. Affichage honnête : « 3 relevés, faible confiance » plutôt qu'un chiffre trompeur.

## 7. Cadre légal et éthique (je ne suis pas juriste : validation requise)

- **Prix plafonds** : publier un prix observé au-dessus du plafond est de l'information ; **ne jamais nommer un commerçant ni une boutique, ni publier de photo identifiable**. Agréger par marché / commune.
- **Aucun conseil d'achat ou d'investissement** ; mention « indicatif, non contractuel ».
- **Données personnelles minimales** : aucun nom exigé ; si vérification par téléphone, stocker une empreinte et non le numéro. Conformité à la loi guinéenne à vérifier.
- **Exclusions** : pas de signalements politiques ou sécuritaires dans le baromètre (risque HAC et rumeurs).
- **Taux de change de rue** : risque à évaluer avant publication.
- **Responsabilité éditoriale** : une personne (directeur de publication) responsable des publications automatiques.

## 8. Architecture technique (indicative)

- Application Django `prix` : `Produit` (catégorie, définition, unité), `Lieu` (ville, marché), `Observation` (produit, lieu, prix en GNF, date, type de source, statut, contributeur, preuve facultative), `SerieQuotidienne` (médiane, effectif, confiance).
- **Imports automatiques** (commandes de gestion) : PAM/HDX et Banque mondiale (fichiers CSV), BCRG (extraction des PDF), INS (PDF), carburant (saisie rédaction). Planification : tâche cron Render (coût à vérifier) ou déclenchement programmé par GitHub Actions sur un point d'entrée protégé.
- **Modération** dans l'admin Wagtail (même interface que les articles).
- **Graphiques légers** (SVG côté serveur, très peu de JavaScript) pour les connexions lentes.
- **Données ouvertes** : export CSV/JSON avec attribution, ce qui aide le référencement et la crédibilité.
- **Lien avec la rédaction** : bloc « Graphique de prix » à insérer dans un article ; **brouillon hebdomadaire « Panier de la ménagère »** généré à partir des données et **relu par un humain** avant publication.
- Plan gratuit Render/Supabase suffisant au démarrage (requêtes d'agrégation légères) ; surveiller la taille de la base.

## 9. Sprints du volet Prix

| Sprint | Contenu | Critère de réussite (en production) | Vous |
|---|---|---|---|
| **P1 — Fondations + données officielles** | Modèles, admin, catalogue niveau 1, imports PAM/Banque mondiale/BCRG, fiches produit, bloc « Chiffres du jour » | 8 produits/indicateurs avec courbe et source ; chaque chiffre porte sa date et son origine | Vérifier simprix.gov.gn ; valider la liste de produits |
| **P2 — Contributions citoyennes** | Formulaire « Signaler un prix », file de modération, contrôle qualité (§6), score de confiance | Un relevé de test apparaît « à confirmer », puis publié après recoupement ; un aberrant est rejeté automatiquement | Recruter 5–10 premiers contributeurs ; valider la charte |
| **P3 — Graphiques, articles, données ouvertes** | Bloc graphique dans les articles, brouillon « Panier de la ménagère », export CSV/JSON | Un article avec graphique publié ; export téléchargeable | Relire le brouillon hebdomadaire |
| **P4 — Signalements sur carte** | Pénurie de carburant, embouteillages, coupures d'électricité, avec durée de vie courte | Un signalement expire seul ; aucun contenu politique/sécuritaire | Décision après P2 |

## 10. Autres idées issues de la recherche

- **Marchés publics et appels d'offres** : des organismes (OIM, FMI, Banque mondiale) publient des appels d'offres et des ventes de véhicules en PDF sur des sites de presse ; une rubrique « Appels d'offres » est un service très demandé. Faisabilité : bonne (saisie rédaction + flux).
- **Fréquentation de zones** : à clarifier (§12). Le plus réaliste et le moins risqué : signalements citoyens à durée de vie courte (embouteillages, files aux stations). Les données de fréquentation de services commerciaux (type « heures de pointe ») ne sont pas exploitables légalement par extraction ; les API de trafic sont payantes.
- **Électricité** : signalement des coupures par commune.
- **Pharmacies de garde**, **résultats d'examens et calendrier des concours**, **jours fériés et début du Ramadan**, **nécrologie et emplois** (déjà au backlog).
- **Fact-checking** (« Vérifié ») : s'appuyer sur Guinée Check / Africa Check plutôt que de refaire.

## 11. Contraintes de langue et de possibilités

- **Unités locales** : sac de 50 kg, tas, bidon de 20 L, demi-sac… Il faut une unité normalisée par produit, sinon les prix ne sont pas comparables.
- **Montants** : formats lisibles (« 8 000 000 GNF », « 8 millions »), jamais ambigus.
- **Langues locales** : les noms de produits en pulaar/maninka/soussou viennent **du dictionnaire avec provenance** ou d'un locuteur, jamais d'une traduction automatique. Pour les lecteurs peu lettrés : **icônes** et **audio enregistré par un humain** du « prix du jour ».
- **Lecture vocale des nombres** : à tester en français/anglais ; pas de voix pulaar standard (voir `PLAN_EVOLUTION.md` §4-E).
- **Faible débit** : pages légères, mode hors-ligne (PWA), partage WhatsApp d'une fiche prix.
- **Collecte sans smartphone** : SMS ou WhatsApp possibles plus tard, mais avec un coût (SMS, API WhatsApp Business) à budgéter.
- **Capacité technique** : les imports PDF (BCRG, INS) sont fragiles ; prévoir une saisie de secours par la rédaction.

## 12. Questions ouvertes

1. Nom : « Baromètre des prix », « Le prix du jour », ou autre ?
2. **« Fréquentation de zones »** : voulez-vous dire embouteillages, affluence des marchés, files aux stations, ou autre chose ?
3. Premiers produits souhaités (au-delà de la moto, du riz, du carburant) ?
4. Qui valide les relevés au début (vous, un relecteur) ?
5. SIMPRIX : voulez-vous qu'on le cite comme source, voire qu'on contacte la DNCIC pour un partenariat ?

## Sources

- SIMPRIX : allAfrica (26 juillet 2025) ; Guinéenews (31 juillet 2024, lancement) ; allAfrica (17 février 2026, protocole sur les prix plafonds) ; Koaci (19 février 2026).
- Données ouvertes : HDX « WFP Food Prices for Guinea » ; Banque mondiale, Microdata Library « Monthly food price estimates by product and market » (Guinée, 20 marchés, version du 2026-10-05).
- BCRG : cours de référence (PDF du 19/09/2025 et du 30/12/2025). INS Guinée : bulletins IHPC.
- Carburant : GlobalPetrolPrices (Guinée) ; Guinéenews (Union des Consommateurs ; pénurie de Kindia).
- Presse : Guinéenews, « Panier de la ménagère à Conakry » (8 mars 2025).
- Méthodes de collecte citoyenne : JRC (Commission européenne), « Food Price Crowdsourcing Africa » ; Nature Scientific Data (PMC10338426) ; Banque mondiale, blog « Real-time prices, real results ».
