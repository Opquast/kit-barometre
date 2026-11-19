# Analyse de cohésion : skill `barometre-sites`

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, references/lectures-independantes.md, INSTALLER-AVEC-UN-ASSISTANT-IA.md), lue avec le code du kit (`scripts/barometre.py`, `scripts/README.md`, `AGENTS.md`, `package.json`, `requirements.txt`, `../LISEZ-MOI.md`).

Nature : ce n'est pas un agent à persona ni un agent à mémoire (pas de `assets/`, pas de sanctuaire). C'est une skill de workflow opérée par un « opérateur de mesure » implicite. La dimension « persona » est donc lue comme « posture et identité de rôle » : prudence en production, recoupement des sources, l'humain tranche.

## Bilan

La skill est très cohérente sur son cœur de métier : un seul objectif (taux de conformité Opquast V5), un pipeline en six étapes que `barometre.py` reproduit exactement, une méthode d'arbitrage claire (quatre questions, jamais de vote) et des garde-fous de production solides et répétés partout (SKILL, guide d'installation, AGENTS.md). Les faiblesses tiennent surtout à la **double identité** du dossier : un outil interne pour le parc de Mattea (noms, URL d'Artifact, eServices Manager, note de cadrage, dépôt personnel) et un kit distribué aux élèves pour leurs propres sites. Plusieurs étapes du parcours (contre-examen, import ESM, liste des règles à une seule source) existent dans le code mais pas dans la skill, ou l'inverse.

## Dimensions de cohésion

| Dimension | Note | Explication |
|---|---|---|
| Alignement posture / capacités | Fort | La description promet mesure, recoupement, arbitrage, page et CSV : tout est livré par des étapes nommées et des scripts réels. Les principes (lecture seule, pas de contournement, pas de donnée personnelle, accord avant installation) se retrouvent dans le code (`barometre.py` code 3, `--ignore-scripts`, robot identifié honnêtement). |
| Cohérence d'identité (public visé) | Moyen | SKILL.md parle à « Mattea » (7 mentions), à une URL d'Artifact fixe, à un dépôt personnel et à `note_cadrage.md` (absent du kit). Le guide d'installation, lui, s'adresse à n'importe quelle personne et à n'importe quel assistant. Le lecteur ne sait pas toujours s'il est dans le cas « Mattea » ou dans le cas « élève ». |
| Complétude des capacités | Moyen | Installation, passage, reprise, arbitrage et livraison sont couverts. Manquent : comment produire l'export ESM basics et le contre-examen (scripts présents mais non décrits), comment générer la liste des règles à une seule source pour la lecture DOM, et un mode « sans ESM » explicite. |
| Redondance | Moyen | Prérequis, règles absolues et passage de nuit sont écrits deux fois (SKILL.md et INSTALLER). C'est en partie voulu (portabilité), mais les deux copies divergeront. |
| Intégration externe | Fort | MCP Opquast (`get_rule`), sous-agents en arrière-plan, Artifact, SendUserFile, AskUserQuestion, eServices Manager : chaque appel a une raison et le guide donne l'équivalent hors Claude. Très bon point. |
| Granularité | Fort | Les six étapes sont au bon niveau, avec reprise `--depuis` et exécution ciblée `--service`, `--etapes synthese`. Les trois lectures IA ont chacune un périmètre de règles et un format de preuve distincts. |
| Parcours utilisateur | Moyen | Entrée claire (vérifier l'installation, proposer la nuit), sortie utile (page, trois CSV, compte rendu). Mais une boucle n'est pas dite : la lecture DOM a besoin d'une synthèse préalable, puis d'une seconde synthèse. |

## Cohésion par capacité

| Capacité | S'intègre ? | Remarque |
|---|---|---|
| Vérification et installation des prérequis | Oui | Exemplaire : liste, explication, accord explicite, puis seulement installation. Cohérent avec le blocage code 3 de `barometre.py`. |
| Passage automatique (referentiel, moteur, mesure, releve, sources, synthese) | Oui | Le tableau de SKILL.md correspond ligne à ligne à `ORDRE` et `etapes()` dans `barometre.py`. |
| Mode nuit | Oui | Bien aligné sur le code (`pmset`, `caffeinate`, `systemd-inhibit`, journal daté, `--forcer`). `--forcer` n'est pas documenté dans SKILL.md. |
| Lectures IA indépendantes | Oui, avec un trou | Principe d'indépendance fort et vérifié (`verifier_citations.py`). Mais la lecture 3 exige un fichier JSON des règles à une seule source qu'aucun script ne produit. |
| Robot ESM basics | Partiel | « Réutiliser le dernier export » sans dire comment l'export devient `resultats/esm-basics-*/agregat.json` ni que `synthese_esm_basics.py` doit être lancé. Pour un élève sans ESM, rien n'indique que le pipeline fonctionne sans. |
| Contre-examen humain | Absent de la skill | Revendiqué comme source dans INSTALLER et LISEZ-MOI, lu par `generer_suivi.py` (`resultats/contre-examen-*/fiche.json`), produit par `contre_examen.mjs` et `fiche_contre_examen.py`, mais jamais mentionné dans SKILL.md ni lancé par `barometre.py`. |
| Arbitrage des écarts | Oui | Le point le plus fort : quatre questions ordonnées, décisions écrites dans `ANALYSE_SOURCES`, contrôle final « liste vide ». La commande Python en une ligne est fragile mais vérifiable. |
| Publication (données personnelles, Artifact, CSV, ESM, note de cadrage, commit) | Partiel | Les étapes 1 à 3 sont génériques et utiles. Les étapes 2 (URL fixe), 4 (ESM), 5 (`note_cadrage.md` absent) et 6 (« dépôt personnel ») sont propres au parc de Mattea. |

## Constats

### Moyenne : le contre-examen humain est une source fantôme
- Zone : SKILL.md, Déroulé ; `scripts/contre_examen.mjs`, `scripts/fiche_contre_examen.py`, `scripts/generer_suivi.py` (l. 720).
- Problème : la méthode annonce le contre-examen comme une des cinq familles de sources, la page de suivi le lit, mais la skill ne dit ni quand le lancer ni comment Mattea valide la fiche. Un nouveau passage réutilise donc silencieusement une ancienne fiche, ou n'en a aucune chez un élève.
- Correction : ajouter une étape « Contre-examen » entre `sources` et `synthese` (à côté des lectures IA et d'ESM), avec les deux commandes, la règle « la décision reste à valider par la personne » et le comportement attendu sans fiche.

### Moyenne : la lecture DOM dépend d'une entrée que rien ne produit, et d'un ordre non dit
- Zone : `references/lectures-independantes.md`, section 3 ; SKILL.md, Déroulé.
- Problème : la lecture 3 porte sur « les règles qui restent à une seule source après l'étape `synthese` », à lister dans un JSON. Or le Déroulé place les lectures avant la synthèse, et aucun script n'écrit ce JSON (seul `generer_suivi.py` calcule `n < 2` pour l'affichage).
- Correction : écrire explicitement la boucle (synthèse, lectures 1 et 2 possibles plus tôt, lecture 3 après une première synthèse, seconde synthèse) et ajouter une sortie `regles-une-source.json` à `lecture_critique.py` ou `generer_suivi.py`.

### Moyenne : identité double, outil interne et kit pour élèves
- Zone : description et SKILL.md (Mattea, Colorz, URL d'Artifact, « dépôt personnel », `note_cadrage.md`, eServices Manager).
- Problème : un élève qui suit le guide tombe sur des étapes impossibles (publier sur un Artifact qui ne lui appartient pas, mettre à jour une note absente du kit, saisir dans un ESM qu'il n'a pas). Le guide d'installation traduit les outils Claude, pas ces dépendances propres au parc.
- Correction : remplacer « Mattea » par « la personne responsable du baromètre », sortir les éléments propres au parc dans un fichier de configuration (URL de suivi, audits ESM, nom de la note) et marquer les étapes 4 et 5 de Publication comme optionnelles « si ESM » et « si note de cadrage ».

### Moyenne : ESM est requis implicitement
- Zone : SKILL.md, étape 2 entre `sources` et `synthese` ; `scripts/etat_barometre.py`.
- Problème : `etat_barometre.py` cherche `resultats/esm-basics-*`. La skill ne dit ni comment créer ce dossier depuis l'export ESM, ni ce qui se passe s'il n'existe pas.
- Correction : une sous-section « Avec ou sans eServices Manager » : chemin d'import (export, `agregat.json`, `synthese_esm_basics.py`), et confirmation que la synthèse tourne sans (ou ce qu'il faut faire).

### Basse : documentation à deux endroits
- Zone : SKILL.md (Prérequis, Déroulé) et INSTALLER (étapes 2 et 5).
- Problème : listes d'outils, règles absolues et conseils de nuit sont recopiés. La première évolution créera un écart.
- Correction : garder le détail dans SKILL.md et faire pointer INSTALLER vers les sections, en ne gardant chez lui que l'adaptation aux sites et la table d'équivalences entre assistants.

### Basse : références mortes ou non branchées
- `scripts/README.md` cite `controles_email.py`, absent du kit ; `lecture_critique.py` lit `resultats/email-*` et `requirements.txt` installe checkdmarc pour un « baromètre e-mails » hors du périmètre de cette skill.
- `import_esm.py` et `generer_schema.py` sont cités dans l'étape d'adaptation mais pas dans le déroulé.
- Correction : retirer ou signaler comme « hors périmètre » ce qui relève des e-mails, et dire à quoi servent les scripts hors pipeline.

### Basse : commit et push sans dépôt
- Zone : règles et Publication, étape 6.
- Problème : « commit et push après chaque étape » suppose un dépôt Git distant ; le kit n'en fournit pas et la commande de contrôle des données personnelles est la seule protection avant publication.
- Correction : « si le projet est sous Git », et rappeler que `resultats/` du jour doit passer le contrôle avant tout commit.

### Suggestion : la description est longue et très propre au parc
- La description cite les 6 boutiques Shopify, Mattea et Colorz. Les déclencheurs (« relancer le baromètre », « scores Opquast », « CSV du baromètre ») sont bons ; la partie propre au parc pourrait passer dans le corps pour que la skill se déclenche aussi chez un élève qui parle de « ses sites ».

## Points forts

- **Une seule promesse, tenue** : tout sert le taux de conformité, et les outils sont explicitement des preuves, pas des scores. C'est la colonne vertébrale qui rend la skill lisible.
- **Correspondance exacte skill / code** : les étapes, options et sorties décrites existent dans `barometre.py`, ce qui rend la skill fiable à suivre.
- **Garde-fous cohérents de bout en bout** : lecture seule, refus des cookies seul clic, pas de contournement de 429, pas de robot payant, accord avant installation, `npm ci --ignore-scripts`, outils récents écartés avec leur raison.
- **Indépendance des lectures IA réellement outillée** : interdiction de lire `resultats/`, preuves au mot près, rejet automatique par `verifier_citations.py`.
- **Arbitrage exemplaire** : quatre questions ordonnées, exemples concrets (règles 124, 153), « à arbitrer » quand une interprétation subsiste, contrôle « aucun écart sans décision ».
- **Portabilité pensée** : la table d'équivalences entre Claude et les autres assistants (Agent, MCP, Artifact, SendUserFile, AskUserQuestion) est rare et très utile.

## Idées pour aller plus loin

- **Mode « comparer deux passages »** : une étape qui sort l'évolution des scores et des statuts par règle depuis le passage précédent. Un baromètre prend son sens dans la durée, et les CSV datés le permettent déjà.
- **Assistant d'adaptation** : transformer l'étape 3 du guide (six fichiers à éditer à la main) en un script `configurer_sites.py` qui lit une seule liste de sites et met à jour `SERVICES`/`SITES` partout. Cela supprimerait la principale source d'erreur pour les élèves.
- **Fichier `profil.json`** : responsable, URL de suivi, ESM oui/non, note de cadrage oui/non. La skill lirait ce profil et sauterait d'elle-même les étapes sans objet, ce qui réglerait la double identité.
- **Compte rendu type** : un modèle du message final (scores, part à deux sources, écarts tranchés et à arbitrer, non mesuré) généré par `exporter_csv.py`, pour que la sortie soit identique d'un passage et d'un assistant à l'autre.
- **Tableau de bord des sources par règle** : signaler avant la synthèse les règles qui resteront à une seule source, pour orienter les lectures IA et le contre-examen plutôt que de les découvrir après coup.
