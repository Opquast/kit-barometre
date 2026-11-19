# Analyse de la qualité des prompts : skill `barometre-sites`

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, `references/lectures-independantes.md`, `INSTALLER-AVEC-UN-ASSISTANT-IA.md`), recoupée avec le code du kit (`scripts/`, `referentiel/`, `AGENTS.md`).
Pré-passe : `prompt-metrics-prepass.json` (3 fichiers, environ 6 300 tokens, aucun motif de remplissage, aucun renvoi arrière, aucun chargement suggestif, aucun mur de texte ; `is_memory_agent: false`).

## Évaluation d'ensemble

**Type de skill.** Ce n'est pas un agent à persona : c'est une **skill de workflow orchestrateur** (chaîne de scripts déterministes, puis jugement de Claude sur les lectures indépendantes, l'arbitrage des écarts et la publication). Les critères « persona », « voix » et « Communication Style » de la grille BMAD ne s'appliquent donc pas ; l'absence de persona n'est pas un défaut. Le bon repère est « résultat + justification + HOW sélectif ».

**Vue d'ensemble.** La pré-passe compte `overview_lines: 0` parce qu'aucune section ne s'appelle « Overview ». En pratique, les lignes 8 à 10 de SKILL.md jouent ce rôle, et bien : l'objectif (taux de conformité, notes A à E), le principe directeur (deux sources indépendantes par règle, les outils ne votent pas) et le périmètre (fichiers de référence). C'est concis et porteur de sens. Il manque seulement un titre pour la repérer.

**Divulgation progressive.** 118 lignes, environ 3 300 tokens : bien en dessous des seuils. Le détail des lectures IA est sorti dans `references/`, et le guide multi-assistants dans un fichier à part. Le seul bloc qu'on pourrait encore sortir est le tableau des étapes (8 lignes), mais il est court et sert au routage : à garder.

**Synthèse.** La qualité d'écriture est élevée : des consignes impératives et denses, des justifications là où une contrainte n'est pas évidente (indépendance des sous-agents, ordre des lectures, « que vit l'utilisateur »), des conditions de sortie vérifiables (codes de retour, liste d'écarts vide), aucun remplissage. Les défauts sont de deux natures : la **portabilité du kit** (nom de la cliente, chiffres datés et un fichier absent du kit, codés en dur) et l'**autonomie des briefs de sous-agents** (chemin et format de sortie donnés pour une lecture sur trois seulement).

## Santé des prompts

| Indicateur | Constat |
|---|---|
| En-tête de config (`{communication_language}`) | 0/2. Sans objet : skill monolingue en français, hors cadre de config BMAD. Pas un défaut. |
| Conditions de progression | La pré-passe dit 0, faute de marqueurs standard, mais SKILL.md en contient de vraies : code 3 vers l'installation, « après son accord seulement », « quand les trois lectures sont rendues », « la liste des écarts sans décision doit être vide », « code 0 avant chaque commit ». C'est satisfaisant. |
| Autonomie (survie à la compaction) | `lectures-independantes.md` est conçu pour être copié dans chaque brief (« Consignes communes »), ce qui est bien, mais il reste incomplet pour les lectures 2 et 3 (voir constat M1). `INSTALLER-…md` est autonome par construction. |
| Frontmatter (`name`, `description`, `menu-code`) absent de deux fichiers | Sans objet : ce ne sont pas des prompts de capacité routés par un menu, mais une référence et un guide d'installation. |

## Fichier par fichier

- **SKILL.md** : orienté résultat, avec juste ce qu'il faut de HOW (commandes exactes, options, ordre). Les règles à ne jamais enfreindre viennent en tête, ce qui est le bon endroit. Les quatre questions pour trancher un écart forment un vrai cadre de jugement, avec exemples (règles 124 et 153), et non une formule de score. Le niveau de détail est bon.
- **references/lectures-independantes.md** : le cadrage est bon (statuts, preuve exigée, « ne jamais deviner », confidentialité, format du bilan). Il est sous-spécifié sur les sorties des lectures 2 et 3, et les listes de règles sont codées en dur (voir constats M1 et M2).
- **INSTALLER-AVEC-UN-ASSISTANT-IA.md** : très bonne idée, bien exécutée. Il couvre l'adaptation à un autre parc de sites, la correspondance entre les outils propres à Claude et leurs équivalents ailleurs, et le rappel des règles absolues. Le tableau des adaptateurs par plateforme correspondrait d'habitude à l'anti-motif « per-platform adapter » ; ici, c'est le livrable même du fichier, qui vise des assistants autres que Claude, donc **ce n'est pas du bruit**. Il reprend en partie le contenu de SKILL.md (liste de nuit, prérequis) : voir constat L4.

## Constats

### Moyenne

**M1. Briefs des lectures 2 et 3 sans chemin ni format de sortie** (`references/lectures-independantes.md:17-26`)
La section 1 donne le chemin (`resultats/sources-<date>/lecture_ia_lotN.json`) et le format JSON. Les sections 2 et 3 ne donnent que le nom du fichier. Or `lecture_critique.py:283-291` ne lit que `resultats/sources-*/lecture_{dom,visuelle}_lot*.json`. Un sous-agent qui ne reçoit que la section 3, ou une session compactée, peut écrire au mauvais endroit ou dans une autre forme, et la synthèse ignore alors la lecture sans rien signaler. Correctif : dans chaque section, écrire en toutes lettres « Sortie : `resultats/sources-<date>/lecture_visuelle_lotN.json`, même format `{"Site": {"n": [statut, preuve, "visuel"]}}` », et préciser pour la lecture 2 la forme de preuve `capture: <fichier> | <ce qui est vu>` que `verifier_citations.py:74` reconnaît.

**M2. Nom de la cliente et contexte propre à un projet codés en dur dans une skill distribuée en kit** (`SKILL.md:3, 19, 83, 94, 108, 109, 111`)
« Mattea », « Colorz » et « 6 boutiques Shopify » figurent dans la description et à sept endroits du corps. De son côté, `INSTALLER-…md` parle de « la personne » et anonymise les sites (« Boutique A à F »). Pour quelqu'un qui reprend le kit, la description se déclenche sur un contexte qui n'est pas le sien, et les consignes d'accord (« sans l'accord de Mattea ») visent une autre personne. L'étape 3 du guide d'installation liste les fichiers à adapter, mais pas SKILL.md. Correctif : écrire « la personne responsable du baromètre » (ou un nom défini une seule fois en tête), généraliser la description (« les sites du parc défini dans `scripts/ecrans_en_ligne.csv` »), et ajouter SKILL.md au tableau de l'étape 3. Note : `referentiel/repartition-regles.csv` et une trentaine de lignes des scripts nomment aussi Mattea ; cela relève du scanner de scripts.

**M3. Étape de publication qui renvoie à un fichier absent du kit** (`SKILL.md:110`)
`note_cadrage.md` n'existe pas dans `kit-barometre-sites/code/` (`generer_suivi.py:420` pointe vers le dépôt personnel d'origine). Avec le kit neuf, l'étape 5 échoue, ou pousse l'agent à créer une note sans cadre. Correctif : écrire « si `note_cadrage.md` existe… », sur le modèle déjà adopté pour ESM (ligne 85) et `liens-locaux.json` (ligne 107).

### Basse

**L1. Chiffre daté dans la vue d'ensemble** (`SKILL.md:8`) : « 92 % atteints le 13/11/2026 » vieillira au premier passage. Le retirer, ou le présenter comme un repère historique.

**L2. Contrôle déterministe en ligne de commande dans le prompt** (`SKILL.md:98-100`) : le one-liner Python qui vérifie qu'il ne reste aucun écart sans décision est fragile (glob, clés internes) et peu lisible. Ce contrôle a sa place dans un script (par exemple un code de retour de `lecture_critique.py`, ou une option `--verifier` de `barometre.py`), et le prompt ne garderait que « doit sortir à 0 ». Catégorie `intelligence-placement` (le scanner L6 détaillera).

**L3. Ordre des lectures ambigu après un passage complet** (`SKILL.md:76-81`) : le passage complet de nuit exécute déjà l'étape `synthese`. L'étape 1 du matin relance pourtant une « première synthèse », ce qui est redondant. Par ailleurs, la liste « une source » est calculée avant l'apport des lectures 1 et 2, donc la lecture 3 traite aussi des règles qu'elles auraient couvertes. C'est un choix défendable (gain de temps) mais il n'est pas dit. Une phrase suffit : « après un passage complet, la première synthèse est déjà faite : passer à l'étape 2 », et la raison du recouvrement assumé.

**L4. Doublons entre SKILL.md et INSTALLER qui ont commencé à diverger** : la liste du mode nuit (`SKILL.md:51-55` et `INSTALLER:80-84`), avec VPN et PowerToys Awake d'un seul côté, et le cas de Windows (« régler à la main » d'un côté, WSL de l'autre). Le doublon est voulu (le guide vise d'autres assistants), mais il faut décider lequel fait foi pour ces détails, ou aligner les deux textes.

**L5. Listes de numéros de règles codées en dur** (`lectures-independantes.md:15, 19, 26`) : la liste de la lecture 1 se termine par « 208, 2, 17, 40 », visiblement ajoutés après coup, ce qui annonce une dérive par rapport à `referentiel/repartition-regles.csv`. Mieux vaudrait faire produire ces listes par un script (comme `regles_une_source.py` le fait pour la lecture 3) ou les tirer du référentiel. Elles restent acceptables en l'état, car c'est une connaissance métier nécessaire.

**L6. Options incomplètes** (`SKILL.md:34, 65`) : `--installer` est montré sans `--hors`, alors que le contrôle du moteur Opquast en dépend (ligne 26) ; `--forcer` (passage de nuit sur batterie, `barometre.py:138`) n'est pas mentionné, alors que la ligne 51 dit que le mode nuit s'arrête sur batterie.

**L7. Vue d'ensemble sans titre** (`SKILL.md:8-10`) : le contenu est bon. Un titre « ## Vue d'ensemble » aiderait le repérage et les outils de contrôle. C'est purement cosmétique.

### Note

- `SKILL.md:20` demande « commit et push après chaque étape terminée » : c'est cohérent avec le contrôle `verifier_publication.py` avant chaque commit (ligne 106). Pour une personne qui reprend le kit, préciser que le dépôt doit être le sien (la ligne 111 dit « dépôt personnel »).
- Aucun remplissage défensif, aucune méta-explication, aucun « You are an AI » : la pré-passe et la relecture concordent.

## Points forts (à préserver)

- **Les garde-fous viennent en tête et sont formulés sans ambiguïté** (`SKILL.md:12-20`), avec le seul clic permis et l'unique exception (le panier sans saisie). Ils sont repris en substance dans `AGENTS.md` et `INSTALLER`.
- **L'accord avant installation est ancré dans le code**, pas seulement dans le prompt : `barometre.py` renvoie 3 et `verifier_installation.py` n'installe qu'avec `--installer`. Le prompt et le script disent la même chose.
- **Les quatre questions pour trancher un écart** (`SKILL.md:89-96`) : un cadre de jugement court, ordonné, illustré, avec une sortie explicite (« à arbitrer ») et le refus du vote entre outils. C'est exactement ce qui doit rester en prose.
- **L'indépendance des sous-agents est justifiée** (« c'est ce qui rend la lecture indépendante ») et vérifiée après coup (citations retrouvées mot pour mot, `verifier_citations.py`) : le jugement reste à l'IA, le contrôle au script.
- **Les cas dégradés sont traités** : pas d'ESM (ligne 85), premier passage sur un compte (ligne 107), anti-robot ou 429 (NT avec la raison).
- **Les codes de retour sont documentés** pour `verifier_publication.py` (0, 1, 2) et correspondent au code.
- **Le guide multi-assistants** : la table de correspondance entre les outils propres à Claude et leurs équivalents ailleurs rend le kit réellement portable.
