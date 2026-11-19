# Opportunités d'amélioration : skill `barometre-sites` et kit

Analyse créative (scanner DreamBot), purement consultative : rien de ce qui suit n'est cassé, ce sont des pistes pour améliorer l'expérience. Périmètre lu : `SKILL.md`, `references/lectures-independantes.md`, `INSTALLER-AVEC-UN-ASSISTANT-IA.md` (identique dans la skill et à la racine du kit), `LISEZ-MOI.md`, `AGENTS.md`, `scripts/barometre.py`, `scripts/README.md`, et les tables de sites codées en dur dans les scripts.

## Ce qu'est la skill

Un orchestrateur de mesure Opquast V5 sur un parc de boutiques Shopify : une longue chaîne automatique (`barometre.py`, six étapes, plusieurs heures), puis trois lectures IA indépendantes à preuve vérifiée, l'arbitrage écrit des écarts et la publication (Artifact, trois CSV, ESM, note de cadrage, commit). Elle sert à deux publics très différents : Mattea, sur son parc d'origine, et les élèves de la formation qui reçoivent le kit pour l'appliquer à leurs propres sites, avec n'importe quel assistant. Ses hypothèses principales : le parc est celui des six boutiques, Shopify, une session de Claude qui connaît déjà l'historique, et une personne disponible le matin pour finir.

## Parcours utilisateurs

### La première fois (élève de la formation, kit neuf)

Elle ouvre `code/`, donne le guide à son assistant. La vérification d'installation est exemplaire : rien ne s'installe sans accord, les commandes sont montrées, les mots de passe restent à elle. Puis vient l'étape 3 « adapter aux sites » : il faut modifier **six fichiers Python** (`SITES`, `SERVICES` dans cinq scripts, plus `generer_suivi.py` dont chaque entrée contient description, version, liste d'écrans et URL), un JSON ESM et retirer à la main 20 à 25 décisions nommées dans `ANALYSE_SOURCES`. En plus, des comportements propres aux anciennes boutiques restent enfouis dans le code (`HORS_SITE = ("Boutique C", "Boutique D", "Boutique E")` dans `redbot_local.py` et `i18n_w3c.py`, `'/fr'` pour Boutique D dans `contre_examen.mjs`). Le `ecrans_en_ligne.csv` livré contient « Ma boutique » alors que tous les scripts attendent « Boutique A » à « F » : sans édition, le premier passage tourne sur un site que les scripts de synthèse ne connaissent pas.

- Friction : mur d'hypothèses (« assumption wall ») au moment le plus fragile, la configuration. Aucune validation de cohérence entre `ecrans_en_ligne.csv` et les tables des scripts.
- Point fort : `--essai` existe, les règles absolues sont claires et répétées partout.

### L'expert (Mattea, passage habituel)

Elle dit « relance le baromètre ». La skill propose nuit ou maintenant, lance, et le matin la reprise par `--depuis` est simple. Mais elle doit se souvenir d'un déroulé matinal en quatre temps (lectures 1 et 2 en parallèle de la première synthèse, `regles_une_source.py`, lecture 3, synthèse finale, puis vérification des écarts par une ligne Python illisible). Il n'existe pas de commande « où en suis-je dans ce passage ? ».

- Friction : l'expert retient l'ordre de tête ; un oubli (lecture 3 lancée trop tôt) casse l'indépendance ou la couverture sans alerte.
- Point fort : l'option `--etapes synthese` en quelques secondes permet d'itérer vite sur l'arbitrage.

### L'utilisateur perdu

« Fais-moi un audit Opquast de ce site » ou « donne-moi le score de Boutique B ». La description de la skill est très large (« les scores Opquast des boutiques », « le CSV ») : une simple question de lecture risque de déclencher un passage de plusieurs heures, ou une proposition de lancement nocturne alors que la personne voulait seulement lire le dernier `scores.csv`.

- Friction : pas de chemin « consultation » distinct du chemin « mesure ».

### Le cas limite

Un site non Shopify, un site multilingue, un site qui passe derrière un anti-robot au milieu de la nuit, un écran qui renvoie 404 parce que le produit a été retiré du catalogue. Le kit dit honnêtement que certaines sources n'existent pas hors Shopify, mais ne dit pas lesquelles se désactivent ni comment : `sources_shopify.py` et `sources_panier.mjs` sont lancées sans condition. Un produit retiré entre deux passages fait basculer des règles en NT ou NC sans qu'on sache si c'est le site ou la liste d'écrans qui a vieilli.

### L'environnement hostile

Batterie : bien géré (code 4). Windows : honnête (« non géré »). En revanche : un 429 persistant ou un anti-robot sur un site arrête-t-il tout le passage ? Avec le défaut (sans `--continuer`), un seul script en échec stoppe la nuit entière et le matin on découvre que 5 sites sur 6 n'ont pas été mesurés. Le MCP Opquast indisponible (non authentifié) n'a pas de repli explicite dans la skill elle-même, seulement dans le guide multi-assistant. Compactage du contexte pendant les lectures : l'état (« lecture 1 rendue, lecture 2 en cours ») n'est écrit nulle part.

### L'automate

Un passage planifié (cron, tâche programmée) est presque possible : `barometre.py` est non interactif. Mais tout ce qui suit est conversationnel et sans contrat de sortie : lectures IA, arbitrage, publication. Rien ne permet à un autre agent de demander « relance et rends-moi les scores ».

## Évaluation du mode sans interaction (headless)

**Niveau : partiellement adaptable.**

- Peut se résoudre seul : le choix nuit/maintenant (paramètre), la vérification d'installation (échec net code 3 si manque, sans installation), toute la chaîne `barometre.py`, les lectures 1 et 2 (sous-agents, entrées fixées), `regles_une_source.py`, la lecture 3, la synthèse finale, `verifier_publication.py`, l'export CSV.
- Doit rester humain : l'installation (accord), tout robot ESM payant, la saisie ESM (Mattea connectée), les écarts marqués « à arbitrer par Mattea », le commit et l'envoi.
- Contrat proposé : entrée `{headless: true, hors, quand: "maintenant"|"nuit", sites?: [...], publier: false}` ; sortie un fichier `resultats/barometre-<date>/bilan.json` avec scores et notes par site, part à deux sources, écarts tranchés, écarts sans décision, règles NT avec raison, chemins des CSV et de la page, et un statut global (`complet`, `partiel`, `bloque_installation`, `ecarts_a_arbitrer`). Le mode s'arrête avant la publication et liste ce qui attend l'humain.

## Constats

### Configuration du parc dispersée dans le code
- **Gravité** : high-opportunity
- **Zone** : étape 3 du guide, `etat_barometre.py`, `fusion_scripts.py`, `generer_suivi.py`, `import_esm.py`, `generer_schema.py`, `redbot_local.py`, `i18n_w3c.py`, `contre_examen.mjs`, `lecture_critique.py`
- **Constat** : la liste des sites vit à au moins sept endroits, avec des particularités par boutique codées en dur. Le CSV d'écrans livré (« Ma boutique ») ne correspond à aucune table.
- **Suggestion** : un seul fichier `referentiel/parc.json` (nom, code court, domaine, préfixe ESM, description, particularités comme « compte hors site » ou « préfixe de langue ») lu par tous les scripts, et une sous-étape « adapter » de la skill qui pose les questions (sites, écrans, droit d'auditer, ESM oui ou non) puis écrit ce fichier et le CSV. Ajouter à `verifier_installation.py` un contrôle de cohérence parc / écrans.

### Pas de mode consultation
- **Gravité** : high-opportunity
- **Zone** : description et ouverture de `SKILL.md`
- **Constat** : la skill démarre toujours sur « lancer la mesure ». Les questions « quel est le score de Boutique B ? », « qu'est-ce qui a changé ? », « pourquoi la règle 153 est NC ? » n'ont pas de chemin.
- **Suggestion** : une première question d'intention en trois branches : consulter le dernier passage (lire `scores.csv`, `lecture.json`, sans rien lancer), rejouer seulement la synthèse ou l'arbitrage, ou lancer un nouveau passage. Lire d'abord la date du dernier passage et la proposer : « Le dernier passage date du 19/11. Voulez-vous le consulter ou en lancer un nouveau ? »

### Un baromètre sans évolution
- **Gravité** : high-opportunity
- **Zone** : `generer_suivi.py`, `exporter_csv.py`, compte rendu final
- **Constat** : un baromètre se lit dans le temps, mais la synthèse ne compare pas au passage précédent. Le compte rendu demandé (scores, deux sources, écarts) ne dit pas ce qui a progressé ou régressé.
- **Suggestion** : une colonne « passage précédent » et « écart » dans `scores.csv`, une liste « règles passées de C à NC et inversement » par site, et une phrase d'ouverture du compte rendu du type « Boutique C gagne 4 points, deux régressions sur la sécurité ». Signaler aussi les écarts qui viennent d'un changement de liste d'écrans plutôt que du site.

### Tableau de bord d'état du passage
- **Gravité** : medium-opportunity
- **Zone** : déroulé du matin, après `sources`
- **Constat** : l'ordre lectures 1 et 2, synthèse 1, `regles_une_source`, lecture 3, synthèse finale est fragile et n'est consigné nulle part ; après un compactage de contexte ou le lendemain, Claude ne sait plus où il en est.
- **Suggestion** : un `python3 scripts/etat_passage.py` (ou une option `barometre.py --etat`) qui lit `resultats/` et le journal et répond : étapes faites, lectures rendues (fichiers `lecture_ia_lot*.json`, `lecture_visuelle_lot*`, `lecture_dom_lot*`), écarts sans décision, prochaine action. Il remplace aussi la ligne Python de contrôle des écarts, difficile à relire. La skill l'appelle à chaque reprise.

### Une nuit perdue pour un seul site
- **Gravité** : medium-opportunity
- **Zone** : `barometre.py --nuit`
- **Constat** : sans `--continuer`, un échec de script arrête tout ; or la nuit personne ne peut corriger. Le matin, les sites non mesurés sont la mauvaise surprise.
- **Suggestion** : en mode `--nuit`, activer `--continuer` par défaut et écrire en fin de journal un bilan lisible (« 5 sites complets, Boutique E arrêtée à `sources_tiers` : 429 persistant, reprendre avec `--depuis sources --service "Boutique E"` »). La skill lit ce bilan en premier le matin et propose la commande exacte.

### Sites hors Shopify
- **Gravité** : medium-opportunity
- **Zone** : `LISEZ-MOI.md` « À savoir », étape `sources`
- **Constat** : le kit cible des élèves qui n'ont pas forcément des boutiques Shopify, mais les sources Shopify tournent sans condition et le guide ne dit pas quelles règles perdent leur deuxième source.
- **Suggestion** : un champ `plateforme` dans le futur `parc.json`, les étapes Shopify sautées avec une ligne « non applicable à cette plateforme » dans le bilan, et dans le guide une courte liste des règles qui tombent à une source hors Shopify (que la lecture 3 viendra combler).

### Écrans obsolètes
- **Gravité** : medium-opportunity
- **Zone** : `ecrans_en_ligne.csv`, étape `mesure`
- **Constat** : une fiche produit retirée du catalogue renvoie 404 ou une redirection ; le passage mesure alors une autre page sans le dire.
- **Suggestion** : un pré-contrôle rapide en début de passage (une requête par écran) qui signale les écrans en 404 ou redirigés et propose un remplaçant (par exemple le premier produit de la collection), avant de lancer des heures de mesure.

### Repli quand le MCP Opquast manque
- **Gravité** : medium-opportunity
- **Zone** : « Trancher les écarts » et `lectures-independantes.md`
- **Constat** : l'arbitrage et les trois lectures exigent `get_rule`. Le repli (page publique de la règle via le slug de `opquast-checklist-v5.json`) n'est décrit que dans le guide pour les autres assistants.
- **Suggestion** : reprendre ce repli dans `SKILL.md` et dans les consignes communes des sous-agents (« si `get_rule` est indisponible, lire la règle dans `referentiel/opquast-checklist-v5.json` »), en le signalant dans le compte rendu. Attention à l'indépendance : ce fichier de référentiel est neutre, il peut être autorisé explicitement aux sous-agents.

### Compte rendu qui reste dans la conversation
- **Gravité** : low-opportunity
- **Zone** : Publication, point 6
- **Constat** : le compte rendu final à Mattea (scores, écarts à arbitrer, ce qui n'a pas pu être mesuré) n'est écrit nulle part : il disparaît avec la session.
- **Suggestion** : l'écrire aussi dans `resultats/barometre-<date>/compte-rendu.md` (sans données personnelles, vérifié par `verifier_publication.py`) et le citer en tête de la page de suivi. C'est aussi la sortie naturelle du mode headless.

### Liste « à arbitrer par Mattea » actionnable
- **Gravité** : low-opportunity
- **Zone** : « Trancher les écarts », question 4
- **Constat** : les écarts d'interprétation sont marqués, mais Mattea doit les retrouver dans la page ou le CSV.
- **Suggestion** : en fin de passage, lui présenter ces écarts un par un (règle, ce que dit chaque source, proposition, capture ou citation), avec un choix rapide, et écrire sa décision dans `ANALYSE_SOURCES`. Cela transforme le point mort en un moment court et utile.

### Élève : parcours guidé du premier résultat
- **Gravité** : low-opportunity
- **Zone** : `LISEZ-MOI.md`, fin de passage
- **Constat** : le LISEZ-MOI donne une excellente astuce (filtrer `tests.csv` sur `accord_avec_la_decision = non`), mais la skill ne la reprend pas au moment où l'élève reçoit ses propres résultats.
- **Suggestion** : terminer un premier passage par trois pistes de lecture : le score et sa note, les trois règles NC les plus faciles à corriger (`recommandations.csv` existe déjà), et deux exemples d'outils contredits par le recoupement. Valeur pédagogique forte pour une formation.

## Trois idées qui changeraient le plus l'expérience

1. **Un seul fichier de parc, une question d'adaptation guidée.** Le kit est fait pour être réutilisé par des élèves, mais la réutilisation passe par l'édition de sept scripts. Centraliser le parc transforme l'étape la plus risquée en cinq questions.
2. **Faire du baromètre un baromètre : l'évolution d'un passage à l'autre.** C'est la question que Mattea et ses clients poseront en premier (« ça va mieux ? »), et les données sont déjà là, passage par passage, dans `resultats/`.
3. **Un état de passage lisible par la machine.** Il répond à la fois à la reprise du matin, au compactage du contexte et au mode sans interaction, et remplace la ligne Python de contrôle par une réponse en français.

## Modèles d'animation

| Modèle | État | Commentaire |
|---|---|---|
| Accord avant action (soft gate) | présent | installation, mode nuit, robot ESM : très bien tenu |
| Intention avant lecture | absent | la skill ne demande pas si l'on veut consulter ou mesurer ; c'est le manque le plus utile à combler |
| Capturer sans interrompre | sans objet | peu de découverte conversationnelle |
| Double sortie | partiel | page HTML et CSV pour les humains ; un `bilan.json` compact servirait les agents et l'automatisation |
| Relectures parallèles | présent, et c'est le cœur | lectures indépendantes isolées de `resultats/`, citation vérifiée mot pour mot : une vraie force |
| Trois modes (guidé, rapide, autonome) | partiel | `--essai`, `--etapes synthese` et `--nuit` en sont l'amorce ; un mode autonome qui s'arrête avant la publication compléterait |
| Dégradation douce | partiel | sans ESM et sans secteur : prévu ; sans MCP Opquast, sans Shopify, ou si un site bloque la nuit : à prévoir |
