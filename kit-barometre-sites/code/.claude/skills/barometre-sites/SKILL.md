---
name: barometre-sites
description: Baromètre qualité des sites e-commerce de Mattea (formation Opquast, Colorz) — relance toute la mesure des 6 boutiques Shopify sur les 245 règles Opquast V5 (scripts réseau et page, outils libres axe, IBM, Alfa, Sa11y, Pa11y, html-validate, Lighthouse, moteur Opquast devtools, relevé navigateur, données publiques Shopify, lectures IA indépendantes à preuve vérifiée), recoupe au moins deux sources par règle, tranche les écarts selon le protocole Opquast, puis sort la page de suivi publiée en Artifact et un CSV détaillé (une ligne par règle et par site) avec les scores. Utiliser dès qu'on parle de relancer, rejouer, mettre à jour ou refaire le baromètre des sites, un nouveau passage, les scores Opquast des boutiques, le CSV ou le rapport du baromètre, ou /barometre-sites, même sans dire « skill ».
---

# Baromètre qualité des sites

Un objectif de contrôle : le **taux de conformité Opquast V5** de chaque boutique, conformes ÷ (conformes + non conformes), note A (90 et plus) à E (moins de 50). Les outils ne comptent pas à part : ils servent à confirmer ou contredire chaque statut (au moins **deux sources indépendantes par règle**, 92 % atteints le 13/11/2026).

Périmètre : `scripts/ecrans_en_ligne.csv` (6 boutiques, 47 écrans). Règles mesurées et volets : `referentiel/repartition-regles.csv` (204 mesurées, 41 écartées avec leur raison). Retraits par site : `referentiel/exclusions-sites.json`.

## Règles à ne jamais enfreindre

- Sites clients en production : **aucune commande, aucun paiement, aucun envoi de formulaire, aucune création de compte**. Ajouter un article au panier et afficher la page de paiement sans rien saisir est admis.
- **Aucun contournement** de vérification anti-robot ou de limitation (429) : la page est notée « non testé » avec la raison.
- Seul clic autorisé sur un site : **refuser les cookies** (choix le plus protecteur).
- **Aucune donnée personnelle** dans le dépôt, les rapports ou les commentaires ESM : noms, e-mails, téléphones masqués (les scripts le font ; vérifier avant chaque commit avec `scripts/verifier_publication.py`, voir la section Publication).
- Textes légaux, DOM, captures et moteur Opquast restent **hors du dépôt**, dans le dossier `--hors` (le dossier temporaire de session est vidé entre deux sessions).
- eServices Manager : **jamais de robot payant** sans l'accord de Mattea ; ne jamais saisir ses identifiants (elle se connecte elle-même dans le volet navigateur).
- Aucun tiret long « — » dans les livrables. Commit et push après chaque étape terminée.

## Prérequis et installation (sur n'importe quel ordinateur)

Avant le premier passage sur un ordinateur, et à chaque fois que `barometre.py` s'arrête avec le code 3 :

1. Lancer `python3 scripts/verifier_installation.py --hors <dossier>`. Il ne modifie rien et liste ce qui est présent ou manquant :
   - Node.js 22 ou plus et npm ;
   - les paquets npm du projet, versions épinglées dans `package.json` et `package-lock.json` : Playwright, axe-core, IBM accessibility-checker, Lighthouse, Pa11y, html-validate, Siteimprove Alfa, Sa11y, moteurs QualWeb, linkinator ;
   - le navigateur Chromium de Playwright ;
   - Python 3.10 ou plus et l'environnement `.venv`, avec REDbot, openpyxl et checkdmarc (`requirements.txt`) ;
   - les outils système git, curl, dig, xmllint, et pdftotext, pdftoppm, pdfinfo (poppler) ;
   - le moteur libre Opquast devtools, cloné et construit par l'étape « moteur ».
2. S'il manque quelque chose, **ne rien installer de soi-même**. Montrer à la personne la liste exacte : chaque élément, à quoi il sert dans le baromètre, et la commande qui l'installera. Lui demander son accord explicite, avec AskUserQuestion : tout installer, installer seulement une partie, ou ne rien installer.
3. Après son accord seulement : `python3 scripts/verifier_installation.py --installer`, ou les seules commandes acceptées.
   - Les paquets npm s'installent avec `npm ci --ignore-scripts`, sans exécuter leurs scripts d'installation, aux versions du fichier de verrouillage.
   - Chromium s'installe avec `npx playwright install chromium`.
   - Les outils système passent par Homebrew sur macOS ou apt sur Linux, et peuvent demander le mot de passe de la personne : c'est elle qui le saisit.
4. Relancer la vérification et donner le résultat.

Ne jamais ajouter d'outil hors de cette liste sans le présenter d'abord : qui le maintient, sa licence, sa date de publication (au moins deux semaines), et ce qu'il apporte en sources. Restent écartés : QualWeb complet (il embarque un module de contournement des anti-robots), emailens et les outils e-mail d'Intopia (trop jeunes).

Hors de l'ordinateur, vérifier aussi dans Claude :
- le connecteur MCP Opquast, qui donne le protocole des règles (ToolSearch « opquast ») ;
- l'accès à eServices Manager : la personne se connecte elle-même dans le volet navigateur.

## Déroulé

`scripts/barometre.py` enchaîne tout ce qui est automatique. Un passage complet dure plusieurs heures : une requête toutes les 6 à 10 s par site.

**Proposer de le lancer la nuit** (AskUserQuestion : « ce soir, en mode nuit » ou « maintenant »). Avant un passage de nuit, rappeler à la personne de :
- brancher l'ordinateur sur secteur : le mode nuit s'arrête sur batterie ;
- laisser le capot ouvert ou brancher un écran externe ;
- garder une connexion stable ;
- repousser les mises à jour et redémarrages automatiques ;
- fermer les applications lourdes.

```bash
python3 scripts/barometre.py --hors "<dossier temporaire>/hors" --nuit
```

`--nuit` vérifie le secteur, bloque la mise en veille pendant tout le passage (macOS : `caffeinate -dimsu` ; Linux : `systemd-inhibit` ; Windows : régler l'alimentation sur « jamais » à la main) et écrit tout dans `resultats/journal-barometre-<date>.log`. Le matin : lire le journal, reprendre une étape en échec avec `--depuis`, puis faire les lectures indépendantes et la synthèse. En journée, le même passage sans `--nuit`, lancé en arrière-plan.

Pour installer et lancer le baromètre avec un autre assistant IA (Mistral, Codex, Gemini, Cursor…), suivre `INSTALLER-AVEC-UN-ASSISTANT-IA.md`, dans ce dossier.

Options : `--etapes synthese` (seulement le rapport et le CSV, quelques secondes), `--depuis sources` (reprise après un échec), `--service "Boutique A"` (un site), `--essai` (affiche les commandes), `--continuer` (ne s'arrête pas sur un échec).

| Étape | Ce qu'elle fait | Sorties |
|---|---|---|
| referentiel | répartit les 245 règles en volets | `referentiel/repartition-regles.csv` |
| moteur | clone et construit le moteur libre Opquast devtools s'il manque (hors dépôt) | `<hors>/opquast-devtools/public/engine` |
| mesure | réseau, code de la page, W3C i18n, REDbot, axe-core, IBM et Lighthouse, Pa11y et sitemap, aria | `resultats/{reseau,page,i18n,redbot,axe,outils,aria}-<date>/` |
| releve | relevé navigateur (mesures, pages légales, impression, 404, panier), parcours sans commande, décisions | `resultats/releve-<date>/decisions.json` |
| sources | deuxièmes sources : axe et IBM complémentaires, Shopify public, HTML brut et CSS, curl, API panier, outils tiers | `resultats/sources-<date>/*.json` |
| synthese | vérifie les citations, fusionne, recoupe, tranche, génère la page et les CSV | `suivi-barometre.html`, `resultats/barometre-<date>/` (barometre, tests, scores) |

Après `sources`, les étapes qui demandent Claude ou ESM se font **dans cet ordre** (la lecture 3 dépend de la première synthèse) :

1. **En parallèle** : lancer en arrière-plan les lectures IA 1 (textes légaux) et 2 (captures) décrites dans `references/lectures-independantes.md`, deux lots de trois sites chacun, et pendant ce temps la première synthèse : `python3 scripts/barometre.py --hors <hors> --etapes synthese`. Les sous-agents ne lisent jamais `resultats/` (indépendance).
2. **Règles à une seule source** : `python3 scripts/regles_une_source.py <hors>` écrit `<hors>/regles_une_source.json`, la liste par site des règles restées à moins de deux sources.
3. **Lecture 3** (DOM, captures et paiement) : lancer les sous-agents sur cette liste seulement.
4. **Synthèse finale** : quand les trois lectures sont rendues, relancer `--etapes synthese`. Une réponse « conforme » d'une lecture IA n'est retenue que si sa citation ou son extrait est retrouvé mot pour mot (`scripts/verifier_citations.py`, lancé par la synthèse).

**Robot Opquast basics d'eServices Manager** : réutiliser le dernier export (`resultats/esm-basics-*`) tant qu'aucun nouvel audit basics n'a été lancé. Un nouvel audit ne se lance qu'avec l'accord de Mattea.

**Sans eServices Manager** (kit neuf, ou ESM non utilisé) : la synthèse tourne quand même. Les verdicts du robot et les liens vers les audits sont absents, la fiche de contre-examen part de constats vides et les règles concernées restent « non testé » ou « à vérifier ». Le dire dans le compte rendu.

## Trancher les écarts

`lecture_critique.py` confronte toutes les sources règle par règle. Un écart (une source dit conforme, une autre non conforme) se tranche avec quatre questions, toujours dans cet ordre :

1. **Que demande la règle ?** Relire le protocole (`get_rule` du MCP Opquast, format `detailed`). Exemple : règle 124, toute vidéo à démarrage automatique, même muette.
2. **Qu'a regardé chaque source ?** Code ou page affichée, une page ou tous les écrans, identité de robot ou de navigateur.
3. **Que vit l'utilisateur ?** Retenir la source qui observe ce que voit et fait un visiteur plutôt qu'un indice dans le code.
4. **Reste-t-il une interprétation ?** Le statut suit le protocole et l'écart est marqué « à arbitrer par Mattea » (ex. fenêtre cookies bloquante, règle 153).

On ne fait jamais voter les outils. Chaque décision est écrite dans `ANALYSE_SOURCES` (`scripts/lecture_critique.py`) : type d'écart, statut retenu, pourquoi, que faire. Après l'étape `synthese`, la liste des écarts sans décision doit être vide :

```bash
python3 -c "import json,glob;d=json.load(open(sorted(glob.glob('resultats/lecture-critique-*/lecture.json'))[-1]));print([(s,e['regle']) for s,v in d.items() if not s.startswith('_') for e in v['ecarts'] if e['statut'] not in ('C','NC','NA') and e['regle']!='-'])"
```

Une nouvelle source s'ajoute dans `lecture_critique.py` (fonction `poser`) et dans `ABR` de `generer_suivi.py` (colonne de la matrice).

## Publication

1. **Données personnelles** : `python3 scripts/verifier_publication.py` doit sortir avec le code 0. Il lit les dossiers du **dernier passage** (la date la plus récente de `resultats/`, même si le passage de nuit a commencé la veille) et `suivi-barometre.html`. Code 1 : une adresse e-mail ou un téléphone a été trouvé, le masquer avant tout commit. Code 2 : aucun fichier n'a été lu, la vérification n'a pas eu lieu. Le relancer avant **chaque** commit.
2. **Page** : publier `suivi-barometre.html` avec l'outil Artifact sur la même adresse que le suivi existant pour garder le lien. Cette adresse est propre au compte qui publie : elle se lit dans `liens-locaux.json` (hors dépôt, entrée « Suivi du baromètre »), jamais dans les fichiers du kit. Si l'entrée n'existe pas (premier passage sur ce compte), publier une nouvelle page, puis noter son adresse dans `liens-locaux.json` ({"titre": "Suivi du baromètre", "url": "…", "detail": ""}) pour les passages suivants.
3. **CSV** : envoyer à Mattea, avec SendUserFile, les trois fichiers de `resultats/barometre-<date>/` : `barometre.csv` (une ligne par règle et par site, une colonne par type d'audit avec son verdict, puis le statut retenu et la décision), `tests.csv` (tous les tests effectués : une ligne par règle, site et audit, avec la famille d'audit, le verdict, la décision retenue, l'accord ou non avec elle et la raison quand l'audit a été contredit) et `scores.csv`. Séparateur « ; », UTF-8 avec BOM : s'ouvrent tels quels dans Excel.
4. **eServices Manager** : reporter les statuts du relevé qui ont changé (audits « règles complémentaires » de `referentiel/audits-esm.json`) ; une règle absente d'un audit en cours va dans un nouvel audit « règles complémentaires N » (sélection ad hoc des critères, page d'accueil seule). Mattea doit être connectée.
5. **Note de cadrage** : mettre à jour les chiffres (`note_cadrage.md`, une page A4 : `python3 scripts/verifier_page_a4.py`).
6. **Commit et push** sur le dépôt personnel, après un dernier `python3 scripts/verifier_publication.py` à 0, puis dire à Mattea : scores et notes par site, part des statuts à deux sources ou plus, écarts tranchés et à arbitrer, ce qui n'a pas pu être mesuré et pourquoi.

## Fichiers utiles

- `scripts/barometre.py` : l'enchaînement. `scripts/verifier_publication.py` : contrôle des données personnelles avant commit et publication. `scripts/regles_une_source.py` : liste des règles à une seule source, pour la lecture 3. `scripts/exporter_csv.py` : les trois CSV (détail par règle avec une colonne par type d'audit, tous les tests avec leur décision, scores).
- `references/lectures-independantes.md` : consignes des sous-agents de lecture.
- `referentiel/recommandations.csv` et `referentiel/exemples.json` : une recommandation et un exemple clé en main par règle non conforme.
