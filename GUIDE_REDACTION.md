# Guide de la rédaction

Ce guide s'adresse aux personnes qui publient les articles. Aucune compétence
technique n'est nécessaire.

> **À personnaliser avant de le remettre à un client :** remplace « Kaloum24 »
> par le nom de son site et `http://127.0.0.1:5000` par son adresse réelle.

---

## 1. Se connecter

1. Ouvre `http://127.0.0.1:5000/connexion`
2. Saisis ton pseudo et ton mot de passe
3. Clique sur **Admin** en haut à droite

Si tu ne vois pas le bouton **Admin**, c'est que ton compte n'a pas les droits
de rédaction. Demande à l'administrateur du site de te passer en « modérateur ».

Mot de passe oublié : clique sur **Mot de passe oublié ?** depuis la page de
connexion. Tu recevras un lien valable une heure.

---

## 2. Publier un article

**Articles → + Nouvel article**

### Les champs, un par un

| Champ | À quoi il sert | Conseil |
| ----- | -------------- | ------- |
| **Titre** | Le titre affiché partout | Court et concret. Évite les titres vagues. |
| **Résumé** | Apparaît dans les listes **et dans l'aperçu WhatsApp** | 2 phrases. C'est ce que les gens lisent avant de cliquer — soigne-le. |
| **Contenu** | Le corps de l'article | Voir la barre d'outils ci-dessous. |
| **Image principale** | La photo en haut de l'article et dans les partages | Format paysage. Un article avec photo est beaucoup plus partagé. |
| **Crédit photo** | Le nom du photographe ou de l'agence | À remplir dès que la photo n'est pas de toi. |
| **Rubrique** | Le classement de l'article | Obligatoire. |

### La barre d'outils du contenu

- **Normal / Titre 2 / Titre 3** : structure l'article avec des intertitres.
  Un article long sans intertitres décourage la lecture.
- **B / I / U** : gras, italique, souligné.
- **Guillemets** : met une citation en valeur.
- **Lien** : sélectionne d'abord le texte, puis clique sur le lien.
- **Image** : insère une photo *dans* le texte (différent de l'image principale).
- **Listes** : à puces ou numérotées.
- **Tx** : efface la mise en forme d'un texte collé depuis Word.

> **Collage depuis Word ou un PDF :** colle ton texte, sélectionne-le, puis
> clique sur **Tx**. Cela supprime les mises en forme parasites qui déforment
> l'affichage.

### Les trois cases à cocher

- **Réservé aux abonnés** — seuls les abonnés payants voient l'article complet.
  Les autres n'en lisent que le début.
- **Mettre à la une** — place l'article en grand en haut de l'accueil.
  Un seul article peut être à la une : cocher cette case retire l'ancien.
- **Publier** — décoche pour enregistrer en **brouillon** (invisible du public).

Clique sur **Créer l'article**. C'est en ligne.

---

## 3. Modérer les commentaires

**Commentaires**

Les commentaires n'apparaissent **jamais** sur le site avant ta validation.
C'est volontaire : cela évite les insultes et le spam.

Quatre onglets :

- **En attente** — à traiter. Le chiffre orange dans le menu indique combien.
- **Signalés** — des lecteurs ont alerté sur ces commentaires. À regarder en priorité.
- **Approuvés** / **Rejetés** — l'historique.

Pour chaque commentaire : **Approuver** (il devient public), **Rejeter** (il
reste caché) ou **Supprimer** (il disparaît définitivement).

Le bouton **Tout approuver** traite d'un coup toute la file d'attente. À
n'utiliser que si tu as relu les commentaires — il ne fait aucune vérification.

**Rythme conseillé :** passe voir les commentaires deux fois par jour. Une file
qui s'accumule décourage les lecteurs de commenter.

---

## 4. Gérer les rubriques et les comptes

*(réservé aux administrateurs)*

**Rubriques** — ajoute ou supprime les sections du menu. Une rubrique contenant
des articles ne peut pas être supprimée : déplace-les d'abord.

**Utilisateurs** — attribue les rôles :

| Rôle | Peut faire |
| ---- | ---------- |
| `user` | Lire et commenter |
| `moderateur` | + Écrire des articles, modérer les commentaires |
| `admin` | + Gérer les rubriques, les comptes et les rôles |

Le bouton **Bannir** empêche un compte de commenter, sans le supprimer.

---

## 5. Publier depuis WhatsApp (correspondants)

*(l'ajout de correspondants est réservé aux administrateurs — voir
**Correspondants** dans le menu)*

Un correspondant enregistré peut rédiger et envoyer un article complet sans
jamais ouvrir le site, uniquement depuis WhatsApp.

### Pour un administrateur : ajouter un correspondant

1. **Correspondants** → renseigne son nom et son numéro WhatsApp (tu peux le
   taper comme on te le donne, ex. `620 00 00 01` — il est complété
   automatiquement).
2. C'est tout. Le correspondant peut écrire dès que son numéro apparaît dans
   la liste avec le statut **Actif**.

Le bouton **Désactiver** coupe l'accès sans supprimer l'historique — utile si
un correspondant part temporairement. **Supprimer** retire l'accès
définitivement ; ses articles déjà publiés restent en ligne.

### Pour le correspondant : comment ça marche

Depuis son numéro WhatsApp enregistré :

1. Il envoie son texte — **la première ligne devient le titre** de l'article.
2. Il envoie une photo s'il en a une (facultatif).
3. Il écrit **PUBLIER**.

L'article part alors dans la file de relecture, **jamais publié
automatiquement** — il apparaît en brouillon parmi les autres articles,
identifié par un badge « WhatsApp », et suit exactement le même circuit de
relecture qu'un article écrit depuis le site.

D'autres commandes existent : **ANNULER** efface le brouillon en cours,
**STATUT** rappelle où il en est, **AIDE** renvoie ces instructions.

**Ce que ça change pour la modération :** un article WhatsApp arrive sans
rubrique choisie (classé par défaut) et sans mise en forme (pas de gras, pas
d'intertitres — juste des paragraphes). Prévois de le retravailler un minimum
avant publication, comme une dépêche brute reçue par téléphone.

---

## 6. Ce que voient les lecteurs

- **Mode sombre** : bouton lune/soleil en haut. Le choix est mémorisé.
- **Écouter l'article** : le site lit l'article à voix haute. Utile en
  déplacement et pour les personnes qui lisent difficilement.
- **Partage** : boutons WhatsApp, X, Facebook et copie du lien sur chaque
  article. WhatsApp est de loin le plus utilisé — c'est pour ça qu'un bon
  résumé et une bonne photo comptent autant.
- **Météo** : affichée automatiquement dans l'en-tête.

---

## 7. Bonnes pratiques

**Pour être lu**
- Un titre concret vaut mieux qu'un titre spectaculaire mais vague.
- Le résumé est ce qui s'affiche sur WhatsApp : écris-le en pensant à quelqu'un
  qui hésite à cliquer.
- Toujours une photo. Un article sans image est nettement moins partagé.
- Des intertitres tous les 3 ou 4 paragraphes.

**À éviter**
- Publier une photo trouvée sur Internet sans en avoir le droit. C'est un risque
  juridique réel pour le site. Utilise tes propres photos, des banques d'images
  libres, ou obtiens l'autorisation.
- Laisser des articles en brouillon trop longtemps : ils vieillissent.
- Approuver les commentaires en masse sans les lire.

**En cas de doute sur une information :** ne publie pas. Une rectification coûte
toujours plus cher en crédibilité que le retard d'une heure.
