# Analyse de la surface de personnalisation : barometre-sites

Skill analysée : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, references/lectures-independantes.md, INSTALLER-AVEC-UN-ASSISTANT-IA.md), avec un regard sur le code du kit (`scripts/`, `referentiel/`, `AGENTS.md`). Analyse purement consultative : rien n'est cassé.

## Archétype

**Sans état (stateless)**, confirmé par le pré-passage : aucun sanctuaire (PERSONA, CREED, BOND, CAPABILITIES), aucune mémoire propre. L'état du baromètre vit dans les données du kit (`resultats/`, `referentiel/`) et dans un fichier hors dépôt (`liens-locaux.json`), pas dans l'agent. C'est donc la grille « stateless » qui s'applique : les deux moitiés (opportunités et abus) comptent, avec un accent sur les chemins codés en dur et les points d'accroche.

Particularité qui cadre tout le reste : ce n'est pas un agent de module BMAD, mais une skill de projet Claude Code, livrée dans un kit qui vise aussi d'autres assistants (Mistral, Codex, Gemini, Cursor, via `AGENTS.md` et le guide d'installation). Un `customize.toml` ne serait lu que par le résolveur BMAD ; les autres assistants l'ignoreraient. Les recommandations ci-dessous en tiennent compte.

## Posture de personnalisation

- **Pas de `customize.toml`**, donc ni bloc `[agent]` de métadonnées ni surface de surcharge.
- La personnalisation réelle passe aujourd'hui par **l'édition directe du code** : l'étape 3 du guide d'installation demande de modifier à la main un CSV, deux JSON et **cinq scripts Python** (`SITES` dans `etat_barometre.py` et `generer_schema.py`, `SERVICES` dans `fusion_scripts.py`, `generer_suivi.py`, `import_esm.py`), plus le tri des lignes propres aux anciens sites dans `ANALYSE_SOURCES` de `lecture_critique.py`. C'est exactement le « fork pour un changement de trois lignes » que la personnalisation doit éviter.
- Surface actuelle : nulle. Surface implicite (ce qu'un nouvel utilisateur doit changer) : large et dispersée.

## Constats sur les métadonnées

| Sévérité | Constat | Suggestion |
|---|---|---|
| high-opportunity | Aucun `customize.toml` : la skill ne peut pas être référencée dans `module.yaml:agents[]` ni dans un registre central. | Seulement si le kit doit entrer dans un module BMAD : créer `customize.toml` avec `[agent] code = "barometre-sites"`, `name = ""`, `title = "Baromètre qualité des sites"`, `icon` (par ex. « 📊 »), `description` (une phrase neutre), `agent_type = "stateless"`. Si le kit reste autonome et multi-assistant, ce constat tombe à low : documenter le choix dans le guide d'installation. |
| medium-opportunity | Le `description` du frontmatter de SKILL.md nomme une personne (« Mattea ») et une organisation (« Colorz ») et fige le périmètre (« 6 boutiques Shopify »). C'est la seule métadonnée de déclenchement : après l'étape 3 du guide (remplacement des sites), elle décrit encore l'ancien parc. | Rendre la description neutre (« Baromètre qualité Opquast V5 d'un parc de sites… ») et laisser le nom du commanditaire et le nombre de sites dans une donnée configurable (voir plus bas). Si un `customize.toml` est ajouté, son `title`/`description` doivent reprendre exactement ce texte pour éviter la dérive. |

## Opportunités

### 1. Parc de sites défini à six endroits (high-opportunity)

La liste des sites est dupliquée : `scripts/ecrans_en_ligne.csv` plus les constantes `SITES`/`SERVICES` de cinq scripts, plus les lots codés en dur dans `references/lectures-independantes.md` (« Boutique A, Boutique B, Boutique C » puis « D, E, F »), plus les préfixes d'exemple (`Boutique_D`). Changer de parc demande sept éditions cohérentes, sans contrôle.

Suggestion : un seul fichier de parc, par exemple `referentiel/parc.json` (nom affiché, code court, code ESM, préfixe de page), lu par les cinq scripts ; `ecrans_en_ligne.csv` reste la liste des écrans. Côté skill, scalaire `sites_file = "referentiel/parc.json"` et lots de lectures calculés (« le parc découpé en lots de trois ») au lieu d'être nommés. C'est d'abord un chantier de code, mais c'est la variance numéro un du kit.

### 2. Commanditaire et circuit de validation codés en dur (medium-opportunity)

« Mattea » apparaît comme celle qui autorise les robots payants ESM, se connecte à ESM, arbitre les écarts (« à arbitrer par Mattea »), reçoit les CSV et le compte rendu ; 33 occurrences du nom dans les scripts (libellés générés). Toute autre organisation doit réécrire ces passages.

Suggestion : scalaire `approver_name = "la commanditaire"` (ou `client_contact`), référencé dans SKILL.md par `{agent.approver_name}` et lu par les scripts depuis le fichier de parc. Le libellé « à arbitrer par … » devient générique.

### 3. Chemins de références et de sorties codés en dur (medium-opportunity)

- `references/lectures-independantes.md` est chargé en dur : c'est le brief des sous-agents, que d'autres équipes voudront adapter (autres règles par lecture, autres seuils de citation). Suggestion : `independent_readings_template = "references/lectures-independantes.md"`.
- Cible de publication : SKILL.md impose l'Artifact et lit l'adresse dans `liens-locaux.json`, entrée « Suivi du baromètre ». Le guide multi-assistant montre déjà que la cible varie (navigateur, hébergement privé). Suggestion : `report_output_path = "suivi-barometre.html"` et `publish_link_entry = "Suivi du baromètre"` ; la mécanique Artifact reste la valeur par défaut, pas un booléen.
- Dossier `--hors` : laissé à chaque appel ; un scalaire `outside_repo_dir` avec une valeur par défaut éviterait le « dossier temporaire vidé entre deux sessions » signalé dans les règles.

### 4. Pas de `persistent_facts` (medium-opportunity)

Aucun chargement de contexte projet. Ajouter `persistent_facts = ["file:{project-root}/**/project-context.md"]` permettrait à une organisation d'apporter son contexte (parc, contraintes contractuelles, contacts) sans toucher SKILL.md. On peut y ajouter `note_cadrage.md`, que la publication met déjà à jour.

### 5. Points d'accroche naturels (medium-opportunity)

- **Avant activation** : la vérification `scripts/verifier_installation.py` est déjà une étape préalable conditionnelle (« avant le premier passage, et à chaque code 3 »). Elle se prête à `activation_steps_prepend`, où une organisation pourrait aussi ajouter ses propres contrôles (VPN, droit d'audit des sites).
- **Après la publication** : les étapes 4 (report dans eServices Manager) et 5 (note de cadrage A4) sont propres à cette mission ; le guide reconnaît déjà le cas « sans eServices Manager ». Les sortir dans `activation_steps_append` (ou une liste `publish_steps`) les rendrait remplaçables sans forker la section Publication.

Rester à deux accroches au plus (voir abus 7).

### 6. Paramètres de méthode variables d'une organisation à l'autre (low-opportunity)

Seuils de note A à E (90 / … / 50), objectif de deux sources par règle, rythme de 6 à 10 s par requête, règle typographique « aucun tiret long », politique « commit et push sur le dépôt personnel après chaque étape ». Ce sont des choix plausiblement variables, mais la plupart sont aussi des garanties de méthode. Ne lever que ceux qui le sont vraiment pour un client (seuils de note, rythme de requêtes), sous forme de valeurs, pas d'interrupteurs.

## Abus

Aucune surface n'existant, il n'y a pas d'abus présent. Les risques portent sur la future surface, si l'auteur l'ouvre.

| Sévérité | Risque | Recommandation |
|---|---|---|
| high-abuse (préventif) | Transformer les règles de sécurité en options : `allow_orders`, `bypass_rate_limit`, `mask_personal_data = true`, `allow_paid_robot`. | Ne jamais exposer la section « Règles à ne jamais enfreindre » ni les règles absolues d'`AGENTS.md`. Elles font partie du contrat de la skill, pas de sa configuration. |
| high-abuse (préventif) | Ferme d'interrupteurs pour les variantes de passage : `night_mode = true`, `use_esm = true`, `publish_artifact = true`. | Ces choix existent déjà comme options de ligne de commande (`--nuit`, `--etapes`, `--service`) et comme question posée à la personne. Les garder là ; l'usage d'ESM se déduit de la présence de `referentiel/audits-esm.json` renseigné. |
| high-abuse (préventif) | Double source de vérité : déclarer `sites_file` ou `approver_name` dans `customize.toml` en laissant SKILL.md et les scripts avec les valeurs en dur. | Câbler chaque scalaire jusqu'au bout (`{agent.X}` dans SKILL.md, lecture du même fichier par les scripts), sinon la surcharge n'a aucun effet. |
| medium-abuse | Le kit vise plusieurs assistants : une configuration qui ne vivrait que dans `customize.toml` laisserait Mistral, Codex ou Gemini sur les valeurs en dur. | Mettre les valeurs dans un fichier neutre du kit (`referentiel/parc.json` ou `referentiel/config-barometre.json`), lu par les scripts et par tous les assistants ; `customize.toml` ne fait que pointer vers lui. |
| low-abuse (préventif) | Champs `name` et `title` qu'on croirait surchargeables. | Si `customize.toml` est créé, un commentaire indiquant qu'ils sont en lecture seule à l'exécution. Un commentaire d'une ligne au-dessus de chaque scalaire. |

## Adéquation à l'archétype

Pour une skill sans état, la surface est **sous-exposée** : métadonnées absentes, une référence chargée en dur, une cible de publication fixe, un commanditaire nommé, et surtout un parc de sites recopié dans sept fichiers que le guide d'installation demande de modifier à la main. C'est le cas « stateless avec seulement des valeurs en dur et une variance évidente » que la grille signale. À l'inverse, le kit a bien fait de garder les variantes de passage dans la ligne de commande et les garanties de sécurité hors de toute configuration : c'est ce qu'il faut préserver en ouvrant une surface.

## Points clés

1. **Le parc de sites est la vraie surface de personnalisation, et elle est éclatée** : sept emplacements (un CSV, cinq constantes de scripts, les lots nommés dans `lectures-independantes.md`). Un fichier de parc unique, lu par les scripts et référencé par la skill, remplace l'étape 3 manuelle du guide d'installation.
2. **La skill porte l'identité d'une mission** (« Mattea », « Colorz », « 6 boutiques Shopify » jusque dans la description de déclenchement). Neutraliser la description et lever le commanditaire en valeur `approver_name` rend le kit réutilisable sans réécriture.
3. **Ouvrir une surface petite et câblée** : métadonnées `[agent]` si intégration BMAD, `persistent_facts` par défaut, deux accroches (vérification d'installation avant, étapes ESM et note de cadrage après), et jamais d'interrupteur sur les règles de sécurité. Comme le kit est multi-assistant, les valeurs doivent vivre dans un fichier neutre du kit, `customize.toml` ne faisant que pointer vers lui.
