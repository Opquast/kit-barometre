# Revue de code BMAD du 19/11/2026

**Cible** : modifications apportées au kit depuis son import (`28b270a..8d4acd1`), hors tests et hors `rapports/` : 26 fichiers, 912 lignes de diff. Les 6 200 lignes de tests (au-delà du seuil de 3 000 lignes de BMAD) restent pour un second passage.
**Mode** : sans spec (`no-spec`), donc 5 couches lancées en parallèle : Blind Hunter, Edge Case Hunter, et les 3 couches Opquast (Test Coverage Auditor, Magic Values Hunter, Performance & Resource Auditor). L'Acceptance Auditor est sauté, faute de spec. Aucune couche n'a échoué.
**Workflow** : `bmad-code-review` vanilla et surcharge `customizations/bmad-code-review.toml` du module bmad-opquast, lus en lecture seule.

**Bilan** : 0 `decision-needed`, 13 `patch`, 10 `defer`, 9 écartés.

## Patch : à corriger, la correction est sans ambiguïté

| # | Constat | Fichier | Sources |
|---|---|---|---|
| P1 | **Tests sautés en silence.** Dans `cd X && python -m pytest`, si le `cd` échoue, `set -e` ne s'applique pas : la suite est sautée et le push passe sans tests. | `outils/verifications/tests_couverture.sh` | blind + edge |
| P2 | **`liens-locaux.json` lu à l'import.** Un JSON mal formé, une racine qui n'est pas une liste ou une entrée sans `titre` ou `url` fait planter l'import de `generer_suivi.py` sans message utile. Les tests dépendent aussi de la présence du fichier sur le poste. Il faut lire le fichier à la génération, avec une erreur claire, et ajouter un fichier `liens-locaux.example.json`. | `scripts/generer_suivi.py:427-437` | blind + edge + coverage |
| P3 | **`exclude: ^rapports/` est global.** gitleaks et le contrôle des gros fichiers ne passent donc jamais sur `rapports/`. L'exclusion doit être limitée au hook « partage ». | `.pre-commit-config.yaml` | blind |
| P4 | **CLAUDE.md mal rangé.** Les puces « scripts de contrôle », « liens locaux » et « Sécurité » sont tombées sous « Tests » ; la commande `pre-commit install` diffère de celle de la config ; l'exclusion globale de B404, B603 et B607 dans `.bandit.yaml` n'est pas dite, alors que le fichier annonce « exception justifiée en ligne ». | `CLAUDE.md` | blind |
| P5 | **Un script JS sans test échappe aux 100 %.** `node --test --experimental-test-coverage` ne compte que les fichiers chargés : un nouveau script de `scripts/` sans test disparaît du rapport sans erreur. Il faut un test qui vérifie que chaque `scripts/*.mjs` et `*.js` a son fichier de tests. | `package.json` (`test:js`) | blind |
| P6 | **Version de Node non fixée.** `mock.module` et les options de couverture exigent Node 22.3 ou plus, sans champ `engines`. Par ailleurs, `jsdom` est en `^26.1.0`, alors que les autres paquets sont épinglés. | `package.json` | blind + edge |
| P7 | **`node_modules` incomplet mal signalé.** La garde ne vérifie que le dossier : si `jsdom` manque, le hook échoue sur une erreur d'import peu lisible. | `tests_couverture.sh` | edge |
| P8 | **Données personnelles : filtre sensible à la casse.** Les fichiers `.CSV` et `.XLSX` ne sont jamais contrôlés. Un classeur corrompu donne une trace d'erreur au lieu d'un refus clair. `logo@2x.png` est pris pour une adresse e-mail. Il manque les en-têtes accentués ou composés (« Prénom », « E-mail client »). | `donnees_personnelles.py`, `.pre-commit-config.yaml` | blind + edge |
| P9 | **Données personnelles : lecture Excel entièrement en mémoire.** `lire_excel` charge toutes les lignes, ce qui annule le mode `read_only`. Il faut lire les lignes une par une. | `donnees_personnelles.py:66-73` | perf |
| P10 | **Partage : motifs incomplets.** `C:/Users/x` (barres obliques) n'est pas détecté ; `/Users/Shared` et `/home/runner` (CI) bloquent à tort. | `partage.py:18` | blind + edge |
| P11 | **Structure des skills : faux refus.** Un SKILL.md en CRLF ou avec BOM est déclaré « sans frontmatter ». Une ligne `----` coupe le YAML. `scripts/x.py:42` est signalé introuvable. Sans argument, `node_modules/` et `.venv/` sont parcourus. Un fichier non UTF-8 donne une trace d'erreur. | `structure_skill.py` | blind + edge |
| P12 | **Tests manquants pour le nouveau code.** Il manque des tests pour `node_check.sh` (sortie 1 même si le dernier fichier est valide) et pour la garde `node_modules` de `tests_couverture.sh`, ainsi que des cas limites : domaine sosie `notexample.com`, téléphone à points ou tirets, en-tête Excel `None`, description de 1 024 caractères exactement, exclusions `/Users/{x}` et `/home/user/`. | `outils/tests/` | coverage |
| P13 | **Valeurs magiques dans le code ajouté.** Il faut nommer les constantes : 20 et 65 dans `verifier` (`NB_REGLES_IA`, `NB_REGLES_BASICS`), 8192 et 4096 (tailles d'échantillon), les extensions, `"---\n"` et sa longueur 4, `"SKILL.md"`, `".claude"`. | `repartir_regles.py`, `outils/verifications/*` | magic |

## Defer : réel, mais antérieur à ces modifications ou à décider plus tard

- **Règle 125 jamais conforme** (`controles_page.js`). La branche « conforme » est inaccessible et la ligne est marquée ignorée pour la couverture. La 124 lit la propriété `muted` et la 125 l'attribut. Défaut du kit, déjà signalé, à corriger avec la 122 (jamais conforme) et la 71 du HTML brut (`required` sans valeur).
- **Code mort marqué ignoré au lieu d'être supprimé** : `?? {}` dans `sources_tiers.mjs`, et `return 429` dans 4 scripts Python. On peut le simplifier en refactorisant, mais cela touche le code d'origine. Si `find` ne trouve aucune clé, les résultats Alfa partent dans `c["undefined"]`.
- **Fonction `get` copiée 3 fois** (`sources_html.py`, `sources_html2.py`, `sources_shopify.py`). Délais réseau et `Accept-Language` en dur (30, 25, 20, 60 s).
- **`npm audit --omit=dev`** ne contrôle que les 7 paquets de `dependencies`, alors que Playwright, Lighthouse, Pa11y et jsdom sont en `devDependencies`. Le hook ne tourne aussi que si le lock change. L'élargir risque de bloquer les push sur des failles de Lighthouse ou Pa11y : choix à faire.
- **`# nosec B310`** : aucun contrôle de schéma avant `urlopen`, et `statut_lien` suit des liens extraits de pages tierces. Code d'origine.
- **`.bandit.yaml`** : B603 et B607 sont exclus globalement, alors que des URL passées à curl ou redbot viennent en partie de sites tiers. Rien ne protège d'un argument commençant par `-`.
- **ESLint** : les `.mjs` reçoivent à la fois les globales du navigateur et de Node, donc un `document` utilisé hors de `page.evaluate` passe. **Ruff** est volontairement minimal (E4, E7, E9, F, 200 colonnes). Ce sont des choix de rigueur.
- **Historique git** : les 3 URL d'Artifact retirées, le compte `itsmatlsr` et les prénoms y restent. À nettoyer avant un passage en public.
- **`SKILL.md` et `liens-locaux.json`** : l'entrée « Suivi du baromètre » s'afficherait dans les liens de la page elle-même, et aucun code ne la relit pour publier.
- **Second passage** sur les 6 200 lignes de tests.

## Écartés (9)

- `.githooks/commit-msg` « absent du diff » : il existe et il est exécutable, il vient d'un commit antérieur à la plage relue.
- `node --check` qui rejetterait les scripts navigateur en module : il passe sur tous les fichiers actuels.
- Suppression de `_pages(nom)` dans `coup_doeil_site` : la fonction est pure, sans cache ni effet de bord.
- Champs de `liens-locaux.json` injectés sans échappement : `vue_ensemble` les passe par `e()`.
- Le français pour tout et l'anglais pour les commits : la règle est explicite dans CLAUDE.md.
- La même config ruff pour `outils/` : voulu.
- `verifier_installation.py` et `shell=True` : les commandes sont des constantes du script, lancées avec `--installer` après accord.
- Détection des binaires sur 8 Ko, et fichiers UTF-16 : cas absents du dépôt.
- Bascule de `core.hooksPath` : faite et documentée dans le commit `5a57517`.
