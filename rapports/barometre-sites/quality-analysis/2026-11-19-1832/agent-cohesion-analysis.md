# Analyse de cohésion : skill `barometre-sites`

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, references/lectures-independantes.md, INSTALLER-AVEC-UN-ASSISTANT-IA.md), confrontée au code du kit (`scripts/barometre.py` et scripts appelés). Scan consultatif : les constats sont des suggestions.

## Verdict

Ce n'est pas un agent à persona mais une skill de flux de travail (pas de section Identity, pas de dossier `assets/`, pas de mémoire). On l'évalue donc sur la cohérence entre ce qu'elle promet (description), ce qu'elle fait faire (déroulé, arbitrage, publication) et ce que le kit sait réellement exécuter. Le cœur est très cohérent : un objectif unique (taux de conformité Opquast V5), un principe directeur (deux sources indépendantes par règle, jamais de vote entre outils) qui se retrouve dans chaque étape, et un parcours complet de l'installation à la livraison. Les faiblesses tiennent à des sources citées comme piliers (contre-examen humain, robot ESM basics) dont la production n'est décrite nulle part, et à un ancrage sur une personne et un parc précis alors que le kit se veut portable.

## Dimensions de cohésion

| Dimension | Note | Explication |
|---|---|---|
| Alignement objectif / capacités | Fort | La description annonce mesure, recoupement, arbitrage, page et CSV : les six étapes de `barometre.py`, la section « Trancher les écarts » et la section « Publication » couvrent exactement cela. |
| Cohérence d'identité (ton, principes) | Fort | Les principes (lecture seule sur sites en production, pas de contournement anti-robot, pas de donnée personnelle, accord avant installation) sont traduits en mécanismes concrets : `verifier_installation.py` sans `--installer` ne modifie rien, `verifier_publication.py` avec codes de sortie, citations vérifiées mot pour mot. |
| Complétude des capacités | Modéré | Le pipeline automatique est complet, mais deux sources consommées par la synthèse (contre-examen navigateur, export ESM basics) n'ont aucune étape documentée pour être produites. Pas de comparaison explicite avec le passage précédent. |
| Redondance | Modéré | INSTALLER reprend une large part de SKILL.md (prérequis, mode nuit, règles absolues, arbitrage) : utile pour les autres assistants, mais deux sources de vérité à tenir à jour. |
| Intégration externe | Modéré à fort | MCP Opquast, Artifact, SendUserFile, AskUserQuestion, Agent : chaque outil a un rôle clair et INSTALLER donne un équivalent hors Claude. eServices Manager est un point de friction (voir constats). |
| Granularité | Fort | Les étapes de `barometre.py` ont la bonne taille (referentiel, moteur, mesure, releve, sources, synthese), avec reprise `--depuis` et filtre `--service`. Les trois lectures IA sont bien découpées par nature de preuve. |
| Parcours utilisateur | Modéré à fort | Entrée claire (vérifier l'installation, proposer la nuit), sortie de valeur (page, trois CSV, compte rendu). Le passage du matin (journal, lectures, synthèses successives) est bien ordonné mais son point de synchronisation entre lectures 1-2 et lecture 3 est ambigu. |

## Cohésion par capacité

| Capacité | Cohérente ? | Commentaire |
|---|---|---|
| Vérification et installation des prérequis | Oui | Exemplaire : liste, accord explicite, installation avec `npm ci --ignore-scripts`. Petit écart : le validateur Nu local (`scripts/nu_local.mjs`, vnu) n'est ni dans la liste ni dans le pipeline. |
| Passage automatique (`barometre.py`, mode nuit) | Oui | Le mode nuit (secteur, blocage de veille, journal daté) colle à la durée réelle du passage. |
| Lectures IA indépendantes | Oui | Très bien alignées sur le principe d'indépendance (interdiction de lire `resultats/`, preuve vérifiable, NT plutôt que deviner). |
| Règles à une source puis lecture 3 | Partiel | Voir constat sur l'ordonnancement. |
| Arbitrage des écarts | Oui | Les quatre questions ordonnées et l'écriture dans `ANALYSE_SOURCES` donnent une méthode reproductible ; la commande de contrôle des écarts sans décision ferme la boucle. |
| Contre-examen humain | Non documenté | Cité comme source dans INSTALLER et consommé par `lecture_critique.py` et `generer_suivi.py` (`resultats/contre-examen-*/fiche.json`), mais `contre_examen.mjs` et `fiche_contre_examen.py` ne sont ni dans le pipeline ni dans SKILL.md. |
| Robot ESM basics | Partiel | SKILL dit « réutiliser le dernier export `esm-basics-*` » sans dire comment il est produit (`synthese_esm_basics.py` attend un `agregat.json` tiré de l'export ESM, hors pipeline). |
| Publication (données personnelles, Artifact, CSV, ESM, note, commit) | Oui, avec réserve | Bien chaînée. Le report dans ESM (point 4) est manuel alors que `scripts/import_esm.py` prépare justement un import : non cité. |
| Note de cadrage, schéma du parc | Marginal | `note_cadrage.md` et `verifier_page_a4.py` sont cités ; `generer_schema.py` (schema-parc.html) et `outils_en_ligne.py` (services J2) existent sans être mentionnés. |

## Constats

1. **Moyen : source « contre-examen » orpheline.**
   Zone : SKILL.md (Déroulé), INSTALLER (« Ce qu'est le baromètre »), `scripts/contre_examen.mjs`, `scripts/fiche_contre_examen.py`.
   Problème : le contre-examen navigateur pèse lourd dans l'arbitrage (« Le contre-examen dans le navigateur, validé par Mattea, tranche », `lecture_critique.py`), mais aucune étape ne le relance. Sur un kit neuf, la source disparaît sans qu'on le sache ; sur le parc actuel, l'ancienne fiche est réutilisée silencieusement.
   Amélioration : ajouter une étape (ou une sous-étape de `releve`) qui lance `contre_examen.mjs` puis `fiche_contre_examen.py`, ou bien une ligne dans le Déroulé qui dit quand la refaire et qui la valide, et la signaler dans le compte rendu quand elle date d'un passage antérieur.

2. **Moyen : ESM présent en entrée et en sortie, sans mode d'emploi.**
   Zone : SKILL.md (« Robot Opquast basics », Publication point 4).
   Problème : l'entrée (`esm-basics-*`, `synthese_esm_basics.py`) et la sortie (`import_esm.py`) existent mais ne sont pas reliées au texte ; le report est décrit comme une saisie manuelle.
   Amélioration : un court paragraphe « eServices Manager » : comment produire `agregat.json` depuis l'export, quand lancer `synthese_esm_basics.py`, et utiliser `import_esm.py` pour le report.

3. **Moyen : skill portable mais incarnée par une personne et un parc.**
   Zone : description et règles de SKILL.md (« sites e-commerce de Mattea », « accord de Mattea », « 92 % atteints le 13/11/2026 », « 6 boutiques, 47 écrans »).
   Problème : INSTALLER invite à remplacer le parc, mais la description et les garde-fous restent nominatifs et datés. Chez un autre utilisateur, la skill demande l'accord d'une personne absente et se déclenche sur des formulations propres à Mattea.
   Amélioration : parler de « la personne responsable du baromètre » dans les règles, déplacer les chiffres datés dans la page de suivi, et garder le nom seulement dans un exemple. Les docstrings de scripts (« validé par Mattea ») méritent le même traitement.

4. **Bas : ordonnancement lectures 1-2 / lecture 3 ambigu.**
   Zone : SKILL.md (étapes 1 à 3 après `sources`), references/lectures-independantes.md section 3.
   Problème : `regles_une_source.py` tourne après la première synthèse, lancée en parallèle des lectures 1 et 2, donc avant leurs résultats. La liste confiée à la lecture 3 inclut des règles que les lectures 1 et 2 vont couvrir, ce qui gonfle son travail ; ou bien il faut attendre les lectures 1-2, ce que le texte ne dit pas.
   Amélioration : préciser « attendre le retour des lectures 1 et 2, relancer `--etapes synthese`, puis `regles_une_source.py` », ou assumer explicitement le recouvrement.

5. **Bas : duplication SKILL.md / INSTALLER.**
   Zone : INSTALLER étapes 2, 5, 6 et règles absolues.
   Problème : prérequis, mode nuit et règles absolues sont réécrits ; un changement (nouvel outil, nouvelle règle) devra être fait deux fois.
   Amélioration : dans INSTALLER, garder uniquement ce qui est propre aux autres assistants (tables d'équivalence, adaptation du parc) et renvoyer vers les sections de SKILL.md pour le reste.

6. **Bas : outils hors pipeline non répertoriés.**
   Zone : `scripts/` (`nu_local.mjs`, `outils_en_ligne.py`, `generer_schema.py`, `axe_navigateur.js`, `controles_page.js`).
   Problème : on ne sait pas s'ils sont des variantes manuelles, des sources abandonnées ou des compléments à lancer. `verifier_installation.py` ne vérifie pas vnu.
   Amélioration : une ligne par outil dans « Fichiers utiles » (« variante navigateur », « abandonné, Cloudflare », etc.).

7. **Bas : emplacement de `liens-locaux.json` flou.**
   Zone : Publication point 2.
   Problème : dit « hors dépôt » alors que `generer_suivi.py` le lit à la racine du code (fichier ignoré par Git, donc dans l'arborescence). Une IA pourrait le chercher dans `--hors`.
   Amélioration : écrire « à la racine du code, ignoré par Git ».

8. **Suggestion : comparaison avec le passage précédent.**
   Le baromètre est par nature répétitif, mais ni la skill ni le compte rendu final ne demandent l'évolution des scores et des statuts depuis le dernier passage. Une colonne « avant » dans `scores.csv` et une phrase « ce qui a changé » dans le message final donneraient tout son sens au mot baromètre.

## Points forts

- Un fil conducteur unique et tenu partout : deux sources indépendantes, preuve vérifiable, jamais de vote, NT plutôt que deviner.
- Des garde-fous éthiques qui ne sont pas déclaratifs : chacun a son script ou sa vérification (codes de sortie, citations mot pour mot, `--ignore-scripts`).
- Le mode nuit et la reprise `--depuis` répondent directement à la contrainte réelle (plusieurs heures, une requête toutes les 6 à 10 s).
- La méthode d'arbitrage en quatre questions ordonnées est transmissible, y compris à un humain.
- Le cas dégradé « sans eServices Manager » est prévu et doit être dit dans le compte rendu.
- La portabilité vers d'autres assistants est pensée avec de vraies équivalences (sous-agent isolé, page publique de règle, chemin des CSV).

## Pistes créatives

- **Mode « passage éclair »** : un seul site, un seul gabarit, synthèse immédiate, pour une démonstration en formation en quelques minutes.
- **Fiche d'arbitrage pour Mattea** : générer, en fin de synthèse, la liste des écarts « à arbitrer » sous forme de questions fermées (AskUserQuestion), puis réinjecter ses réponses dans `ANALYSE_SOURCES`.
- **Indicateur de fraîcheur des sources** : afficher dans la page de suivi l'âge de chaque source réutilisée (contre-examen, export ESM), pour éviter qu'une vieille preuve ne tranche un passage récent.
- **Étape `contre-examen` dans `ORDRE`**, optionnelle, qui rendrait visible et rejouable la source humaine aujourd'hui implicite.
