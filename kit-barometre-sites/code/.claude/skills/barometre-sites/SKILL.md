---
name: barometre-sites
description: Baromètre qualité Opquast d'un parc de sites e-commerce (referentiel/parc.json, scripts/ecrans_en_ligne.csv). Consulte le dernier passage, rejoue la synthèse ou relance toute la mesure des sites du parc sur les 245 règles Opquast V5 (scripts réseau et page, outils libres axe, IBM, Alfa, Sa11y, Pa11y, html-validate, Lighthouse, moteur Opquast devtools, relevé navigateur, données publiques Shopify, lectures IA indépendantes à preuve vérifiée), recoupe au moins deux sources par règle, tranche les écarts selon le protocole Opquast, puis sort la page de suivi publiée en Artifact, les CSV (détail, tests, scores avec l'évolution, changements) et un compte rendu chiffré. Utiliser dès qu'on parle du baromètre des sites, de relancer, rejouer ou mettre à jour un passage, des scores Opquast d'un site, du CSV, du rapport ou de l'évolution du baromètre, ou de /barometre-sites, même sans dire « skill ».
---

# Baromètre qualité des sites

Un objectif de contrôle : le **taux de conformité Opquast V5** de chaque site, conformes ÷ (conformes + non conformes), note A (90 et plus) à E (moins de 50). Les outils ne comptent pas à part : ils servent à confirmer ou contredire chaque statut (au moins **deux sources indépendantes par règle** ; la part atteinte est donnée par le compte rendu).

Périmètre : `scripts/ecrans_en_ligne.csv` (les écrans) et `referentiel/parc.json` (les sites et la personne responsable, voir « Adapter le kit à un autre parc »). Règles mesurées et volets : `referentiel/repartition-regles.csv`, chaque règle écartée avec sa raison. Retraits par site : `referentiel/exclusions-sites.json`.

Dans cette skill, « la personne responsable » est le `responsable` de `referentiel/parc.json` : elle valide les décisions, arbitre les écarts et reçoit les livrables.

## Règles à ne jamais enfreindre

- Sites clients en production : **aucune commande, aucun paiement, aucun envoi de formulaire, aucune création de compte**. Ajouter un article au panier et afficher la page de paiement sans rien saisir est admis.
- **Aucun contournement** de vérification anti-robot ou de limitation (429) : la page est notée « non testé » avec la raison.
- Seul clic autorisé sur un site : **refuser les cookies** (choix le plus protecteur).
- **Aucune donnée personnelle** dans le dépôt, les rapports ou les commentaires ESM : noms, e-mails, téléphones masqués (les scripts le font ; vérifier avant chaque commit avec `scripts/verifier_publication.py`, voir la section Publication).
- Textes légaux, DOM, captures et moteur Opquast restent **hors du dépôt**, dans le dossier `--hors` (le dossier temporaire de session est vidé entre deux sessions).
- eServices Manager : **jamais de robot payant** sans l'accord de la personne responsable ; ne jamais saisir ses identifiants (elle se connecte elle-même dans le volet navigateur).
- Aucun tiret long « — » dans les livrables. Commit et push après chaque étape terminée.

## D'abord : que veut faire la personne ?

Demander avec AskUserQuestion, avant toute autre chose. Un nouveau passage dure plusieurs heures : ne pas le lancer si la personne veut seulement voir les résultats.

- **Consulter le dernier passage** (rien n'est relancé, quelques secondes) :
  ```bash
  python3 scripts/consulter_barometre.py                       # tous les sites
  python3 scripts/consulter_barometre.py --site "Nom du site"  # un seul site
  python3 scripts/consulter_barometre.py --regle 12            # une règle, pour chaque site
  ```
  Pour chaque site : date du dernier passage, score et note, évolution depuis le passage précédent, règles non conformes et leur recommandation. Avec `--regle` : statut retenu, statut au passage précédent et recommandation. Code 0 : tout va bien. Code 1 : aucun passage, proposer un nouveau passage. Code 2 : site ou règle absents de tous les passages. Répondre en phrases simples, sans rien publier ni commiter.
- **Rejouer la synthèse** (mesures gardées, quelques minutes) : `python3 scripts/barometre.py --hors "<dossier temporaire>/hors" --depuis synthese`, puis la partie Publication. Utile après une correction, un arbitrage ou une lecture ajoutée.
- **Lancer un nouveau passage** (plusieurs heures) : suivre la suite, à partir de « Prérequis et installation ».

## Prérequis et installation (sur n'importe quel ordinateur)

Avant le premier passage sur un ordinateur, et à chaque fois que `barometre.py` s'arrête avec le code 3 :

1. Lancer `python3 scripts/verifier_installation.py --hors <dossier>`. Il ne modifie rien et liste ce qui est présent ou manquant :
   - Node.js 22 ou plus et npm ;
   - les paquets npm du projet, versions épinglées dans `package.json` et `package-lock.json` : Playwright, axe-core, IBM accessibility-checker, Lighthouse, Pa11y, html-validate, Siteimprove Alfa, Sa11y, moteurs QualWeb, linkinator ;
   - le navigateur Chromium de Playwright ;
   - Python 3.10 ou plus et l'environnement `.venv`, avec REDbot, openpyxl et checkdmarc (`requirements.txt`) ;
   - les outils système git, curl, dig, xmllint, et pdftotext, pdftoppm, pdfinfo (poppler) ;
   - le moteur libre Opquast devtools (avec `--hors` seulement), cloné et construit par l'étape « moteur ».
2. S'il manque quelque chose, **ne rien installer de soi-même**. Montrer à la personne la liste exacte : chaque élément, à quoi il sert dans le baromètre, et la commande qui l'installera. Lui demander son accord explicite, avec AskUserQuestion : tout installer, installer seulement une partie, ou ne rien installer.
3. Après son accord seulement : `python3 scripts/verifier_installation.py --hors <dossier> --installer`, ou les seules commandes acceptées.
   - Les paquets npm s'installent avec `npm ci --ignore-scripts`, sans exécuter leurs scripts d'installation, aux versions du fichier de verrouillage.
   - Chromium s'installe avec `npx playwright install chromium`.
   - Les outils système passent par Homebrew sur macOS ou apt sur Linux, et peuvent demander le mot de passe de la personne : c'est elle qui le saisit.
4. Relancer la vérification et donner le résultat.

Ne jamais ajouter d'outil hors de cette liste sans le présenter d'abord : qui le maintient, sa licence, sa date de publication (au moins deux semaines), et ce qu'il apporte en sources. Restent écartés : QualWeb complet (il embarque un module de contournement des anti-robots), emailens et les outils e-mail d'Intopia (trop jeunes).

Hors de l'ordinateur, vérifier aussi dans Claude :
- le connecteur MCP Opquast, qui donne le protocole des règles (ToolSearch « opquast ») ;
- l'accès à eServices Manager, s'il est utilisé : la personne se connecte elle-même dans le volet navigateur.

## Adapter le kit à un autre parc

Le parc tient dans deux fichiers ; aucun script ne contient de nom de site ni de personne.

- `scripts/ecrans_en_ligne.csv` : les écrans à mesurer (colonnes `service`, `gabarit`, `url`). Un service est un site.
- `referentiel/parc.json` : un objet par site, dans l'ordre du CSV, plus `responsable` et `auditeur_esm` (code court de la personne dans eServices Manager, utilisé par `import_esm.py`).

| Champ d'un site | Rôle | Par défaut |
|---|---|---|
| `nom` | identique à la colonne `service` du CSV | nom du service |
| `code_esm` | code du service dans eServices Manager | `WEB-<NOM>` |
| `prefixe_pages` | préfixe des codes de page ESM et des écrans e-mail `<PREFIXE>-EM-…` | initiales du nom |
| `plateforme` | `shopify` ou autre ; les sources Shopify ne tournent que sur `shopify` | `shopify` |
| `compte_client_hors_site` | compte client hébergé hors du site : `/account` noté « non testé » | vrai sur Shopify |
| `prefixe_langue` | `/fr` si la version auditée est sous un préfixe de langue | lu dans l'adresse de l'accueil |
| `compte_email` | compte e-mail associé (onglet e-mail du suivi), vide sinon | vide |

Pour un nouveau parc :

1. Remplir `scripts/ecrans_en_ligne.csv` (mêmes gabarits sur chaque site si possible).
2. `python3 scripts/configurer_parc.py --responsable "Prénom Nom" --auditeur-esm ABC` crée ou complète `referentiel/parc.json` (valeurs déjà saisies gardées, champs manquants remplis par défaut).
3. Relire `parc.json` : surtout `code_esm` et `prefixe_pages` s'ils diffèrent des codes d'eServices Manager, `plateforme` hors Shopify, `compte_email` si les e-mails sont audités.
4. `python3 scripts/configurer_parc.py --verifier` (n'écrit rien) : 0 cohérent ; 1 incohérence (site absent d'un côté, nom, code ou préfixe en double, champ manquant), une ligne « INCOHÉRENCE » par problème ; 2 CSV absent ou parc illisible. Le relancer après chaque modification du CSV.

Les scripts Node lisent le même fichier (`scripts/parc.mjs` ; `BAROMETRE_PARC=<chemin>` pour un autre parc). Facultatif : copier `referentiel/suivi-complements.exemple.json` en suivi-complements.json (même dossier) ajoute à la page de suivi l'historique propre à une mission (tests d'accès, « Fait » et « À faire », liens, scores basics, jalons) ; format dans la docstring de `charger_complements` (`scripts/generer_suivi.py`).

## Déroulé d'un nouveau passage

`scripts/barometre.py` enchaîne tout ce qui est automatique. Un passage complet dure plusieurs heures : une requête toutes les 6 à 10 s par site.

**Proposer de le lancer la nuit** (AskUserQuestion : « ce soir, en mode nuit » ou « maintenant »). Avant un passage de nuit, rappeler à la personne de :
- brancher l'ordinateur sur secteur : le mode nuit s'arrête sur batterie (`--forcer` le lance quand même, à éviter) ;
- laisser le capot ouvert ou brancher un écran externe ;
- garder une connexion stable ;
- repousser les mises à jour et redémarrages automatiques ;
- fermer les applications lourdes.

```bash
python3 scripts/barometre.py --hors "<dossier temporaire>/hors" --nuit
```

`--nuit` vérifie le secteur, bloque la mise en veille pendant tout le passage (macOS : `caffeinate -dimsu` ; Linux : `systemd-inhibit` ; Windows : régler l'alimentation sur « jamais » à la main) et écrit tout dans `resultats/journal-barometre-<date>.log`. La nuit, `--continuer` est actif par défaut : un échec sur un site n'arrête pas le reste (`--arreter` rétablit l'arrêt au premier échec). En journée, le même passage sans `--nuit`, lancé en arrière-plan.

À chaque commande, `barometre.py` réécrit l'état du passage dans `resultats/etat-passage-<date>.json` : étapes, commandes, codes, durées, échecs et commande de reprise exacte. Après un compactage ou le lendemain, reprendre depuis ce fichier, pas de mémoire. Codes de sortie : 0 tout a réussi ; le code de la commande en échec (arrêt au premier échec) ; 1 avec `--continuer` et au moins un échec ; 2 étape inconnue ; 3 prérequis manquants ; 4 sur batterie avec `--nuit`.

Pour un autre assistant IA (Mistral, Codex, Gemini, Cursor…), suivre `INSTALLER-AVEC-UN-ASSISTANT-IA.md`, dans ce dossier : il reprend les mêmes commandes ; cette skill fait foi.

Options : `--etapes synthese` (seulement le rapport et les CSV), `--depuis sources` (reprise après un échec), `--service "<nom du site>"` (un site, nom tel qu'il figure dans le CSV), `--essai` (affiche les commandes), `--continuer`, `--arreter`, `--forcer`.

| Étape | Ce qu'elle fait | Sorties |
|---|---|---|
| referentiel | répartit les 245 règles en volets | `referentiel/repartition-regles.csv` |
| moteur | clone et construit le moteur libre Opquast devtools s'il manque (hors dépôt) | `<hors>/opquast-devtools/public/engine` |
| mesure | réseau, code de la page, W3C i18n, REDbot, axe-core, IBM et Lighthouse, Pa11y et sitemap, aria | `resultats/{reseau,page,i18n,redbot,axe,outils,aria}-<date>/` |
| releve | relevé navigateur (mesures, pages légales, impression, 404, panier), parcours sans commande, décisions | `resultats/releve-<date>/decisions.json` |
| sources | deuxièmes sources : axe et IBM complémentaires, Shopify public (sites `shopify` seulement), HTML brut et CSS, curl, API panier, outils tiers | `resultats/sources-<date>/*.json` |
| synthese | vérifie les citations et les sorties des lectures IA (`valider_lectures.py`), fusionne, recoupe, tranche, génère la page, les CSV, puis liste les règles à une seule source | `suivi-barometre.html`, `resultats/barometre-<date>/`, `<hors>/regles_une_source.json` |

### Le matin

Ne jamais lire le journal de nuit en entier. Dans cet ordre :

1. **Bilan** : `python3 scripts/bilan_journal.py`. Il affiche le bloc final : étapes faites, échecs avec leur commande, commande de reprise exacte (`--depuis`). Code 0 : tout a réussi. Code 1 : au moins un échec, lancer la commande « Reprise » affichée. Code 2 : aucun passage. Code 3 : passage non terminé (en cours ou interrompu). `--journal` ou `--etat` pour choisir un fichier.
2. **Lectures IA indépendantes**, dans l'ordre ci-dessous.
3. **Écarts** : `python3 scripts/ecarts_a_trancher.py` doit sortir à 0 (voir « Trancher les écarts »).
4. **Publication** et compte rendu. En cas de doute sur l'étape où l'on en est, `python3 scripts/compte_rendu.py` affiche la prochaine action.

### Lectures IA indépendantes

Le détail est dans `references/lectures-independantes.md` ; listes de règles, entrées et formats dans `referentiel/lectures.json`. Les sous-agents ne lisent jamais `resultats/` (indépendance) et rendent un bilan de 15 lignes au plus.

1. **Briefs des lectures 1 et 2** : `python3 scripts/preparer_lectures.py <hors>` écrit un brief par sous-agent dans `<hors>/briefs/` (lecture 1 : lots de trois sites ; lecture 2 : un site par sous-agent). Code 1 : une entrée manque (textes ou captures), le brief le signale.
2. **Lectures 1 et 2** : lancer en arrière-plan un sous-agent par brief, en passant le brief tel quel.
3. **Attendre** que tous soient rendus, puis `python3 scripts/valider_lectures.py <hors> --exiger 1,2`. Code 1 : corriger ou relancer le sous-agent fautif, puis revalider jusqu'au code 0.
4. **Synthèse** : `python3 scripts/barometre.py --hors <hors> --etapes synthese`. Elle écrit elle-même `<hors>/regles_une_source.json`, la liste par site des règles restées à moins de deux sources (à la main : `python3 scripts/regles_une_source.py <hors>`).
5. **Lecture 3** (DOM, captures et paiement) : `python3 scripts/preparer_lectures.py <hors> --lecture 3`, puis un sous-agent par site (un site sans règle à une source n'a pas de brief).
6. **Validation** : `python3 scripts/valider_lectures.py <hors> --exiger 1,2,3` jusqu'au code 0.
7. **Synthèse finale** : relancer `--etapes synthese`. Une réponse « conforme » n'est retenue que si sa citation ou son extrait est retrouvé mot pour mot (`verifier_citations.py`) ; une entrée invalide (site inconnu, règle hors liste, preuve hors format) est écartée par `lecture_critique.py`, qui l'annonce. La synthèse s'arrête avant la fusion si `valider_lectures.py` trouve une sortie mal formée : corriger le fichier, puis relancer.

### Sources réutilisées d'un passage à l'autre

Ces sources ne sont pas refaites par `barometre.py` : la synthèse reprend leur dernier fichier. Dire dans le compte rendu de quand elles datent.

- **Robot Opquast basics d'eServices Manager** (`resultats/esm-basics-<date>/`) : réutiliser le dernier export tant qu'aucun nouvel audit basics n'a été lancé. Un nouvel audit ne se lance qu'avec l'accord de la personne responsable. Après un nouvel audit, exporter les résultats page par page dans `resultats/esm-basics-<date>/agregat.json`, puis `python3 scripts/synthese_esm_basics.py resultats/esm-basics-<date>` (écrit `resultats.json` et `rapport.md`).
- **Contre-examen dans le navigateur** (`resultats/contre-examen-<date>/`) : à refaire quand le thème d'un site a changé ou à un nouvel audit basics : `node scripts/contre_examen.mjs [--service "<nom du site>"]`, puis `python3 scripts/fiche_contre_examen.py` (fiche des règles manuelles, décisions à valider par la personne responsable).
- **Sans eServices Manager** (kit neuf, ou ESM non utilisé) : la synthèse tourne quand même. Les verdicts du robot et les liens vers les audits sont absents, la fiche de contre-examen part de constats vides et les règles concernées restent « non testé » ou « à vérifier ». Le dire dans le compte rendu.

## Trancher les écarts

`lecture_critique.py` confronte toutes les sources règle par règle. Un écart (une source dit conforme, une autre non conforme) se tranche avec quatre questions, toujours dans cet ordre :

1. **Que demande la règle ?** Relire le protocole (`get_rule` du MCP Opquast, format `detailed`). Exemple : règle 124, toute vidéo à démarrage automatique, même muette.
2. **Qu'a regardé chaque source ?** Code ou page affichée, une page ou tous les écrans, identité de robot ou de navigateur.
3. **Que vit l'utilisateur ?** Retenir la source qui observe ce que voit et fait un visiteur plutôt qu'un indice dans le code.
4. **Reste-t-il une interprétation ?** Le statut suit le protocole et l'écart est marqué « à arbitrer » par la personne responsable (ex. fenêtre cookies bloquante, règle 153).

On ne fait jamais voter les outils. Chaque décision est écrite dans `ANALYSE_SOURCES` (`scripts/lecture_critique.py`) : type d'écart, statut retenu, pourquoi, que faire.

Après l'étape `synthese`, `python3 scripts/ecarts_a_trancher.py` doit sortir avec le code 0. Code 0 : aucun écart sans décision (il peut rester des écarts à arbitrer). Code 1 : il en reste. Code 2 : aucune lecture critique, lancer d'abord la synthèse. `--dossier` affiche une fiche compacte par écart (règle et site, sources et verdicts, preuves, analyse, que faire, clé `ANALYSE_SOURCES` à écrire), `--site "<nom>"` limite à un site. Présenter les écarts à arbitrer **un par un** à la personne responsable, avec la fiche et un choix court (garder le statut retenu ou l'inverser) ; écrire sa décision dans `ANALYSE_SOURCES`, puis relancer `--etapes synthese`.

Une nouvelle source s'ajoute dans `lecture_critique.py` (fonction `poser`) et dans `ABR` de `generer_suivi.py` (colonne de la matrice).

## Publication

1. **Données personnelles** : `python3 scripts/verifier_publication.py` doit sortir avec le code 0. Il lit les dossiers du **dernier passage** (la date la plus récente de `resultats/`, même si le passage de nuit a commencé la veille) et `suivi-barometre.html`. Code 1 : une adresse e-mail ou un téléphone a été trouvé, le masquer avant tout commit. Code 2 : aucun fichier n'a été lu, la vérification n'a pas eu lieu. Le relancer avant **chaque** commit.
2. **Page** : publier `suivi-barometre.html` avec l'outil Artifact sur la même adresse que le suivi existant pour garder le lien. Cette adresse est propre au compte qui publie : elle se lit dans `liens-locaux.json` (hors dépôt, entrée « Suivi du baromètre »), jamais dans les fichiers du kit. Si l'entrée n'existe pas (premier passage sur ce compte), publier une nouvelle page, puis noter son adresse dans `liens-locaux.json` ({"titre": "Suivi du baromètre", "url": "…", "detail": ""}) pour les passages suivants.
3. **CSV** : envoyer à la personne responsable, avec SendUserFile, les quatre fichiers de `resultats/barometre-<date>/` (séparateur « ; », UTF-8 avec BOM : ils s'ouvrent tels quels dans Excel) :
   - `barometre.csv` : une ligne par règle et par site, une colonne par type d'audit avec son verdict, puis le statut retenu et la décision ;
   - `tests.csv` : tous les tests effectués, une ligne par règle, site et audit, avec la famille d'audit, le verdict, la décision retenue, l'accord ou non avec elle et la raison quand l'audit a été contredit ;
   - `scores.csv` : score et note par site, et l'évolution (`score_precedent`, `note_precedente`, `ecart`, vides au premier passage) ;
   - `changements.csv` : une ligne par règle et par site dont le statut retenu a changé depuis le passage précédent (avant, après, sens : amélioration, régression ou autre). Le passage précédent est le dossier `resultats/barometre-<date>` le plus récent strictement antérieur au jour ; au premier passage, le fichier ne contient que l'en-tête.
4. **eServices Manager** (s'il est utilisé) : reporter les statuts qui ont changé, à partir de `changements.csv`, dans les audits « règles complémentaires » de `referentiel/audits-esm.json` ; une règle absente d'un audit en cours va dans un nouvel audit « règles complémentaires N » (sélection ad hoc des critères, page d'accueil seule). Pour les résultats des scripts sans IA, `python3 scripts/import_esm.py resultats/reseau-<date>` prépare le fichier d'import (bouton « Importer » de « Nouvel audit »). La personne responsable doit être connectée.
5. **Note de cadrage** (si le projet en a une) : mettre à jour ses chiffres depuis `compte-rendu.md` et vérifier qu'elle tient sur une page A4 : `python3 scripts/verifier_page_a4.py <note>.md`.
6. **Compte rendu, commit et push** : après un dernier `python3 scripts/verifier_publication.py` à 0, commiter et pousser sur le dépôt du projet, puis lancer `python3 scripts/compte_rendu.py` et donner son contenu à la personne responsable. Il écrit `resultats/barometre-<date>/compte-rendu.md` depuis les mêmes fichiers que la page publiée : scores et notes par site, part des statuts à deux sources ou plus, écarts tranchés et à arbitrer, ce qui n'a pas pu être mesuré et pourquoi (règles non testées, commandes en échec, absence d'export ESM, lectures non rendues), « Ce qui a changé » (évolution par site, chaque régression citée avec son numéro et son intitulé ; au premier passage, rien à comparer), puis l'état du passage et la prochaine action. `--date AAAA-MM-JJ` choisit un passage. Code 0 : écrit ; code 2 : aucun `scores.csv`. Ne jamais recopier les chiffres à la main.

## Fichiers utiles

Pipeline et matin :
- `scripts/barometre.py` : l'enchaînement, et `resultats/etat-passage-<date>.json`, son état machine. `scripts/bilan_journal.py` : bloc final du dernier passage et commande de reprise.
- `scripts/preparer_lectures.py` et `scripts/valider_lectures.py` : briefs et validation des lectures IA. `scripts/regles_une_source.py` : liste des règles à une seule source, pour la lecture 3.
- `scripts/ecarts_a_trancher.py` : écarts sans décision (code 1) et fiches `--dossier`. `scripts/compte_rendu.py` : compte rendu chiffré et prochaine action.
- `scripts/exporter_csv.py` : les quatre CSV. `scripts/consulter_barometre.py` : mode consultation, sans rien relancer. `scripts/verifier_publication.py` : contrôle des données personnelles avant commit et publication.
- `scripts/configurer_parc.py` : crée, complète et vérifie `referentiel/parc.json`.

Outils hors pipeline, lancés à la main :
- `scripts/controles_page.js` et `scripts/axe_navigateur.js` : les mêmes contrôles que `page_playwright.mjs` et `axe_playwright.mjs`, à coller dans la console du navigateur sur une page bloquée pour le robot.
- `scripts/nu_local.mjs <vnu>` : validateur Nu du W3C en local (vnu, à installer à part et non vérifié par `verifier_installation.py`), quand le service en ligne limite les appels. `scripts/outils_en_ligne.py` : SSL Labs et validateur Nu en ligne (`--sans-nu`).
- `scripts/generer_schema.py` : régénère le schéma du parc (`schema-parc.html`, s'il existe).
- `scripts/synthese_esm_basics.py`, `scripts/import_esm.py`, `scripts/contre_examen.mjs`, `scripts/fiche_contre_examen.py` : voir « Sources réutilisées ».

Référentiels :
- `references/lectures-independantes.md` : consignes des sous-agents de lecture ; `referentiel/lectures.json` : leurs règles et formats.
- `referentiel/recommandations.csv` et `referentiel/exemples.json` : une recommandation et un exemple clé en main par règle non conforme.
