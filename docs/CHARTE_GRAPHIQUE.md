# Kaloum24 — Charte graphique (S0b) : état et choix en attente

> Statut : **direction « indigo + ocre » (inspirée des références africaines de Samba) appliquée le 2026-11-21 — voir « Implémentation S0b » en bas.** Les 3 directions A/B/C ci-dessous sont l'historique. Aucun secret ici.

## 1. Constat (vérifié dans le code et en production, 2026-11-21)

- Les couleurs viennent du gabarit Wagtail « news-template » : *mackerel* `#26899E` / `#96D7E5` / `#1A2A2E` + gris. Ce n'est pas une identité Kaloum24.
- **Les polices Source Serif 4 et Source Sans 3 sont déclarées dans Tailwind mais jamais chargées** : le CSS compilé ne contient des `@font-face` que pour Source Code Pro. Les titres s'affichent donc avec la police serif/sans **par défaut de l'appareil** : le rendu varie d'un téléphone à l'autre.
- **Aucune des polices du site (ni Source Serif 4, Source Sans 3, Source Code Pro, ni Montserrat/Roboto Slab de `/pulaar/`) ne contient les lettres du Pulaar ɓ ɗ ŋ ƴ.** Ces lettres s'affichent par repli sur une autre police (visible, mais irrégulier). Mesuré sur les fichiers `.woff2` du dépôt avec fontTools.
- Couleurs ajoutées sans charte : rouge `#c8102e` du flash info, reflet du logo (provisoires).
- Logo : le nom « KALOUM24 » en texte (police de titre). **Conservé.**

## 2. Polices vérifiées pour les lettres du Pulaar

Couverture de ɓ ɗ ŋ ƴ (majuscules comprises) mesurée sur les fichiers `latin` + `latin-ext` de Fontsource :

| Police | ɓ ɗ ŋ ƴ Ɓ Ɗ Ŋ Ƴ | Rôle possible |
|---|---|---|
| Noto Sans, Noto Serif, Inter, Merriweather, Andika | **toutes présentes** | retenues |
| Source Sans 3 | manque ƴ Ƴ | écartée |
| Source Serif 4, Fraunces, Lora, IBM Plex (Sans/Serif), Work Sans | manque ɓ ɗ ƴ (et majuscules) | écartées |

Toutes les polices retenues sont sous licence libre (OFL). À auto-héberger en `woff2` (sous-ensembles latin + latin-ext) : pas de dépendance à Google, poids maîtrisé.

## 3. Les trois directions

| | **A — Encre** | **B — Drapeau** | **C — Terre** |
|---|---|---|---|
| Ambiance | presse sérieuse, sobre | couleurs guinéennes, identitaire | chaleureuse, humaine |
| Titres / texte | Merriweather / Noto Sans | Noto Serif / Inter | Noto Serif / Andika |
| Marque | bleu nuit `#12263A` | vert `#0B6B3A` | terre cuite `#A2411F` |
| Accent | bleu-vert `#0E7C86` | jaune `#FCD116` (aplat seulement) | ocre `#C98A1B` (aplat seulement) |
| Urgence (flash info) | `#C8102E` | `#CE1126` | `#B3261E` |
| Fond clair | `#FFFFFF` | `#FFFDF5` | `#FBF6EE` |
| Mode sombre | fond `#0F1A24` | fond `#0C1710` | fond `#1C1410` |

Contrastes calculés (WCAG, 4,5 minimum pour le texte) : tous les couples texte/fond, marque/fond, texte/étiquette et blanc/urgence sont ≥ 4,5 en clair et en sombre. **Règle** : le jaune (B) et l'ocre (C) ne servent jamais de couleur de texte sur fond clair (1,4 et 2,7).

Détails complets dans l'aperçu HTML.

## 4. À décider (propriétaire)

1. Direction A, B, C, ou mélange (ex. palette B avec polices A).
2. Logo : garder le nom en texte (défaut) ; faut-il un pictogramme (icône carrée pour WhatsApp, favicon) ? Si oui, un logo existant à reprendre, ou conception sur demande.
3. Mode sombre : conservé (défaut) ou retiré.

## 5. Mise en œuvre (après choix)

1. Variables CSS uniques `--k24-*` (couleurs, polices, espacements) ; suppression des couleurs en dur (`#c8102e` etc.).
2. Auto-hébergement des polices retenues (`static/fonts/`, `@font-face` avec `font-display: swap`) ; correction du chargement actuel.
3. Application : bandeau, accueil, cartes, article, étiquettes (Rédaction / Tribune / Contribution / Décryptage), boutons, formulaires. Gabarit `/pulaar/` inchangé (charte Tiadra).
4. Tests : présence des `@font-face`, contraste, rendu des quatre lettres ; vérification en production sur téléphone.
5. Mettre à jour ce document avec la direction retenue et les jetons définitifs.

## Implémentation S0b (déployée le 2026-11-21)

Direction retenue : **indigo + ocre sur crème**, inspirée des photos de référence de Samba (cercles concentriques sculptés, indigo tissé, bandes de couvertures, vannerie). Les photos ne sont pas reproduites : motifs refaits à la main en SVG/CSS.

- Tokens `--k24-*` dans `kaloum24_v2/home/static/home/k24.css` : indigo #1E2B63, nuit #0E1433, ocre #E08A2E (ocre foncé #9A4F0B pour texte), crème #F6EEDF, sable #E8DAC0, rouille #A3442A, encre #141A33.
- Polices auto-hébergées (woff2, `home/static/home/fonts/`) : **Unbounded 600** (titres, nav) et **Charis SIL 400/700** (texte). Sous-ensemble latin-ext limité aux lettres ɓ ɗ ŋ ƴ ɲ ɛ ɔ ƙ + diacritiques : vérifié en production.
- Signature : médaillon concentrique (`medaillon.svg`, masque CSS) dans le logo (rotation lente) et le hero ; bande tissée ocre/indigo sous l'en-tête.
- Mode sombre : fond nuit indigo, liens ocre clair.
- Accessibilité : focus visible ocre, `prefers-reduced-motion` respecté.
- Fait ensuite : pages article, pied de page, mobile, recherche en français, teintes du gabarit remplacées. Reste : listes par rubrique, dictionnaire `/pulaar/`, Safari, et la diversification par page (voir « Une charte, plusieurs ambiances »).

## Principe : une charte, plusieurs ambiances (demande du propriétaire, 2026-11-21)

Le propriétaire veut une **hyperdiversification** : chaque type de page a son propre décor et ses propres éléments, au lieu d'un seul habillage répété. Se fait **au fil du temps**, page type par page type. Non planifié en sprint pour l'instant.

**Règle** : ce qui reste commun = les tokens `--k24-*` (couleurs, polices, contrastes, accessibilité, mouvement réduit). Ce qui change par page = motif, composition, mouvement, illustration. Chaque ambiance est un fichier CSS (+ JS léger) chargé **uniquement** sur sa page (poids maîtrisé pour les connexions lentes).

| Page type | Ambiance proposée (à valider) | État |
|---|---|---|
| Accueil | Le seuil (cercles), étoffes par rubrique, lettres du pulaar | **fait** |
| Article | Lecture calme, barre de progression | base faite, à enrichir |
| Liste / rubrique | À décider : une ambiance par rubrique (motif et teinte dominante propres) | à faire |
| Dictionnaire pulaar | Charte Tiadra + motifs peuls, sur validation des locuteurs | à faire |
| Météo, Prix, Revue de presse | Une identité par service (données lisibles d'abord) | à faire |
| Pages cadre (À propos, mentions) | Sobre | à faire |

**Contraintes** : pas d'imitation de motifs réels sans source ; aucun sens inventé ; poids de page surveillé ; contraste ≥ 4,5 ; respect de « mouvement réduit ».
