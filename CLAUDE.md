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
- Les scripts de contrôle maison sont dans `outils/verifications/`. Une exception bandit se justifie en ligne (`# nosec Bxxx: raison`).
- Les liens propres à un compte (URL d'Artifact publiés) vont dans `kit-barometre-sites/code/liens-locaux.json`, ignoré par git.
- **Sécurité** : ne jamais committer de secrets (mots de passe, clés d'API, jetons, fichiers `.env`).

## À compléter

- **Objectifs** : _à définir_
- **Public** : _à définir_
- **Livrables** : _à définir_
