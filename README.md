# Kit baromètre qualité des sites (Opquast V5)

Ce dépôt mesure la conformité d'un parc de sites e-commerce aux 245 règles Opquast V5. Pour chaque règle, il recoupe au moins deux sources indépendantes (scripts, outils libres, robot eServices Manager, lectures IA à preuve vérifiée, contre-examen humain), tranche les écarts par une décision écrite, puis produit une page de suivi, des CSV et un compte rendu.

**Autrice initiale** : Mattea LUSSIER, qui a conçu la méthode et le kit et les a partagés avec les élèves de la formation Opquast (voir `kit-barometre-sites/LISEZ-MOI.md`).

Ce README sert à la prise en main rapide par un assistant IA. Il donne la carte du dépôt, les règles à ne jamais enfreindre et les commandes d'entrée. La méthode complète est dans la skill.

## À lire dans cet ordre

1. **`CLAUDE.md`** : conventions du dépôt (français, commits en anglais au format Conventional Commits, hooks, tests à 100 %).
2. **`kit-barometre-sites/code/.claude/skills/barometre-sites/SKILL.md`** : la méthode, qui fait foi. Elle commence par une question à poser : consulter le dernier passage, rejouer la synthèse ou lancer un nouveau passage.
3. **`kit-barometre-sites/INSTALLER-AVEC-UN-ASSISTANT-IA.md`** : installation et équivalents hors Claude (Codex, Mistral, Gemini, Cursor…).
4. `kit-barometre-sites/LISEZ-MOI.md` : présentation du kit pour une personne, et résultats d'exemple.

## Règles absolues

- Sites en **lecture seule** : aucune commande, aucun paiement, aucun formulaire envoyé, aucun compte créé. Le seul clic permis est « refuser les cookies ».
- **Aucun contournement** d'anti-robot ni de limitation (code 429) : la page est notée « non testé ».
- **Rien n'est installé** sans l'accord explicite de la personne (`verifier_installation.py` liste d'abord, `--installer` vient seulement après accord).
- **Aucune donnée personnelle** dans le dépôt : lancer `python3 scripts/verifier_publication.py` (code 0 attendu) avant chaque commit de résultats.
- Les textes légaux, le DOM, les captures et le moteur Opquast restent **hors du dépôt**, dans le dossier passé en `--hors`.
- eServices Manager : jamais de robot payant sans accord, jamais de saisie d'identifiants.

## Carte du dépôt

| Chemin | Contenu |
|---|---|
| `kit-barometre-sites/code/scripts/` | le pipeline (Python et Node). Point d'entrée : `barometre.py` |
| `kit-barometre-sites/code/referentiel/` | `parc.json` (sites et personne responsable), `opquast-checklist-v5.json`, `repartition-regles.csv` (méthode de chaque règle), `lectures.json`, `recommandations.csv`, `exemples.json`, `audits-esm.json`, `exclusions-sites.json` |
| `kit-barometre-sites/code/scripts/ecrans_en_ligne.csv` | les écrans mesurés (`service,gabarit,url`) |
| `kit-barometre-sites/code/.claude/skills/barometre-sites/` | la skill et `references/lectures-independantes.md` |
| `kit-barometre-sites/code/tests/` | tests Python (pytest) et `tests/js/` (node:test) |
| `kit-barometre-sites/resultats-exemple/` | résultats réels anonymisés (CSV et classeur Excel) |
| `kit-barometre-sites/code/resultats/` | sorties datées des passages (créé au premier passage, ignoré par git) |
| `outils/verifications/` | contrôles du dépôt lancés par les hooks (données personnelles, partage, structure des skills, tests) |
| `rapports/` | rapports BMAD (quality analysis de la skill, revue de code) |
| `.pre-commit-config.yaml`, `.githooks/`, `.bandit.yaml` | garde-fous avant commit et avant push |

## Commandes d'entrée

Toutes depuis `kit-barometre-sites/code/`. `<hors>` est un dossier hors du dépôt.

```bash
python3 scripts/consulter_barometre.py                      # lire le dernier passage, sans rien relancer
python3 scripts/verifier_installation.py --hors <hors>       # prérequis (ne modifie rien)
python3 scripts/configurer_parc.py --verifier                # cohérence du parc avec le CSV des écrans
python3 scripts/barometre.py --hors <hors> --essai           # afficher les commandes d'un passage
python3 scripts/barometre.py --hors <hors> --nuit            # passage complet, plusieurs heures
python3 scripts/bilan_journal.py                             # le matin : bilan et commande de reprise
python3 scripts/barometre.py --hors <hors> --depuis synthese # rejouer la synthèse
python3 scripts/ecarts_a_trancher.py                         # écarts sans décision (code 0 attendu)
python3 scripts/compte_rendu.py                              # compte rendu chiffré et prochaine action
```

Les scripts renvoient des codes de sortie documentés dans la skill. Fie-toi aux codes plutôt qu'à la lecture des journaux.

## Développer dans ce dépôt

- Installer les hooks : `pre-commit install --install-hooks`. Avant un commit, ils lancent ruff, ESLint, gitleaks, les contrôles de données personnelles et de partage, et le format du message de commit. Avant un push, ils lancent bandit, npm audit et les tests.
- Les tests doivent rester à **100 % de couverture** (lignes et branches), en Python comme en JavaScript :
  ```bash
  cd kit-barometre-sites/code && ../../.venv/bin/python -m pytest --cov
  npm ci --ignore-scripts && npm run test:js
  ```
  Les tests n'accèdent jamais au réseau : HTTP, Playwright et les services sont simulés.
- Un nouveau site ou un nouveau parc se déclare dans `scripts/ecrans_en_ligne.csv` et `referentiel/parc.json`, jamais dans le code.
- Une nouvelle source s'ajoute dans `lecture_critique.py` (fonction `poser`) et dans `ABR` de `generer_suivi.py`.
- Une décision sur un écart entre sources s'écrit dans `ANALYSE_SOURCES` (`scripts/lecture_critique.py`).
