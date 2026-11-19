# Analyse d'efficacité d'exécution : skill `barometre-sites`

Date : 2026-11-19. Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites` (SKILL.md, `references/lectures-independantes.md`, `INSTALLER-AVEC-UN-ASSISTANT-IA.md`) et le code orchestré (`scripts/barometre.py` et ses étapes). Pré-passe : aucun problème détecté (graphe de dépendances vide, aucun cycle, aucune chaîne de sous-agents).

## Bilan

L'exécution est globalement bien pensée : la partie lourde (plusieurs heures de mesure réseau) est entièrement scriptée hors du contexte de Claude, les lectures IA sont déléguées à des sous-agents en arrière-plan qui écrivent leurs résultats dans des fichiers, et les ressources sont chargées à la demande. Les points faibles sont un **ordonnancement contre-productif autour de la lecture 3** (la parallélisation d'une synthèse de quelques secondes fait grossir inutilement la lecture la plus coûteuse), des **appels `get_rule` répétés** dans chaque sous-agent, des **lots de trois sites trop lourds** pour des lectures d'images et de DOM, et une consigne « lire le journal » qui risque de faire entrer un long journal dans le contexte du parent. Aucun problème critique (pas de cycle, pas de sous-agent qui en lance un autre).

## Constats

### 1. La première synthèse tourne en parallèle des lectures 1 et 2, donc la lecture 3 est surdimensionnée (moyenne, ordonnancement)

- **Où** : `SKILL.md:78-80` ; `references/lectures-independantes.md:23` ; `scripts/regles_une_source.py:26-32` ; `scripts/lecture_critique.py:283-293`.
- **Constat** : l'étape 1 lance les lectures 1 (textes légaux) et 2 (captures) en arrière-plan et, « pendant ce temps », la première synthèse. Or `lecture_critique.py` ne fusionne les lectures IA que si leurs fichiers `lecture_ia_lot*.json` et `lecture_visuelle_lot*.json` existent déjà. Comme la synthèse dure quelques secondes (`SKILL.md:65`) et les lectures plusieurs minutes, la première synthèse se fait **sans** les lectures 1 et 2. `regles_une_source.py` liste alors comme « à une seule source » toutes les règles que ces lectures auraient justement apportées en deuxième source (environ 40 règles « lecture » et 30 règles visuelles, par site). La lecture 3 (DOM, captures, paiement), la plus chère en contexte, reçoit donc une liste trop longue.
- **Effet secondaire** : les motifs `resultats/sources-*/lecture_*_lot*.json` sont triés sur toutes les dates. Pendant la fenêtre où les nouvelles lectures ne sont pas encore écrites, la première synthèse peut reprendre les lectures d'un **passage précédent**. C'est d'abord un risque de justesse, mais il fausse aussi le calcul du périmètre de la lecture 3, dans un sens comme dans l'autre.
- **Alternative** : attendre la fin des lectures 1 et 2 (notifications d'arrière-plan), puis lancer la synthèse, puis `regles_une_source.py`, puis la lecture 3. La parallélisation actuelle ne fait gagner que quelques secondes.
- **Gain estimé** : la liste de la lecture 3 se réduit nettement, sans doute de 30 à 50 % des règles par site (les deux tiers des règles des lectures 1 et 2 sortent d'ordinaire avec une preuve C ou NC). Soit autant de lectures de DOM et de captures en moins par sous-agent, et moins de citations à vérifier ensuite.

### 2. Chaque sous-agent rappelle `get_rule` pour les mêmes règles (moyenne, regroupement manqué)

- **Où** : `references/lectures-independantes.md:8` (« Consulter le protocole de chaque règle avec l'outil MCP Opquast `get_rule` »), lignes 15, 19 et 23 pour les listes de règles.
- **Constat** : trois lectures × deux lots = six sous-agents. Les deux lots d'une même lecture portent sur **les mêmes règles** (environ 40 pour la lecture 1, 30 pour la lecture 2, la liste variable de la lecture 3). Chaque sous-agent recharge donc les mêmes protocoles : de l'ordre de 2 × (40 + 30 + N) appels MCP, dont la moitié en double, et une consigne qui n'exige pas de les appeler en parallèle dans un seul message.
- **Alternative** : le parent (ou un petit script) extrait **une fois** les protocoles des règles concernées dans `<hors>/protocoles-lecture-N.json` (avec `get_rule` en format `detailed`, ou à partir de `referentiel/opquast-checklist-v5.json`, qui contient déjà `description` et `goal`), puis passe ce fichier au sous-agent. Les sous-agents restent indépendants des résultats, puisqu'ils ne lisent ni `resultats/` ni les verdicts. À défaut, ajouter à la consigne commune : « appeler `get_rule` pour toutes les règles du lot dans un seul message, en parallèle ».
- **Gain estimé** : environ la moitié des appels `get_rule` en moins, et des sous-agents qui démarrent plus vite. Le protocole est aussi garanti identique pour les deux lots.

### 3. Des lots de trois sites trop lourds pour les captures et le DOM (moyenne, délégation multi-sources)

- **Où** : `references/lectures-independantes.md:3`, lignes 19 et 23.
- **Constat** : les lectures 2 et 3 lisent des captures pleine page (deux JPEG par écran) et des DOM complets. Un lot de trois sites représente environ 23 écrans, donc une cinquantaine d'images, plus autant de fichiers HTML pour la lecture 3. Chaque image et chaque DOM coûte des milliers de jetons. On risque d'atteindre la saturation, puis le résumé automatique du contexte, avec à la clé une perte de preuves et des citations approximatives, rejetées ensuite par `verifier_citations.py`.
- **Alternative** : un sous-agent **par site** pour les lectures 2 et 3 (six en parallèle, en arrière-plan), et garder les lots de trois pour la lecture 1 (des textes, plus légers). La sortie reste un fichier par lot ou par site, que `lecture_critique.py` sait déjà fusionner, puisqu'il lit tous les `lot*` par glob. Il suffit d'accepter un nom `lecture_visuelle_<préfixe>.json`, ou de garder `lotN` avec N de 1 à 6.
- **Gain estimé** : un contexte par sous-agent divisé par trois environ, moins de citations rejetées, et un temps total plus court, puisque six sous-agents tournent en parallèle au lieu de deux.

### 4. « Lire le journal » le matin, sans le cibler (moyenne, lecture par le parent)

- **Où** : `SKILL.md:61` ; `INSTALLER-AVEC-UN-ASSISTANT-IA.md:51` ; `scripts/barometre.py:120-124` et `171-174`.
- **Constat** : le journal d'un passage de nuit capture toute la sortie de plus de 20 scripts sur 47 écrans (une ligne par écran et par outil, des extraits JSON tronqués, des tentatives après 429). Il peut atteindre des milliers de lignes. Si la consigne est appliquée à la lettre, tout le journal entre dans le contexte du parent, alors que seul le bilan final compte, avec les lignes d'échec et de non-test.
- **Alternative** : préciser dans SKILL.md de lire seulement la fin du journal, ou d'en extraire les lignes utiles. Par exemple : `tail -n 40 resultats/journal-barometre-<date>.log` pour le bloc « Bilan », et `grep -nE "ÉCHEC|Échec|non testé|429|anti-robot" …` pour les incidents. On peut aussi déléguer la lecture à un sous-agent qui ne rend qu'un résumé de 10 lignes.
- **Gain estimé** : de quelques milliers à quelques dizaines de milliers de jetons évités dans le contexte principal, à chaque passage.

### 5. Consignes de retour des sous-agents : bonnes, mais chemin de sortie incomplet (faible)

- **Où** : `references/lectures-independantes.md:11`, puis 15, 17 et 21.
- **Constat** : le retour est bien cadré (« bilan court : décompte par statut et par site, cinq constats marquants ») et le détail part dans un fichier JSON au format imposé, ce qui est le bon modèle. Mais seule la lecture 1 donne le chemin complet (`resultats/sources-<date>/…`) et le format JSON. Pour les lectures 2 et 3, il n'y a que le nom du fichier, et le format est implicite (preuve `dom:` / `capture:`, mais pas la structure `{"Site": {"n": [statut, preuve, nature]}}`). Il manque aussi une limite de longueur pour le bilan.
- **Alternative** : reprendre dans la consigne commune le chemin de sortie, le format JSON (identique pour les trois lectures) et une contrainte du type « répondre UNIQUEMENT par le bilan, 15 lignes au plus ».
- **Gain estimé** : moins d'allers-retours de correction et des retours plus courts dans le contexte du parent.

### 6. Vérification d'installation lancée deux fois (faible)

- **Où** : `SKILL.md:24-26` ; `scripts/barometre.py:152-156`.
- **Constat** : la skill demande de lancer `verifier_installation.py` avant le premier passage, et `barometre.py` le relance de lui-même avant les étapes `mesure`, `releve` et `sources`. Les deux s'enchaînent à chaque premier passage. C'est sans gravité (un script en lecture seule, quelques secondes), mais la sortie arrive deux fois dans le contexte.
- **Alternative** : dire dans SKILL.md que la vérification manuelle ne sert qu'à l'installation, ou après un code 3, et que le passage normal s'appuie sur la vérification intégrée.

## Pistes d'optimisation plus larges

### A. Entrelacer les sites dans les scripts de mesure (impact fort sur la durée, à valider avec Mattea)

`barometre.py:158-170` enchaîne une vingtaine de scripts strictement l'un après l'autre. Chacun parcourt les 47 écrans **site après site**, avec des pauses de 3 à 10 s : `controles_reseau.py` (délai de 8 s par défaut), `i18n_w3c.py`, `redbot_local.py`, `sources_html.py`, `sources_html2.py` (6 s), `axe_playwright.mjs`, `outils_page.mjs` (6 à 8 s), `sources_page.mjs` (6 à 8 s), `releve_regles.mjs`, etc. La règle de prudence porte sur **une requête toutes les 6 à 10 s par site**. Pourtant, comme les scripts traitent les sites un par un, le passage attend 6 fois plus que cette règle ne l'impose.

`controles_reseau.py:87-99` gère déjà un espacement **par hôte** (`self.derniere[hote]`). Une boucle en tourniquet sur les sites (écran 1 du site A, puis écran 1 du site B, etc.), ou un travailleur par site, garderait le même rythme pour chaque boutique et diviserait le temps d'attente par 4 à 6. Le passage durerait environ une heure au lieu de plusieurs.

**Réserve importante** : `controles_reseau.py:19` écrit explicitement « un seul site à la fois ». Les six boutiques sont hébergées chez Shopify, donc le rythme global vu par l'infrastructure Shopify depuis une même adresse IP serait multiplié par six, ce qui augmente le risque de 429 ou de contrôle anti-robot. Le passage de nuit rend aussi la durée peu gênante. Il faut donc présenter cette piste comme une option (par exemple un `--entrelacer` limité à 2 ou 3 sites à la fois), et non comme un défaut. La décision revient à Mattea.

### B. Ordonnancement cible des étapes qui demandent Claude

1. Lectures 1 et 2 en arrière-plan : lecture 1 en deux lots, lecture 2 avec un sous-agent par site. Les protocoles sont extraits une fois au préalable (constat 2).
2. Attente des notifications, puis première synthèse et `regles_une_source.py` (constat 1).
3. Lecture 3 avec un sous-agent par site, sur la liste réduite.
4. Synthèse finale, puis la commande d'une ligne qui liste les écarts sans décision (`SKILL.md:98-100`, déjà compacte).

## Ce qui est déjà efficace (à garder)

- **Le travail lourd est hors du contexte du modèle** : toute la mesure est dans `barometre.py`, avec reprise par `--depuis`, rapport par étape, `--essai` et `--service`. Claude ne lit jamais les DOM ni les résultats bruts pour produire les scores.
- **Délégation correcte des lectures** : sous-agents `general-purpose` en arrière-plan, et le parent ne lit pas les sources (textes, captures, DOM) avant de déléguer. L'interdiction de lire `resultats/` garantit à la fois l'indépendance et un contexte réduit.
- **Agrégation par fichiers** : chaque sous-agent écrit un JSON que `lecture_critique.py` fusionne par glob. Le parent ne reçoit qu'un bilan court. C'est le bon modèle pour des résultats de plus de 10 éléments.
- **Parallélisation des lectures 1 et 2** : les deux lectures indépendantes sont lancées ensemble. Seule la place de la synthèse dans ce bloc est à revoir.
- **Pas de chaîne de sous-agents** : les sous-agents ne délèguent pas eux-mêmes, et l'enchaînement passe par le parent.
- **Chargement des ressources à la demande** : SKILL.md est court (117 lignes). `references/lectures-independantes.md` n'est lu qu'au moment des lectures, et `INSTALLER-AVEC-UN-ASSISTANT-IA.md` ne concerne que les autres assistants.
- **Vérifications compactes** : la commande d'une ligne qui liste les écarts sans décision ne renvoie que des couples (site, règle). `verifier_publication.py` répond par un code de sortie. `regles_une_source.py` affiche un seul compte par site.
- **Pas de mémoire persistante** : l'agent est sans état, donc sans risque de chargement de mémoire inutile.
