# Analyse des opportunités de scripts : skill `barometre-sites`

Date : 19/11/2026. Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, 114 lignes ; references/lectures-independantes.md, 28 lignes ; INSTALLER-AVEC-UN-ASSISTANT-IA.md, 98 lignes), lue avec le code du kit (`scripts/`, `referentiel/`, `AGENTS.md`). Lecture seule.

## Inventaire des scripts existants

La skill n'a pas de dossier `scripts/` propre : elle s'appuie sur les 41 fichiers de `code/scripts/` (environ 8 200 lignes). L'essentiel du travail mécanique est déjà scripté, et bien :

| Domaine | Scripts | Couverture |
|---|---|---|
| Orchestration | `barometre.py` | 6 étapes, `--etapes`, `--depuis`, `--service`, `--essai`, `--continuer`, `--nuit` (secteur vérifié par `pmset`, veille bloquée, journal daté), arrêt code 3 si prérequis manquants |
| Prérequis | `verifier_installation.py` | Node, npm, paquets npm, Chromium, Python, `.venv`, outils système, moteur Opquast ; `--installer` après accord |
| Mesure, relevé, sources | `controles_reseau.py`, `page_playwright.mjs`, `axe_playwright.mjs`, `i18n_w3c.py`, `redbot_local.py`, `outils_page.mjs`, `outils_j2.mjs`, `controles_aria.py`, `releve_regles.mjs`, `parcours.mjs`, `regles_releve.py`, `sources_*.py/.mjs` | toutes les sources déterministes |
| Synthèse | `verifier_citations.py`, `fusion_scripts.py`, `etat_barometre.py`, `lecture_critique.py`, `generer_suivi.py`, `exporter_csv.py` | vérification des citations des lectures IA (textes et DOM), recoupement, page HTML, 3 CSV, retrait des tirets longs dans les livrables (`generer_suivi.py:1979`, `exporter_csv.py:127`) |
| Annexes | `import_esm.py`, `synthese_esm_basics.py`, `verifier_page_a4.py`, `repartir_regles.py`, `generer_schema.py`, `fiche_contre_examen.py` | import ESM (réseau seulement), page A4 |

Écarts d'inventaire relevés au passage (dérive de documentation, à signaler au rapport de synthèse) :
- `scripts/README.md:80` décrit `controles_email.py`, absent du kit.
- `scripts/README.md:70` annonce une répartition 20 / 25 / 57 / 143 ; `repartition-regles.csv` contient aujourd'hui relevé 95, page 57, écartée 42, réseau 25, manuel 20, IA 6, alors que `SKILL.md:10` annonce « 204 mesurées, 41 écartées ».
- `SKILL.md:10` annonce « 6 boutiques, 47 écrans » ; le `ecrans_en_ligne.csv` du kit contient 1 service (« Ma boutique ») et 5 écrans, alors que `SITES`/`SERVICES` de 5 scripts listent toujours Boutique A à F. Ces trois incohérences sont exactement le genre de vérification qu'un script ferait sans effort (constats 9 et 11).

## Verdict

Le placement de l'intelligence est très bon : la mesure, le recoupement, la vérification des preuves et la production des livrables sont déterministes, et la skill réserve le LLM aux vrais jugements (trancher un écart avec les quatre questions, lectures probabilistes à preuve vérifiée, dialogue d'installation). Les opportunités restantes se trouvent aux **jointures** entre étapes : préparer les briefs des sous-agents, valider leurs sorties, lire le journal du matin, comparer avec le passage précédent pour ESM, et rédiger le compte rendu final. Ce sont des opérations où le LLM lit aujourd'hui de gros fichiers (journal de plusieurs heures, `lecture.json`, CSV de plus de 1 200 lignes) pour en tirer quelques chiffres.

## Constats

### 1. Lecture du journal de nuit (élevée)

- **Où** : `SKILL.md:61` (« Le matin : lire le journal, reprendre une étape en échec avec `--depuis` ») ; `INSTALLER-AVEC-UN-ASSISTANT-IA.md:90`.
- **Ce que fait le LLM** : lire `resultats/journal-barometre-<date>.log`, qui contient toute la sortie standard de plusieurs heures de mesure (dizaines de commandes, journaux Playwright, Lighthouse), pour retrouver l'étape en échec, son code, et la valeur de `--depuis`.
- **Ce qu'un script ferait** : `barometre.py` connaît déjà tout (liste `bilan`, lignes 157 à 174). Lui faire écrire `resultats/bilan-barometre-<date>.json` (étape, script, code, durée, dernières 20 lignes d'erreur de chaque commande en échec, commande de reprise exacte), ou ajouter `scripts/resume_journal.py <journal>` qui extrait les blocs `=== étape`, les lignes `$`, `Échec`, `ÉCHEC`, `Traceback`, `Error`, et la ligne `===== fin ..., code N`.
- **Économie estimée** : 3 000 à 20 000 jetons par passage de nuit (le journal est lu en entier ou par morceaux), remplacés par un JSON de 200 à 400 jetons.
- **Pré-passe** : oui, c'est la pré-passe idéale du « matin ». Valeur autonome forte ; réutilisable par toute orchestration nocturne.

### 2. Liste des règles à une seule source pour la lecture DOM (élevée)

- **Où** : `references/lectures-independantes.md:23` (« celles qui restent à une seule source après l'étape `synthese` (les lister par site dans un fichier JSON passé au sous-agent) »).
- **Ce que fait le LLM** : ouvrir `resultats/lecture-critique-*/lecture.json` (ou `barometre.csv`), parcourir `sources_par_regle` de chaque site, regrouper les sources par famille (`ABR` de `generer_suivi.py`), ne garder que les règles à moins de deux familles, puis écrire le JSON.
- **Ce qu'un script ferait** : la logique existe déjà dans `exporter_csv.py:81-84` (`groupes = {g.ABR.get(a, a) ...}`, `len(groupes) >= 2`) et la colonne `nb_sources` de `barometre.csv`. Un `scripts/regles_une_source.py --lot 1|2` (ou une option `--une-source` d'`exporter_csv.py`) écrirait `<hors>/briefs/regles_une_source_lotN.json`, avec exclusion des règles écartées et des retraits de `exclusions-sites.json`.
- **Économie estimée** : 1 500 à 5 000 jetons (lecture de `lecture.json` pour 6 sites et 200 règles), et suppression d'un risque d'erreur de recoupement qui fausserait la sélection.
- **Pré-passe** : oui, alimente directement le sous-agent DOM. Note : le sous-agent doit rester aveugle à `resultats/` ; c'est l'orchestrateur qui lance le script et ne passe que la liste de numéros, ce qui préserve l'indépendance.

### 3. Validation des sorties des sous-agents de lecture (élevée)

- **Où** : `references/lectures-independantes.md:9, 15, 19, 24-26` ; `SKILL.md:78`.
- **Ce que fait le LLM** : relire les six fichiers `lecture_*_lotN.json` pour vérifier qu'ils respectent le contrat : statuts dans `C/NC/NA/NT`, noms de sites exacts, numéros de règles dans la liste autorisée de chaque lecture, citation de 25 mots au plus, extrait DOM de 20 à 160 caractères, règles du tunnel (35, 36, 41, 44, 52, 56, 57, 86, 88, 89) fondées seulement sur `paiement/`, aucun e-mail ou téléphone, aucun tiret long. Sinon ces écarts passent en silence dans `lecture_critique.py`.
- **Ce qui existe** : `verifier_citations.py` vérifie seulement la présence mot pour mot des citations (lectures « textes ») et des extraits (lectures « DOM »). Il ne valide ni le schéma, ni les listes de règles, ni les longueurs, ni la règle du tunnel, et **ne contrôle rien du tout pour `lecture_visuelle_lot*.json`** (pas même l'existence du fichier de capture cité).
- **Ce qu'un script ferait** : `scripts/valider_lectures.py` (ou un mode `--schema` de `verifier_citations.py`) avec les listes de règles par lecture en constante (celles de `lectures-independantes.md:15, 19`), lancé en tête de l'étape `synthese` ; sortie : rejets par fichier, site et règle, code de sortie non nul en cas de violation de format. Les mêmes listes servent au constat 4.
- **Économie estimée** : 2 000 à 6 000 jetons si le LLM vérifie lui-même ; surtout, fiabilité : une règle hors liste ou un statut mal orthographié change un score sans que personne ne le voie.
- **Post-passe** : oui. Valeur autonome : contrôle de contrat réutilisable pour toute source probabiliste ajoutée ensuite.

### 4. Préparation des briefs des six sous-agents (moyenne)

- **Où** : `references/lectures-independantes.md:3` (calcul des préfixes `[^A-Za-z0-9_]` vers `_`), `:5-11` (consignes communes « à copier dans chaque brief »), `:15, 19, 23` (entrées et règles par lecture), `SKILL.md:78`.
- **Ce que fait le LLM** : assembler à la main six briefs (3 lectures × 2 lots) : recopier les consignes, transformer les noms de site en préfixes, lister les fichiers d'entrée présents dans `<hors>/textes`, `<hors>/captures`, `<hors>/dom`, `<hors>/paiement`, recopier les listes de règles, le chemin et le format de sortie.
- **Ce qu'un script ferait** : `scripts/preparer_lectures.py --hors <hors>` écrit `<hors>/briefs/<lecture>_lotN.md` complets (consignes communes, liste des fichiers réellement présents par site, règles, chemin de sortie daté), et signale les sites sans fichiers d'entrée (lecture inutile, à noter NT). L'orchestrateur n'a plus qu'à passer chaque brief à l'outil Agent. La même fonction de préfixe que `verifier_citations.py:34` évite toute divergence.
- **Économie estimée** : 1 500 à 3 000 jetons par passage (six briefs de 300 à 500 jetons générés, plus l'exploration des dossiers), et des briefs identiques d'un passage à l'autre, ce qui rend les lectures comparables.
- **Pré-passe** : oui. Remarque : `references/lectures-independantes.md` deviendrait la documentation du script plutôt que son contenu copié.

### 5. Différences de statuts à reporter dans eServices Manager (élevée)

- **Où** : `SKILL.md:106` (« reporter les statuts du relevé qui ont changé ... une règle absente d'un audit en cours va dans un nouvel audit »).
- **Ce que fait le LLM** : comparer le passage du jour au précédent, règle par règle et site par site (environ 200 règles × 6 sites), puis croiser avec le contenu des audits de `referentiel/audits-esm.json` pour savoir où va chaque changement.
- **Ce qu'un script ferait** : `scripts/diff_passages.py` compare les deux derniers `resultats/barometre-*/barometre.csv` (colonnes `site`, `regle`, `statut_retenu`) avec `csv` et produit la liste des changements, classée par audit cible (règles complémentaires, règles complémentaires N, nouvel audit) ; option de sortie au format d'import d'`import_esm.py` (aujourd'hui limité au réseau, `import_esm.py:8`). Le diff servirait aussi au compte rendu (constat 6) et à la page de suivi (évolution).
- **Économie estimée** : 3 000 à 10 000 jetons (deux CSV de plus de 1 200 lignes) et une saisie ESM sans oubli.
- **Valeur autonome** : forte ; réutilisable pour tout suivi longitudinal.

### 6. Compte rendu final à Mattea (moyenne à élevée)

- **Où** : `SKILL.md:108` (« scores et notes par site, part des statuts à deux sources ou plus, écarts tranchés et à arbitrer, ce qui n'a pas pu être mesuré et pourquoi ») ; `INSTALLER-AVEC-UN-ASSISTANT-IA.md:98`.
- **Ce que fait le LLM** : relire `scores.csv`, `lecture.json` (écarts et drapeau `a_arbitrer`) et `barometre.csv` (statuts `NT` et leur raison) pour en tirer les chiffres.
- **Ce qui existe** : `exporter_csv.py:129-130` imprime score, note et part à deux sources. Il manque le décompte des écarts tranchés et à arbitrer, la liste des NT par raison, et l'évolution par rapport au passage précédent.
- **Ce qu'un script ferait** : `scripts/bilan_passage.py` (ou une sortie `bilan.json` / `bilan.md` d'`exporter_csv.py`) avec tous ces chiffres, prêts à commenter. Le LLM garde la mise en forme et les cinq constats qui méritent l'attention, sans recalculer.
- **Économie estimée** : 1 500 à 4 000 jetons ; chiffres garantis identiques à ceux des CSV et de la page.
- **Pré-passe** : oui, pour le message final et pour la mise à jour de la note de cadrage (constat 12).

### 7. Contrôle « aucun écart sans décision » en une ligne inline (moyenne)

- **Où** : `SKILL.md:90-94`.
- **Ce que fait le LLM** : recopier et exécuter un one-liner Python de 250 caractères, puis interpréter sa sortie (une liste de tuples). Le filtre `e['regle']!='-'` et l'exclusion des clés `_` sont des détails internes qui n'ont rien à faire dans le prompt.
- **Ce qu'un script ferait** : `python3 scripts/lecture_critique.py --verifier` (ou un contrôle en fin de `main()`), qui sort avec un code non nul et une liste lisible « site, règle, type d'écart » ; l'étape `synthese` de `barometre.py` peut le lancer automatiquement et l'afficher dans le bilan.
- **Économie estimée** : 150 à 300 jetons par passage, plus un one-liner fragile en moins dans la skill.
- **Valeur autonome** : garde-fou de publication.

### 8. Vérification des données personnelles, du tiret long et du contenu hors dépôt avant commit (moyenne)

- **Où** : `SKILL.md:17-18, 20, 100-102`.
- **Ce que fait le LLM** : lancer un `grep -rnoE` avec une expression régulière longue, l'exclure par `grep -v`, puis juger chaque ligne restante « adresse d'exemple ou non ». Rien ne vérifie que les textes légaux, DOM et captures ne sont pas entrés dans Git (règle de la ligne 18), ni l'absence de tiret long hors des deux livrables déjà nettoyés (fichiers `lecture_*`, `note_cadrage.md`, JSON de `resultats/`).
- **Ce qu'un script ferait** : `scripts/verifier_publication.py` en Python (portable, Windows/WSL compris) : expressions e-mail et téléphone avec liste blanche explicite (`exemple.`, `@2x`, `@media`, domaines des sites), recherche de `—` dans les livrables, `git ls-files` et `git status --porcelain` pour refuser tout fichier sous `textes/`, `dom/`, `captures/`, `paiement/` ou `opquast-devtools/` ; code de sortie non nul, et appel possible en crochet de pré-commit.
- **Économie estimée** : 200 à 1 000 jetons par publication selon le nombre de faux positifs à examiner ; surtout, une vérification de confidentialité ne devrait pas dépendre d'une lecture attentive.
- **Valeur autonome** : forte ; réutilisable dans tous les kits de formation.

### 9. Adaptation aux sites de la personne et cohérence des listes de sites (moyenne)

- **Où** : `INSTALLER-AVEC-UN-ASSISTANT-IA.md:41-51`.
- **Ce que fait le LLM** : modifier à la main cinq constantes (`SITES` de `etat_barometre.py:27` et `generer_schema.py:15`, `SERVICES` de `fusion_scripts.py:30`, `generer_suivi.py:41`, `import_esm.py:24`), `audits-esm.json`, et retirer de `ANALYSE_SOURCES` les lignes qui nomment une boutique.
- **Constat concret** : dans le kit, `ecrans_en_ligne.csv` contient « Ma boutique » alors que les cinq constantes et `audits-esm.json` listent Boutique A à F. L'incohérence n'est détectée par rien.
- **Ce qu'un script ferait** : `scripts/configurer_sites.py` lit les services de `ecrans_en_ligne.csv` et vérifie (mode par défaut) ou réécrit (`--appliquer`, après accord) les constantes ; mieux, une source unique `referentiel/sites.json` lue par les cinq scripts supprime la duplication. Un mode `--lister-specifiques` sort les entrées d'`ANALYSE_SOURCES` qui nomment un site absent.
- **Économie estimée** : 1 000 à 3 000 jetons à l'installation (lecture de cinq gros fichiers, dont `generer_suivi.py` de 1 984 lignes), et un contrôle de cohérence à zéro jeton à chaque passage si `verifier_installation.py` l'appelle.
- **Valeur autonome** : oui, lint de configuration.

### 10. Rôle de chaque prérequis manquant (faible)

- **Où** : `SKILL.md:26-33` (« Montrer à la personne la liste exacte : chaque élément, à quoi il sert dans le baromètre, et la commande qui l'installera »).
- **Ce que fait le LLM** : `verifier_installation.py:94-98` affiche le nom, l'état et la commande, mais pas « à quoi il sert ». Le LLM recompose ce rôle à partir des lignes 27 à 32 de la skill.
- **Ce qu'un script ferait** : un quatrième champ « rôle » dans chaque tuple de `verifier_installation.py`, et une option `--json` pour que la question d'accord (tout, une partie, rien) soit construite directement.
- **Économie estimée** : 100 à 200 jetons ; la liste montrée à la personne devient identique d'un assistant à l'autre (Mistral, Codex, Gemini), ce qui compte pour `INSTALLER-AVEC-UN-ASSISTANT-IA.md`.

### 11. Chiffres figés dans la skill (faible)

- **Où** : `SKILL.md:8` (« 92 % atteints le 13/11/2026 »), `SKILL.md:10` (« 6 boutiques, 47 écrans », « 204 mesurées, 41 écartées »).
- **Constat** : ces chiffres dérivent déjà (42 règles écartées dans `repartition-regles.csv`, 1 service et 5 écrans dans le CSV du kit). Ils sont calculables en quelques lignes.
- **Ce qu'un script ferait** : soit retirer les chiffres de la skill et renvoyer vers `scores.csv` et la sortie de `repartir_regles.py`, soit un petit contrôle `scripts/verifier_skill.py` qui compare les nombres cités dans `SKILL.md` aux fichiers de référence.
- **Économie estimée** : moins de 100 jetons, mais évite qu'un agent raisonne sur un périmètre faux.

### 12. Chiffres de la note de cadrage (faible)

- **Où** : `SKILL.md:107` (« mettre à jour les chiffres (`note_cadrage.md`) »).
- **Ce que fait le LLM** : retrouver les nouveaux scores, notes et parts, puis les reporter à la main dans la note.
- **Ce qu'un script ferait** : marqueurs dans la note (par exemple `<!-- score:Boutique A -->`) remplis depuis le `bilan.json` du constat 6, puis `verifier_page_a4.py` comme aujourd'hui. Le texte autour reste rédigé par le LLM.
- **Économie estimée** : 100 à 300 jetons ; aucune faute de recopie.

### 13. Nouvelle source sans colonne dans la matrice (faible)

- **Où** : `SKILL.md:96` (« Une nouvelle source s'ajoute dans `lecture_critique.py` (fonction `poser`) et dans `ABR` de `generer_suivi.py` »).
- **Ce que fait le LLM** : se souvenir de modifier deux fichiers en accord. Un oubli d'`ABR` passe en silence : `exporter_csv.py:83` retombe sur le nom brut de l'outil, qui compte alors comme une famille à part et gonfle la part « deux sources ou plus ».
- **Ce qu'un script ferait** : contrôle en fin de `lecture_critique.py` ou d'`exporter_csv.py` : tout nom d'outil présent dans `recoupement` doit avoir une entrée dans `ABR` (et une famille dans `FAMILLE`), sinon avertissement.
- **Économie estimée** : moins de 100 jetons, mais protège l'indicateur principal.

## Ce qui doit rester au LLM

- Trancher les écarts avec les quatre questions (`SKILL.md:81-90`) et rédiger les entrées d'`ANALYSE_SOURCES`.
- Les lectures indépendantes elles-mêmes (textes, captures, DOM), déjà encadrées par une vérification mot pour mot.
- Le dialogue d'installation et d'accord, le choix nuit ou jour, les rappels de préparation de l'ordinateur (seul le secteur est mesurable, et il l'est déjà).
- La mise en forme du compte rendu et le choix des constats marquants.

## Économies cumulées

| Constat | Gravité | Jetons économisés par passage (estimation) |
|---|---|---|
| 1. Journal de nuit | élevée | 3 000 à 20 000 |
| 2. Règles à une source | élevée | 1 500 à 5 000 |
| 3. Validation des lectures | élevée | 2 000 à 6 000 |
| 5. Diff pour ESM | élevée | 3 000 à 10 000 |
| 4. Briefs des sous-agents | moyenne | 1 500 à 3 000 |
| 6. Compte rendu final | moyenne | 1 500 à 4 000 |
| 7. Écarts sans décision | moyenne | 150 à 300 |
| 8. Vérification avant publication | moyenne | 200 à 1 000 |
| 9. Configuration des sites | moyenne | 1 000 à 3 000 (installation) |
| 10 à 13. Petits contrôles | faible | 300 à 700 |

Total : environ **13 000 à 50 000 jetons par passage complet** (plus 1 000 à 3 000 à l'installation), dont plus des trois quarts viennent des constats 1, 3 et 5. Ordre de mise en œuvre conseillé : 1 (bilan JSON dans `barometre.py`, quelques lignes), 7 et 13 (contrôles en fin de scripts existants), 3 et 2 (contrat des lectures), puis 5 et 6 (diff et bilan, qui partagent la lecture des CSV), enfin 8 et 9. Toutes ces additions sont en Python, bibliothèque standard seule, dans la lignée des scripts du kit ; chacune peut documenter son interface par `--help`, ce qui permettrait de raccourcir les sections « Déroulé » et « Publication » de la skill d'environ 30 %.
