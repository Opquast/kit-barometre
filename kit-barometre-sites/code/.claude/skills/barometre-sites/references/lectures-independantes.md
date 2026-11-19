# Lectures IA indépendantes (sources probabilistes)

Trois lectures faites par des sous-agents (outil Agent, `general-purpose`, en arrière-plan). Elles servent de deuxième source aux règles que les outils automatiques ne savent pas trancher. Tout ce qui les décrit est dans `referentiel/lectures.json` : listes de règles, entrées attendues, taille des lots, nom du fichier de sortie, forme de preuve, règles du tunnel, consignes communes et longueur du bilan. Ne jamais recopier ces listes à la main : les modifier dans ce fichier.

## Briefs : générés, jamais écrits à la main

```bash
python3 scripts/preparer_lectures.py <hors>               # lectures 1 et 2
python3 scripts/preparer_lectures.py <hors> --lecture 3   # après regles_une_source.py
```

Un brief par sous-agent dans `<hors>/briefs/lecture<L>_lot<n>.md`, à passer tel quel comme prompt. Il contient les consignes communes, les sites du lot (lus dans `referentiel/parc.json`) avec leur préfixe de fichiers, la liste des fichiers d'entrée trouvés, la liste dédoublonnée des règles, la forme de preuve et le chemin de sortie daté exact (`resultats/sources-<date>/…`, `--date` pour un autre jour). Code 1 : une entrée obligatoire manque (textes, captures, DOM) ; le brief est écrit quand même et le signale, le sous-agent mettra NT. Relancer l'étape qui produit l'entrée si c'est possible.

Protocoles : chaque brief demande un seul `get_rule` par règle, au début. `<hors>/briefs/regles_a_charger.json` donne l'union des règles de tous les briefs : pour ne charger chaque protocole qu'une fois en tout, l'écrire dans `<hors>/protocoles/<règle>.md` avant de lancer les sous-agents ; les briefs régénérés pointent alors vers ces fichiers au lieu de `get_rule`.

Bilan rendu par chaque sous-agent : 15 lignes au plus (`bilan_max_lignes`), décompte par statut et par site, cinq constats au plus. Le détail est dans le fichier de sortie, pas dans la réponse.

## Les trois lectures

| Lecture | Lots | Entrées (`<hors>/…`) | Sortie (`resultats/sources-<date>/`) | Preuve |
|---|---|---|---|---|
| 1. Textes légaux | 3 sites | `textes/<préfixe>__*.txt` (pages légales, politiques Shopify `__politique_*`) | `lecture_ia_lot<n>.json` | `« citation exacte » (fichier.txt)`, 25 mots au plus ; NC ou NA par absence : `absent: ce qui a été cherché (fichier.txt)` |
| 2. Captures | 1 site | `captures/<préfixe>__*.jpg` (haut de page et page entière) | `lecture_visuelle_lot<n>.json` | `capture: fichier.jpg \| ce qui est vu` |
| 3. DOM, captures et paiement | 1 site | `dom/<préfixe>__*.html`, `captures/`, `paiement/<préfixe>.txt` et `.jpg` | `lecture_dom_lot<n>.json` | `dom: fichier \| extrait exact de 20 à 160 caractères` ou `capture: fichier.jpg \| ce qui est vu` |

Format commun de sortie : `{"Site": {"16": ["C", "<preuve>", "lecture"]}}`, nom du site exactement comme dans le parc, numéro de règle en chaîne, statut C, NC, NA ou NT. Le préfixe de fichiers est le nom du site où chaque suite de caractères hors `[A-Za-z0-9_]` devient `_` (`Boutique D` donne `Boutique_D`).

- Lecture 1 : règles « avant validation de la commande » en NT, en notant ce que disent les CGV. Un C n'est retenu que si sa citation est retrouvée mot pour mot (`verifier_citations.py`).
- Lecture 2 : statut au niveau du site (non conforme si un écran l'est, cet écran en preuve) ; NT pour ce qu'une image fixe ne montre pas (survol, animation, focus).
- Lecture 3 : règles de `<hors>/regles_une_source.json` seulement, un sous-agent par site. Règles du tunnel (liste `regles_tunnel`) : seulement sur `paiement/`, sinon NT. Un extrait DOM introuvable mot pour mot est rejeté.

## Validation des sorties

```bash
python3 scripts/valider_lectures.py <hors> [--exiger 1,2]
```

Lit les sorties du dernier passage de chaque lecture et vérifie : statut dans C, NC, NA, NT ; site connu du parc ; règle dans la liste de sa lecture (lecture 3 : liste du site dans `regles_une_source.json`) ; preuve au format ; fichier cité appartenant au site et présent dans `<hors>`. Code 0 : tout est valide ; 1 : liste lisible des erreurs (fichier, site, règle, raison), à corriger ou relancer le sous-agent ; 2 : usage. `--exiger` rend obligatoire la présence des lectures citées. `lecture_critique.py` applique les mêmes règles et écarte, en le disant, toute entrée invalide.

## Ordre

1. `preparer_lectures.py <hors>`, puis lancer en arrière-plan les sous-agents des lectures 1 et 2 (un par brief).
2. Attendre qu'ils soient tous rendus, puis `valider_lectures.py <hors> --exiger 1,2` jusqu'au code 0.
3. Synthèse : `python3 scripts/barometre.py --hors <hors> --etapes synthese`.
4. `python3 scripts/regles_une_source.py <hors>` (liste par site des règles restées à moins de deux sources).
5. `preparer_lectures.py <hors> --lecture 3`, puis un sous-agent par site.
6. Quand ils sont rendus : `valider_lectures.py <hors> --exiger 1,2,3` jusqu'au code 0.
7. Synthèse finale (`--etapes synthese`), puis trancher les nouveaux écarts.

Les sous-agents ne lisent jamais `resultats/`, `scripts/` ni `referentiel/` : c'est ce qui rend la lecture indépendante. Seule exception : écrire leur fichier de sortie.
