# Lectures IA indépendantes (sources probabilistes)

Trois lectures, chacune en deux lots de trois sites (« Boutique A, Boutique B, Boutique C » puis « Boutique D, Boutique E, Boutique F »), lancées en arrière-plan avec l'outil Agent (`general-purpose`). Elles servent de deuxième source aux règles que les outils automatiques ne savent pas trancher. Préfixes de fichiers : le nom du site avec tout caractère hors `[A-Za-z0-9_]` remplacé par `_` (`Boutique_D`, `Boutique_E`).

## Consignes communes (à copier dans chaque brief)

- Lecture seule, aucune requête réseau. INTERDIT de lire quoi que ce soit dans le dépôt (`resultats/`, `scripts/`, `referentiel/`) : c'est ce qui rend la lecture indépendante. Seule exception : écrire le fichier de sortie.
- Consulter le protocole de chaque règle avec l'outil MCP Opquast `get_rule` (paramètre `number`) et l'appliquer à la lettre.
- Statuts : `C`, `NC`, `NA` avec une preuve, ou `NT` quand les fichiers ne suffisent pas. Ne jamais deviner.
- Confidentialité : remplacer noms de personnes, e-mails et téléphones par `[masqué]`. Pas de tiret long.
- Répondre par un bilan court : décompte par statut et par site, cinq constats marquants.

## 1. Textes légaux (`lecture_ia_lot1.json`, `lecture_ia_lot2.json`)

Entrées : `<hors>/textes/<préfixe>__*.txt` (pages légales du relevé et politiques Shopify publiques `__politique_*`). Règles : celles de nature « lecture » du relevé (contenus, e-commerce, identification, données personnelles : 7, 8, 16, 22, 29, 35, 36, 37, 42 à 45, 47 à 56, 58, 68, 99 à 101, 106, 108, 109, 112, 114, 115, 129, 151, 177, 178, 208, 2, 17, 40). Preuve : « citation exacte » (25 mots au plus) et le fichier. Règles « avant validation de la commande » : NT, en notant ce que disent les CGV. Sortie : `resultats/sources-<date>/lecture_ia_lotN.json` au format `{"Site": {"16": ["C", "« citation » (fichier)", "lecture"]}}`.

## 2. Captures (`lecture_visuelle_lot1.json`, `lecture_visuelle_lot2.json`)

Entrées : `<hors>/captures/<préfixe>__<gabarit>__haut.jpg` et `.jpg` (page entière). Règles visuelles : 2, 4, 6, 7, 8, 12, 22, 39, 40, 56, 65, 99, 100, 123, 127, 138, 139, 143, 153, 155, 157, 158, 160 à 163, 180, 184, 188, 192. Statut au niveau du site (non conforme si un écran l'est), avec l'écran en preuve. NT pour ce qu'une image fixe ne montre pas (survol, animation, focus).

## 3. DOM, captures et paiement (`lecture_dom_lot1.json`, `lecture_dom_lot2.json`)

Entrées : `<hors>/dom/*.html`, `<hors>/captures/`, `<hors>/paiement/<préfixe>.txt` et `.jpg`. Règles : celles qui restent à une seule source après l'étape `synthese` (les lister par site dans un fichier JSON passé au sous-agent). Preuve obligatoire sous l'une de deux formes, vérifiée ensuite :
- `dom: <fichier> | <extrait exact de 20 à 160 caractères>` (introuvable mot pour mot = rejeté) ;
- `capture: <fichier .jpg> | <ce qui est vu>` (jugement visuel).
Règles du tunnel (35, 36, 41, 44, 52, 56, 57, 86, 88, 89) : seulement sur `paiement/`, sinon NT.

Après les lectures : relancer `python3 scripts/barometre.py --hors <hors> --etapes synthese`, puis trancher les nouveaux écarts.
