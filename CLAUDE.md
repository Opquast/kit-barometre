# Test Formation

Projet Opquast « Test Formation ». Il contient le **kit baromètre qualité des sites** (Opquast V5) : scripts de mesure, référentiel, skill Claude, tests et rapports. Dépôt GitHub privé : `Opquast/kit-barometre` (branche `main`). Ce fichier donne le contexte et les conventions à Claude Code, qui le charge automatiquement. Prise en main rapide : `README.md`.

## Où sont les choses

- `kit-barometre-sites/code/` : le kit (scripts Python et Node, `referentiel/`, tests). Point d'entrée : `scripts/barometre.py`.
- `kit-barometre-sites/code/.claude/skills/barometre-sites/SKILL.md` : la méthode du baromètre, qui fait foi pour l'utiliser.
- `kit-barometre-sites/code/referentiel/parc.json` et `scripts/ecrans_en_ligne.csv` : les sites mesurés et la personne responsable. On ne met jamais de nom de site ni de personne dans le code ; `scripts/configurer_parc.py --verifier` contrôle leur cohérence.
- `outils/verifications/` : scripts de contrôle maison lancés par les hooks.
- `rapports/` : rapports BMAD (quality analysis de la skill, revue de code).

## Conventions

- **Langue** : toujours répondre et rédiger en français. Seule exception : les messages de commit, en anglais.
- **Organisation** : ranger les fichiers dans des sous-dossiers thématiques, pas en vrac à la racine.
- **Noms de fichiers** : sans espaces ni accents, en minuscules avec des tirets (ex. `module-01-introduction.md`).
- **Git** : un commit par étape de travail. Les messages suivent [Conventional Commits](https://www.conventionalcommits.org/), en anglais (ex. `feat(barometer): add CSV export of scores`). Types acceptés : `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. Titre de 72 caractères maximum, sans point final. Le hook `.githooks/commit-msg` refuse les messages non conformes (format, accents, mots français courants).
- **Sécurité** : ne jamais committer de secrets (mots de passe, clés d'API, jetons, fichiers `.env`) ni de données personnelles.
- **Liens propres à un compte** (URL d'Artifact publiés) : dans `kit-barometre-sites/code/liens-locaux.json`, ignoré par git.
- **Sites mesurés** : lecture seule, aucun contournement d'anti-robot, rien installé sans l'accord de la personne (détail dans `SKILL.md`).

## Garde-fous (pre-commit)

Les hooks sont gérés par le framework [pre-commit](https://pre-commit.com), configuré dans `.pre-commit-config.yaml`. Après un clone :

```bash
pre-commit install --install-hooks -t pre-commit -t commit-msg -t pre-push
```

- **Avant chaque commit** : JSON, YAML et TOML valides ; ruff (Python, config `kit-barometre-sites/code/pyproject.toml`) ; `node --check` et ESLint (config `kit-barometre-sites/code/eslint.config.mjs`) ; gitleaks (secrets) ; structure des skills (frontmatter, fichiers cités) ; données personnelles dans les CSV et Excel ; partage (chemins absolus `/Users/…`, URL d'Artifact claude.ai) ; fichiers de plus de 1 Mo refusés.
- **Avant chaque push** : structure des skills, bandit (sécurité Python), `npm audit` (dépendances du kit), tests Python et JavaScript avec couverture à 100 %.
- **Bandit** : B404, B603 et B607 sont exclus pour tout le dépôt dans `.bandit.yaml` (les scripts lancent volontairement des outils locaux). Toute autre exception se justifie en ligne : `# nosec Bxxx: raison`.
- **Hors hooks** : la quality analysis BMAD de la skill et la revue de code BMAD se lancent à la main ; leurs rapports vont dans `rapports/`.
- Le push vers GitHub est bloqué par les permissions de Claude Code sur ce Mac : donner la commande `git push` à Mickaël.

## Tests

- Couverture exigée : **100 %** (lignes et branches), vérifiée avant chaque push par `outils/verifications/tests_couverture.sh`.
- Tests Python du kit : `kit-barometre-sites/code/tests/` (config dans `kit-barometre-sites/code/pyproject.toml`) ; tests des scripts de contrôle : `outils/tests/` (config dans `outils/pyproject.toml`). Lancer depuis le dossier de la suite : `../../.venv/bin/python -m pytest --cov` (environnement `.venv` à la racine : `python3 -m venv .venv && .venv/bin/pip install pytest pytest-cov openpyxl pyyaml`).
- Tests JavaScript : `kit-barometre-sites/code/tests/js/` (node:test, `npm run test:js` ; dépendances : `npm ci --ignore-scripts`, aucun navigateur requis). Playwright et les autres paquets sont simulés par `mock.module` ; chaque scénario tourne dans un processus enfant, car deux imports du même script dans un processus ne fusionnent pas leur couverture.
- Les tests n'accèdent jamais au réseau ni aux sites : HTTP, DNS, TLS, sous-processus et services en ligne sont simulés. Chaque test écrit dans un dossier temporaire (fixture `racine` de `tests/conftest.py`) ; `tests/aide_parc.py` y pose un parc de test.
- Une ligne réellement inaccessible se marque `# pragma: no cover` (Python) ou `/* node:coverage ignore next */` (JavaScript), avec sa raison. Tout nouveau code arrive avec ses tests.

## Défauts connus, non corrigés

- Scripts Node : `new URL('..', import.meta.url).pathname` encode l'espace du chemin (`Test%20Formation`), si bien qu'ils ne trouvent pas leurs fichiers depuis ce dossier. La correction passe par `fileURLToPath`.
- Règles qui ne peuvent jamais sortir conformes : 122 et 125 (`controles_page.js`), et 71 dans le HTML brut (`sources_html2.py` ne voit pas `required` sans valeur).
- Revue de code du 19/11 : les 13 correctifs listés dans `rapports/code-review/2026-11-19-revue-bmad.md` ne sont pas encore appliqués.
- L'historique git contient encore des prénoms, un compte GitHub tiers et d'anciennes URL d'Artifact : à nettoyer avant tout passage du dépôt en public.

## À compléter

- **Objectifs** : _à définir_
- **Public** : _à définir_
- **Livrables** : _à définir_
