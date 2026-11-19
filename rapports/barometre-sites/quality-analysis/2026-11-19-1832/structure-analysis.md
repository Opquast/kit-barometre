# Analyse de structure et de capacités : barometre-sites

Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, 117 lignes ; `references/lectures-independantes.md`, 28 lignes ; `INSTALLER-AVEC-UN-ASSISTANT-IA.md`, 98 lignes).
Pré-passe : `structure-capabilities-prepass.json` (statut « warning », 11 constats : 7 élevés, 4 moyens). `is_memory_agent` : false.

## Verdict

La structure tient : chaque fichier, script et référentiel cité par la skill existe dans le kit (24 sur 24 vérifiés), l'enchaînement est ordonné (prérequis, passage, lectures, synthèse, arbitrage, publication) et les garde-fous sont posés en tête. Ce n'est pas un agent à persona mais une **skill de workflow** : les sections d'agent BMAD (Identity, Communication Style, Principles, On Activation) manquent par construction, ce qui explique l'essentiel des constats de la pré-passe. Les vrais défauts sont ailleurs : la skill décrit un parc réel (« Mattea », « 6 boutiques, 47 écrans ») alors que le kit livre un modèle à une boutique, un fichier cité par la publication (`note_cadrage.md`) est absent du kit, et quelques chiffres datés sont figés dans les consignes.

## Sections présentes

| Section attendue (gabarit agent BMAD) | Présente | Équivalent dans la skill |
|---|---|---|
| Frontmatter `name` / `description` | oui | `barometre-sites`, description longue en français |
| Overview | non (en titre) | paragraphe d'ouverture, lignes 8 à 10 (objectif, formule du taux, périmètre) |
| Identity | non | aucun (skill de procédure, sans persona) |
| Communication Style | non | aucun ; consignes de forme dispersées (pas de tiret long, ligne 20 ; compte rendu final, ligne 111) |
| Principles | non | « Règles à ne jamais enfreindre » (l. 12) et « Trancher les écarts » (l. 87) jouent ce rôle |
| On Activation | non | « Prérequis et installation » (l. 22) puis « Déroulé » (l. 46) |
| Sections interdites (On Exit, Exiting) | non | conforme |
| Artefacts de gabarit (`{if-*}`, `{displayName}`) | non | conforme |

Sections propres à la skill : Règles à ne jamais enfreindre (l. 12), Prérequis et installation (l. 22), Déroulé (l. 46), Trancher les écarts (l. 87), Publication (l. 104), Fichiers utiles (l. 113).

## Inventaire des capacités

| Capacité | Routage | Cible | État |
|---|---|---|---|
| Vérifier et installer les prérequis | SKILL.md l. 22-44 | `scripts/verifier_installation.py` (`--hors`, `--installer`) | existe ; options conformes au script |
| Passage automatique (6 étapes) | SKILL.md l. 46-74 | `scripts/barometre.py` (`ORDRE` = referentiel, moteur, mesure, releve, sources, synthese) | existe ; options `--etapes`, `--depuis`, `--service`, `--essai`, `--continuer`, `--nuit` conformes ; code 3 bien renvoyé par le script (l. 156) ; `--forcer` existe mais n'est pas documenté |
| Lectures IA indépendantes 1, 2, 3 | SKILL.md l. 76-81 | `references/lectures-independantes.md` | existe ; noms de fichiers de sortie (`lecture_ia_lot*`, `lecture_visuelle_lot*`, `lecture_dom_lot*`) cohérents avec `lecture_critique.py` l. 283-291 et `verifier_citations.py` |
| Règles à une source | SKILL.md l. 79 | `scripts/regles_une_source.py <hors>` | existe |
| Vérification des citations | SKILL.md l. 81 | `scripts/verifier_citations.py` | existe |
| Robot ESM basics | SKILL.md l. 83-85 | `resultats/esm-basics-*` lu par `etat_barometre.py` | cohérent ; cas « sans ESM » prévu |
| Trancher les écarts | SKILL.md l. 87-102 | `scripts/lecture_critique.py` (`ANALYSE_SOURCES` l. 150, `poser` l. 382), `generer_suivi.py` (`ABR` l. 1452) | existe ; contrôle final par un one-liner Python en ligne (l. 99) |
| Publication (6 étapes) | SKILL.md l. 104-111 | `verifier_publication.py`, `exporter_csv.py`, `verifier_page_a4.py`, `referentiel/audits-esm.json`, `liens-locaux.json`, `note_cadrage.md` | scripts présents ; `liens-locaux.json` hors dépôt par conception ; **`note_cadrage.md` absent du kit** |
| Portage vers un autre assistant | SKILL.md l. 63 | `INSTALLER-AVEC-UN-ASSISTANT-IA.md`, `AGENTS.md` | existent ; table d'équivalences outil par outil |

## Constats

### Constats de la pré-passe (repris tels quels)

| Sévérité | Fichier:ligne | Constat |
|---|---|---|
| moyenne | SKILL.md:1 | Name "barometre-sites" should contain "agent" (e.g., agent-{name} or {code}-agent-{name}) |
| moyenne | SKILL.md:1 | Description missing "Use when..." trigger phrase |
| élevée | SKILL.md:1 | Missing ## Overview section |
| élevée | SKILL.md:1 | Missing ## Identity section |
| élevée | SKILL.md:1 | Missing ## Communication Style section |
| élevée | SKILL.md:1 | Missing ## Principles section |
| élevée | SKILL.md:1 | Missing ## On Activation section |
| moyenne | INSTALLER-AVEC-UN-ASSISTANT-IA.md:1 | No config header with language variables found |
| élevée | INSTALLER-AVEC-UN-ASSISTANT-IA.md:99 | No progression condition keywords found |
| moyenne | lectures-independantes.md:1 | No config header with language variables found |
| élevée | lectures-independantes.md:29 | No progression condition keywords found |

Lecture de ces constats : ils mesurent la skill contre le gabarit d'un **agent** BMAD. Pour une skill de workflow autonome hors du système BMAD, le nom sans « agent », l'absence de persona et d'en-tête de configuration sont des choix cohérents, pas des pannes. La clause de déclenchement existe en français (« Utiliser dès qu'on parle de… »), équivalent du « Use when ». Les deux fichiers secondaires ne sont pas des prompts de capacité à étapes mais des références : l'absence de mots de progression y est normale. Le seul constat qui mérite une action est l'Overview (voir plus bas, sévérité basse).

### Constats de jugement

1. **Moyenne. Le kit livre un modèle, la skill décrit le parc d'origine.** SKILL.md:3, 8, 10, 19, 83, 94, 108-111. La description et le corps parlent de « Mattea », de « Colorz », de « 6 boutiques Shopify » et de « 47 écrans », alors que `scripts/ecrans_en_ligne.csv` du kit contient une seule boutique d'exemple (« Ma boutique », 5 écrans) et que `INSTALLER-AVEC-UN-ASSISTANT-IA.md` (étape 3) demande justement de remplacer le parc. Un assistant qui suit la skill sur un kit neuf annoncera un périmètre faux et cherchera l'accord d'une personne qui n'est pas son utilisatrice. Correction : dans la version kit, parler de « la personne » ou « la responsable du baromètre », et lire le nombre de sites et d'écrans dans `ecrans_en_ligne.csv` au lieu de l'écrire ; garder les noms réels dans une copie privée.

2. **Moyenne. `note_cadrage.md` absent du kit.** SKILL.md:110. L'étape 5 de la publication demande de mettre à jour ce fichier et de lancer `verifier_page_a4.py` dessus ; il n'existe pas à la racine de `code/` (le script le prend par défaut, `verifier_page_a4.py:71`, et échouera). Correction : livrer un modèle de note de cadrage, ou rendre l'étape conditionnelle (« si `note_cadrage.md` existe »).

3. **Basse. Chiffres datés figés dans les consignes.** SKILL.md:8 (« 92 % atteints le 13/11/2026 ») et SKILL.md:10 (« 204 mesurées, 41 écartées »). Ces valeurs vieillissent à chaque passage et faussent le compte rendu si l'assistant les reprend. Correction : renvoyer vers `scores.csv` et `repartition-regles.csv` pour les valeurs courantes, ou marquer le chiffre comme historique.

4. **Basse. Description longue et déclenchement large.** SKILL.md:3. Environ 800 caractères, une liste d'outils qui n'aide pas au déclenchement, et « même sans dire skill » qui assume une activation organique. C'est voulu et le domaine est étroit, mais « les scores Opquast des boutiques » peut recouper les audits faits avec le connecteur MCP Opquast. Correction : résumé court (« Relance le baromètre Opquast V5 des boutiques et publie suivi et CSV. »), puis phrases de déclenchement entre guillemets (« relancer le baromètre », « nouveau passage », « /barometre-sites ») ; la liste des outils peut descendre dans le corps.

5. **Basse. Pas de titre Overview.** SKILL.md:6-10. Le paragraphe d'ouverture fait office de vue d'ensemble mais n'annonce pas l'enchaînement global. Correction facultative : une ligne « En bref : prérequis, passage de nuit, lectures IA, synthèse, arbitrage, publication ».

6. **Basse. Synthèse lancée pendant l'écriture des lectures 1 et 2.** SKILL.md:78. La première synthèse lit `resultats/sources-*/lecture_*_lot*.json` (`lecture_critique.py:283-291`) pendant que les sous-agents peuvent y écrire. Sans conséquence si les fichiers s'écrivent d'un coup, mais un fichier partiel ferait échouer ou fausser la synthèse. Correction : préciser que les sous-agents écrivent dans un fichier temporaire puis le renomment, ou ignorer dans la première synthèse les lectures non terminées.

7. **Basse. Contrôle final par un one-liner illisible.** SKILL.md:99. La vérification « écarts sans décision = liste vide » est une commande Python d'une ligne, fragile à recopier et à porter vers un autre assistant. Correction : en faire une option d'un script existant (par exemple `regles_une_source.py --ecarts` ou un `verifier_ecarts.py`) avec un code de sortie.

8. **Basse. Option `--forcer` non documentée.** `scripts/barometre.py:138` existe (passage de nuit sur batterie) mais n'apparaît pas dans SKILL.md:65. À ajouter, ou à laisser volontairement cachée en le disant.

9. **Basse. Tension légère sur les commits.** SKILL.md:20 (« Commit et push après chaque étape terminée ») et SKILL.md:106 (« relancer `verifier_publication.py` avant chaque commit »). Cohérent à la lecture, mais la règle de la ligne 20 gagnerait à rappeler la vérification pour éviter un commit intermédiaire non contrôlé.

### Sur-spécification

Pas de sur-spécification notable. Les procédures détaillées (ordre des lectures, quatre questions d'arbitrage, formes de preuve vérifiables, codes de sortie) sont du savoir de domaine indispensable à la reproductibilité, pas des consignes que le modèle suivrait de lui-même. La table d'équivalences par assistant dans `INSTALLER-AVEC-UN-ASSISTANT-IA.md` relève de l'adaptateur par plateforme, mais elle sert un vrai besoin du kit (portabilité hors Claude) et tient en un fichier séparé que Claude n'a pas à charger : acceptable.

## Points solides à conserver

- Garde-fous regroupés en tête et repris dans `INSTALLER` et `AGENTS.md` : lecture seule sur les sites en production, aucun contournement d'anti-robot, aucune saisie d'identifiants, aucun robot payant sans accord, contrôle des données personnelles avant commit.
- Installation à consentement explicite : vérification sans effet de bord, liste montrée, accord demandé, puis `--installer` ; paquets npm en `npm ci --ignore-scripts` aux versions verrouillées.
- Dépendance d'ordre bien expliquée et justifiée (lecture 3 après la première synthèse, synthèse finale après les trois lectures).
- Indépendance des lectures IA rendue structurelle (interdiction de lire `resultats/`) et vérifiée après coup (citations retrouvées mot pour mot par `verifier_citations.py`).
- Méthode d'arbitrage claire et ordonnée, avec trace écrite obligatoire (`ANALYSE_SOURCES`) et refus du vote entre outils.
- Codes de sortie explicites (3 pour prérequis, 0/1/2 pour `verifier_publication.py`) qui donnent des points de décision nets.
- Cas dégradé « sans eServices Manager » prévu et à signaler dans le compte rendu.
- Toutes les références de fichiers résolues dans le kit, sauf `note_cadrage.md`.

## Mémoire et mode sans surveillance

- **Mémoire** : aucune mémoire d'agent. L'état persistant vit dans le dépôt (`resultats/<étape>-<date>/`) et dans `liens-locaux.json` hors dépôt (adresse de l'Artifact propre au compte), ce qui est cohérent et documenté (SKILL.md:107). Aucun chemin de mémoire à concilier (pré-passe : `memory_paths` vide).
- **Mode sans surveillance** : pas de mode headless au sens BMAD, mais un mode `--nuit` bien cadré (secteur vérifié, veille bloquée, journal daté, reprise par `--depuis`). Les étapes qui demandent la personne (installation, ESM, arbitrages « à arbitrer par Mattea ») restent hors du passage automatique : bon découpage.
