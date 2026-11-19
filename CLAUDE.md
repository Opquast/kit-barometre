# Test Formation

Projet Opquast « Test Formation ». Ce fichier donne le contexte et les conventions à Claude Code, qui le charge automatiquement.

## Conventions

- **Langue** : toujours répondre et rédiger en français.
- **Organisation** : ranger les fichiers dans des sous-dossiers thématiques (par exemple `supports/`, `exercices/`, `evaluations/`, `ressources/`), pas en vrac à la racine.
- **Noms de fichiers** : sans espaces ni accents, en minuscules avec des tirets (ex. `module-01-introduction.md`).
- **Git** : un commit par étape de travail. Les messages de commit suivent [Conventional Commits](https://www.conventionalcommits.org/) et sont rédigés **en anglais** (ex. `feat(barometer): add CSV export of scores`). Types acceptés : `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. Titre de 72 caractères maximum, sans point final.
- **Hook git** : le hook `.githooks/commit-msg` refuse les messages non conformes (format, accents, mots français courants). Après un clone, l'activer avec `git config core.hooksPath .githooks`.
- **Sécurité** : ne jamais committer de secrets (mots de passe, clés d'API, jetons, fichiers `.env`).

## À compléter

- **Objectifs** : _à définir_
- **Public** : _à définir_
- **Livrables** : _à définir_
