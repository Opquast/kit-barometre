# BMad Method · Analyse qualité : barometre-sites

**📊 Baromètre qualité des sites** : skill de workflow, mesure répétable de la conformité Opquast V5 d'un parc de sites
**Analysé le :** 2026-11-19T11:25:00Z | **Chemin :** /Users/mickaelh/Documents/Opquast/Test Formation/kit-barometre-sites/code/.claude/skills/barometre-sites
**Rapport interactif :** quality-report.html

## Portrait

Le Baromètre qualité des sites est un opérateur de mesure prudent et méthodique : il relance des heures de contrôles sur des boutiques en production sans jamais rien commander, saisir ni contourner, et exige au moins deux sources indépendantes par règle. Son cœur est un protocole d'arbitrage en quatre questions où l'on « ne fait jamais voter les outils » et où l'humain tranche ce qui reste ambigu. Né comme carnet de bord d'un parc précis, il est désormais le moteur d'un kit pédagogique distribué à des élèves et à d'autres assistants IA.

## Capacités

| Capacité | État | Observations |
| --- | --- | --- |
| Vérifier et installer les prérequis (`scripts/verifier_installation.py`) | Bon | 2 (faibles) |
| Passage automatique (`scripts/barometre.py`) | À revoir | 4 |
| Lectures IA indépendantes (`references/lectures-independantes.md`) | À revoir | 9 |
| Trancher les écarts (`scripts/lecture_critique.py`) | À revoir | 2 |
| Robot Opquast basics d'eServices Manager | À revoir | 3 |
| Contre-examen humain | À revoir | 1 |
| Publication (SKILL.md) | À revoir | 6 |
| Installation multi-assistants (`INSTALLER-AVEC-UN-ASSISTANT-IA.md`) | À revoir | 4 |

## Évaluation

**Good (bon)** : une skill de workflow remarquablement bien pensée, avec des garde-fous de production exemplaires, un orchestrateur Python fidèle à la documentation et un protocole d'arbitrage qui donne au modèle un vrai cadre de jugement. Sa principale faiblesse est d'être restée écrite pour une personne et un parc précis alors qu'elle est distribuée dans un kit, et de laisser au modèle, aux jointures entre étapes, des contrôles et des calculs déterministes qui devraient être des scripts.

Note sur la pré-passe : les sept constats « élevés » sur les sections Overview, Identity, Communication Style, Principles et On Activation supposent un agent à persona. Pour cette skill de workflow, ils sont hors cible : leurs fonctions sont tenues par l'introduction, les règles, les prérequis et le déroulé.

## Ce qui est cassé

1. **Le contrôle des données personnelles peut réussir sans rien avoir examiné** (SKILL.md:101, prompt-craft). Le `grep` vise `resultats/*-$(date +%F)` : après un passage de nuit, aucun dossier ne correspond, la sortie standard reste vide, exactement comme le succès attendu. C'est le seul garde-fou avant commit et push. Correctif : `scripts/verifier_publication.py`, qui cible le dernier passage et échoue explicitement.
2. **Publication sur une URL d'Artifact du compte d'origine** (SKILL.md:104, structure). Chez toute autre personne, publication refusée ou visant le suivi d'autrui. Correctif : adresse lue dans une configuration, nouvelle page si vide.
3. **La lecture DOM est placée avant la synthèse dont elle dépend** (lectures-independantes.md:23, structure). SKILL.md place les trois lectures avant `synthese`, mais la lecture 3 porte sur les règles restées à une seule source après `synthese`.
4. **Synthèse vraisemblablement bloquée sans export ESM** (`scripts/etat_barometre.py`, enhancement). `etat_barometre.py` et `fiche_contre_examen.py` supposent des dossiers `esm-*` ; ESM est pourtant présenté comme facultatif.

## Opportunités

### 1. Une skill écrite pour une personne et un parc, distribuée comme un kit (élevée, 12 observations)

SKILL.md parle à Mattea, cite Colorz, une URL d'Artifact fixe, un dépôt personnel, une note de cadrage absente du kit et des chiffres datés, alors que le guide d'installation s'adresse à n'importe quelle élève. Les étapes de publication 2, 4, 5 et 6 sont impossibles ou fausses hors du parc d'origine.

**Correctif :** séparer la méthode (à figer) de la configuration du parc : un fichier de profil (personne responsable, URL de suivi ou vide, ESM, Git, note de cadrage), Publication conditionnelle, description générique en deux temps, chiffres datés retirés du prompt.

- SKILL.md:3 : Mattea, Colorz, « 6 boutiques Shopify » dans la description (structure)
- SKILL.md:104 : valeurs d'installation codées en dur (prompt-craft)
- Identité double, outil interne et kit pour élèves (agent-cohesion) ; deux publics, un seul texte (enhancement)
- SKILL.md:88 et 104 : commanditaire et URL à lever en paramètres ; étapes ESM présentées comme obligatoires (customization-surface)
- SKILL.md:107 : `note_cadrage.md` orphelin (structure)
- SKILL.md:8 : chiffres figés et déjà faux : 92 %, 47 écrans, 41 écartées contre 42 (script-opportunities)
- SKILL.md:20 : commit et push sans dépôt Git (agent-cohesion)
- SKILL.md:3 : description d'environ 900 caractères, tiret long compris (prompt-craft)
- INSTALLER:41 : SKILL.md absent du tableau d'adaptation (structure)

### 2. Les lectures indépendantes : ordre non dit et entrées préparées à la main (élevée, 12 observations)

La lecture DOM dépend d'une première synthèse et d'une liste de règles à une seule source qu'aucun script ne produit. Briefs, protocoles `get_rule` et validation des sorties sont laissés au modèle ; une sortie mal formée est ignorée en silence par `lecture_critique.py` (`.get(nom, {})`).

**Correctif :** une étape scriptée `preparer_lectures` qui écrit dans `<hors>/lectures/` les protocoles, les règles à une seule source par lot et les six briefs complets (schéma de sortie compris), puis `valider_lectures.py` en tête de synthèse ; un Déroulé avec des vagues parallèles explicites.

- SKILL.md:76 : ordre incohérent (structure, execution-efficiency)
- lectures-independantes.md:23 : liste des règles à une seule source faite à la main (prompt-craft, execution-efficiency, agent-cohesion, script-opportunities)
- lectures-independantes.md:17 : format de sortie donné pour une seule lecture (prompt-craft)
- lectures-independantes.md:9 : aucune validation de schéma, rien pour `lecture_visuelle` (script-opportunities)
- SKILL.md:78 : « retrouvée mot pour mot » faux pour la lecture visuelle (prompt-craft)
- lectures-independantes.md:8 : environ 142 appels `get_rule` pour 63 protocoles (execution-efficiency)
- Briefs assemblés à la main (script-opportunities) ; lots figés pour six sites (enhancement)

### 3. Des garde-fous déterministes écrits en ligne de commande dans le prompt (élevée, 6 observations)

Les deux conditions de passage majeures (aucune donnée personnelle, aucun écart sans décision) sont des commandes copiées du prompt et interprétées par le modèle : l'une peut réussir sans rien examiner, l'autre dépend de la structure interne de `lecture.json`.

**Correctif :** `verifier_publication.py` (données personnelles du dernier passage, tiret long, fichiers hors dépôt suivis par Git) et `lecture_critique.py --verifier` (écarts sans décision, sources absentes d'`ABR`), lancés par `synthese` ; le prompt dit seulement « doit finir avec le code 0 ».

- SKILL.md:101-102 : contrôle lié à la date du jour, faux succès silencieux (structure, prompt-craft)
- SKILL.md:100 : rien ne vérifie l'absence de textes, DOM et captures dans Git (script-opportunities)
- SKILL.md:92 : one-liner Python de 300 caractères (prompt-craft, script-opportunities)
- SKILL.md:96 : un oubli d'`ABR` gonfle la part à deux sources (script-opportunities)

### 4. Le matin, moment critique et le moins outillé (élevée, 11 observations)

Après la nuit, la personne revient dans une session neuve : journal volumineux, aucun état de reprise, et peut-être ni ESM, ni MCP Opquast, ni Shopify. Pas de tri d'intention : une simple question de score peut lancer des heures de mesure. Le contre-examen humain, compté comme source, n'est décrit nulle part.

**Correctif :** une section « Au démarrage et reprise » : trier l'intention (relancer tout, un site, consulter, adapter, comprendre un écart), lire un bilan JSON écrit par `barometre.py` plutôt que le journal, vérifier l'état des lectures et des écarts, documenter les replis et le contre-examen.

- SKILL.md:61 : journal lu en entier, 20 à plus de 100 k jetons (execution-efficiency, script-opportunities)
- SKILL.md:61 : pas de point de reprise (enhancement)
- ESM requis implicitement, synthèse sans historique (agent-cohesion, enhancement)
- SKILL.md:85 et lectures-independantes.md:8 : pas de repli sans MCP Opquast (structure, enhancement)
- SKILL.md:76 : contre-examen humain, source fantôme (agent-cohesion)
- SKILL.md:3 : tri d'intention absent (enhancement) ; sites non Shopify sans traitement (enhancement)
- SKILL.md:22 : pas d'ordre de démarrage explicite (structure)

### 5. La liste des sites dispersée dans cinq scripts (moyenne, 4 observations)

Adapter le baromètre impose d'éditer `SITES`/`SERVICES` dans cinq scripts. Dans le kit, `ecrans_en_ligne.csv` contient « Ma boutique » alors que les scripts attendent « Boutique A » à « F » : la première passe d'une élève est ignorée par la synthèse, sans message.

**Correctif :** une source unique `referentiel/sites.json` lue par les scripts (ou `configurer_sites.py`), contrôlée par `verifier_installation.py` à chaque passage.

- INSTALLER:41 (enhancement, script-opportunities, customization-surface) ; INSTALLER:39, assistant d'adaptation (agent-cohesion)

## Points forts

- **Protocole d'arbitrage en quatre questions** : ordonné, illustré (règles 124, 153), « on ne fait jamais voter les outils », issue « à arbitrer » prévue. À ne pas transformer en table de décision.
- **Garde-fous de production concrets et cohérents partout** : chaque interdit dit quoi faire à la place, et SKILL.md, l'INSTALLER, AGENTS.md et le code disent la même chose.
- **Consentement à l'installation exemplaire** : vérification sans modification, liste avec rôle et commande, accord en trois options, `npm ci --ignore-scripts`, arrêt code 3.
- **Indépendance des lectures IA réellement outillée** : interdiction de lire `resultats/`, preuves mot pour mot vérifiées par script.
- **Correspondance exacte entre la skill et le code** (`ORDRE`, `ANALYSE_SOURCES`, `poser`, `ABR`).
- **Travail lourd délégué, contexte parent préservé** : un orchestrateur avec reprise, essai à blanc, site seul et mode nuit.
- **Portabilité** : table d'équivalences entre les outils Claude et les autres assistants.
- **Attention à ce que vit l'utilisatrice** : préparation de l'ordinateur pour la nuit, secteur, veille, journal, `--depuis`.
- **Aucun remplissage** : SKILL.md court (115 lignes) et divulgation progressive saine.

## Analyse détaillée

### Structure et capacités

Structurellement saine en tant que skill de workflow : frontmatter valide, six étapes adossées à un orchestrateur réel, références de scripts toutes résolues. Constats hors thèmes : sections de persona et nom sans « agent » hors cible ; fichier INSTALLER à la racine et `../hors` signalés par le lint de chemins mais délibérés (fichier pour les autres assistants, référencé par AGENTS.md ; `../hors` est un argument d'exemple) ; règle « seul clic autorisé » contredite par la règle panier (SKILL.md:16, moyenne) ; `--forcer` non documentée, « versions épinglées » inexact, liste de règles non triée (faibles).

### Persona et voix

Pas de persona, et c'est adapté : voix de mode d'emploi impératif, concrète, sans remplissage. La justification (pourquoi deux sources, pourquoi l'indépendance) est éparpillée ; les règles de forme (tiret long, rythme de commit) sont mêlées aux règles de sécurité ; SKILL.md et l'INSTALLER divergent déjà (Windows, VPN, contre-examen, conditions d'ajout d'un outil).

### Cohésion d'identité

Alignement posture et capacités, intégration externe et granularité : forts. Cohérence d'identité, complétude, redondance et parcours : moyens, à cause de la double identité et des étapes présentes dans le code mais pas dans la skill. Hors thèmes : documentation recopiée entre SKILL.md et l'INSTALLER ; références mortes (`controles_email.py`, `checkdmarc`, `resultats/email-*`).

### Efficacité d'exécution

Aucun problème critique : script unique pour le travail long, sous-agents en arrière-plan qui écrivent dans des fichiers. Hors thèmes : traiter les sites en parallèle dans les scripts réseau (jusqu'à 6 fois plus rapide, mais risque de 429 Shopify et fusion sans verrou : à arbitrer par la responsable) ; recouvrir les étapes sans réseau ; regrouper les étapes indépendantes de publication.

### Expérience de conversation

Six parcours : la première fois (installation exemplaire puis consignes adressées à Mattea), l'experte (pas de passage ciblé rapide ni d'évolution), la personne venue par erreur (pas de tri d'intention), le cas limite (non Shopify, un seul site, site très bloqué), l'environnement hostile (sans ESM ni MCP, session fermée) et l'automate (pas de contrat de sortie). Mode sans interaction : **partiellement adaptable** ; un tel mode devrait s'arrêter après la synthèse et renvoyer un JSON court. Hors thèmes : évolution entre deux passages, démonstration sur `resultats-exemple/`, seuil de fiabilité du score, estimation de durée et glossaire.

### Opportunités de scripts

Placement de l'intelligence très bon ; les opportunités sont aux jointures. Économie estimée : **13 000 à 50 000 jetons par passage**, plus 1 000 à 3 000 à l'installation. Hors thèmes : `diff_passages.py` pour le report ESM (élevée), `bilan_passage.py` pour le compte rendu, rôle des prérequis dans `verifier_installation.py`, marqueurs dans la note de cadrage.

### Surface de personnalisation

Archétype sans état, sans `customize.toml` ni bloc `[agent]` : posture trop mince, puisque la personnalisation passe par l'édition du code et du texte de la skill. La vraie surface est le parc de sites (thème 5) ; viennent ensuite `commanditaire`, `suivi_artifact_url` et deux points d'accroche (`activation_steps_append`, `on_publish`) plutôt que des booléens. Aucun abus présent ; à prévenir : ne pas transformer les options de `barometre.py` en fermes de booléens, et ne jamais rendre surchargeables la méthode (barème, deux sources, quatre questions, rythme des requêtes) ni les règles de sécurité. Comme les autres assistants ne liront pas `customize.toml`, le fichier de configuration du kit doit rester la source principale de ce que consomment les scripts.

## Recommandations

1. Séparer la méthode de la configuration du parc (profil, `referentiel/sites.json`, Publication conditionnelle, description générique, chiffres datés retirés). Résout 16 observations, effort moyen.
2. Réécrire la séquence des lectures indépendantes et ajouter `preparer_lectures.py` et `valider_lectures.py`. Résout 12 observations, effort moyen.
3. Ajouter une section « Au démarrage et reprise » avec tri d'intention, bilan JSON, replis sans ESM, sans MCP et hors Shopify, et contre-examen. Résout 11 observations, effort moyen.
4. Remplacer les commandes en ligne par `verifier_publication.py` et `lecture_critique.py --verifier`. Résout 6 observations, effort faible.
5. Ajouter `diff_passages.py` et `bilan_passage.py` (report ESM, compte rendu, évolution). Résout 4 observations, effort moyen.
6. Faire pointer l'INSTALLER vers SKILL.md et corriger les détails d'exactitude. Résout 6 observations, effort faible.
7. Mettre les protocoles `get_rule` en cache partagé et lancer chaque vague de sous-agents dans un seul message. Résout 2 observations, effort faible.
8. Étudier, avec l'accord de la responsable, l'entrelacement des sites dans les scripts réseau. Résout 1 observation, effort élevé.
9. Si la skill rejoint un module BMAD, créer un `customize.toml` minimal en gardant la méthode et la sécurité hors surcharge. Résout 3 observations, effort faible.
