# Efficacité d'exécution : skill `barometre-sites`

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, 114 lignes ; references/lectures-independantes.md, 28 lignes ; INSTALLER-AVEC-UN-ASSISTANT-IA.md, 98 lignes), avec le code qu'elle pilote (`scripts/barometre.py`, scripts de mesure, `lecture_critique.py`).

Pré-passe (`execution-deps-prepass.json`) : aucun motif séquentiel, aucune boucle, aucun cycle, aucune chaîne de sous-agents signalés (0 problème). Ce résultat est cohérent : la skill délègue presque tout l'enchaînement à un script Python, et la pré-passe ne voit pas ce qui se passe dans ce script. Les constats ci-dessous viennent de la lecture directe des fichiers.

Type d'agent : skill sans mémoire (pas de sanctum, pas de fichiers de mémoire). Les vérifications propres aux agents à mémoire ne s'appliquent pas.

## Évaluation

La skill est efficace dans l'ensemble. Le travail déterministe et long est confié à un seul script (`barometre.py`). Il tourne la nuit ou en arrière-plan, et le contexte de l'agent ne contient jamais les données brutes. Les lectures IA sont déléguées à des sous-agents en arrière-plan qui écrivent dans des fichiers et ne renvoient qu'un bilan court. Le parent ne lit jamais les sources lui-même.

Quatre points de friction restent :
- la lecture n°3 dépend d'une synthèse préalable, et ce n'est pas dit dans le déroulé ;
- les mêmes protocoles `get_rule` sont rechargés dans chaque sous-agent ;
- le parent risque de lire en entier un journal de plusieurs heures ;
- la durée totale (plusieurs heures) vient surtout du traitement d'un site après l'autre.

Il n'y a aucun problème critique.

## Constats

### 1. Dépendance cachée : la lecture n°3 a besoin d'une synthèse préalable (moyen)

- **Où** : SKILL.md:76-78 ; references/lectures-independantes.md:23 et 28.
- **Ce qui est écrit** : SKILL.md place les trois lectures « entre `sources` et `synthese` », comme si elles étaient indépendantes. Or la lecture DOM (n°3) porte sur « celles qui restent à une seule source après l'étape `synthese` ». Elle exige donc une synthèse **avant** elle. Si l'agent suit SKILL.md à la lettre, deux issues sont possibles :
  - il lance les 6 sous-agents d'un coup, sans liste pour la lecture n°3 ;
  - il découvre la dépendance en cours de route et refait une partie du travail.
- **Ordre efficace**, à écrire explicitement :
  1. Dans un même message : lancer les 4 sous-agents des lectures 1 et 2 (2 lots × 2 lectures, en arrière-plan) **et** `barometre.py --etapes synthese`, qui prend quelques secondes.
  2. Construire la liste des règles à une seule source par site, puis lancer les 2 sous-agents de la lecture 3 dès que la synthèse est finie, sans attendre les lectures 1 et 2.
  3. Lancer la synthèse finale quand les 6 sous-agents ont rendu leur résultat.
- **Gain estimé** : on évite qu'un lot de la lecture 3 soit lancé sans liste puis relancé (2 sous-agents perdus, soit plusieurs dizaines de milliers de jetons). Le temps d'attente des lectures 1-2 et 3 se superpose.

### 2. Le parent construit à la main la liste des règles à une seule source (moyen)

- **Où** : references/lectures-independantes.md:23 (« les lister par site dans un fichier JSON passé au sous-agent »).
- **Ce qui se passe** : aucun script ne produit cette liste. `lecture_critique.py` et `generer_suivi.py` calculent « une seule source » (generer_suivi.py:790, 1483) mais ne l'exportent pas. Le parent doit donc ouvrir `lecture.json` ou le suivi HTML, gros fichiers qui couvrent 204 règles × 6 sites, pour en tirer la liste. Il charge ainsi dans son contexte des résultats qu'il n'a pas besoin de voir.
- **Alternative** : faire écrire par `lecture_critique.py` (ou un petit script dédié) un fichier `<hors>/une-seule-source.json` du type `{"Site": [règles]}`. Une seule commande, puis le chemin est passé au sous-agent. Le fichier va dans `<hors>` et non dans `resultats/`, ce qui préserve la règle d'indépendance des sous-agents (« ne jamais lire `resultats/` »).
- **Gain estimé** : 10 à 40 k jetons de contexte parent, et la liste devient reproductible au lieu d'être faite à la main.

### 3. Les mêmes protocoles `get_rule` sont rechargés dans chaque sous-agent (moyen)

- **Où** : references/lectures-independantes.md:8, 15, 19.
- **Ce qui se passe** : chaque sous-agent doit appeler `get_rule` pour chacune de ses règles.
  - Lecture 1 : 41 règles. Lecture 2 : 30 règles. Les deux listes ont 8 règles en commun (2, 7, 8, 22, 40, 56, 99, 100).
  - Chaque lecture tourne en 2 lots qui ont exactement la même liste de règles.
  - Résultat : environ 142 appels `get_rule` pour les lectures 1 et 2, contre 63 protocoles distincts. Il faut ajouter la lecture 3.
  - En format `detailed`, un protocole fait environ 0,5 à 1,5 k jetons : 70 à 210 k jetons, dont plus de la moitié en double.
- **Alternative** : le parent fait une seule passe `get_rule` avant de lancer les sous-agents. Il écrit les protocoles dans `<hors>/protocoles/<n>.md`, idéalement avec des appels groupés dans un même message ou un script. Chaque brief dit alors : « lire le protocole dans `<hors>/protocoles/` ». Les protocoles sont le référentiel public, pas des résultats, donc l'indépendance est préservée. Autre option, garder `get_rule` mais demander de grouper tous les appels dans un seul message au début.
- **Gain estimé** : 50 à 60 % des jetons consacrés aux protocoles dans les sous-agents, et une latence plus faible (beaucoup moins d'allers-retours MCP).

### 4. Le journal de nuit risque d'être lu en entier (moyen)

- **Où** : SKILL.md:61 (« Le matin : lire le journal ») ; barometre.py:116-125.
- **Ce qui se passe** : en mode `--nuit`, toute la sortie de tous les scripts va dans `resultats/journal-barometre-<date>.log`. Pour 47 écrans, une vingtaine de scripts et plusieurs heures, ce journal peut atteindre des milliers de lignes. La consigne « lire le journal » pousse à le charger en entier dans le contexte.
- **Alternative** : préciser « lire le bilan final : `tail -n 60` du journal, plus `grep -n "ÉCHEC\|Échec\|429\|non testé"` ». Le bilan récapitulatif est déjà imprimé en fin de passage (barometre.py:171-174) et suffit pour décider d'un `--depuis`.
- **Gain estimé** : de 20 à plus de 100 k jetons évités au réveil, selon la taille du journal.

### 5. Le lancement en parallèle des sous-agents n'est pas explicite (bas)

- **Où** : SKILL.md:78 ; references/lectures-independantes.md:3.
- **Ce qui est écrit** : « lancées en arrière-plan » ne dit pas « dans un seul message ». Un agent peut les lancer une par une et attendre entre chaque.
- **Alternative** : ajouter « lancer les sous-agents d'une même vague dans un seul message (plusieurs appels Agent) » (voir constat 1 pour les vagues).
- **Gain estimé** : de la latence de démarrage. Faible, puisqu'ils tournent en arrière-plan.

### 6. Format de sortie précisé seulement pour la lecture 1 (bas)

- **Où** : references/lectures-independantes.md:15 (format JSON donné), 17-26 (lectures 2 et 3 : nom de fichier et forme de la preuve, mais pas de structure JSON).
- **Ce qui se passe** : `lecture_critique.py:282-293` lit les trois familles de fichiers avec la même structure `{"Site": {"règle": [...]}}`. Le sous-agent de la lecture 2 ou 3 doit deviner qu'il faut reprendre le format de la lecture 1, alors que la section « Consignes communes » est la seule copiée dans chaque brief.
- **Alternative** : mettre le schéma JSON dans les « Consignes communes ». Ajouter une limite de taille au bilan renvoyé, par exemple « 15 lignes au plus ». La contrainte « bilan court » est déjà bonne mais n'a pas de limite chiffrée.
- **Gain estimé** : on évite qu'un fichier soit rejeté par `verifier_citations.py` puis qu'un sous-agent soit relancé.

### 7. Publication : étapes indépendantes faites l'une après l'autre (bas)

- **Où** : SKILL.md:98-108.
- **Ce qui se passe** : plusieurs étapes ne dépendent pas les unes des autres une fois la vérification des données personnelles passée (étape 1) :
  - publier l'Artifact (2) ;
  - envoyer les 3 CSV avec SendUserFile (3) ;
  - lancer `verifier_page_a4.py` (5).
  La numérotation pousse à les faire une par une.
- **Alternative** : préciser qu'après l'étape 1, on peut regrouper les étapes 2, 3 et la vérification A4 dans un même message. L'étape ESM (4) reste à part puisqu'elle attend Mattea.
- **Gain estimé** : 2 à 3 allers-retours.

## Pistes d'optimisation plus larges

### A. Traiter les sites en parallèle dans les scripts réseau (impact fort sur la durée, à arbitrer)

- **Ce qui se passe** : `barometre.py` lance une vingtaine de scripts l'un après l'autre (barometre.py:158-170). Chaque script parcourt les 6 sites l'un après l'autre (« un seul site à la fois », controles_reseau.py:19), avec 6 à 15 s d'attente entre deux requêtes. Le délai est compté **par hôte** (`Client._attendre`, controles_reseau.py:95-99), mais comme un seul hôte est visité à la fois, les attentes s'additionnent au lieu de se chevaucher. C'est la cause principale du « plusieurs heures ».
- **Option** : entrelacer les sites (tourniquet entre hôtes) ou lancer 2 à 3 sites en même temps. Le délai par hôte reste inchangé, donc la politesse envers chaque boutique est respectée.
- **Gain** : jusqu'à environ 6 fois moins de temps sur les étapes `mesure`, `releve` et `sources`.
- **Réserves** :
  1. Les 6 boutiques sont sur Shopify. Shopify peut limiter le débit par adresse IP sur l'ensemble des boutiques, d'où un risque de 429 accru. Commencer à 2 sites en même temps et surveiller les 429.
  2. Lancer plusieurs `barometre.py --service X` en même temps n'est **pas** sûr en l'état. La fusion des `resultats.json` par service est une suite lecture, fusion, écriture sans verrou (controles_reseau.py:485-494). Deux processus concurrents peuvent écraser le travail l'un de l'autre. Le parallélisme doit vivre dans les scripts, pas dans le lancement.
  3. C'est un choix de méthode (prudence affichée) : à décider par la responsable, pas par l'agent.

### B. Recouvrir les étapes sans réseau

Plusieurs commandes ne font aucune requête :
- `synthese_axe.py` et `controles_aria.py` (étape `mesure`) ;
- `regles_releve.py` (étape `releve`) ;
- la construction du moteur (`moteur`), indépendante de `referentiel` et de `mesure`.

Elles pourraient tourner pendant l'étape réseau suivante. Le gain est modeste (minutes sur des heures) et ne vaut la peine que si la piste A n'est pas retenue.

### C. Pré-calculer le paquet d'entrée des sous-agents

Les constats 2 et 3 se combinent bien. Une étape `preparer_lectures` (script) écrirait dans `<hors>/lectures/` :
- les protocoles des règles ;
- la liste des règles à une seule source par site ;
- la liste des fichiers d'entrée par lot.

Le parent n'aurait plus qu'à lancer 6 sous-agents avec 6 briefs presque identiques, sans rien lire lui-même. Impact : un contexte parent minimal, des sous-agents plus courts, et une meilleure reproductibilité d'un passage à l'autre.

## Ce qui est déjà efficace (à garder)

- **Le travail lourd est délégué à un script** : `barometre.py` enchaîne les 6 étapes, avec reprise (`--depuis`), essai à blanc (`--essai`), un site seul (`--service`) et poursuite après échec (`--continuer`). L'agent ne pilote pas 25 commandes une par une et ne voit pas les données brutes.
- **Le parent ne lit pas les sources** : textes légaux, captures et DOM ne sont lus que par les sous-agents. SKILL.md n'invite jamais le parent à les ouvrir.
- **L'agrégation se fait par fichiers** : chaque sous-agent écrit un JSON dans `resultats/sources-<date>/` et ne renvoie qu'un « bilan court ». C'est le bon choix vu le volume (plus de 40 règles × 3 sites par lot).
- **Les sous-agents tournent en arrière-plan** sur une tâche longue qui n'a pas besoin de dialogue. Il n'y a pas de chaîne de sous-agents (aucun sous-agent n'en lance un autre).
- **La découpe en lots de 3 sites** limite le volume d'images par sous-agent tout en gardant peu d'agents (6 par vague).
- **Les ressources sont chargées à la demande** : `references/lectures-independantes.md` n'est lu qu'au moment des lectures. `INSTALLER-AVEC-UN-ASSISTANT-IA.md` ne sert qu'aux autres assistants. SKILL.md reste court (114 lignes).
- **Des réutilisations évitent du travail** : le dernier export ESM basics est repris tant qu'aucun nouvel audit n'est lancé. Le moteur Opquast n'est construit que s'il manque (barometre.py:54).
- **Les prérequis sont vérifiés avant de commencer** : `barometre.py` lance `verifier_installation.py` avant les étapes réseau et s'arrête avec le code 3. On ne perd pas des heures sur un outil manquant.
- **`get_rule` n'est appelé qu'au cas par cas** quand on tranche un écart (SKILL.md:85), et seulement pour les écarts réels.
