# Analyse des opportunités de scripts : skill `barometre-sites`

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, 117 lignes ; references/lectures-independantes.md, 28 lignes ; INSTALLER-AVEC-UN-ASSISTANT-IA.md, 98 lignes), avec les scripts du kit dans `kit-barometre-sites/code/scripts/` (node_modules exclu).
Date : 19/11/2026. Scanner : ScriptHunter (déterminisme).

## Inventaire des scripts existants

Le kit est déjà très outillé : 42 fichiers, environ 8 300 lignes, orchestrés par `barometre.py`.

| Famille | Scripts | Couverture |
|---|---|---|
| Orchestration | `barometre.py` (étapes referentiel, moteur, mesure, releve, sources, synthese ; `--depuis`, `--essai`, `--continuer`, `--nuit` avec contrôle secteur, blocage de veille et journal daté ; bilan ok/ÉCHEC en fin de passage) | tout l'automatique |
| Installation | `verifier_installation.py` (liste, puis `--installer` après accord) | prérequis Node, npm, Chromium, Python, outils système, moteur |
| Référentiel | `repartir_regles.py`, `generer_schema.py` | volets des 245 règles |
| Mesure | `controles_reseau.py`, `controles_page.js`, `page_playwright.mjs`, `axe_playwright.mjs`, `axe_navigateur.js`, `synthese_axe.py`, `i18n_w3c.py`, `redbot_local.py`, `outils_page.mjs`, `outils_j2.mjs`, `controles_aria.py`, `outils_en_ligne.py` | réseau, code, accessibilité |
| Relevé | `releve_regles.mjs`, `parcours.mjs`, `regles_releve.py`, `contre_examen.mjs` | navigateur, pages légales |
| Deuxièmes sources | `sources_page.mjs`, `sources_shopify.py`, `sources_html.py`, `sources_html2.py`, `sources_curl.py`, `sources_panier.mjs`, `sources_tiers.mjs` | recoupement |
| Synthèse | `verifier_citations.py` (citations des lectures 1 et extraits `dom:` des lectures 3), `fusion_scripts.py`, `etat_barometre.py`, `lecture_critique.py` (57 ko, table `ANALYSE_SOURCES`), `generer_suivi.py` (150 ko), `exporter_csv.py` (3 CSV, remplace les tirets longs), `fiche_contre_examen.py`, `synthese_esm_basics.py`, `import_esm.py` | consolidation et livrables |
| Contrôles de publication | `verifier_publication.py` (e-mails, téléphones ; codes 0/1/2), `verifier_page_a4.py`, `regles_une_source.py` | garde-fous |

## Verdict

Le placement de l'intelligence est bon : toute la mesure, la fusion, le recoupement, le score et les livrables sont déterministes, et le LLM garde surtout le jugement (trancher les écarts, lectures indépendantes, échanges avec la personne). Les opportunités restantes sont concentrées **aux jointures entre scripts et étapes Claude** : préparation des briefs des sous-agents, validation de leurs sorties, lecture du journal de nuit, extraction des écarts à trancher, comparaison entre deux passages pour ESM et compte rendu chiffré. C'est là que le LLM lit de gros fichiers ou recopie des listes à la main, avec un risque de dérive silencieuse.

## Constats

### 1. Aucune validation de structure des sorties des lectures IA (élevée)

- **Où** : `references/lectures-independantes.md:15`, `:19`, `:23-26` ; `SKILL.md:78-81`. Côté code : `scripts/lecture_critique.py:282-293` et `:435-442` chargent les `lecture_*_lot*.json` sans contrôle.
- **Ce que fait le LLM** : relire les six à neuf fichiers rendus par les sous-agents pour s'assurer qu'ils respectent le format `{"Site": {"16": ["C", "preuve", "lecture"]}}`, que les noms de site sont exacts, que les règles sont celles demandées.
- **Ce qui manque** : `verifier_citations.py` ne contrôle que les « C » de la lecture 1 et les preuves `dom:` de la lecture 3. Rien ne détecte : un nom de site mal écrit (`Boutique_D` au lieu de `Boutique D` : le site disparaît sans erreur de la fusion), un statut hors `C/NC/NA/NT`, une règle hors de la liste du lot, une liste à deux éléments, une citation de plus de 25 mots, un extrait `dom:` hors 20-160 caractères, une règle du tunnel (35, 36, 41, 44, 52, 56, 57, 86, 88, 89) prouvée autrement que par `paiement/`, une capture citée qui n'existe pas. Surtout, **la lecture 2 (`lecture_visuelle`) n'est vérifiée par rien** : `lecture_critique.py:441-442` la pose directement comme source.
- **Script proposé** : `scripts/valider_lectures.py <hors>` (stdlib, `json`, `re`, `pathlib`), lancé en tête de l'étape `synthese` avant `verifier_citations.py`. Sortie JSON par fichier et par site (erreurs bloquantes, avertissements), code 1 si un fichier est invalide. Les sites attendus et les listes de règles se lisent dans la même source que le constat 2.
- **Économie** : 800 à 1 500 jetons par passage (lecture des JSON par le LLM), et surtout suppression d'une perte silencieuse de site ou de règle dans le score.
- **Pré-passe** : oui (alimente la synthèse finale) ; valeur autonome : lint de toute sortie de sous-agent.

### 2. Les briefs des sous-agents sont assemblés à la main (élevée)

- **Où** : `references/lectures-independantes.md:3` (calcul des préfixes `[A-Za-z0-9_]`), `:5-11` (consignes communes « à copier dans chaque brief »), `:15` (34 numéros de règles recopiés), `:19` (33 numéros), `:23` (liste par lot tirée de `regles_une_source.json`), `SKILL.md:78` (deux lots de trois sites).
- **Ce que fait le LLM** : six à neuf fois par passage, il recopie les consignes, calcule le préfixe de fichier de chaque site, liste les entrées, recopie la liste de règles, compose le chemin de sortie daté `resultats/sources-<date>/…` et découpe les lots.
- **Risques** : les listes de règles vivent seulement dans un Markdown, sans lien avec `referentiel/repartition-regles.csv` ; une faute de recopie fait sauter une règle ; un dossier `<hors>/textes` ou `captures` vidé entre deux sessions part en brief sans que personne ne le voie.
- **Script proposé** : déplacer les trois listes de règles dans `referentiel/lectures.json` (lecture, entrées, règles, règles du tunnel, format de preuve, fichier de sortie) et écrire `scripts/preparer_lectures.py <hors> --lecture 1|2|3`. Il produit un brief complet par lot (Markdown prêt à coller dans l'outil Agent) : sites, préfixes, liste des fichiers d'entrée **vérifiés présents** (avec leur nombre), règles, chemin de sortie, consignes communes. Code 1 si un site n'a aucune entrée. La lecture 3 lit directement `regles_une_source.json`. Le document de référence peut alors renvoyer à `--help` au lieu de répéter les listes.
- **Économie** : 1 500 à 3 000 jetons par passage (génération de six à neuf briefs) et environ 400 jetons de liste en moins dans la référence.
- **Pré-passe** : oui ; réutilisable par tout autre assistant (INSTALLER, ligne 70).

### 3. Lecture du journal de nuit par le LLM (élevée)

- **Où** : `SKILL.md:61` (« Le matin : lire le journal, reprendre une étape en échec avec `--depuis` ») ; `INSTALLER-AVEC-UN-ASSISTANT-IA.md:90`.
- **Ce que fait le LLM** : ouvrir `resultats/journal-barometre-<date>.log`, qui concatène plusieurs heures de sortie de tous les sous-processus (souvent des milliers de lignes), pour trouver l'étape en échec et ce qui n'a pas pu être mesuré.
- **Script proposé** : `scripts/bilan_journal.py [journal]` (ou `barometre.py --bilan`). Il isole le dernier bloc `===== début … fin, code N`, extrait le tableau « Bilan » ou, s'il manque, la dernière commande lancée et les 20 dernières lignes avant l'échec, compte les pages « non testé » pour 429 ou anti-robot par site, et propose la commande de reprise exacte (`--depuis <étape>`). Sortie courte en texte et en JSON.
- **Économie** : 2 000 à 10 000 jetons selon la taille du journal, à chaque passage de nuit.
- **Pré-passe** : oui (alimente aussi le compte rendu, constat 5).

### 4. Écarts sans décision : une ligne Python fragile, et pas de dossier compact pour trancher (élevée)

- **Où** : `SKILL.md:96-100` (one-liner `python3 -c …` dans le prompt) ; `SKILL.md:89-94` (quatre questions) ; `SKILL.md:102`.
- **Ce que fait le LLM** : recopier et lancer une ligne Python de 300 caractères (filtre `e['regle']!='-'` peu lisible), puis, pour chaque écart, ouvrir `resultats/lecture-critique-*/lecture.json` et les sorties des outils pour reconstituer qui dit quoi, avec quelle preuve et en regardant quoi.
- **Script proposé** : `scripts/ecarts_a_trancher.py`, code 1 s'il reste des écarts sans décision (le contrôle devient un garde-fou rejouable, pas une ligne à recopier). Avec `--dossier`, il écrit pour chaque écart une fiche compacte : numéro et intitulé de la règle (depuis `referentiel/opquast-checklist-v5.json`), chaque source avec son verdict, sa preuve tronquée, sa nature (code, page affichée, robot, navigateur, lecture IA) et sa portée (une page ou tous les écrans), et la ligne `ANALYSE_SOURCES` la plus proche s'il y en a une. Le LLM garde les questions 1, 3 et 4 (le jugement) ; la question 2 (« qu'a regardé chaque source ? ») devient une donnée.
- **Économie** : environ 150 jetons pour le contrôle, et 1 000 à 3 000 jetons par séance d'arbitrage (lecture de `lecture.json` et des sorties brutes évitée).
- **Pré-passe** : oui, pour la décision et pour `ANALYSE_SOURCES`.

### 5. Compte rendu final assemblé à la main (moyenne)

- **Où** : `SKILL.md:111` ; `INSTALLER-AVEC-UN-ASSISTANT-IA.md:98`.
- **Ce que fait le LLM** : rassembler scores et notes, part des statuts à deux sources ou plus, écarts tranchés et à arbitrer, ce qui n'a pas pu être mesuré et pourquoi. Les chiffres sont éparpillés : `exporter_csv.py:130` imprime scores et part à deux sources, `lecture_critique.py` imprime les écarts, les raisons des « non testé » sont dans les sorties d'outils et le journal.
- **Script proposé** : `scripts/compte_rendu.py` qui lit `scores.csv`, `lecture.json`, `tests.csv` et le bilan du constat 3, et produit le squelette chiffré en Markdown (une ligne par site, totaux, liste des règles « à arbitrer par Mattea », non testés regroupés par raison). Le LLM n'ajoute que le commentaire.
- **Économie** : 500 à 1 000 jetons par passage, et des chiffres qui ne peuvent plus diverger de la page publiée.
- **Pré-passe** : oui ; aussi réutilisable pour la note de cadrage (constat 8).

### 6. Report des changements dans eServices Manager (moyenne)

- **Où** : `SKILL.md:109` (« reporter les statuts du relevé qui ont changé », « une règle absente d'un audit en cours va dans un nouvel audit »).
- **Ce que fait le LLM** : comparer le passage du jour au précédent, règle par règle et site par site, puis vérifier dans `referentiel/audits-esm.json` dans quel audit chaque règle se trouve.
- **Existant** : `import_esm.py` ne prépare l'import que des contrôles réseau.
- **Script proposé** : `scripts/changements_passage.py` : différence entre les deux derniers `resultats/releve-*/decisions.json` (ou `etat-*`), avec pour chaque changement l'audit ESM cible ou « nouvel audit règles complémentaires N ». Option `--import` pour produire le CSV au format de `import_esm.py` quand c'est possible, sinon la liste à saisir dans le navigateur.
- **Économie** : 500 à 2 000 jetons par passage (deux grands JSON comparés par le LLM) ; supprime l'oubli d'une règle changée.
- **Pré-passe** : oui, pour la saisie ESM faite avec Mattea connectée.

### 7. Adaptation aux sites de la personne : cinq dictionnaires à modifier à la main (moyenne, ponctuelle)

- **Où** : `INSTALLER-AVEC-UN-ASSISTANT-IA.md:46` (`SITES` ou `SERVICES` dans `etat_barometre.py:27`, `fusion_scripts.py:30`, `generer_suivi.py:41`, `import_esm.py:24`, `generer_schema.py:15`), plus `referentiel/audits-esm.json` et `ecrans_en_ligne.csv`.
- **Ce que fait le LLM** : éditer cinq scripts aux formats différents (dict nom vers code, dict nom vers tuple, liste), en gardant la cohérence des noms et des codes.
- **Script proposé** : une seule source `referentiel/sites.json` (nom affiché, code ESM, préfixe de page) lue par les cinq scripts, et `scripts/configurer_sites.py` qui la remplit depuis `ecrans_en_ligne.csv`, régénère les clés vides de `audits-esm.json` et vérifie la cohérence (chaque service du CSV a un code, aucun code en double). La même source sert aux constats 1 et 2.
- **Économie** : 1 000 à 2 000 jetons à chaque installation, et la fin d'une classe d'erreurs (site oublié dans un des cinq fichiers).
- **Pré-passe** : non ; valeur autonome forte (installation par un autre assistant).

### 8. Chiffres de la note de cadrage (faible)

- **Où** : `SKILL.md:110`.
- **Ce que fait le LLM** : retrouver et réécrire les chiffres dans `note_cadrage.md`. `verifier_page_a4.py` ne contrôle que la longueur.
- **Script proposé** : balises de remplacement dans la note (par exemple `<!-- chiffre:part_deux_sources -->`) remplies par le script du constat 5, ou au moins un contrôle qui signale les chiffres de la note différents de `scores.csv`.
- **Économie** : 200 à 400 jetons par passage.

### 9. Tiret long : contrôle seulement sur deux livrables (faible)

- **Où** : `SKILL.md:20`, `references/lectures-independantes.md:10`.
- **Existant** : `exporter_csv.py:126-127` et `generer_suivi.py:1987` remplacent « — » ; rien ne contrôle `note_cadrage.md`, les sorties des lectures IA ni les commentaires préparés pour ESM.
- **Script proposé** : ajouter à `verifier_publication.py` un avertissement (sans changer les codes 0/1/2, ou avec un code dédié) pour tout « — » dans les livrables du dernier passage et la note.
- **Économie** : moins de 100 jetons, mais supprime une vérification à l'œil.

### 10. Adresse de publication et export ESM réutilisé (faible)

- **Où** : `SKILL.md:107` (lire `liens-locaux.json`, entrée « Suivi du baromètre », ou la créer) ; `SKILL.md:83` (réutiliser le dernier `resultats/esm-basics-*`).
- **Existant** : `generer_suivi.py:427` (`liens_locaux()`) lit déjà ce fichier ; `etat_barometre.py:62` prend déjà le dernier export basics.
- **Script proposé** : que la synthèse imprime en fin de course l'adresse Artifact à réutiliser (ou « aucune : première publication ») et la date de l'export basics utilisé, avec son âge en jours. Option `--noter-lien <url>` pour écrire l'entrée sans éditer le JSON à la main.
- **Économie** : 50 à 150 jetons par passage.

### 11. Enchaînement synthèse puis règles à une source (faible)

- **Où** : `SKILL.md:78-80`, `references/lectures-independantes.md:23`.
- **Ce que fait le LLM** : lancer à la main `regles_une_source.py <hors>` après la première synthèse.
- **Script proposé** : l'ajouter en dernière commande de l'étape `synthese` de `barometre.py:83-89` (le dossier `--hors` y est déjà connu), puis enchaîner directement sur `preparer_lectures.py --lecture 3` (constat 2).
- **Économie** : moins de 100 jetons, une étape oubliable en moins.

## Ce qui est déjà bien placé

- Prérequis et installation (`SKILL.md:24-38`) : entièrement scripté, avec la décision d'installer laissée à la personne.
- Passage de nuit (`SKILL.md:50-61`) : secteur, blocage de veille et journal gérés par `barometre.py --nuit`. Seuls les rappels à la personne (capot, connexion, mises à jour) restent au LLM, ce qui est normal.
- Données personnelles (`SKILL.md:106`) : `verifier_publication.py` avec un code 2 explicite quand rien n'a été lu.
- Citations et extraits des lectures 1 et 3 : vérifiés mot pour mot par `verifier_citations.py`.
- Les quatre questions pour trancher un écart et les lectures IA elles-mêmes relèvent du jugement : elles doivent rester au LLM.

## Économies cumulées

| Constat | Gravité | Jetons économisés par passage |
|---|---|---|
| 1. Validation des sorties des lectures | élevée | 800 à 1 500 |
| 2. Préparation des briefs | élevée | 1 500 à 3 000 |
| 3. Bilan du journal de nuit | élevée | 2 000 à 10 000 |
| 4. Écarts à trancher et dossier compact | élevée | 1 150 à 3 150 |
| 5. Compte rendu chiffré | moyenne | 500 à 1 000 |
| 6. Changements pour ESM | moyenne | 500 à 2 000 |
| 8. Note de cadrage | faible | 200 à 400 |
| 9, 10, 11. Contrôles mineurs | faible | 150 à 350 |
| **Total par passage** | | **environ 6 800 à 21 400** |
| 7. Configuration des sites (à l'installation) | moyenne | 1 000 à 2 000, une fois |

Au-delà des jetons, les constats 1, 2 et 7 ferment des chemins de **perte silencieuse** (site mal nommé, règle oubliée dans une liste recopiée, lecture visuelle jamais vérifiée) qui faussent le score sans qu'aucune étape ne le signale. Ordre conseillé : 7 (source unique des sites) puis 2 et 1 qui s'appuient dessus, puis 3 et 4.
