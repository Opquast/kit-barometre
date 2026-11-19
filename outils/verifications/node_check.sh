#!/bin/sh
# Vérifie la syntaxe de chaque fichier JavaScript passé en argument (node --check).
status=0
for f in "$@"; do
  node --check "$f" || status=1
done
exit $status
