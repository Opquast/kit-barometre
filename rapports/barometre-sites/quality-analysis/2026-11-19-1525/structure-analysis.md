# Analyse structure et capacités : skill `barometre-sites`

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, `references/lectures-independantes.md`, `INSTALLER-AVEC-UN-ASSISTANT-IA.md`), avec le code du kit (`scripts/`, `referentiel/`, `package.json`, `requirements.txt`, `AGENTS.md`).
Date : 19/11/2026. Pré-passe : `structure-capabilities-prepass.json` (11 constats : 0 critique, 7 élevés, 4 moyens). `is_memory_agent` : false.

## Verdict

La skill est structurellement saine **en tant que skill de workflow** : frontmatter valide, déroulé clair en six étapes adossé à un orchestrateur réel (`scripts/barometre.py`), garde-fous forts et explicites, et toutes les références vers des scripts du kit sont résolues. Ce n'est pas un agent BMAD à persona : les sections Overview / Identity / Communication Style / Principles / On Activation signalées manquantes par la pré-passe le sont par conception, et leurs fonctions sont tenues par d'autres sections (l'introduction tient lieu d'Overview, « Règles à ne jamais enfreindre » de Principles, « Prérequis » et « Déroulé » d'On Activation). Les vrais problèmes sont ailleurs : la skill n'est **pas encore désanonymisée pour un kit distribué** (Mattea, Colorz, adresse d'Artifact et chiffres datés en dur), et il y a **une incohérence d'ordre** entre la lecture DOM et l'étape `synthese`.

## Sections trouvées

| Section (SKILL.md) | Ligne | Rôle structurel |
|---|---|---|
| Frontmatter (`name`, `description`) | 1-4 | valide, kebab-case |
| Introduction (objectif, périmètre) | 6-10 | tient lieu d'Overview |
| Règles à ne jamais enfreindre | 12 | tient lieu de Principles / limites d'accès |
| Prérequis et installation | 22 | première étape d'activation (vérification avant tout) |
| Déroulé | 46 | séquence d'exécution, tableau des étapes |
| Trancher les écarts | 81 | cadre de décision (quatre questions ordonnées) |
| Publication | 98 | livrables et clôture |
| Fichiers utiles | 110 | index des fichiers |

Absentes au sens BMAD : Overview, Identity, Communication Style, Principles, On Activation (voir pré-passe). Aucune section invalide (On Exit, Exiting). Aucun artefact de gabarit (`{if-*}`, `{displayName}`).

## Inventaire des capacités

Il n'y a pas de table de routage au sens agent ; les « capacités » sont les étapes et les fichiers référencés. Vérification d'existence faite sur le kit.

| Capacité | Routage | Cible existe | Remarques |
|---|---|---|---|
| Vérifier / installer les prérequis | `scripts/verifier_installation.py` (`--hors`, `--installer`) | oui | options confirmées ; code retour 3 de `barometre.py` confirmé (l. 153-156) |
| Passage automatique (referentiel, moteur, mesure, releve, sources, synthese) | `scripts/barometre.py` | oui | `ORDRE` correspond au tableau ; options `--etapes`, `--depuis`, `--service`, `--essai`, `--continuer`, `--nuit` confirmées ; `--forcer` existe mais n'est pas documentée dans SKILL.md |
| Lectures IA indépendantes (3 lectures × 2 lots) | `references/lectures-independantes.md` | oui | fichiers de sortie `lecture_ia_lot*`, `lecture_visuelle_lot*`, `lecture_dom_lot*` bien lus par `lecture_critique.py` (l. 282-293) ; voir constat ordre DOM / synthese |
| Vérification des citations | `verifier_citations.py` (via `synthese`) | oui | |
| Trancher les écarts | `scripts/lecture_critique.py` (`ANALYSE_SOURCES`, `poser`) | oui | `ANALYSE_SOURCES` l. 150, `poser` l. 382 |
| Ajouter une source à la matrice | `ABR` de `scripts/generer_suivi.py` | oui | l. 1443 |
| Export CSV | `scripts/exporter_csv.py` | oui | |
| Recommandations / exemples | `referentiel/recommandations.csv`, `referentiel/exemples.json` | oui | |
| Robot ESM basics | `resultats/esm-basics-*`, `referentiel/audits-esm.json` | partiel | `audits-esm.json` présent ; `resultats/` absent du kit (normal pour un kit neuf) |
| Note de cadrage | `note_cadrage.md` + `scripts/verifier_page_a4.py` | **non** pour `note_cadrage.md` | référence orpheline dans le kit |
| Publication de la page | outil Artifact, URL en dur | n/a | URL propre au projet d'origine |
| Installation multi-assistants | `INSTALLER-AVEC-UN-ASSISTANT-IA.md`, `AGENTS.md` | oui | cohérents entre eux |

## Constats de la pré-passe (conservés tels quels)

| Fichier:ligne | Sévérité | Catégorie | Constat |
|---|---|---|---|
| SKILL.md:1 | medium | frontmatter | Name "barometre-sites" should contain "agent" |
| SKILL.md:1 | medium | frontmatter | Description missing "Use when..." trigger phrase |
| SKILL.md:1 | high | sections | Missing ## Overview section |
| SKILL.md:1 | high | sections | Missing ## Identity section |
| SKILL.md:1 | high | sections | Missing ## Communication Style section |
| SKILL.md:1 | high | sections | Missing ## Principles section |
| SKILL.md:1 | high | sections | Missing ## On Activation section |
| INSTALLER-AVEC-UN-ASSISTANT-IA.md:1 | medium | config-header | No config header with language variables found |
| INSTALLER-AVEC-UN-ASSISTANT-IA.md:99 | high | progression | No progression condition keywords found |
| lectures-independantes.md:1 | medium | config-header | No config header with language variables found |
| lectures-independantes.md:29 | high | progression | No progression condition keywords found |

Lecture : ces constats supposent un agent BMAD à persona. Pour une skill de workflow, « agent » dans le nom et les cinq sections de persona ne sont pas attendus ; la clause de déclenchement existe en français (« Utiliser dès qu'on parle de… ») ; les deux fichiers signalés pour « config header » et « progression » sont un brief de sous-agents et un guide d'installation, pas des prompts de capacité. À décider au niveau du rapport final : soit accepter ces écarts comme hors cible, soit ajouter une courte section « Vue d'ensemble » et « Au démarrage » explicites (voir constat 7).

## Constats de jugement

### 1. Élevé : skill non désanonymisée pour un kit distribué
- **SKILL.md:3** : la description nomme « Mattea », « Colorz », « 6 boutiques Shopify ».
- **SKILL.md:19, 79, 88, 105, 106, 108** : Mattea est la personne qui donne son accord, arbitre et reçoit les CSV.
- **SKILL.md:104** : adresse d'Artifact en dur (`https://claude.ai/artifact/12y1tK8TKX8uMtbi92d1Q8`), propre au compte d'origine ; chez une autre personne, la publication sur cette adresse échouera ou visera un artifact d'autrui.
- **SKILL.md:8** : « 92 % atteints le 13/11/2026 » : chiffre daté d'un passage précis.
- Incohérence avec **INSTALLER-AVEC-UN-ASSISTANT-IA.md:41-49**, qui annonce un code anonymisé (« Boutique A » à « F ») et liste les fichiers à adapter, sans mentionner SKILL.md (nom de la personne, URL de l'Artifact, description).
- **Correctif** : remplacer Mattea par « la personne responsable du baromètre » (ou une variable lue d'un fichier de configuration), retirer Colorz et le chiffre daté, remplacer l'URL par « l'adresse du suivi existant s'il y en a un, sinon une nouvelle publication », et ajouter SKILL.md au tableau d'adaptation de l'étape 3 d'INSTALLER.

### 2. Élevé : ordre incohérent entre la lecture DOM et l'étape `synthese`
- **SKILL.md:76-78** : les lectures indépendantes se font « entre `sources` et `synthese` ».
- **lectures-independantes.md:23** : la lecture DOM porte sur « celles qui restent à une seule source **après l'étape `synthese`** ».
- Il faut donc une première `synthese` avant la lecture DOM, puis une seconde (l. 28). SKILL.md ne le dit pas ; un agent qui suit SKILL.md à la lettre lancera la lecture DOM sans liste de règles.
- De plus, aucun script ni commande n'est indiqué pour produire « le fichier JSON » des règles à une seule source passé au sous-agent.
- **Correctif** : dans le Déroulé, écrire la séquence explicite : `sources` → lectures 1 et 2 → `synthese` → extraire les règles à une seule source (commande ou script nommé) → lecture 3 → `synthese` à nouveau → trancher.

### 3. Moyen : vérification des données personnelles liée à la date du jour
- **SKILL.md:102** : `grep … resultats/*-$(date +%F) …`. Un passage de nuit commencé avant minuit écrit des dossiers datés de la veille ; la vérification du matin ne les voit pas et ne renvoie rien, ce qui ressemble à un succès. Sous zsh, un motif sans correspondance provoque aussi une erreur « no matches found ».
- **Correctif** : cibler les dossiers du dernier passage (date lue dans le journal ou dans `resultats/barometre-*` le plus récent), ou passer la date en paramètre, et échouer explicitement si aucun dossier ne correspond.

### 4. Moyen : référence orpheline `note_cadrage.md`
- **SKILL.md:107** : « mettre à jour les chiffres (`note_cadrage.md` …) ». Le fichier n'existe pas dans le kit (seul `scripts/verifier_page_a4.py` existe).
- **Correctif** : fournir un modèle de note dans le kit, ou rendre l'étape conditionnelle (« si le projet a une note de cadrage »).

### 5. Moyen : règle « seul clic autorisé » contredite par la règle panier
- **SKILL.md:14** admet l'ajout au panier et l'affichage du paiement ; **SKILL.md:16** dit que le seul clic autorisé est le refus des cookies. Même tension dans INSTALLER:14.
- **Correctif** : « Seuls clics autorisés : refuser les cookies, et (pour les scripts du relevé) ajouter un article au panier et ouvrir la page de paiement sans rien saisir. »

### 6. Moyen : description très longue et déclenchement large
- **SKILL.md:3** : environ 900 caractères, dont une énumération d'outils qui n'aide pas au déclenchement. La clause « même sans dire skill » et « les scores Opquast des boutiques » rendent le déclenchement organique ; c'est cohérent avec l'usage, mais risque de collision avec d'autres skills Opquast (audit d'une page, MCP Opquast).
- **Correctif** : format deux temps : « Relance et publie le baromètre Opquast V5 d'un parc de sites. Utiliser pour relancer, rejouer ou mettre à jour le baromètre des sites, son CSV ou son rapport, ou /barometre-sites. » Déplacer la liste d'outils dans le corps. Accessoirement, la description contient un tiret long « — », que la skill bannit de ses livrables (l. 20) : sans gravité, mais incohérent.

### 7. Faible : pas d'ordre de démarrage explicite
- Le démarrage est implicite (Prérequis puis Déroulé). Il manque une phrase « Au démarrage » : vérifier l'installation, vérifier le connecteur MCP Opquast (l. 42-44), demander nuit ou maintenant, et, au matin, lire le journal. Cela répondrait aussi aux constats de pré-passe sur On Activation.
- Aucune solution de repli n'est donnée dans SKILL.md si le MCP Opquast est absent, alors qu'INSTALLER:71 en donne une (page publique de la règle). Ajouter un renvoi.

### 8. Faible : détails d'exactitude
- **SKILL.md:28** dit « versions épinglées dans `package.json` » : plusieurs dépendances sont en `^` (lighthouse, pa11y, linkinator…) ; c'est le fichier de verrouillage qui épingle. `@themarkup/blacklight-collector` et `doiuse-email` sont dans `package.json` sans être cités dans la liste.
- **SKILL.md:65** : `--forcer` (lancer `--nuit` sur batterie) existe dans `barometre.py:138` sans être documentée.
- **SKILL.md:20** : « Commit et push après chaque étape » suppose un dépôt Git personnel que le kit ne crée pas ; INSTALLER ne le mentionne pas.
- **lectures-independantes.md:15** : liste de règles non triée (« … 208, 2, 17, 40 »), source facile d'oubli à la relecture.

## Points forts (à préserver)

- Garde-fous clairs, concrets et répétés de façon cohérente dans SKILL.md, INSTALLER et AGENTS.md : lecture seule sur sites en production, aucun contournement d'anti-robot, consentement explicite avant toute installation, aucun mot de passe saisi, aucun robot payant sans accord.
- Cadre de décision « Trancher les écarts » réellement directeur : quatre questions dans un ordre fixe, « on ne fait jamais voter les outils », décisions écrites et contrôle de complétude par une commande.
- Indépendance des lectures IA bien conçue (interdiction de lire `resultats/`, preuve vérifiée mot pour mot), avec une vraie raison donnée.
- Toutes les références vers les scripts, options et constantes (`ORDRE`, `ANALYSE_SOURCES`, `poser`, `ABR`, `SITES`/`SERVICES`) sont résolues dans le code.
- Portabilité pensée : INSTALLER donne l'équivalent hors Claude de chaque outil propre à Claude (Agent, MCP, Artifact, SendUserFile, AskUserQuestion), et `AGENTS.md` renvoie correctement vers les deux fichiers.
- Pas de sur-spécification : le contenu est du savoir métier (protocole Opquast, périmètre, sorties), pas des consignes sur ce que le modèle sait déjà faire.

## Mémoire et mode sans surveillance

- **Mémoire** : aucune mémoire d'agent (pas de sanctum, pas de chemins de mémoire ; pré-passe : `memory_paths` vide). L'état persiste dans les fichiers du projet (`resultats/`, `ANALYSE_SOURCES`, Git), ce qui convient à ce workflow. Rien à corriger.
- **Sans surveillance** : pas de mode headless d'agent déclaré. Le passage `--nuit` en tient lieu côté scripts (secteur vérifié, veille bloquée, journal daté, reprise par `--depuis`), et il est bien documenté. Les étapes qui demandent une personne (lectures IA, ESM, publication) sont explicitement exclues du passage automatique, ce qui est cohérent. Les sous-agents de lecture tournent en arrière-plan et doivent accéder au MCP Opquast : prévoir le repli décrit au constat 7 s'il n'est pas connecté.
