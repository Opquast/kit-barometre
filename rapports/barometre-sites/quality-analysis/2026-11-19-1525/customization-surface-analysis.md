# Analyse de la surface de personnalisation : barometre-sites

Scanner : customization-surface (Artisan). Date : 19/11/2026. Cible : `kit-barometre-sites/code/.claude/skills/barometre-sites/` (SKILL.md, `references/lectures-independantes.md`, `INSTALLER-AVEC-UN-ASSISTANT-IA.md`), avec le code du kit (`scripts/`, `referentiel/`, `AGENTS.md`) comme contexte.

Analyse purement consultative : rien n'est cassé, il s'agit d'opportunités à exposer ou de risques à éviter.

## Archétype

**Sans état (stateless).** Le prépassage confirme l'absence de sanctuaire (`assets/` absent, aucun gabarit PERSONA, CREED, BOND, CAPABILITIES). Pas de persona, pas de nom d'agent, pas de menu : c'est une skill de flux de travail (workflow) plus qu'un agent BMAD au sens strict. Les deux moitiés du scan s'appliquent donc : opportunités (chemins figés, points d'accroche) et abus potentiels (fermes de booléens, fuite de persona).

Nuance importante qui cadre tout le reste : la skill est livrée dans un **kit portable** destiné à d'autres personnes et à d'autres assistants (Mistral, Codex, Gemini, Cursor). La personnalisation réelle existe déjà, mais elle se fait **en modifiant le code** (étape 3 de `INSTALLER-AVEC-UN-ASSISTANT-IA.md`), pas par une surface déclarée.

## Posture de personnalisation

- **Aucun `customize.toml`.** Ni bloc `[agent]` de métadonnées, ni surface de surcharge.
- Aucune référence `{agent.X}` dans SKILL.md, aucune étape d'activation par résolveur.
- La variance entre utilisateurs (sites audités, nom de la commanditaire, URL de publication, usage d'eServices Manager) est **codée en dur** à trois niveaux : le frontmatter et le corps de SKILL.md, les consignes de `references/`, et cinq scripts Python.

## Constats sur les métadonnées

### M1. Pas de `customize.toml`, donc pas de bloc `[agent]` : `high-opportunity`

Selon la grille, toute skill de type agent doit livrer un bloc `[agent]` (`code`, `title`, `icon`, `description`, `agent_type`, `name`). Sans lui, la skill n'est ni recensée par `module.yaml:agents[]` ni visible dans le registre central.

Portée réelle : la skill vit aujourd'hui hors d'un module BMAD, dans un kit autonome. L'enjeu d'intégration au registre est donc faible tant que le kit n'est pas versé dans un module. En revanche, si le baromètre doit rejoindre `bmad-opquast`, c'est un prérequis. Proposition minimale :

```toml
# Métadonnées lues à l'installation (registre). Non surchargeables à l'exécution.
[agent]
code = "barometre-sites"
title = "Baromètre qualité des sites"
icon = "📊"
description = "Mesure répétable des sites selon les 245 règles Opquast V5, deux sources par règle, page de suivi et CSV."
agent_type = "stateless"
name = ""   # skill de flux de travail, sans persona
```

### M2. Données propres à une personne dans le frontmatter : `medium-opportunity`

La `description` du frontmatter nomme la commanditaire (« de Mattea »), l'organisme (« Colorz ») et le parc (« 6 boutiques Shopify »). C'est le texte de déclenchement, il sera recopié tel quel chez chaque personne qui reçoit le kit. Le guide d'installation demande pourtant d'anonymiser et de remplacer les sites. Deux options :
- rendre la description générique (« des sites audités », sans prénom ni nombre de boutiques) et laisser le détail du parc au fichier de configuration ;
- ou, si un `customize.toml` est créé, garder la description générique dans `[agent].description` et ne pas laisser SKILL.md la contredire.

Pas de dérive de titre ni d'icône à signaler : il n'existe qu'une seule source de vérité (SKILL.md), faute de `customize.toml`.

## Constats d'opportunité

### O1. Le parc de sites est dispersé dans cinq scripts : `high-opportunity`

L'étape 3 du guide d'installation demande de remplacer les six boutiques dans `etat_barometre.py` (`SITES`), `fusion_scripts.py` (`SERVICES`), `generer_suivi.py` (`SERVICES`), `import_esm.py` (`SERVICES`) et `generer_schema.py` (`SITES`), en plus de `scripts/ecrans_en_ligne.csv`. C'est exactement le cas de figure « une modification de trois lignes de configuration qui oblige à un fork ».

Ce n'est pas un champ de `customize.toml` (les scripts ne le lisent pas), mais c'est le premier chantier de personnalisation du kit. Suggestion : un seul fichier `referentiel/sites.json` (nom affiché, code court, code ESM, préfixe de page), lu par les cinq scripts, avec `ecrans_en_ligne.csv` pour les écrans. SKILL.md et le guide n'auraient plus qu'une ligne : « le parc se décrit dans `referentiel/sites.json` et `scripts/ecrans_en_ligne.csv` ».

Corollaire dans `references/lectures-independantes.md` : les deux lots « Boutique A, B, C » puis « D, E, F » et les préfixes `Boutique_D` sont figés. À dériver du fichier de sites (découpage automatique en lots de trois).

### O2. URL de publication de l'Artifact codée en dur : `medium-opportunity`

SKILL.md, section Publication, étape 2 : `https://claude.ai/artifact/12y1tK8TKX8uMtbi92d1Q8`. `generer_suivi.py` contient aussi deux liens d'Artifact (schéma du parc, comparatif REDbot). Pour toute autre personne, ces adresses pointent vers les publications de la commanditaire d'origine, auxquelles elle n'a pas accès en écriture. Proposition :

```toml
# Adresse de l'Artifact de suivi à mettre à jour. Vide : publier une nouvelle page et noter son adresse ici.
suivi_artifact_url = ""
```

SKILL.md référencerait alors `{agent.suivi_artifact_url}` avec la consigne « si vide, publier une nouvelle page ».

### O3. Nom de la commanditaire répété dans les consignes : `medium-opportunity`

« Mattea » apparaît dans les règles absolues (accord pour un robot payant, connexion ESM), la section Lectures (accord pour un nouvel audit), Trancher (« à arbitrer par Mattea »), Publication (destinataire des CSV, compte rendu). Les scripts la nomment aussi (`fiche_contre_examen.py`, `generer_schema.py`, `lecture_critique.py`). Un autre utilisateur du kit aura une autre personne, ou sera lui-même la commanditaire. Proposition :

```toml
# Personne qui valide les arbitrages, autorise les robots payants et reçoit les livrables.
commanditaire = "la personne"
```

avec `{agent.commanditaire}` dans SKILL.md. Côté scripts, le libellé « à arbitrer par … » peut lire la même valeur depuis le fichier de configuration du kit.

### O4. Étapes eServices Manager propres à une organisation : `medium-opportunity`

Deux étapes ne concernent que les personnes qui ont un compte ESM : « Robot Opquast basics d'eServices Manager » (entre `sources` et `synthese`) et « eServices Manager » (étape 4 de Publication). Le guide le reconnaît déjà (« si la personne utilise ESM ; sinon laisser le modèle »), mais SKILL.md les présente comme obligatoires. Plutôt qu'un booléen `utiliser_esm` (voir A1), deux points d'accroche conviennent mieux :

```toml
# Étapes ajoutées après l'étape « sources » (ex. import du dernier export ESM basics).
activation_steps_append = []
# Étapes ajoutées à la publication (ex. report des statuts dans ESM, mise à jour de la note de cadrage).
on_publish = []
```

Le comportement ESM actuel deviendrait la valeur par défaut documentée pour l'organisation d'origine, et disparaîtrait proprement ailleurs. Même logique pour l'étape 5 (« Note de cadrage », `note_cadrage.md`), qui est un livrable propre à la formation d'origine.

### O5. Fichier de consignes des sous-agents en chemin fixe : `low-opportunity`

`references/lectures-independantes.md` est chargé en dur. Son contenu (listes de règles par nature : lecture, visuelle, tunnel) relève de la méthode Opquast, pas de l'organisation : il est raisonnable de le garder figé. Un `lectures_template = "references/lectures-independantes.md"` n'aurait d'intérêt que si une organisation voulait d'autres lots ou d'autres règles ; pas de demande visible. À ne pas exposer pour l'instant.

### O6. Pas de `persistent_facts` : `medium-opportunity`

La convention BMAD livre `persistent_facts = ["file:{project-root}/**/project-context.md"]` par défaut. Aucun `project-context.md` n'existe dans le kit, mais le besoin est réel : le contexte du parc (qui audite, quel droit d'audit, quel périmètre, décisions déjà validées) est aujourd'hui éparpillé entre SKILL.md, `note_cadrage.md` et les scripts. Ajouter la valeur par défaut ne coûte rien et donne un emplacement naturel à ce contexte quand le kit change de mains.

### O7. Synthèse : opter pour une surface de surcharge réduite : `medium-opportunity`

La grille classe en `high-opportunity` un agent sans état qui charge plusieurs gabarits figés. Ici, la variance n'est pas dans des gabarits mais dans des **valeurs d'organisation** (parc, commanditaire, URL de publication, ESM). Une surface de quatre éléments suffit : `commanditaire`, `suivi_artifact_url`, `activation_steps_append`, `on_publish`, plus `persistent_facts`. Au-delà, on fige des promesses inutiles.

Limite à garder en tête : `customize.toml` n'est lu que par un résolveur BMAD sous Claude. Le kit vise aussi Mistral, Codex, Gemini, Cursor, qui ne le liront pas. Le fichier de configuration du kit (O1) doit donc rester la source principale pour tout ce que les scripts consomment, et `customize.toml` ne porter que ce que la skill elle-même consomme. Le guide d'installation devrait le dire en une ligne.

## Constats d'abus

Aucune surface de surcharge n'existe : il n'y a donc **aucun abus présent**. Les points suivants sont préventifs, pour la création éventuelle de `customize.toml`.

### A1. Ne pas transformer les options de `barometre.py` en booléens : `high-abuse` si fait

Tentations visibles : `mode_nuit = true`, `utiliser_esm = true`, `continuer_sur_echec = false`, `publier_artifact = true`. Ce sont des options de passage, choisies à chaque exécution (`--nuit`, `--continuer`, `--etapes`) ou des étapes d'organisation (mieux servies par des points d'accroche, voir O4). Trois booléens ou plus feraient de la configuration une variante de skill déguisée.

### A2. Ne pas exposer la méthode : `high-abuse` si fait

Doivent rester figés dans SKILL.md : le barème A à E, la formule du taux de conformité, la règle des deux sources indépendantes, l'ordre des quatre questions pour trancher, l'interdiction de faire voter les outils, le rythme d'une requête toutes les 6 à 10 s, et toutes les règles « à ne jamais enfreindre » (aucune commande, aucun contournement, refus des cookies, données personnelles). Rendre l'un de ces points surchargeable casserait la comparabilité des passages et l'engagement de sécurité envers les sites en production. Un commentaire en tête de `customize.toml` pourrait le rappeler.

### A3. Documenter chaque champ : `low-abuse` si oublié

Chaque scalaire proposé ci-dessus porte un commentaire d'une ligne. À conserver : sans lui, `commanditaire` ou `on_publish` deviennent des boutons opaques.

### A4. Champs d'identité en lecture seule : `low-abuse` si oublié

Si le bloc `[agent]` est créé, noter en commentaire que `title` et `name` ne se surchargent pas à l'exécution (voir l'en-tête proposé en M1).

## Adéquation à l'archétype

Pour un agent sans état, la posture actuelle (aucune métadonnée, aucune surface) est **trop mince**. Ce n'est pas un utilitaire pur à une capacité sans variance : la skill a au moins quatre préoccupations qui varient d'une organisation à l'autre et qui sont codées en dur, et son propre guide d'installation consacre une étape entière à les modifier à la main. Le signal jaune est l'inverse de celui des agents à mémoire : pas une surface trop bruyante, mais une personnalisation qui passe par l'édition du code et du texte de la skill.

Risque de fuite de persona : nul (pas de persona). Risque de conflit avec un sanctuaire : sans objet.

## Points clés

1. **La vraie surface de personnalisation est le parc de sites, éparpillé dans cinq scripts et dans les consignes des sous-agents.** Le regrouper dans un seul fichier de configuration lu par les scripts (`referentiel/sites.json`) apporte plus que n'importe quel champ de `customize.toml`, et sert tous les assistants, pas seulement Claude.
2. **SKILL.md porte des valeurs d'une seule organisation** : le prénom de la commanditaire (frontmatter compris), l'URL de l'Artifact de suivi, les étapes ESM et la note de cadrage. Les lever en `commanditaire`, `suivi_artifact_url` et deux points d'accroche (`activation_steps_append`, `on_publish`) rend le kit transmissible sans réécriture du texte.
3. **Créer un `customize.toml` minimal** (bloc `[agent]` avec `agent_type = "stateless"`, `name = ""`, `persistent_facts` par défaut) si la skill doit rejoindre un module BMAD, en gardant la méthode et les règles de sécurité strictement hors de la surface surchargeable.
