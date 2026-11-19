# Installer et lancer le baromètre qualité des sites avec n'importe quel assistant IA

Ce fichier s'adresse à l'assistant IA qui va installer et faire tourner le baromètre : Claude (Claude Code, Claude Desktop), Mistral (Le Chat, Vibe, Codestral), OpenAI Codex, Gemini CLI, Cursor, Copilot ou tout autre agent qui sait lire des fichiers et lancer des commandes dans un terminal. La personne qui vous le donne est votre utilisatrice ou utilisateur : lisez tout le fichier avant d'agir, puis suivez les étapes dans l'ordre.

## Ce qu'est le baromètre

Une mesure répétable de la qualité de sites web (au départ des boutiques Shopify) selon les **245 règles Opquast V5**. Un seul indicateur par site : le **taux de conformité**, conformes ÷ (conformes + non conformes), noté de A (90 et plus) à E (moins de 50). Chaque statut repose sur **au moins deux sources indépendantes** : scripts, outils libres d'accessibilité et de qualité, moteur libre Opquast, relevé dans le navigateur, lectures IA à preuve vérifiée, contre-examen humain. Quand les sources se contredisent, une décision écrite tranche selon le protocole Opquast. Livrables : une page HTML de suivi et trois CSV (`barometre.csv`, `tests.csv`, `scores.csv`).

Le mode d'emploi détaillé est `SKILL.md`, dans le même dossier que ce fichier : il fait foi pour le déroulé, les règles de décision et la publication. Ce fichier-ci explique comment l'installer chez vous, quel que soit l'assistant.

## Règles absolues (à respecter quel que soit l'assistant)

1. **Rien n'est installé sans l'accord explicite de la personne.** Vous listez d'abord ce qui manque, à quoi ça sert et la commande prévue, puis vous attendez son oui.
2. **Sites en production : lecture seule.** Aucune commande, aucun paiement, aucun envoi de formulaire, aucune création de compte. Le seul clic autorisé est le refus des cookies.
3. **Aucun contournement** de vérification anti-robot, de captcha ou de limitation de débit (code 429) : la page est notée « non testé », avec la raison.
4. **Aucune donnée personnelle** (noms, e-mails, téléphones) dans les résultats, les rapports ou Git : les scripts masquent, vous vérifiez avant chaque publication.
5. Vous ne saisissez **jamais un mot de passe** à la place de la personne et ne lancez **aucun robot payant** (eServices Manager ou autre) sans son accord.

## Étape 1 : récupérer le code

Le dossier `code/` du kit (ou le dépôt Git qu'on vous a donné) contient `scripts/`, `referentiel/`, `package.json`, `package-lock.json`, `requirements.txt` et la skill (`.claude/skills/barometre-sites/`). Placez-vous à sa racine pour toutes les commandes.

## Étape 2 : prérequis, vérifiés puis installés avec accord

```bash
python3 scripts/verifier_installation.py --hors ../hors
```

Le script ne modifie rien. Il vérifie : Node.js 22 ou plus et npm, les paquets npm épinglés (Playwright, axe-core, IBM accessibility-checker, Lighthouse, Pa11y, html-validate, Siteimprove Alfa, Sa11y, moteurs QualWeb, linkinator), le navigateur Chromium de Playwright, Python 3.10 ou plus avec `.venv` (REDbot, openpyxl, checkdmarc), git, curl, dig, xmllint, pdftotext, pdftoppm, pdfinfo (poppler), et le moteur libre Opquast devtools.

S'il manque quelque chose : montrez la liste à la personne, demandez son accord (tout, une partie ou rien), puis seulement :

```bash
python3 scripts/verifier_installation.py --installer
```

Il lance `npm ci --ignore-scripts` (versions du fichier de verrouillage, sans scripts d'installation), `npx playwright install chromium`, `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, et les outils système par Homebrew (macOS) ou apt (Linux). Sous Windows, passez par WSL (Ubuntu). Si un mot de passe est demandé, c'est la personne qui le tape. Relancez ensuite la vérification.

## Étape 3 : adapter le baromètre aux sites de la personne

Le code a été écrit pour un parc de six boutiques, anonymisées ici en « Boutique A » à « Boutique F ». Remplacez-les par les sites de la personne. Demandez-lui la liste, et vérifiez qu'elle a le droit de les auditer.

| Fichier | À faire |
|---|---|
| `scripts/ecrans_en_ligne.csv` | une ligne par écran : `service,gabarit,url` (accueil, collection, fiche produit, panier, recherche, compte, pages de contenu ; l'accueil en premier) |
| `scripts/etat_barometre.py` (`SITES`), `scripts/fusion_scripts.py` (`SERVICES`), `scripts/generer_suivi.py` (`SERVICES`), `scripts/import_esm.py` (`SERVICES`), `scripts/generer_schema.py` (`SITES`) | remplacer les six boutiques par les sites de la personne (nom affiché, code court) |
| `referentiel/audits-esm.json` | identifiants des audits eServices Manager, si la personne utilise ESM ; sinon laisser le modèle |
| `referentiel/exclusions-sites.json` | règles retirées pour un site donné, avec la raison (au départ : vide) |
| `scripts/lecture_critique.py` (`ANALYSE_SOURCES`) | décisions propres aux anciens sites : garder les lignes `("*", …)` (générales), retirer celles qui nomment une boutique |

Faites un essai à blanc : `python3 scripts/barometre.py --hors ../hors --essai`.

## Étape 4 : installer la skill dans votre outil

Le contenu de la skill (`SKILL.md` et `references/`) est du Markdown ordinaire : chaque outil le charge à sa façon.

| Assistant | Où mettre la skill |
|---|---|
| Claude Code, Claude Desktop | laisser `.claude/skills/barometre-sites/` à la racine du projet ; la skill se déclenche sur « relancer le baromètre » ou `/barometre-sites` |
| Claude.ai (web) | zipper le dossier `barometre-sites` et l'ajouter dans Réglages, Capacités, Skills |
| OpenAI Codex, et tout outil qui lit `AGENTS.md` | `AGENTS.md` à la racine (fourni dans le kit) renvoie vers `SKILL.md` |
| Mistral (Le Chat, Vibe) | coller le contenu de `SKILL.md` dans les instructions de l'agent ou du projet, et joindre `references/` ; Vibe lit aussi `AGENTS.md` |
| Gemini CLI | copier `AGENTS.md` en `GEMINI.md` à la racine |
| Cursor, Copilot, autres | ajouter `SKILL.md` aux règles du projet (`.cursor/rules/`, `.github/copilot-instructions.md`) ou aux instructions système |

Ce qui est propre à Claude dans `SKILL.md`, et son équivalent ailleurs :

| Dans SKILL.md | Ailleurs |
|---|---|
| sous-agents en arrière-plan (outil Agent) pour les lectures indépendantes | une nouvelle conversation ou un autre agent qui ne voit QUE les fichiers d'entrée (jamais `resultats/`) ; c'est cette séparation qui rend la lecture indépendante |
| connecteur MCP Opquast (`get_rule`) pour le protocole d'une règle | la page publique de la règle : `https://checklists.opquast.com/fr/qualite-numerique/<slug>` (slug dans `referentiel/opquast-checklist-v5.json`) ; liste des règles sans clé : `https://api.opquast.com/checklist/public/` |
| publication en Artifact | ouvrir `suivi-barometre.html` dans un navigateur, ou le déposer sur un hébergement privé |
| SendUserFile | donner le chemin de `resultats/barometre-<date>/` |
| AskUserQuestion | poser la question dans la conversation et attendre la réponse |

## Étape 5 : lancer le passage, de préférence la nuit

Un passage complet dure plusieurs heures : chaque site reçoit au plus une requête toutes les 6 à 10 secondes. Proposez à la personne de le lancer le soir et rappelez-lui de :

- **brancher l'ordinateur sur secteur** : le script s'arrête sur batterie ;
- laisser le capot ouvert, ou brancher un écran externe ;
- garder une connexion stable (Wi-Fi fiable ou câble) et ne pas couper le VPN si les sites l'exigent ;
- repousser les mises à jour système et les redémarrages automatiques de la nuit ;
- fermer les applications lourdes (le passage ouvre un navigateur Chromium sans fenêtre).

```bash
python3 scripts/barometre.py --hors ../hors --nuit
```

`--nuit` bloque la mise en veille (macOS : `caffeinate -dimsu` ; Linux : `systemd-inhibit` ; Windows : régler l'alimentation sur « jamais » ou utiliser PowerToys Awake) et écrit tout dans `resultats/journal-barometre-<date>.log`. Le lendemain matin : lire le journal, reprendre une étape en échec avec `--depuis <étape>`, puis faire les lectures indépendantes (référence `references/lectures-independantes.md`) et la synthèse :

```bash
python3 scripts/barometre.py --hors ../hors --etapes synthese
```

## Étape 6 : trancher, vérifier, livrer

Suivez les sections « Trancher les écarts » et « Publication » de `SKILL.md` : chaque écart entre sources reçoit une décision écrite (quatre questions : que demande la règle, qu'a regardé chaque source, que vit l'utilisateur, reste-t-il une interprétation), la liste des écarts sans décision doit être vide, les données personnelles sont vérifiées, puis vous remettez la page et les trois CSV. Terminez par un compte rendu : scores et notes, part des statuts à deux sources ou plus, écarts tranchés et à arbitrer, ce qui n'a pas pu être mesuré et pourquoi.
