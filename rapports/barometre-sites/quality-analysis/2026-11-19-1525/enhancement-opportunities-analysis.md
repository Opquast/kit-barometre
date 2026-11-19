# Opportunités d'amélioration : skill `barometre-sites`

Scanner : DreamBot (cas limites et expérience). Analyse consultative : rien ici n'est cassé au sens de la structure, tout est une opportunité. Certaines observations touchent toutefois au code du kit, parce que l'expérience vécue par la personne en dépend.

Fichiers lus : `SKILL.md`, `references/lectures-independantes.md`, `INSTALLER-AVEC-UN-ASSISTANT-IA.md` (identique à la copie à la racine du kit), `LISEZ-MOI.md`, `AGENTS.md`, `scripts/README.md`, `scripts/barometre.py`, `scripts/ecrans_en_ligne.csv`, `referentiel/audits-esm.json`, `referentiel/exclusions-sites.json`, extraits de `etat_barometre.py`, `fusion_scripts.py`, `generer_suivi.py`, `lecture_critique.py`, `fiche_contre_examen.py`, `verifier_installation.py`.

## Compréhension de l'agent

La skill pilote un baromètre de qualité Opquast V5 sur des boutiques Shopify : installation vérifiée avec accord, passage automatique de plusieurs heures (`barometre.py`), lectures IA indépendantes par sous-agents, arbitrage des écarts selon quatre questions, puis publication (Artifact, trois CSV, ESM, note de cadrage, commit). Elle a été écrite pour **une utilisatrice précise (Mattea) et un parc précis (Boutique A à F)**, mais elle est désormais **distribuée dans un kit à des élèves de formation** qui l'utiliseront sur leurs propres sites, avec n'importe quel assistant. C'est la tension centrale de cette analyse : la skill porte deux publics, et son texte n'en sert qu'un.

Hypothèses clés : la personne est Mattea ; le parc compte six boutiques ; un historique `resultats/` existe (exports ESM, passages précédents) ; un dépôt Git personnel est configuré ; la session reste ouverte du soir au matin.

## Parcours utilisateurs

### 1. La première fois (une élève de la formation, sur son propre site)

Elle ouvre `code/`, donne `INSTALLER-AVEC-UN-ASSISTANT-IA.md` à Claude Code. L'installation est exemplaire : liste, accord, installation. Puis l'étape 3 lui demande de modifier **six fichiers Python** à la main (`SITES`, `SERVICES` dans cinq scripts) et de nettoyer `ANALYSE_SOURCES`. Or `ecrans_en_ligne.csv` contient déjà « Ma boutique » (5 écrans), alors que tous les scripts attendent « Boutique A » à « F » : sans cette édition, la synthèse ne trouve aucun site.

Ensuite la skill elle-même se déclenche et lui parle comme à Mattea : « sans l'accord de Mattea », « dire à Mattea », « à arbitrer par Mattea », publier sur l'Artifact `12y1tK8TKX8uMtbi92d1Q8` (qu'elle ne possède pas), mettre à jour `note_cadrage.md` (absent du kit), commit et push sur « le dépôt personnel » (le kit n'est pas un dépôt Git).

- Frictions : configuration dispersée dans le code ; consignes nominatives ; étapes de publication impossibles ; « 6 boutiques, 47 écrans » et « 92 % » présentés comme l'état courant.
- Points forts : règles de sécurité limpides ; installation avec consentement ; `--essai` pour un essai à blanc.

### 2. L'experte (Mattea, au cinquième passage)

Elle veut « relancer seulement la Boutique C et republier ». Les options existent (`--service`, `--etapes`), c'est bien. Mais la skill impose toujours la question « ce soir ou maintenant », la checklist de nuit, puis six étapes de publication. Rien ne lui dit ce qui a **changé depuis le dernier passage** : la page de suivi et les CSV donnent un instantané, pas une évolution.

- Frictions : pas de mode « passage ciblé rapide » documenté (un site, une étape, republier) ; pas de comparaison avec le passage précédent.
- Points forts : `--depuis` pour reprendre ; commande de contrôle des écarts sans décision.

### 3. La personne venue par erreur

« Fais-moi un audit Opquast de ce site » ou « quel est le score de la Boutique B ? ». La description très riche capte « scores Opquast des boutiques » : la skill risque de lancer un passage de plusieurs heures pour une simple question de lecture. Aucune branche « consulter le dernier résultat » (lire `scores.csv` du dernier `resultats/barometre-*` ou de `resultats-exemple/`) n'est prévue.

- Friction : pas de tri d'intention à l'entrée (relancer, consulter, expliquer une règle, adapter à un nouveau site).

### 4. Le cas limite (données valides mais inattendues)

- Un site **non Shopify** : le LISEZ-MOI prévient, mais la skill ne dit pas quelles étapes sauter (`sources_shopify.py`, `sources_panier.mjs`) ni comment interpréter les règles alors restées à une seule source.
- **Un seul site** : les lectures indépendantes sont décrites en « deux lots de trois sites » nommés ; rien pour 1, 2 ou 10 sites.
- Un site qui renvoie 429 ou un anti-robot sur la moitié des écrans : la règle « non testé » est claire, mais le score (C ÷ (C+NC)) peut devenir trompeur sur peu de règles mesurées, sans alerte.
- Un écran ajouté entre deux passages : comparabilité des scores non abordée.

### 5. L'environnement hostile

- **Sans eServices Manager** (présenté comme facultatif dans le LISEZ-MOI) : `etat_barometre.py` lit `dernier("resultats/esm-scripts-*")` et `dernier("resultats/esm-basics-*")`, et `fiche_contre_examen.py` fait `sorted(...)[-1]` sur `esm-basics-*`. Sur un kit neuf, sans dossier `resultats/`, l'étape `synthese` s'arrête vraisemblablement sur une erreur d'index. La skill n'en dit rien : impasse au moment le plus attendu (le matin, après la nuit).
- **MCP Opquast non connecté** : le guide multi-assistants donne l'équivalent (page publique de la règle), mais `SKILL.md` et `lectures-independantes.md` imposent `get_rule` sans repli. Les sous-agents bloqueraient.
- **Compaction ou session fermée** pendant la nuit : la skill dit « le matin, lire le journal », mais ne donne pas de point de reprise explicite (quelle étape est faite, lectures IA faites ou non, écarts restants). `etat_barometre.py` existe mais n'est pas présenté comme tableau de bord de reprise.
- Ordinateur passé sur batterie en cours de nuit : `--nuit` vérifie au départ seulement.

### 6. L'automate (planificateur, CI, autre agent)

`barometre.py` est déjà presque autonome : `--nuit`, journal daté, codes de sortie (2, 3, 4, code de l'étape). Mais la skill impose AskUserQuestion pour l'heure de lancement et place les lectures IA et l'arbitrage hors du script. Un agent planifié ne sait pas quoi renvoyer : aucun contrat de sortie (chemin des CSV, scores, nombre d'écarts sans décision, liste des NT).

## Évaluation du mode sans interaction

**Niveau : partiellement adaptable.**

- Peuvent se résoudre seuls : choix du moment (paramètre `moment=maintenant|nuit`), étapes automatiques, lectures IA indépendantes (sous-agents déjà autonomes), synthèse, export CSV, contrôle des données personnelles.
- Doivent rester humains : accord d'installation, arbitrages « à arbitrer par Mattea », lancement d'un robot ESM payant, connexion ESM, publication publique.
- Contrat de sortie suggéré : en mode sans interaction, s'arrêter après `synthese` et le contrôle des données personnelles, et renvoyer un JSON court : `{"date", "scores": {site: [score, note]}, "part_deux_sources", "ecarts_sans_decision": [...], "a_arbitrer": [...], "non_testes": [...], "fichiers": [barometre.csv, tests.csv, scores.csv, suivi-barometre.html]}`. Publication et ESM restent en attente d'un humain.
- Points de contrôle du drapeau : question nuit ou maintenant, installation (échouer avec le code 3 sans rien installer, déjà le cas), étape 4 de Publication.

## Constats

### Haute opportunité

**H1. Deux publics, un seul texte (affecte : toute la skill)**
Constat : la skill parle à Mattea (prénom, Artifact précis, ESM, note de cadrage, dépôt personnel) alors que le kit la distribue à des élèves. Les étapes de publication 2, 4, 5 et 6 sont impossibles ou fausses pour eux.
Suggestion : remplacer « Mattea » par « la personne responsable du baromètre » et sortir les valeurs propres au parc dans un petit fichier de configuration (par exemple `referentiel/parc.json` : nom de la personne, URL d'Artifact existante ou vide, ESM oui/non, dépôt Git oui/non, note de cadrage oui/non). La section Publication devient conditionnelle : « si une URL d'Artifact est configurée, publier dessus ; sinon publier une nouvelle page et noter son URL dans la configuration ».

**H2. Une seule source de vérité pour la liste des sites (affecte : adaptation, étape 3 du guide)**
Constat : la liste des sites est codée en dur dans cinq scripts, tandis que `ecrans_en_ligne.csv` du kit contient « Ma boutique ». La première passe d'une élève produit donc des résultats que la synthèse ignore, sans message clair.
Suggestion : faire lire les noms de sites dans `ecrans_en_ligne.csv` (code court dérivé du nom) ; à défaut, ajouter dans la skill une vérification au démarrage : « les services de `ecrans_en_ligne.csv` sont-ils ceux de `SERVICES` ? », avec un message qui nomme les fichiers à adapter.

**H3. Synthèse sans historique ni ESM (affecte : étape `synthese`, robustesse)**
Constat : `etat_barometre.py` et `fiche_contre_examen.py` supposent des exports `esm-scripts-*` et `esm-basics-*`. ESM est dit facultatif, mais son absence bloque le livrable.
Suggestion : dans la skill, une ligne « sans ESM : ... » et, côté code, un repli (source absente, colonne vide). En attendant, `verifier_installation.py` ou `--essai` pourrait annoncer « synthèse impossible sans export ESM » avant la nuit plutôt qu'au matin.

**H4. Tri d'intention à l'entrée (affecte : déclenchement)**
Constat : toute mention des scores déclenche le parcours de relance complet.
Suggestion : une courte section d'accueil : « Que veut la personne ? Relancer tout ; relancer un site ou une étape ; consulter le dernier résultat ; adapter le baromètre à de nouveaux sites ; comprendre un écart. » La consultation lit le dernier `scores.csv` (ou `resultats-exemple/` sur un kit neuf) en quelques secondes.

### Opportunité moyenne

**M1. Évolution entre deux passages (affecte : sortie, valeur perçue)**
Constat : un baromètre vaut par sa répétition, mais la sortie est un instantané. Rien ne dit « la Boutique C gagne 4 points, règles 146 et 164 corrigées, 2 régressions ».
Suggestion : comparer `scores.csv` et `barometre.csv` au passage précédent et ajouter au compte rendu final (et à la page) les gains, pertes et règles qui changent de statut. C'est le moment de plaisir du baromètre.

**M2. Point de reprise explicite (affecte : matin après la nuit, compaction)**
Constat : la reprise repose sur la lecture d'un journal. Les étapes manuelles (lectures IA, arbitrage) n'ont pas d'état.
Suggestion : une section « Reprendre un passage » : lire la fin du journal, lister les dossiers `resultats/*-<date>`, vérifier la présence des six fichiers `lecture_*_lotN.json`, lancer la commande des écarts sans décision, puis dire à la personne où l'on en est et la prochaine étape.

**M3. Lectures indépendantes pour un nombre quelconque de sites (affecte : `references/lectures-independantes.md`)**
Constat : lots figés « A, B, C » et « D, E, F ».
Suggestion : « lots de trois sites au plus, dans l'ordre de `ecrans_en_ligne.csv` ; un seul lot s'il y a trois sites ou moins », fichiers `lot1..lotN`.

**M4. Repli sans MCP Opquast (affecte : arbitrage, sous-agents)**
Constat : le repli vers `checklists.opquast.com` n'existe que dans le guide multi-assistants.
Suggestion : reprendre une ligne dans `SKILL.md` et dans les consignes communes des sous-agents : « si `get_rule` est indisponible, lire la fiche publique (slug dans `referentiel/opquast-checklist-v5.json`) ».

**M5. Sites non Shopify (affecte : déroulé, étape `sources`)**
Constat : la limite est connue, son traitement non.
Suggestion : préciser les scripts propres à Shopify, prévoir leur saut (option ou détection), et signaler au compte rendu les règles restées à une seule source pour cette raison.

**M6. Démonstration sur les résultats d'exemple (affecte : première prise en main)**
Constat : `resultats-exemple/` est un formidable support, mais la skill ne l'utilise pas.
Suggestion : proposer à la première utilisation « Voulez-vous d'abord voir à quoi ressemble un résultat ? » : présenter `scores.csv` et trois lignes de `tests.csv` où `accord_avec_la_decision = non`. L'élève comprend la méthode avant la nuit de mesure.

**M7. Garde-fou sur la fiabilité du score (affecte : compte rendu)**
Constat : un site très bloqué (429, anti-robot) peut obtenir un score sur peu de règles.
Suggestion : seuil d'alerte au compte rendu (par exemple « score indicatif » si moins de 150 règles mesurées ou plus de 10 % de NT), avec la raison.

**M8. Contre-examen humain (affecte : déroulé)**
Constat : le guide et le LISEZ-MOI citent le contre-examen humain comme cinquième famille de sources, et `contre_examen.mjs` et `fiche_contre_examen.py` existent, mais `SKILL.md` ne dit ni quand ni comment le faire.
Suggestion : une étape courte et facultative après les lectures indépendantes, ou la mention explicite qu'il est hors du passage courant.

### Faible opportunité

**F1. « Commit et push après chaque étape »** : sur un kit sans dépôt, préciser « s'il y a un dépôt Git ». Le contrôle des données personnelles reste obligatoire dans tous les cas.

**F2. Chiffres datés dans la skill** (« 92 % le 13/11/2026 », « 6 boutiques, 47 écrans », « 204 mesurées ») : les présenter comme exemple du parc d'origine, ou les faire lire dans les fichiers, pour éviter qu'ils deviennent faux.

**F3. Batterie en cours de nuit** : `--nuit` ne vérifie le secteur qu'au départ ; noter dans le journal un débranchement en cours de passage aiderait le diagnostic du matin.

**F4. Estimation de durée** : « plusieurs heures » ; une estimation à partir du nombre d'écrans (écrans × requêtes × 6 à 10 s) aiderait à choisir entre nuit et journée, surtout pour un seul site où le passage tient peut-être en une heure.

**F5. Glossaire minimal** : C, NC, NA, NT, « volet », « relevé », « hors » sont implicites. Trois lignes suffisent pour une élève.

## Principales intuitions

1. **La skill est devenue un produit sans le savoir.** Écrite comme un carnet de bord pour une personne et un parc, elle est maintenant le cœur d'un kit pédagogique. Séparer la méthode (universelle, excellente) de la configuration du parc (nom, sites, URL d'Artifact, ESM, Git) transformerait l'expérience des élèves sans rien retirer à Mattea.
2. **Le matin est le moment critique, et il est le moins outillé.** Après des heures de mesure, la personne revient dans une session neuve, peut-être sans ESM, peut-être sur un site unique : c'est là que les impasses (synthèse qui casse, lots figés, pas d'état de reprise) coûtent le plus cher. Une section « Reprendre » et un repli sans ESM sont les gains les plus rentables.
3. **Un baromètre se lit dans le temps.** Ajouter l'évolution par rapport au passage précédent ferait passer la sortie de « voici vos scores » à « voici ce qui a progressé grâce à vos corrections », ce qui est exactement la promesse d'un baromètre.

## Vérification des modèles facilitants

| Modèle | État | Commentaire |
|---|---|---|
| Porte souple | Absent, peu utile | Flux opérationnel ; une porte souple serait utile seulement à la fin : « autre chose à vérifier avant publication ? » |
| Intention avant ingestion | **Absent, haute valeur** | Voir H4 : trier relancer, consulter, adapter, comprendre avant de lancer quoi que ce soit |
| Capturer sans interrompre | Partiel | Les écarts « à arbitrer » sont capturés pour plus tard : bon réflexe à généraliser aux remarques de la personne pendant le passage |
| Double sortie | Partiel | Page HTML pour l'humain, CSV pour Excel ; manque un résumé JSON pour un autre agent (voir contrat de sortie) |
| Lentilles de revue parallèles | **Présent** | Lectures indépendantes en sous-agents, isolées de `resultats/`, preuve vérifiée mot pour mot : point fort remarquable |
| Architecture à trois modes | Absent, valeur moyenne | Guidé (première fois, avec démonstration), rapide (un site ou une étape), autonome (planifié, s'arrête avant publication) |
| Dégradation progressive | Partiel | Bonne pour Windows (veille) et pour les autres assistants (tableau d'équivalences) ; manque pour l'absence d'ESM, de MCP Opquast, de Shopify, et pour un passage sans sous-agents |

Les ajouts les plus utiles : intention avant ingestion, dégradation progressive (ESM et MCP), puis les trois modes.
