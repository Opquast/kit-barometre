# BMad Method · Analyse qualité : barometre-sites

**📊 Baromètre qualité des sites** : Skill de workflow, mesure répétable de la conformité Opquast V5 d'un parc de sites
**Analysé le :** 2026-11-19T14:32:00Z | **Chemin :** /Users/mickaelh/Documents/Opquast/Test Formation/kit-barometre-sites/code/.claude/skills/barometre-sites
**Rapport interactif :** quality-report.html

## Portrait

Le Baromètre qualité des sites est un opérateur de mesure prudent et méthodique : il enchaîne des heures de contrôles sur des boutiques en production sans jamais rien commander, saisir ni contourner, et exige au moins deux sources indépendantes par règle. Son cœur est un protocole d'arbitrage en quatre questions où l'on « ne fait jamais voter les outils » et où l'humain tranche ce qui reste ambigu. Né comme carnet de bord d'un parc précis, il sert désormais de moteur à un kit pédagogique remis à des élèves et à d'autres assistants IA, et c'est cette double vie qui concentre ses marges de progrès.

## Capacités

| Capacité | État | Constats |
| --- | --- | --- |
| Vérifier et installer les prérequis | Bon | 2 (faibles) |
| Passage automatique (6 étapes) | À surveiller | 4 |
| Lectures IA indépendantes | À surveiller | 5 |
| Règles à une source (lecture 3) | À surveiller | 2 |
| Vérification des citations | À surveiller | 1 |
| Trancher les écarts | À surveiller | 2 |
| Robot Opquast basics d'eServices Manager | À surveiller | 2 |
| Contre-examen dans le navigateur | À surveiller | 1 |
| Publication | À surveiller | 4 |
| Portage vers un autre assistant | À surveiller | 3 (dont 2 alertes du lint, voulues ou fausses) |

## Évaluation

**Bon** : la skill tient sa promesse centrale : une mesure lourde entièrement scriptée, deux sources indépendantes par règle, des garde-fous qui sont des mécanismes et non des déclarations, et un arbitrage écrit en quatre questions. Les quatre défauts bloquants du passage de 15 h 25 sont tous résolus et aucun nouveau ne bloque. Les marges de progrès se concentrent sur la portabilité du kit (parc et commanditaire codés en dur) et sur les jointures entre scripts et étapes Claude (briefs des lectures, journal du matin, écarts à trancher).

### Comparaison avec l'analyse précédente (2026-11-19, 15 h 25)

| Défaut bloquant signalé à 15 h 25 | État à 18 h 32 |
| --- | --- |
| Le contrôle des données personnelles pouvait réussir sans rien examiner (grep sur la date du jour) | **Résolu** : `scripts/verifier_publication.py` lit le dernier passage, renvoie 1 en cas de détection et 2 si rien n'a été lu, et il est demandé avant chaque commit (SKILL.md:106, 111). |
| Publication sur une adresse d'Artifact propre au compte d'origine | **Résolu** : l'adresse se lit dans `liens-locaux.json`, avec création au premier passage (SKILL.md:107). Il reste un constat faible sur l'emplacement de ce fichier. |
| Lecture DOM placée avant la synthèse dont elle dépend | **Résolu** : la séquence est explicite (lectures 1 et 2, première synthèse, `regles_une_source.py`, lecture 3, synthèse finale). Nouveau constat moyen : la première synthèse tourne trop tôt et gonfle la lecture 3 (voir thème 2). |
| Synthèse vraisemblablement bloquée sans export eServices Manager | **Résolu côté skill** : le paragraphe « Sans eServices Manager » décrit le cas dégradé (SKILL.md:85) et aucun scanner ne signale de blocage. Reste un constat moyen : l'export ESM et le report n'ont pas de mode d'emploi (thème 4). |

Note générale : Bon à 15 h 25, Bon à 18 h 32, mais de 4 défauts bloquants à 0.

## Ce qui est cassé

Aucun défaut critique ou élevé bloquant. Le lint de chemins signale deux constats élevés sur `INSTALLER-AVEC-UN-ASSISTANT-IA.md` : le fichier est à la racine de la skill (emplacement voulu, c'est un guide pour les humains et les autres assistants, cité « dans ce dossier » par SKILL.md) et la ligne 51 contient `../hors`, qui est un argument de commande d'exemple et non un renvoi de fichier (faux positif). Les constats élevés de la pré-passe de structure (sections Identity, Communication Style, Principles, On Activation) mesurent une skill de workflow contre le gabarit d'un agent à persona et ne sont pas des pannes.

## Opportunités

### 1. Outiller les lectures indépendantes : briefs, sorties et ordonnancement (élevée, 12 constats)

Les six à neuf briefs de sous-agents sont recopiés à la main, seules les lectures 1 et 3 ont un format complet ou une vérification, et la première synthèse tourne avant le retour des lectures 1 et 2, ce qui gonfle la lecture 3. Un site mal nommé ou une lecture visuelle mal formée disparaît de la fusion sans alerte.

**Correctif :** listes de règles dans `referentiel/lectures.json`, briefs générés par `preparer_lectures.py` (entrées vérifiées, protocoles extraits une fois), sorties validées par `valider_lectures.py` avant la synthèse, et ordre écrit : attendre les lectures 1 et 2, synthèse, `regles_une_source.py` intégré à l'étape `synthese`, puis lecture 3 avec un sous-agent par site.

- Aucune validation de structure des sorties, lecture 2 vérifiée par rien (script-opportunities, `scripts/lecture_critique.py:441`)
- Briefs assemblés à la main (script-opportunities, `references/lectures-independantes.md:15`)
- Lectures 2 et 3 sans chemin ni format de sortie (prompt-craft, `references/lectures-independantes.md:17`)
- Bilan des sous-agents sans limite de longueur (execution-efficiency, `references/lectures-independantes.md:11`)
- Première synthèse en parallèle des lectures 1 et 2, lecture 3 surdimensionnée (execution-efficiency, `SKILL.md:78`), même point vu par structure, prompt-craft et agent-cohesion
- `get_rule` rappelé pour les mêmes règles (execution-efficiency, `references/lectures-independantes.md:8`)
- Lots de trois sites trop lourds pour captures et DOM (execution-efficiency, `references/lectures-independantes.md:3`)
- Listes de numéros de règles codées en dur (prompt-craft, `references/lectures-independantes.md:15`)
- `regles_une_source.py` lancé à la main (script-opportunities, `SKILL.md:79`)

### 2. Un kit portable encore incarné par une personne et un parc (élevée, 10 constats)

La description de déclenchement, les garde-fous et la publication nomment « Mattea », « Colorz », « 6 boutiques, 47 écrans » et un chiffre daté, alors que le kit livre un modèle à une boutique. La liste des sites est recopiée dans un CSV, cinq constantes de scripts et les lots nommés des lectures, sans contrôle de cohérence.

**Correctif :** un fichier de parc unique et neutre (par exemple `referentiel/parc.json` : nom, code, code ESM, préfixe, plateforme, personne qui valide), lu par tous les scripts et la skill, rempli par un script de configuration depuis `ecrans_en_ligne.csv` ; description et règles neutralisées (« la personne responsable du baromètre ») ; chiffres datés renvoyés à `scores.csv` et `repartition-regles.csv`. Garder la valeur dans un fichier du kit et non seulement dans un `customize.toml`, que les autres assistants ignoreraient.

- Skill qui décrit le parc d'origine (structure, prompt-craft, agent-cohesion, `SKILL.md:3`, 19, 94)
- Chiffres datés figés (structure, `SKILL.md:8`)
- Configuration du parc dispersée dans sept endroits (enhancement-opportunities, customization-surface)
- Cinq dictionnaires à modifier à la main lors de l'adaptation (script-opportunities, `INSTALLER-AVEC-UN-ASSISTANT-IA.md:46`)
- Commanditaire et description de déclenchement nominatifs (customization-surface, `SKILL.md:3`, 94)
- Sites hors Shopify non prévus (enhancement-opportunities)

### 3. Le matin et les jointures entre scripts et Claude (élevée, 10 constats)

Après la nuit, Claude lit un journal de plusieurs milliers de lignes, retient de tête un déroulé en quatre temps, recopie une ligne Python pour vérifier les écarts, puis reconstitue à la main le dossier de chaque écart et le compte rendu. Rien n'écrit l'état du passage.

**Correctif :** `bilan_journal.py` (bloc final, échecs, commande de reprise exacte), `ecarts_a_trancher.py` à code de sortie (avec `--dossier`), un état du passage et un compte rendu chiffré écrit dans `resultats/` ; `--continuer` par défaut en mode `--nuit`.

- Journal lu en entier (execution-efficiency, script-opportunities, `SKILL.md:61`)
- Une nuit perdue pour un seul site (enhancement-opportunities, `scripts/barometre.py`)
- Pas de tableau de bord d'état (enhancement-opportunities, `SKILL.md:76`)
- One-liner Python des écarts sans décision (script-opportunities, structure, prompt-craft, `SKILL.md:99`)
- Compte rendu assemblé à la main et perdu avec la session (script-opportunities, enhancement-opportunities, `SKILL.md:111`)
- Liste « à arbitrer » non actionnable (enhancement-opportunities, `SKILL.md:94`)

### 4. Sources et étapes citées sans mode d'emploi (moyenne, 9 constats)

Le contre-examen dans le navigateur, l'export ESM basics, le report dans ESM (alors que `import_esm.py` existe), la note de cadrage absente du kit et plusieurs scripts hors pipeline n'ont pas d'étape documentée. Sur un kit neuf, une source disparaît ou l'étape 5 de la publication échoue.

**Correctif :** un paragraphe par source réutilisée (quand la refaire, comment), étape note de cadrage conditionnelle ou modèle livré, `--forcer` et `--hors` pour `--installer` documentés, une ligne par script hors pipeline dans « Fichiers utiles ».

- Contre-examen orphelin (agent-cohesion, `scripts/contre_examen.mjs`)
- ESM sans mode d'emploi, report à la main (agent-cohesion, script-opportunities, `SKILL.md:83`, 109)
- `note_cadrage.md` absent du kit, chiffres recopiés (structure, prompt-craft, script-opportunities, `SKILL.md:110`)
- Outils hors pipeline non répertoriés, vnu non vérifié (agent-cohesion)
- `--forcer` et `--hors` non documentés (structure, prompt-craft, `SKILL.md:65`, 34)

### 5. Un baromètre sans évolution ni mode consultation (élevée, 3 constats)

Ni la synthèse ni le compte rendu ne comparent au passage précédent, et la skill démarre toujours sur « lancer la mesure » : une question sur un score peut déclencher une proposition de passage de plusieurs heures.

**Correctif :** une question d'intention en ouverture (consulter, rejouer la synthèse, nouveau passage) et une colonne « passage précédent » et « écart » dans `scores.csv`, avec les règles passées de C à NC et inversement dans le compte rendu.

- Pas de mode consultation (enhancement-opportunities, `SKILL.md:3`)
- Pas d'évolution d'un passage à l'autre (enhancement-opportunities, agent-cohesion)

## Points forts

- **Garde-fous en tête, traduits en mécanismes** : chaque règle de prudence a son script ou son contrôle. À ne pas transformer en options configurables.
- **Installation à consentement explicite** : rien ne s'installe sans `--installer` et sans accord, code 3 si un prérequis manque.
- **Arbitrage en quatre questions** : ordonné, illustré, sans vote entre outils, avec trace dans `ANALYSE_SOURCES`.
- **Indépendance des lectures IA structurelle et vérifiée** : interdiction de lire `resultats/`, citations retrouvées mot pour mot.
- **Travail lourd hors du contexte du modèle** : mesure, fusion, score et livrables déterministes ; mode `--nuit` et reprise `--depuis`.
- **Contrôle des données personnelles devenu un vrai garde-fou** (corrigé depuis 15 h 25).
- **Cas dégradés prévus** : sans ESM, premier passage sur un compte, anti-robot ou 429, batterie.
- **Portabilité multi-assistants pensée**, avec de vraies équivalences.
- **Prompt dense** : 118 lignes, environ 3 300 jetons, aucun remplissage.

## Analyse détaillée

### Structure et capacités

La structure tient : toutes les références de fichiers résolues sauf `note_cadrage.md`, enchaînement ordonné, garde-fous en tête. Les sections d'agent absentes sont un choix cohérent pour une skill de procédure. Constats isolés : description longue (environ 800 caractères) et déclenchement large, tension légère entre « commit après chaque étape » et le contrôle avant commit (SKILL.md:20), lint sur l'emplacement d'INSTALLER et un faux positif `../`.

### Persona et voix

Sans persona par conception. Le paragraphe d'ouverture joue bien le rôle de vue d'ensemble ; un titre « Vue d'ensemble » aiderait le repérage. Doublons SKILL.md / INSTALLER qui commencent à diverger (mode nuit, Windows) : décider lequel fait foi.

### Cohésion

Fort sur l'alignement objectif / capacités, la cohérence des principes et la granularité ; modéré sur la complétude (contre-examen, ESM), la redondance avec INSTALLER, l'intégration d'eServices Manager et la synchronisation des lectures. Constat isolé : emplacement de `liens-locaux.json` à préciser (« à la racine du code, ignoré par Git »).

### Efficacité d'exécution

Pré-passe sans problème (aucun cycle, aucune chaîne de sous-agents). Constats isolés : vérification d'installation lancée deux fois au premier passage ; piste d'entrelacement des sites dans les scripts de mesure, qui diviserait l'attente par 4 à 6 mais multiplierait le rythme vu par Shopify : option à décider avec la commanditaire, pas un défaut.

### Expérience de conversation

Parcours examinés : élève (mur d'hypothèses à l'adaptation), experte (déroulé du matin à retenir), utilisateur perdu (pas de chemin consultation), cas limites (hors Shopify, écrans obsolètes), environnement hostile (nuit perdue sur un échec, pas de repli sans MCP Opquast dans la skill), automate (pas de contrat de sortie). Mode sans interaction : partiellement adaptable, avec un contrat proposé (`bilan.json` et statut global). Constats isolés : pré-contrôle des écrans en 404, repli `opquast-checklist-v5.json` à reprendre dans SKILL.md, parcours guidé du premier résultat pour un élève.

### Opportunités de scripts

Placement de l'intelligence bon : 42 scripts, environ 8 300 lignes. Économie estimée : environ 6 800 à 21 400 jetons par passage, plus 1 000 à 2 000 à chaque installation. Constats isolés : contrôle du tiret long étendu à tous les livrables, impression de l'adresse Artifact et de l'âge de l'export ESM en fin de synthèse.

### Surface de personnalisation

Archétype sans état, hors module BMAD et multi-assistant. Aucun `customize.toml` : utile seulement si le kit entre dans un module BMAD, sinon documenter le choix. La vraie surface est le parc de sites, éclatée sur sept emplacements (thème 2), suivie du commanditaire (`approver_name`), du brief des lectures et de la cible de publication en valeurs, de `persistent_facts` et de deux points d'accroche au plus (vérification avant, ESM et note de cadrage après). Abus à prévenir : ne jamais exposer les règles de sécurité en interrupteurs, ne pas dupliquer `--nuit` ou ESM en booléens, câbler chaque valeur jusqu'aux scripts, et garder les valeurs dans un fichier neutre du kit lisible par tous les assistants.

## Recommandations

1. Outiller les lectures indépendantes (briefs générés, sorties validées, ordre écrit, un sous-agent par site pour les lectures 2 et 3). Résout 12 constats, effort moyen.
2. Créer un fichier de parc unique et neutre, et neutraliser description, commanditaire et chiffres datés. Résout 10 constats, effort élevé.
3. Outiller le matin : bilan du journal, écarts à trancher à code de sortie, état du passage et compte rendu chiffré ; `--continuer` par défaut la nuit. Résout 10 constats, effort moyen.
4. Documenter les sources réutilisées et les étapes orphelines (contre-examen, ESM, note de cadrage, options). Résout 9 constats, effort faible.
5. Ajouter une question d'intention et l'évolution par rapport au passage précédent. Résout 3 constats, effort moyen.
6. Aligner SKILL.md et INSTALLER, et trancher l'emplacement d'INSTALLER signalé par le lint. Résout 4 constats, effort faible.
