# Scripts du baromètre

## controles_reseau.py

Couche **déterministe** de la méthode : même entrée, même résultat. Le script vérifie, sans navigateur ni IA, les règles Opquast V5 qui se mesurent sur les échanges HTTP.

| Niveau | Règles | Ce qui est vérifié |
|---|---|---|
| Site | 197 | La version `http://` redirige vers `https://` |
| Site | 198 | Certificat TLS signé et en cours de validité (jours restants) |
| Site | 217 | SPF et DMARC du domaine de messagerie (DKIM non vérifiable sans le sélecteur) |
| Site | 218 | Le site répond avec et sans `www` |
| Site | 219, 220 | `robots.txt` présent, sitemap déclaré |
| Site | 222 | Une adresse inexistante renvoie bien 404 |
| Page | 197, 199, 200 | HTTPS, HSTS, aucune ressource chargée en HTTP |
| Page | 206, 207, 228 | `nosniff`, type MIME, jeu de caractères dans l'en-tête |
| Page | 210, 211, 212 | X-XSS-Protection, protection contre l'intégration en cadre, CSP qui restreint l'origine (`default-src` ou `script-src`) |
| Page | 213 | Le serveur n'annonce ni logiciel ni version |
| Page | 214 | Attribut `integrity` sur les scripts et styles tiers |
| Page | 226, 227 | Compression, en-têtes de cache |
| Page | mesure | Poids du HTML (transféré et décompressé), nombre de scripts, styles et images |

Les autres règles réseau (mots de passe 201 à 205, 208, 215, 216, pages d'erreur personnalisées 223 à 225) demandent un parcours : elles relèvent de l'audit dans le navigateur.

### Lancer

```bash
python3 scripts/controles_reseau.py
```

Options : `--service "Boutique A"` pour un seul service (les résultats des autres services du jour sont conservés), `--delai 12` pour espacer davantage les requêtes, `--ecrans autre.csv` pour une autre liste d'écrans.

Les écrans contrôlés sont listés dans [ecrans_en_ligne.csv](ecrans_en_ligne.csv).

### Résultats

Dans `resultats/reseau-AAAA-MM-JJ/` :
- `rapport.md` : tableau par service, bilan et poids des pages ;
- `resultats.json` : tout le détail, page par page, avec les preuves ;
- `mcp-<service>.json` : résultats au format de `generate_audit_report` du MCP Opquast ;
- `journal.txt` : chaque requête envoyée et son code de réponse.

### Règles de prudence

- Requêtes `GET` de lecture uniquement : aucun formulaire envoyé, aucun produit ajouté au panier.
- Une requête toutes les 8 secondes par défaut, en-tête `Retry-After` respecté en cas de code 429.
- Robot identifié honnêtement (`Opquast-barometre-Colorz`). Si un site bloque le robot, la page est marquée « non testé » et vérifiée dans le navigateur : on ne contourne pas les protections.
- Bibliothèque standard Python uniquement, aucune dépendance.

## axe_navigateur.js

Couche **automatique d'accessibilité** : les règles WCAG 2.1 A et AA d'axe-core (Deque, open source), la base de la norme EN 301 549 qu'exige l'European Accessibility Act pour les sites e-commerce.

Le script s'exécute **dans le navigateur**, sur la page à auditer (console des outils de développement, ou par l'agent dans le navigateur intégré). Il charge axe-core 4.10.2, lance les règles WCAG 2.1 A et AA et renvoie un résumé : règles respectées, violations (règle, gravité, critère WCAG, nombre d'éléments) et points à vérifier par un humain. Le résumé va dans `resultats/axe-AAAA-MM-JJ/<service>.json`.

Pourquoi le navigateur plutôt qu'un robot : la page est rendue comme pour un vrai visiteur, et Shopify ne bloque pas un navigateur. Lecture seule : rien n'est cliqué ni envoyé.

Premier test le 12/11/2026 sur l'accueil de Boutique A : 32 règles respectées, 2 violations (`button-name`, critique ; `nested-interactive`, sérieuse), 5 points à vérifier par un humain.

Variante sans navigateur : la checklist native « axe-core — WCAG 2.1 A/AA » (51 critères) du robot d'eServices Manager.

## controles_page.js

Couche **déterministe dans le navigateur** : 54 règles Opquast qui se vérifient en lisant le code de la page rendue (métadonnées, étiquettes de champs, types de champs, alternatives présentes, iframes, médias, liens vides ou en nouvelle fenêtre, fichiers, liens internes cassés, fil d'Ariane, lien d'évitement, recherche, plan du site, taille des cibles, polices, texte justifié, zoom, styles d'impression, codage, titres, identifiants en double, copie et menu contextuel, rafraîchissement, tableaux). Même page, même résultat ; aucune IA. Les règles 182, 185 et 244 viennent d'axe-core.

Premier test le 12/11/2026 sur l'accueil de Boutique A : 44 contrôles exécutés, dont des non-conformités sur les liens en nouvelle fenêtre non annoncés (146), l'absence de lien d'évitement (164) et de plan du site (171), et 27 identifiants en double (236).

## repartir_regles.py

Répartit les 245 règles : 20 confiées à l'IA d'eServices Manager (checklist « Opquast IA, 20 règles »), 25 au script réseau, 57 au code de la page (dont axe-core), 143 écartées pour l'instant (jugement visuel ou parcours réel). Sortie : `referentiel/repartition-regles.csv`, avec la raison de chaque choix.

## Passage complet et consolidation (12/11/2026)

| Script | Rôle |
|---|---|
| `page_playwright.mjs` (`npm run page`) | Passe `controles_page.js` sur les 47 écrans avec Playwright |
| `axe_playwright.mjs` (`npm run axe`) | axe-core sur les 47 écrans, statut des 51 règles de la checklist axe d'eServices Manager |
| `i18n_w3c.py` | W3C Internationalization Checker : règles 130, 228, 232, 233 |
| `redbot_local.py` | REDbot en local (redbot.org demande une vérification humaine) : règles 206, 211, 226, 227, 228 |
| `controles_email.py` | Critères déterministes de la checklist e-mail sur le HTML des templates Klaviyo |
| `fusion_scripts.py` | Fusionne réseau, page, i18n et REDbot par page et par règle, pour eServices Manager |
| `synthese_esm_basics.py` | Synthèse des audits Opquast basics exportés d'eServices Manager et comparaison avec le script réseau |
| `etat_barometre.py` | État consolidé de chaque règle par site (scripts + robot) et des critères e-mail, avec les recommandations de `referentiel/recommandations.csv` ; lu par `generer_suivi.py` |
| `import_esm.py` | Fichiers d'import d'audit pour eServices Manager (utilisables pour des critères à code en majuscules) |
