# Test Formation

Projet Opquast « Test Formation ». Ce fichier donne le contexte et les conventions à Claude Code, qui le charge automatiquement.

## Conventions

- **Langue** : toujours répondre et rédiger en français.
- **Organisation** : ranger les fichiers dans des sous-dossiers thématiques (par exemple `supports/`, `exercices/`, `evaluations/`, `ressources/`), pas en vrac à la racine.
- **Noms de fichiers** : sans espaces ni accents, en minuscules avec des tirets (ex. `module-01-introduction.md`).
- **Git** : un commit par étape de travail. Les messages de commit suivent [Conventional Commits](https://www.conventionalcommits.org/) et sont rédigés **en anglais** (ex. `feat(barometer): add CSV export of scores`). Types acceptés : `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. Titre de 72 caractères maximum, sans point final.
- **Hook de message** : `.githooks/commit-msg` refuse les messages non conformes (format, accents, mots français courants). Il est lancé par pre-commit (voir ci-dessous).

## Garde-fous (pre-commit)

Les hooks sont gérés par le framework [pre-commit](https://pre-commit.com), configuré dans `.pre-commit-config.yaml`. Après un clone :

```bash
pre-commit install --install-hooks
```

- **Avant chaque commit** : JSON, YAML et TOML valides ; ruff (Python, config `kit-barometre-sites/code/pyproject.toml`) ; `node --check` et ESLint (config `kit-barometre-sites/code/eslint.config.mjs`) ; gitleaks (secrets) ; structure des skills (frontmatter, fichiers cités) ; données personnelles dans les CSV et Excel ; partage (chemins absolus `/Users/…`, URL d'Artifact claude.ai) ; fichiers de plus de 1 Mo refusés.
- **Avant chaque push** : structure des skills, bandit (sécurité Python, config `.bandit.yaml`), `npm audit` (dépendances du kit), tests avec couverture à 100 %.
- **Hors hooks** : la quality analysis BMAD se lance à la main, de temps en temps.

## Tests

- Couverture exigée : **100 %** (lignes et branches), vérifiée avant chaque push par `outils/verifications/tests_couverture.sh`.
- Tests du kit : `kit-barometre-sites/code/tests/` (config dans `kit-barometre-sites/code/pyproject.toml`) ; tests des scripts de contrôle : `outils/tests/` (config dans `outils/pyproject.toml`).
- Les tests n'accèdent jamais au réseau ni aux sites : HTTP, DNS, TLS, sous-processus et services en ligne sont simulés, et chaque test écrit dans un dossier temporaire (fixture `racine` de `tests/conftest.py`).
- Lancer à la main, depuis le dossier de la suite : `python -m pytest --cov` (environnement `.venv` à la racine : `python3 -m venv .venv && .venv/bin/pip install pytest pytest-cov openpyxl pyyaml`).
- Tests JavaScript : `kit-barometre-sites/code/tests/js/` (node:test, `npm run test:js` ; dépendances : `npm ci --ignore-scripts`, aucun navigateur requis). Playwright et les autres paquets sont simulés par `mock.module` ; chaque scénario tourne dans un processus enfant, car deux imports du même script dans un processus ne fusionnent pas leur couverture.
- Une ligne réellement inaccessible se marque `# pragma: no cover` (Python) ou `/* node:coverage ignore next */` (JavaScript) avec sa raison ; tout nouveau code arrive avec ses tests.
- Les scripts de contrôle maison sont dans `outils/verifications/`. Une exception bandit se justifie en ligne (`# nosec Bxxx: raison`).
- Les liens propres à un compte (URL d'Artifact publiés) vont dans `kit-barometre-sites/code/liens-locaux.json`, ignoré par git.
- **Sécurité** : ne jamais committer de secrets (mots de passe, clés d'API, jetons, fichiers `.env`).

## À compléter

- **Objectifs** : _à définir_
- **Public** : _à définir_
- **Livrables** : _à définir_
