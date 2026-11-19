#!/bin/sh
# Lance les tests Python avec la couverture exigée à 100 % (hook pre-push).
# Deux suites : les scripts du kit, puis les scripts de contrôle du dépôt.
set -e
racine=$(git rev-parse --show-toplevel)
cd "$racine/kit-barometre-sites/code" && python -m pytest -q -p no:cacheprovider --cov --cov-report=term-missing:skip-covered
cd "$racine/outils" && python -m pytest -q -p no:cacheprovider --cov --cov-report=term-missing:skip-covered
