# Analyse de la qualité rédactionnelle des prompts : skill `barometre-sites`

Scanner : prompt craft (L2). Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites`. Pré-passe : `prompt-metrics-prepass.json` (agent sans mémoire, 3 fichiers, environ 5 900 jetons, aucun remplissage défensif, aucun renvoi arrière, aucun chargement suggestif, aucun bloc de texte massif).

## Évaluation d'ensemble

**Type de skill.** Ce n'est pas un agent à persona : c'est une skill d'orchestration de workflow (lancer une chaîne de scripts, faire tourner des sous-agents de lecture, arbitrer des écarts, publier). La grille « persona / style de communication » ne s'applique donc qu'à la marge. Le bon équilibre pour ce type de skill : résultat attendu, justification, et le « comment » seulement là où il le faut. C'est globalement ce que fait le texte.

**Overview.** Il n'y a pas de section `## Overview` en tant que telle (la pré-passe compte `overview_lines: 0`), mais les lignes 8 à 10 de `SKILL.md` en tiennent lieu : l'objectif (taux de conformité, notes A à E), le principe des deux sources indépendantes, le périmètre et les fichiers de référence. C'est dense et utile. Il manque surtout la **justification**, en une ou deux phrases : pourquoi deux sources (les outils se trompent dans les deux sens), pourquoi des lectures indépendantes (l'agent ne doit pas recopier ce que disent les outils), et à qui sert le livrable (Mattea et son suivi client). Une partie de cette justification apparaît plus loin (l. 78, l. 87, l. 90 « On ne fait jamais voter les outils »), mais elle est éparpillée.

**Divulgation progressive.** Elle est saine : `SKILL.md` fait 115 lignes (environ 2 900 jetons), le détail des briefs de sous-agents est sorti dans `references/lectures-independantes.md`, et le guide pour les autres assistants est dans un fichier à part. Le seul tableau de `SKILL.md` (les étapes, l. 67 à 74) est court et a sa place.

**Synthèse.** La skill est bien écrite : impérative, concrète, sans remplissage, avec des garde-fous clairs et un protocole d'arbitrage qui donne à l'agent un vrai cadre de jugement. Ses deux faiblesses : elle reste **liée à une installation précise** (Mattea, une adresse d'Artifact, un dépôt personnel, `note_cadrage.md`) alors que le kit est fait pour être réutilisé, et deux contrôles déterministes sont écrits en ligne de commande dans le prompt, dont l'un peut **passer à tort sans rien signaler** (le contrôle des données personnelles).

## État des prompts

| Fichier | Rôle | En-tête de configuration | Conditions de passage | Autonome |
|---|---|---|---|---|
| `SKILL.md` | mode d'emploi principal | non (sans objet ici) | implicites (ordre des sections, « après l'étape synthese, la liste doit être vide ») | oui |
| `INSTALLER-AVEC-UN-ASSISTANT-IA.md` | guide pour les assistants autres que Claude | non | étapes numérotées 1 à 6 | oui, délibérément (règles absolues répétées) |
| `references/lectures-independantes.md` | briefs des sous-agents | non | « Après les lectures : relancer synthese » | en partie (voir Constats 5 et 6) |

Aucun fichier n'a d'en-tête `{communication_language}`. Pour une skill monolingue en français, écrite pour une seule utilisatrice, ce n'est pas un défaut. Les champs de frontmatter « manquants » (`name`, `description`, `menu-code`) que la pré-passe relève sur les deux fichiers secondaires sont sans objet : ce ne sont pas des prompts de capacité appelés depuis un menu, mais un guide et une référence.

## Analyse par fichier

### `SKILL.md`
Orienté résultat, avec juste assez de « comment ». Les sections Règles, Prérequis, Déroulé, Trancher et Publication suivent l'ordre réel d'un passage. La section « Trancher les écarts » (l. 81 à 96) est le meilleur passage : quatre questions dans un ordre fixe, chacune avec un exemple de règle réel (124, 153). L'agent a ainsi une méthode de jugement plutôt qu'une table de décision. Les prérequis (l. 22 à 44) sont détaillés, mais ce détail sert : la liste des outils est ce que l'agent doit montrer à la personne avant de demander son accord.

### `INSTALLER-AVEC-UN-ASSISTANT-IA.md`
Écrit pour un autre lecteur (un assistant quelconque) ; il se déclare subordonné à `SKILL.md` (« il fait foi », l. 9). Le tableau des équivalences (l. 66 à 74) est l'exception justifiée à l'anti-motif « instructions par plateforme » : ce n'est pas Claude qu'on informe de ses propres outils, mais d'autres agents qui ne les ont pas. Il explique en plus pourquoi la séparation compte (« c'est cette séparation qui rend la lecture indépendante »). À garder. La répétition des règles absolues est voulue, puisque le fichier doit tenir seul.

### `references/lectures-independantes.md`
Concis et bien pensé : le bloc « Consignes communes (à copier dans chaque brief) » règle d'avance le problème d'autonomie des sous-agents, et la règle d'indépendance est justifiée. En revanche, ce fichier donne le format de sortie pour une seule des trois lectures, et il laisse à l'agent un calcul déterministe à faire (voir Constats 5 et 6).

## Constats (du plus grave au moins grave)

### 1. Élevé : le contrôle des données personnelles peut passer sans rien signaler
`SKILL.md:101-103`. La commande `grep` vise `resultats/*-$(date +%F)`, c'est-à-dire la date du jour où l'on publie. Or la skill recommande un passage de nuit (l. 50) avec la synthèse « le matin » (l. 61). Les dossiers `mesure`, `releve` et `sources` portent alors la date de la veille. Si aucun dossier ne correspond : sous zsh, le motif provoque l'erreur `no matches found` ; sous bash, `grep` écrit « No such file » sur la sortie d'erreur. Dans les deux cas, `grep -v` ne renvoie rien sur la sortie standard, ce qui ressemble exactement au résultat attendu (« ne doit rien renvoyer »). L'agent conclut que tout est propre alors que rien n'a été examiné.
**Pourquoi c'est important :** c'est le seul garde-fou avant le commit et le push des données personnelles (règle l. 17).
**Correction :** sortir ce contrôle dans un script (par exemple `scripts/verifier_donnees_perso.py`, ou une étape de `barometre.py`). Le script lit les dossiers du dernier passage, pas ceux de la date du jour, échoue explicitement quand il ne trouve aucun fichier à examiner, et renvoie un code non nul en cas de détection. Le prompt n'a plus alors qu'à dire : « lancer X ; il doit finir avec le code 0 ».

### 2. Élevé : valeurs propres à une installation, codées en dur dans un kit fait pour être réutilisé
`SKILL.md:3, 19, 79, 88, 104, 105, 106, 107, 108`. La description et le corps nomment « Mattea » partout, fixent l'adresse d'un Artifact précis (`https://claude.ai/artifact/12y1tK8TKX8uMtbi92d1Q8`, l. 104), « le dépôt personnel » (l. 108), « 6 boutiques, 47 écrans » (l. 10), « 92 % atteints le 13/11/2026 » (l. 8) et `note_cadrage.md` (l. 107). Ce dernier fichier n'existe pas dans le kit : `verifier_page_a4.py` le cherche à la racine, et `generer_suivi.py:420` renvoie vers un dépôt GitHub personnel. Pourtant `INSTALLER-AVEC-UN-ASSISTANT-IA.md` (étape 3, l. 39 à 51) dit d'adapter le baromètre aux sites d'une autre personne, et liste les fichiers à modifier sans jamais citer `SKILL.md`.
**Pourquoi c'est important :** chez un autre utilisateur, l'agent essaiera de publier sur un Artifact qu'il ne possède pas (publication refusée, ou pire, tentative de mise à jour du suivi de quelqu'un d'autre), demandera l'accord de « Mattea », et échouera sur `note_cadrage.md`.
**Correction :** remplacer ces valeurs par des paramètres déclarés une seule fois, en tête de `SKILL.md` ou dans un petit fichier `referentiel/config.json` (personne commanditaire, adresse de l'Artifact s'il existe sinon « nouvelle publication », dépôt, note de cadrage facultative). Ajouter `SKILL.md` (et cette configuration) au tableau de l'étape 3 de l'INSTALLER. Pour la publication, écrire : « sur l'Artifact de suivi existant s'il est configuré ; sinon, publier un nouvel Artifact et noter son adresse ». Garder les chiffres datés (92 %, 13/11) dans le suivi plutôt que dans le prompt, où ils vieillissent.

### 3. Moyen : vérification déterministe écrite en une ligne Python dans le prompt (placement de l'intelligence)
`SKILL.md:92-94`. La condition de passage la plus importante du workflow (« la liste des écarts sans décision doit être vide ») est contrôlée par une ligne `python3 -c` de 300 caractères, qui dépend de la structure interne de `lecture.json` (clés `_`, `ecarts`, `statut`, `regle != '-'`). C'est un contrôle de structure, donc du travail de script. Écrit dans le prompt, il est fragile (une évolution de `lecture_critique.py` le casse sans bruit) et l'agent ne peut ni le lire ni le corriger facilement. Le scanner des opportunités de script (L6) donnera le détail.
**Correction :** une option `lecture_critique.py --verifier` (ou une vérification à la fin de l'étape `synthese` dans `barometre.py`) qui affiche les écarts sans décision et renvoie un code non nul. Le prompt dit : « l'étape synthese doit finir sans écart non tranché ».

### 4. Moyen : l'affirmation sur la vérification des preuves est trop large
`SKILL.md:78` dit : « Une réponse « conforme » n'est retenue que si sa citation ou son extrait est retrouvé mot pour mot ». Dans le code, c'est vrai pour `lecture_ia` (citation vérifiée) et pour `lecture_dom` (extrait vérifié, ou « jugement visuel » accepté pour une preuve `capture:`). Mais `lecture_visuelle` est retenue **sans aucune vérification** (`lecture_critique.py:442-443`), et les « jugements visuels » de la lecture DOM aussi.
**Pourquoi c'est important :** quand l'agent tranche un écart, il donne à une lecture visuelle le poids d'une preuve vérifiée, et le compte rendu à Mattea (« part des statuts à deux sources ou plus ») surestime la solidité de ces statuts.
**Correction :** préciser la phrase, par exemple : « textes et DOM : citation ou extrait retrouvé mot pour mot ; captures : jugement visuel non vérifiable, à traiter comme la source la plus faible à la question 3 ». Ou bien ajouter une marque de vérification dans le code.

### 5. Moyen : format de sortie absent pour deux des trois lectures
`references/lectures-independantes.md:17-26`. Seule la lecture des textes légaux donne le format JSON (`{"Site": {"16": ["C", "« citation » (fichier)", "lecture"]}}`, l. 15) et le chemin `resultats/sources-<date>/`. Les lectures visuelle et DOM ne donnent ni le chemin complet ni la forme attendue. Or `lecture_critique.py` attend la même structure `{site: {règle: [statut, preuve, …]}}`, avec les noms de site exacts (pas les préfixes de fichiers). Le sens du troisième élément (« lecture ») n'est expliqué nulle part.
**Pourquoi c'est important :** les sous-agents ne voient que leur brief. S'ils inventent un format (clé « Boutique_D » au lieu de « Boutique D », liste d'objets, etc.), leur lecture est ignorée en silence à la synthèse : `lecture_critique.py` fait `.get(nom, {})`.
**Correction :** une ligne « Sortie » commune dans les Consignes communes : chemin, structure, nom de site exact tel qu'il figure dans `ecrans_en_ligne.csv` (et non le préfixe), et rôle du troisième élément.

### 6. Moyen : calcul déterministe laissé à l'agent pour la lecture DOM
`references/lectures-independantes.md:23` : « Règles : celles qui restent à une seule source après l'étape `synthese` (les lister par site dans un fichier JSON passé au sous-agent) ». Établir cette liste est un comptage de sources sur les sorties de `lecture_critique.py` : c'est déterministe. Laisser l'agent la reconstruire à la main, c'est risquer des oublis. Il faut en plus remarquer une circularité : il faut lancer `synthese` une première fois, faire la lecture DOM, puis relancer `synthese` (l. 28). `SKILL.md:76-78` présente les lectures comme une étape faite **avant** `synthese`, sans mentionner ce double passage.
**Correction :** faire écrire par `lecture_critique.py` (ou `generer_suivi.py`) un fichier `regles_une_source.json` par site, que le brief cite directement. Dans `SKILL.md`, expliciter l'ordre : textes et captures, puis `synthese`, puis DOM sur les règles à une seule source, puis `synthese` à nouveau.

### 7. Faible : dérive entre `SKILL.md` et l'INSTALLER sur des points secondaires
Les deux fichiers répètent la liste des prérequis, la liste de vérification du soir et les options de `--nuit`. Cette répétition est voulue, mais les deux versions ont déjà divergé :
- Windows : l'INSTALLER conseille WSL (l. 37) puis un réglage d'alimentation ou PowerToys (l. 90). `SKILL.md:61` ne parle que du réglage manuel.
- Le VPN (INSTALLER l. 82) est absent de `SKILL.md`.
- Le « contre-examen humain », compté comme source dans l'INSTALLER (l. 7), n'apparaît pas dans `SKILL.md`.
- Les conditions d'ajout d'un outil (mainteneur, licence, au moins deux semaines d'ancienneté, outils écartés, `SKILL.md:40`) manquent dans l'INSTALLER, alors que c'est justement l'assistant non-Claude qui sera tenté d'en ajouter.

`--forcer` (option réelle de `barometre.py`) n'est documenté dans aucun des deux fichiers. C'est peut-être volontaire, mais l'agent ne le saura pas si le script s'arrête avec le code 4 sur batterie.
**Correction :** dans l'INSTALLER, garder les règles absolues mais renvoyer à `SKILL.md` pour la liste des outils et la liste du soir, plutôt que de les recopier. Ou bien aligner les deux versions et documenter les codes de sortie 3 (prérequis) et 4 (batterie).

### 8. Faible : description de frontmatter très longue
`SKILL.md:3` (environ 130 mots). L'énumération des treize outils et sources n'aide pas au déclenchement : personne ne demande « relance Sa11y et html-validate ». Elle noie les vraies phrases de déclenchement de la fin (« relancer, rejouer, mettre à jour le baromètre… »). Le nom « Mattea » et « Colorz » y figurent aussi (voir Constat 2).
**Correction :** une phrase sur ce que la skill produit (taux de conformité Opquast V5 par site, page de suivi, CSV), puis les déclencheurs. La liste des outils a déjà sa place dans le corps (l. 28).

### 9. Faible : règle de forme mêlée aux règles de sécurité
`SKILL.md:20` : « Aucun tiret long » et « Commit et push après chaque étape » sont rangés parmi les « Règles à ne jamais enfreindre », au même rang que l'interdiction de payer ou de contourner un anti-robot. Le commit après chaque étape entre aussi en tension avec la règle l. 17 (vérifier les données personnelles avant chaque commit), alors que le contrôle n'est décrit qu'à la publication.
**Correction :** déplacer la règle de style et le rythme de commit dans une courte section « Conventions », et préciser que le contrôle des données personnelles (Constat 1) se lance avant chaque commit, pas seulement à la publication.

## Points forts (à préserver)

- **Le protocole d'arbitrage en quatre questions** (`SKILL.md:83-90`) : ordonné, illustré par des règles réelles, avec un principe clair (« On ne fait jamais voter les outils ») et une issue prévue quand l'ambiguïté demeure (« à arbitrer par Mattea »). C'est exactement le cadre qui permet de juger un cas imprévu.
- **Des garde-fous concrets et justifiés** : chaque interdit dit quoi faire à la place (« noté « non testé » avec la raison », « refuser les cookies », « elle se connecte elle-même »).
- **Le consentement à l'installation** (l. 26 à 38) : vérification sans modification, puis une liste avec le rôle de chaque élément et la commande prévue, puis l'accord en trois options, puis `npm ci --ignore-scripts`. C'est un modèle de conception sûre, de plus repris dans le code (`barometre.py` renvoie 3 avec le même message).
- **L'indépendance des sous-agents** : interdiction de lire `resultats/`, consignes à copier dans chaque brief, preuve à citer mot pour mot et vérifiée par un script. L'intelligence est bien placée : le jugement revient à l'IA, la vérification au script.
- **La gestion du temps et de la machine** (passage de nuit, liste de vérification, reprise avec `--depuis`) : elle tient compte de ce que vit l'utilisatrice, pas seulement de ce que fait le script.
- **Aucun remplissage** : la pré-passe ne relève aucune formule défensive, aucune méta-explication, aucun renvoi arrière, et la lecture le confirme.
