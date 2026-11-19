# Baromètre qualité des sites : le kit

Kit partagé par Mattea Lussier (Colorz) avec les élèves de la formation Opquast. Il contient la méthode, la présentation, des résultats réels anonymisés et le code pour refaire le baromètre sur vos propres sites, avec l'assistant IA de votre choix.

## Ce qu'il y a dans ce dossier

| Élément | Contenu |
|---|---|
| `Presentation barometre qualite des sites.pdf` | les 14 slides : de quoi est composé le baromètre, pourquoi on recoupe plusieurs audits, quatre cas réels détaillés audit par audit, comment l'humain tranche, résultats et limites |
| `resultats-exemple/` | les résultats du 19/11/2026 sur six boutiques Shopify, anonymisées en « Boutique A » à « Boutique F » : `scores.csv` (un score par boutique), `barometre.csv` (une ligne par règle et par boutique, une colonne par type d'audit), `tests.csv` (les 2 836 tests effectués, avec la décision retenue et la raison quand un audit a été contredit), et le classeur `barometre-sites-exemple.xlsx` qui réunit les trois |
| `INSTALLER-AVEC-UN-ASSISTANT-IA.md` | le guide à donner à votre assistant IA (Claude, Mistral, Codex, Gemini, Cursor…) pour tout installer et lancer |
| `code/` | les scripts, le référentiel Opquast V5, la skill (`.claude/skills/barometre-sites/`) et `AGENTS.md` |

Les CSV et le classeur s'ouvrent dans Excel ou Google Sheets (séparateur « ; »). Pour lire les résultats, commencez par `scores.csv`, puis filtrez `tests.csv` sur `accord_avec_la_decision = non` : ce sont les erreurs d'outils que le recoupement a corrigées.

## La méthode en bref

- **Un objectif** : le taux de conformité Opquast V5 de chaque site.
- **Plusieurs preuves par règle** : 28 sources en cinq familles. Elles servent à confirmer ou contredire chaque statut, pas à faire le score.
  - Opquast : le robot d'eServices Manager et le moteur libre devtools.
  - Scripts maison.
  - Outils libres : axe-core, IBM, Siteimprove Alfa, Sa11y, Pa11y, html-validate, Lighthouse, Nu, REDbot…
  - Lectures avec preuve vérifiée.
  - Contre-examen humain.
- **L'automatique trouve, l'humain tranche** : quand les sources sont d'accord, le verdict est retenu. Quand elles divergent, une décision écrite répond à quatre questions :
  1. Que demande la règle ?
  2. Qu'a regardé chaque audit ?
  3. Que vit l'utilisateur ?
  4. Reste-t-il une interprétation ?
- **Résultat sur notre parc** : 92 % des statuts reposent sur au moins deux sources, et 183 écarts ont été tranchés.

## Refaire le baromètre sur vos sites

1. Ouvrez le dossier `code/` dans votre outil (Claude Code, Codex, Cursor, un terminal avec Mistral Vibe…).
2. Donnez à votre assistant IA le fichier `INSTALLER-AVEC-UN-ASSISTANT-IA.md` et demandez-lui de le suivre. Il vérifie ce qui manque sur votre ordinateur et **vous demande votre accord avant d'installer quoi que ce soit**. Il vous demande aussi la liste de vos sites et de vos écrans.
3. Lancez le passage complet **la nuit**, car il dure plusieurs heures :
   - branchez l'ordinateur sur secteur ;
   - laissez le capot ouvert ;
   - gardez une connexion stable ;
   - repoussez les mises à jour automatiques.

   L'option `--nuit` empêche la mise en veille et tient un journal.
4. Le lendemain, l'assistant fait les lectures indépendantes et la synthèse. Vous récupérez la page de suivi et les trois CSV.

## À savoir

- Le code a été écrit pour des boutiques **Shopify**. Certaines sources, comme l'API publique du panier ou les politiques Shopify, n'existent pas ailleurs : les autres fonctionnent sur tout site.
- **eServices Manager est facultatif** : sans lui, le robot Opquast basics manque comme source, mais le reste tourne.
- **Sites en production : lecture seule**. Aucune commande, aucun formulaire envoyé, aucun compte créé, aucun contournement d'anti-robot. N'auditez que des sites que vous avez le droit d'auditer.
- **Licences** :
  - checklist Opquast V5 : Opquast, CC BY-SA 4.0 ;
  - moteur Opquast devtools : MPL, GPL ou LGPL ;
  - outils libres : licences MIT, Apache, ISC, GPL ou MPL selon l'outil (voir `code/package.json`).
