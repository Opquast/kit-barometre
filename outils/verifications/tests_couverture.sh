#!/bin/sh
# Lance les tests avec la couverture exigée à 100 % (hook pre-push).
# Trois suites : les scripts Python du kit, les scripts de contrôle du dépôt, puis les scripts JavaScript du kit.
set -e
racine=$(git rev-parse --show-toplevel)
cd "$racine/kit-barometre-sites/code" && python -m pytest -q -p no:cacheprovider --cov --cov-report=term-missing:skip-covered
cd "$racine/outils" && python -m pytest -q -p no:cacheprovider --cov --cov-report=term-missing:skip-covered
# Tests JavaScript (node:test), couverture exigée à 100 % ; dépendances : npm ci --ignore-scripts
cd "$racine/kit-barometre-sites/code"
if [ ! -d node_modules ]; then
  echo "✖ node_modules absent : lancer « npm ci --ignore-scripts » dans kit-barometre-sites/code" >&2
  exit 1
fi
npm run -s test:js
