#!/usr/bin/env python3
"""Lecture critique des résultats, site par site (atelier « 3 résultats intéressants » du support J2).

Pour chaque écart repéré entre deux sources (robot Opquast basics d'eServices Manager, nos scripts, le contre-examen
dans le navigateur, les outils entre eux, les parcours réels), quatre champs courts :
- constat : ce qu'on observe, en deux phrases ;
- pourquoi : pourquoi c'est un faux positif, un faux négatif, un résultat inattendu ou une limite d'outil ;
- recommandation : que faire ;
- statut : le statut à retenir dans le baromètre (conforme, non conforme, non applicable, à trancher).
Trois résultats « intéressants » sont retenus par site : un faux positif, un faux négatif, un inattendu pertinent.

Entrées : resultats/etat-*/etat.json, resultats/contre-examen-*/fiche.json, resultats/outils-*/, resultats/axe-*/,
          resultats/parcours-*/parcours.json.
Sortie : resultats/lecture-critique-AAAA-MM-JJ/lecture.json
Usage : python3 scripts/lecture_critique.py
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Écarts robot / scripts : (type, statut à retenir, fait clé du constat, pourquoi, recommandation)
ANALYSE = {
    "227": ("faux positif", "C",
            "Shopify sert la page HTML sans cache (max-age=0) et met en cache les fichiers statiques sur son CDN.",
            "Le robot ne regarde que la page HTML ; or la règle demande des informations de mise en cache, et elles sont bien envoyées pour tout ce qui peut l'être.",
            "Garder conforme et noter dans l'audit que le HTML est volontairement non mis en cache par Shopify."),
    "136": ("faux négatif", "NC",
            "Le robot et axe-core trouvent des liens icônes (panier, réseaux sociaux) sans intitulé.",
            "Notre script ne contrôle que les liens visibles au chargement : il laisse passer ceux des tiroirs et des menus.",
            "Donner un aria-label à chaque lien icône, puis étendre controles_page.js aux liens masqués."),
    "168": ("faux positif", "C",
            "Le champ de recherche existe dans le code mais s'ouvre derrière une icône loupe.",
            "Le robot juge la page affichée, où le champ n'est pas visible : il conclut à tort qu'il n'y a pas de recherche.",
            "Garder conforme ; vérifier d'un clic que la loupe ouvre bien un champ."),
    "69": ("faux négatif", "NC",
           "Les champs des popups et tiroirs (newsletter, recherche) n'ont qu'un placeholder, sans étiquette.",
           "Notre script ne regarde que les champs visibles au chargement ; le robot évalue aussi ceux des popups.",
           "Associer une étiquette à chaque champ, popups compris ; tester les popups dans le script."),
    "3": ("faux négatif", "NC",
          "Certaines pages ont une meta description vide ou identique d'une page à l'autre.",
          "Notre script vérifie seulement que la balise existe ; le robot juge aussi si elle décrit la page.",
          "Rédiger une description propre à chaque page citée par le robot."),
    "124": ("divergence de critère", "NC",
            "Une vidéo se lance seule à l'arrivée sur la page, sans le son et en boucle.",
            "Notre script exempte les vidéos décoratives ; le robot applique la règle à toute vidéo lancée seule. Le texte Opquast ne prévoit pas d'exception.",
            "Retenir non conforme par prudence et ajouter un bouton pause visible, ou lancer la vidéo au clic."),
    "104": ("faux positif", "C",
            "Une icône de favori est déclarée dans le code de chaque page.",
            "Le robot n'a pas réussi à la charger ou l'a jugée invalide, alors que le script la trouve et qu'elle répond.",
            "Garder conforme après avoir ouvert l'URL de l'icône dans le navigateur."),
}
# Écarts robot / contre-examen : (type, statut à retenir, pourquoi, recommandation)
ANALYSE_CE = {
    "165": ("faux positif", "C",
            "Le robot s'appuie sur une règle CSS outline:none présente quelque part dans le thème, pas sur un élément réel ; au clavier, le contour de focus se voit.",
            "Passer en conforme ; garder un style :focus-visible commun dans le thème pour éviter toute régression."),
    "203": ("faux positif", "NA",
            "Le compte client Shopify se connecte par code envoyé par e-mail : il n'y a aucun mot de passe, donc rien à mesurer.",
            "Passer en non applicable."),
    "75": ("faux positif", "NA", "Aucun mot de passe n'est créé par l'utilisateur (connexion par code e-mail Shopify).", "Passer en non applicable."),
    "76": ("faux positif", "NA", "Aucun mot de passe n'est créé par l'utilisateur (connexion par code e-mail Shopify).", "Passer en non applicable."),
    "68": ("faux positif", "C",
           "Le robot a jugé l'accueil et les collections, où l'origine n'a pas à figurer ; la règle se juge sur les fiches produits, et la fiche testée l'indique.",
           "Passer en conforme sur les fiches ; vérifier quelques autres fiches."),
}
# Correspondance entre règles des outils d'accessibilité et règles Opquast (ces outils ne rapportent que des défauts).
AXE_OPQUAST = {"link-name": "136", "image-alt": "118", "label": "69", "select-name": "69", "color-contrast": "182", "meta-viewport": "193"}
IBM_OPQUAST = {"a_text_purpose": "136", "img_alt_valid": "118", "input_label_exists": "69", "label_content_exists": "69",
               "text_contrast_sufficient": "182", "aria_id_unique": "236", "target_spacing_sufficient": "186"}
SOURCES_SCRIPTS = [("reseau", "Script réseau (controles_reseau.py)"), ("page", "Script code de la page (controles_page.js)"),
                   ("i18n", "W3C i18n Checker"), ("redbot", "REDbot"), ("aria", "axe-core et IBM (aria-hidden, tableaux)")]
PA11Y_OPQUAST = [(r"^1_1_1\.H37$|H37$", "118"), (r"H30\.2$", "117"), (r"(Input\w*|Select|Textarea)\.Name$|H44|F68", "69"),
                 (r"(A\.EmptyNoId|A\.Empty|A\.NoContent)$", "136"), (r"G18\.Fail$|G145\.Fail$", "182"), (r"F77$", "236")]
LH_OPQUAST = {"meta-description": "3", "image-alt": "118", "link-name": "136", "color-contrast": "182", "viewport": "193", "is-on-https": "197",
              "uses-text-compression": "226", "uses-long-cache-ttl": "227", "unminified-css": "229", "unminified-javascript": "230",
              "uses-responsive-images": "119", "label": "69"}
OUTILS_DETERMINISTES = {"Script réseau (controles_reseau.py)", "Script code de la page (controles_page.js)", "W3C i18n Checker", "REDbot",
                        "axe-core", "IBM Equal Access", "Validateur Nu (W3C)", "Pa11y (HTML_CodeSniffer)",
                        "Lighthouse", "Qualys SSL Labs", "MDN HTTP Observatory", "Sitemap (xmllint)"}
LH = "Lighthouse"
PAGE = "Script code de la page (controles_page.js)"
ROBOT = "Opquast basics (robot)"


def analyse_outils(k, src):
    """Analyse propre aux écarts entre outils de recoupement : (type, statut retenu, pourquoi, que faire) ou None."""
    nc = {a for a, x in src.items() if x == "NC"}
    det = {"axe-core", "IBM Equal Access", "Pa11y (HTML_CodeSniffer)", PAGE}
    if k == "69":
        return ("faux négatif", "NC", "axe-core et Lighthouse ne testent que les champs affichés ; nos scripts, IBM et Pa11y voient aussi ceux des popups et tiroirs fermés au chargement (recherche, newsletter), souvent sans étiquette.",
                "Donner une étiquette à chaque champ, popups comprises ; ne pas se fier à axe-core seul pour cette règle.")
    if k in ("117", "118"):
        if nc == {ROBOT}:
            return ("divergence de critère", "NC", "Les outils vérifient qu'une alternative existe ; le robot juge si elle est pertinente (alt générique, nom de fichier, alternative qui ne dit pas la destination).",
                    "Retenir le jugement de pertinence du robot et relire les images qu'il cite ; la présence de l'attribut ne suffit pas.")
        return ("faux négatif", "NC", "IBM relève des images dont l'alternative n'est pas valide, que les autres sources ne signalent pas.", "Corriger les images citées par IBM.")
    if k == "119":
        return ("faux négatif", "NC", "Lighthouse mesure toute image servie plus grande qu'affichée ; notre script ne signale qu'au-delà de 3 fois la taille affichée : seuil trop large.",
                "Servir les images à la taille d'affichage (srcset) ; abaisser le seuil du script à 1,5.")
    if k == "136":
        if nc == {ROBOT}:
            return ("faux positif", "C", "Tous les outils déterministes, y compris notre script corrigé qui contrôle désormais les liens masqués, trouvent un intitulé à chaque lien ; seul le robot dit le contraire.",
                    "Garder conforme ; relire le lien cité par le robot.")
        if nc & det or "axe-core" in nc:
            return ("faux négatif", "NC", f"{', '.join(sorted(nc & (det | {LH})))} relève(nt) au moins un lien sans intitulé que d'autres sources ne voient pas (lien icône, lien vide dans un widget).",
                    "Donner un intitulé au lien relevé (aria-label ou texte masqué).")
    if k == "182":
        return ("divergence de critère", "NC", "Les outils ne testent pas les mêmes éléments (texte sur image, états, pages différentes) : un seul contraste insuffisant relevé suffit pour la règle.",
                "Corriger les textes relevés ; vérifier à l'œil les textes posés sur des images.")
    if k == "186":
        return ("divergence de critère", "NC", "IBM applique l'exception d'espacement des WCAG (une petite cible bien espacée passe) ; notre script mesure la taille, ce que demande Opquast.",
                "Porter les zones cliquables à 24 x 24 px au moins.")
    if k == "193":
        return ("faux négatif", "NC", "Lighthouse vérifie la présence de la meta viewport, pas le blocage du zoom ; notre script et axe-core lisent maximum-scale et user-scalable.",
                "Retirer maximum-scale et user-scalable=no de la meta viewport.")
    if k == "226":
        return ("faux positif", "C", "Nos scripts, REDbot et le robot voient le site servir ses contenus compressés ; Lighthouse signale aussi des fichiers d'applications tierces, hors serveur du site.",
                "Garder conforme ; signaler aux éditeurs des applications concernées.")
    if k in ("229", "230"):
        st = src.get(LH)
        return ("écart à vérifier" if st == "NC" else "faux positif", st or "NT",
                "Lighthouse mesure les octets gagnables sur les fichiers non minifiés ; le robot juge sur un échantillon. La mesure de Lighthouse est retenue.",
                "Minifier les fichiers du thème signalés par Lighthouse ; les fichiers d'applications tierces sont à voir avec leurs éditeurs." if st == "NC" else "Garder conforme.")
    if k == "236":
        return ("faux négatif", "NC", "IBM ne contrôle que les identifiants référencés par ARIA ; nos scripts, Pa11y et le validateur Nu contrôlent tous les identifiants de la page.",
                "Rendre uniques les identifiants des sections répétées du thème.")
    return None


STATUT_LIB = {"C": "conforme", "NC": "non conforme", "NA": "non applicable", "NT": "à trancher", "": "sans objet"}


def dernier(motif: str) -> Path | None:
    l = sorted(RACINE.glob(motif))
    return l[-1] if l else None


# Écarts entre les deuxièmes sources du 12/11 et les sources existantes : (type, statut retenu, pourquoi, que faire, à arbitrer)
IA_CITE = ("faux positif", "C", "La lecture indépendante cite le passage exact (citation retrouvée mot pour mot dans les textes) ; le relevé ne le trouvait pas, faute d'avoir lu la politique Shopify où il se trouve ou parce que son motif de recherche était trop étroit.",
           "Retenir conforme ; élargir le motif du relevé ou lire aussi les politiques Shopify.", False)
JS_RAW = ("limite d'outil", "C", "Le HTML envoyé par le serveur ne contient pas l'élément : il est ajouté en JavaScript. La page affichée, celle que voit l'utilisateur, le contient.",
          "Retenir la page affichée ; rien à corriger pour l'utilisateur (signaler seulement que sans JavaScript l'information manque).", False)
JS_FORM = ("limite d'outil", "NC", "Le défaut vient d'éléments ajoutés en JavaScript (formulaires de la popup ou du thème) : le HTML brut ne les voit pas, la page affichée oui.",
           "Retenir non conforme et corriger les champs relevés dans la page affichée.", False)
ANALYSE_SOURCES = {
    ("*", "51"): IA_CITE, ("*", "53"): IA_CITE, ("*", "50"): IA_CITE, ("Boutique C", "114"): IA_CITE,
    ("Boutique A", "29"): ("faux positif", "C", "La politique des cookies dit ce que change leur blocage (« n'affecte pas l'exécution des services ») : c'est bien l'explication des conséquences du refus demandée par le protocole ; le motif du relevé ne reconnaissait pas cette tournure.",
                            "Retenir conforme.", False),
    ("Boutique B", "114"): ("faux négatif", "C", "Le relevé cite les mentions légales du site, qui nomment le directeur de la publication ; la lecture indépendante n'a lu que la version Shopify de ces mentions, qui ne le nomme pas.",
                               "Retenir conforme ; harmoniser les deux versions des mentions légales.", False),
    ("*", "184"): ("faux négatif", "NC", "Le texte de consentement désigne le bouton par sa seule position (« en cliquant ci-dessus ») : c'est exactement ce que la règle interdit. Sur la capture, la lecture visuelle ne pouvait pas relier la phrase au bouton.",
                   "Retenir non conforme ; nommer le bouton (« en cliquant sur « Je m'inscris » »).", False),
    ("*", "139"): ("divergence de critère", "NC", "Le relevé lit chaque élément souligné dans le code : certains ne sont pas des liens (boutons qui ouvrent un tiroir, bandeaux). Sur une capture, un bouton souligné ressemble à un lien : l'œil ne peut pas faire la différence.",
                   "Retenir non conforme ; réserver le soulignement aux liens (ou faire de ces éléments de vrais liens).", False),
    ("Boutique F", "2"): ("faux positif", "C", "Les captures pleine page montrent le « © 2026 » du pied de page sur les 8 écrans ; le relevé a lu certaines pages avant le chargement complet du pied de page.",
                                  "Retenir conforme.", False),
    ("*", "56"): ("faux négatif", "NC", "Le relevé s'est fondé sur la page de paiement, qui détaille les taxes ; or la règle vise les prix affichés partout, et les fiches produit, collections et recherches affichent un prix sans mention TTC.",
                  "Retenir non conforme ; ajouter « TTC » (et le HT si la clientèle est professionnelle) à côté des prix.", False),
    ("Boutique D", "180"): ("faux négatif", "NC", "Le relevé supposait une charte unique (un seul thème Shopify) ; la capture montre que le formulaire de contact a sa propre présentation (police, carte blanche, libellés en anglais).",
                                   "Retenir non conforme ; intégrer le formulaire de contact au thème du site.", False),
    ("Boutique D", "99"): ("écart à vérifier", "NC", "L'accueil n'affiche qu'une vidéo et « Nouvelle collection », menu replié : rien ne dit en clair que c'est une boutique de vêtements. Le relevé s'appuyait sur le titre et le menu, invisibles à l'arrivée.",
                                  "Retenir non conforme à titre provisoire ; à arbitrer. Ajouter une phrase d'accroche visible.", True),
    ("*", "153"): ("divergence de critère", "NC", "Une fenêtre cookies centrée sur fond assombri doit être franchie avant d'accéder au contenu : le protocole Opquast ne prévoit pas d'exception pour le consentement. Le relevé ne comptait que les pages d'attente (pré-accueil).",
                   "Retenir non conforme selon le protocole, à arbitrer : un bandeau non bloquant (en bas de page) rendrait l'accès immédiat tout en recueillant le consentement.", True),
    ("Boutique A", "162"): ("divergence de critère", "NC", "La fenêtre cookies n'a ni croix, ni « Fermer », ni « Continuer sans accepter » : seulement Refuser, Autoriser, Personnaliser. Le protocole demande un bouton de fermeture au libellé explicite.",
                             "Retenir non conforme selon le protocole, à arbitrer ; ajouter « Continuer sans accepter » ou « Fermer ».", True),
    ("Boutique A", "157"): ("faux positif", "C", "Les captures montrent l'item courant souligné en rouge dans le menu ; le script cherchait un marquage dans le code (aria-current ou classe active), qui n'est pas exigé : la règle porte sur le signalement visuel.",
                             "Retenir conforme ; ajouter aria-current=\"page\" pour les lecteurs d'écran.", False),
    ("*", "231"): ("limite d'outil", "C", "La date lisible par les machines est ajoutée en JavaScript : absente du HTML brut, présente dans la page affichée que lisent les navigateurs et les moteurs qui exécutent le JavaScript.",
                   "Retenir conforme ; idéalement, placer la date dans le HTML envoyé (JSON-LD datePublished).", False),
    ("*", "225"): ("limite d'outil", "C", "Le menu de la page 404 est construit en JavaScript : absent du HTML brut, présent dans la page affichée.", "Retenir conforme.", False),
    ("Boutique E", "196"): ("faux négatif", "NC", "Le PDF réellement imprimé, regardé page à page, montre l'en-tête (menu, recherche, compte, panier) ; l'émulation du relevé ne l'avait pas détecté.",
                                "Retenir non conforme ; masquer l'en-tête et la navigation dans une feuille de style d'impression (@media print).", False),
    ("*", "46"): JS_RAW, ("*", "15"): JS_RAW, ("*", "116"): JS_RAW, ("*", "145"): JS_RAW,
    ("*", "95"): JS_FORM, ("*", "97"): JS_FORM, ("*", "13"): JS_FORM,
}
# 13/11 : écarts ouverts par les outils tiers, le HTML brut et CSS, curl et l'impression réelle.
# « BASE » : on garde le statut établi par les sources déjà retenues (l'outil mesure un autre critère).
ANALYSE_SOURCES.update({
    ("Boutique C", "4"): ("divergence de critère", "NC", "Le moteur Opquast ne contrôle que la forme numérique des dates ; le relevé et la capture montrent des dates d'avis à l'année sur deux chiffres (« 07/11/26 ») et une offre « jusqu'au 15/11 » sans année : le format n'est pas explicite.", "Retenir non conforme ; écrire l'année sur quatre chiffres ou en toutes lettres.", False),
    ("*", "71"): ("limite d'outil", "NC", "Le HTML envoyé par le serveur ne contient pas les formulaires ajoutés en JavaScript (fenêtre d'inscription, avis) ; le robot les voit dans la page affichée, avec des champs obligatoires non signalés.", "Retenir non conforme ; ajouter « (obligatoire) » ou un astérisque expliqué dans l'étiquette.", False),
    ("*", "103"): ("divergence de critère", "BASE", "html-validate signale un titre de plus de 70 caractères : c'est un critère de longueur, que la règle 103 ne demande pas (elle demande que le titre identifie le contenu).", "Garder le statut établi ; raccourcir les titres reste utile pour l'affichage dans les onglets et les moteurs.", False),
    ("*", "124"): ("faux négatif", "NC", "Le protocole Opquast exclut toute vidéo à démarrage automatique (attribut autoplay), même sans le son ; notre script ne comptait que les vidéos lancées avec le son. Le moteur Opquast relève les balises video autoplay.", "Retenir non conforme ; retirer l'attribut autoplay ou laisser l'utilisateur lancer la vidéo.", False),
    ("Boutique A", "126"): ("limite d'outil", "NC", "html-validate ne contrôle que l'attribut autoplay des balises ; le relevé a compté 5 animations automatiques sans bouton pause dans la page affichée.", "Retenir non conforme ; ajouter un bouton pause aux carrousels et animations.", False),
    ("Boutique D", "126"): ("divergence de critère", "C", "La vidéo de l'accueil démarre seule (html-validate le relève) mais elle a ses commandes, avec pause (capture : « 00:06 / 01:00 ») : la règle 126 demande seulement de pouvoir la mettre en pause.", "Retenir conforme pour la règle 126 ; le démarrage automatique relève de la règle 124.", False),
    ("Boutique F", "133"): ("faux négatif", "NC", "Le relevé avait vérifié les liens de langue sur l'accueil ; le HTML brut montre que, sur les autres pages, les liens hreflang renvoient vers l'accueil de chaque langue et non vers la traduction de la page.", "Retenir non conforme ; faire pointer chaque lien de langue vers la page traduite correspondante.", False),
    ("*", "135"): ("faux négatif", "NC", "Notre script réseau s'annonçait comme un robot, et Shopify sert alors la langue demandée ; avec l'identité d'un navigateur ordinaire (curl), la page reste en français malgré la préférence anglaise : c'est ce que vivent les visiteurs.", "Retenir non conforme ; activer la redirection selon la langue du navigateur dans Shopify Markets.", False),
    ("Boutique D", "136"): ("divergence de critère", "C", "Le moteur Opquast et le robot attendent un texte visible dans le lien ; les liens concernés ont un intitulé par aria-label, que axe, IBM, Pa11y et Lighthouse reconnaissent comme nom accessible, ce que la règle 136 demande.", "Retenir conforme ; un texte visible reste préférable.", False),
    ("*", "137"): ("divergence de critère", "BASE", "Sa11y et Alfa repèrent les libellés génériques (« cliquez ici », « en savoir plus ») ; ils ne jugent pas si un libellé décrit bien sa destination, ce que fait le robot et la lecture humaine.", "Garder le statut établi ; quand Sa11y relève un libellé générique, il est non conforme.", False),
    ("Boutique C", "141"): ("limite d'outil", "C", "Le HTML brut ne lit que les feuilles de style liées ; le relevé, dans la page affichée, lit aussi les styles ajoutés par le thème et l'application d'avis, où se trouve la règle :visited.", "Retenir conforme.", False),
    ("Boutique D", "142"): ("faux négatif", "NC", "Le relevé jugeait l'ensemble des liens ; le HTML brut de la fiche produit compte 10 liens externes dont 6 sans aucun signe qui les distingue des liens internes.", "Retenir non conforme ; signaler les liens externes (icône et texte « site externe »).", False),
    ("Boutique E", "144"): ("limite d'outil", "NC", "Le relevé, dans la page affichée, trouve un lien mailto sans libellé explicite (icône seule) ; le HTML brut accepte tout lien qui contient une adresse, sans voir ce qui est affiché.", "Retenir non conforme ; donner au lien un libellé « Écrire à … ».", False),
    ("Boutique E", "152"): ("limite d'outil", "C", "Le seul lien « cassé » est la redirection vers le compte client Shopify, qui répond 404 à une requête sans session ; dans le navigateur il fonctionne.", "Retenir conforme.", False),
    ("Boutique E", "159"): ("divergence de critère", "NC", "axe et html-validate vérifient un nom accessible (aria-label), présent ; la règle 159 demande une légende explicite visible, absente pour l'icône de recherche des avis (robot et moteur Opquast).", "Retenir non conforme ; ajouter un texte visible à côté de l'icône.", False),
    ("*", "164"): ("divergence de critère", "C", "Le moteur Opquast attend des liens d'accès rapide vers le menu, le contenu et la recherche ; le protocole ne les exige que si ces zones ne suivent pas directement l'en-tête. Ici, menu et recherche sont dans l'en-tête et un lien mène au contenu.", "Retenir conforme.", False),
    ("Boutique F", "177"): ("limite d'outil", "NC", "Le lien « Archives » trouvé dans le HTML brut mène à une collection de produits, pas aux newsletters ; aucune newsletter n'est consultable en ligne.", "Retenir non conforme ; publier la dernière newsletter en ligne.", False),
    ("Boutique F", "178"): ("limite d'outil", "NC", "Le lien « Archives » trouvé dans le HTML brut mène à une collection de produits, pas aux newsletters.", "Retenir non conforme ; publier les archives des newsletters.", False),
    ("*", "192"): ("divergence de critère", "BASE", "Sa11y ne relève les majuscules qu'à partir de quatre mots et sans les accents ; le relevé et le moteur Opquast lisent chaque libellé écrit en capitales dans le code.", "Garder le statut établi ; écrire en minuscules et mettre en capitales par les styles (text-transform).", False),
    ("*", "196"): ("limite d'outil", "NC", "Le test du PDF cherchait les libellés du menu ; or les menus imprimés sont des icônes (menu, recherche, panier) ou une fenêtre d'inscription. Le PDF regardé page à page confirme que ces blocs de navigation sont imprimés.", "Retenir non conforme ; masquer en-tête, menus et formulaires dans une feuille de style d'impression.", False),
    ("Boutique D", "235"): ("faux négatif", "NC", "Sa11y et le moteur Opquast, indépendamment, relèvent sur la fiche produit des éléments présentés en liste mais balisés en blocs (div) ; le relevé ne l'avait pas vu.", "Retenir non conforme ; baliser ces éléments en ul/li.", False),
    ("*", "242"): ("divergence de critère", "BASE", "Le moteur Opquast exige un attribut scope ou headers sur chaque entête ; pour un tableau simple, des entêtes th en première ligne suffisent à relier les cellules, ce que lit le HTML brut.", "Garder le statut établi ; ajouter scope=\"col\" reste une bonne pratique.", False),
})
ANALYSE_SOURCES.update({
    ("*", "34"): ("limite d'outil", "NC", "Les données structurées (JSON-LD) et l'API de Shopify donnent la disponibilité aux machines ; le client, lui, ne voit aucune mention de stock sur la fiche, le panier ou le paiement (DOM et captures).", "Retenir non conforme ; afficher « En stock » ou « Épuisé » à côté du bouton d'ajout au panier.", False),
    ("Boutique D", "35"): ("limite d'outil", "NC", "L'API de livraison renvoie des délais, mais la page de paiement n'affiche aucun délai pour le mode Standard sélectionné par défaut ni pour le point relais ; seul l'Express en a un.", "Retenir non conforme ; afficher le délai estimé de chaque mode de livraison.", False),
    ("*", "86"): ("faux négatif", "NC", "Le protocole demande la liste des informations ou documents nécessaires AVANT la première étape d'un processus complexe comme une commande ; la page de paiement commence directement par le paiement express et le champ e-mail. Le relevé avait jugé que le formulaire sur une page suffisait.", "Retenir non conforme ; annoncer dans le panier ce qui sera demandé (adresse, téléphone, moyen de paiement).", False),
    ("*", "88"): ("divergence de critère", "NC", "Le protocole demande l'étape en cours dans le titre de la page ou dans un chemin d'étapes ; le paiement Shopify sur une seule page n'a qu'un intitulé de section « Paiement », que la lecture du DOM a compté comme une étape.", "Retenir non conforme ; afficher un chemin d'étapes (panier, livraison, paiement).", False),
})
NOUVELLES = {"Moteur Opquast devtools", "Sa11y", "Siteimprove Alfa", "html-validate", "Impression PDF (cookies refusés)", "HTML brut et CSS (sans JavaScript)", "curl",
             "API panier Shopify (cart.js)", "API panier Shopify (shipping_rates)", "Page de paiement (affichée)", "Lecture IA du DOM et des captures (probabiliste)",
             "Relevé navigateur (Claude)", "HTML brut (sans JavaScript)", "Lecture IA indépendante (probabiliste)", "Lecture visuelle IA des captures (probabiliste)",
             "HTML brut et JSON-LD", "HTML brut de la page 404", "Chromium page.pdf + pdftotext", "Shopify /policies/*.json", "Playwright (événements popup)"}


def lire(motif: str) -> dict:
    f = dernier(motif)
    return json.loads(f.read_text(encoding="utf-8")) if f else {}


def charger_outil(prefixe: str) -> dict:
    """Statut par site et par règle pour un outil de nos scripts : non conforme si une page l'est, sinon conforme, sinon NA."""
    import re
    out = {}
    for f in sorted(RACINE.glob(f"resultats/{prefixe}-*/resultats.json")):
        if not re.fullmatch(rf"{prefixe}-\d{{4}}-\d{{2}}-\d{{2}}", f.parent.name):
            continue
        for nom, sv in json.loads(f.read_text(encoding="utf-8"))["services"].items():
            d = out.setdefault(nom, {})
            ctl = list(sv.get("site", [])) + [c for p in sv.get("pages", []) for c in p.get("controles", [])]
            for c in ctl:
                st = {"conforme": "C", "non conforme": "NC", "non applicable": "NA"}.get(c["status"].replace("-", " "))
                if not st:
                    continue
                k = str(c["rule_number"])
                prev = d.get(k)
                d[k] = "NC" if "NC" in (st, prev) else "C" if "C" in (st, prev) else "NA"
    return out


def item(typ, regle, titre, entre, constat, pourquoi, reco, statut, base=None):
    """base : statut de départ selon chaque audit, liste de [audit, statut ou valeur]."""
    return {"type": typ, "regle": regle, "titre": titre, "entre": entre, "constat": constat, "pourquoi": pourquoi,
            "recommandation": reco, "statut": statut, "statut_lib": STATUT_LIB.get(statut, statut), "base": base or []}


ECARTEES = {r["numero"] for r in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8")) if r["methode"] == "écartée"}


EXCL_SITES = json.loads((RACINE / "referentiel" / "exclusions-sites.json").read_text(encoding="utf-8"))


def main() -> None:
    etat = lire("resultats/etat-*/etat.json")["sites"]
    fiche = lire("resultats/contre-examen-*/fiche.json")
    axe = lire("resultats/axe-*/resultats.json").get("sites", {})
    en_ligne = lire("resultats/outils-*/en_ligne.json")
    pages = lire("resultats/outils-*/pages.json")
    j2 = lire("resultats/outils-*/j2.json")
    parcours = lire("resultats/parcours-*/parcours.json")
    releve = lire("resultats/releve-*/decisions.json")
    sources_pages = lire("resultats/sources-*/pages.json")
    sources_shopify = lire("resultats/sources-*/shopify.json")
    sources_html = lire("resultats/sources-*/html.json")
    # 13/11 : outils tiers de confiance, HTML brut et CSS, curl, API panier Shopify (dernier passage de chaque fichier)
    def lire_dernier_res(prefixe_):
        l_ = sorted(RACINE.glob(f"resultats/{prefixe_}-*/resultats.json"))
        return json.loads(l_[-1].read_text(encoding="utf-8")).get("services", {}) if l_ else {}

    def lire_dernier(nom_):
        l_ = sorted(RACINE.glob(f"resultats/sources-*/{nom_}"))
        return json.loads(l_[-1].read_text(encoding="utf-8")) if l_ else {}
    sources_tiers = lire_dernier("tiers.json")
    aria_res = lire_dernier_res("aria")
    sources_html2 = lire_dernier("html2.json")
    sources_curl = lire_dernier("curl.json")
    sources_panier = lire_dernier("panier.json")
    lecture_dom: dict = {}
    for f_ in sorted(RACINE.glob("resultats/sources-*/lecture_dom_lot*.json")):
        for site_, regles_ in json.loads(f_.read_text(encoding="utf-8")).items():
            lecture_dom.setdefault(site_, {}).update(regles_)
    lecture_vis: dict = {}
    for f_ in sorted(RACINE.glob("resultats/sources-*/lecture_visuelle_lot*.json")):
        for site_, regles_ in json.loads(f_.read_text(encoding="utf-8")).items():
            lecture_vis.setdefault(site_, {}).update(regles_)
    lecture_ia: dict = {}
    for f_ in sorted(RACINE.glob("resultats/sources-*/lecture_ia_lot*.json")):
        for site_, regles_ in json.loads(f_.read_text(encoding="utf-8")).items():
            lecture_ia.setdefault(site_, {}).update(regles_)
    global OUTILS
    OUTILS = {p_: charger_outil(p_) for p_, _ in SOURCES_SCRIPTS}
    sortie = {}
    for nom, regles in etat.items():
        items = []
        accords = sum(1 for v in regles.values() if v["scripts"] in ("C", "NC") and v["robot"] == v["scripts"])
        # statut de chaque source, règle par règle
        par_regle: dict = {}
        for prefixe, lib in SOURCES_SCRIPTS:
            for k, st in OUTILS[prefixe].get(nom, {}).items():
                par_regle.setdefault(k, {})[lib] = st
        for k, v in regles.items():
            if v.get("robot"):
                par_regle.setdefault(k, {})["Opquast basics (robot)"] = v["robot"]
        for l in fiche.get(nom, []):
            if l.get("decision_statut"):
                par_regle.setdefault(str(l["regle"]), {})["Contre-examen (validé par Mattea)"] = l["decision_statut"]
        preuves = {}
        import re as _re
        if axe.get(nom):
            for k in set(AXE_OPQUAST.values()):
                par_regle.setdefault(k, {})["axe-core"] = "C"
        if any(pg.get("ibm") for pg in pages.get(nom, {}).get("pages", {}).values()):
            for k in set(IBM_OPQUAST.values()):
                par_regle.setdefault(k, {})["IBM Equal Access"] = "C"
        # Pa11y (moteur HTML_CodeSniffer)
        pa = [pg["pa11y"] for pg in j2.get(nom, {}).get("pages", {}).values() if pg.get("pa11y", {}).get("par_code") is not None]
        if pa:
            for _, k in PA11Y_OPQUAST:
                par_regle.setdefault(k, {})["Pa11y (HTML_CodeSniffer)"] = "C"
            for x in pa:
                for code, nb in x["par_code"].items():
                    for motif, k in PA11Y_OPQUAST:
                        if _re.search(motif, code):
                            par_regle[k]["Pa11y (HTML_CodeSniffer)"] = "NC"
                            preuves.setdefault((k, "Pa11y (HTML_CodeSniffer)"), []).append(f"{code} : {nb}")
        # Lighthouse (audits reliés aux règles)
        for pg in pages.get(nom, {}).get("pages", {}).values():
            for aid, sc in (pg.get("lighthouse", {}).get("audits") or {}).items():
                # is-on-https échoue aussi sur les ressources HTTP d'une page HTTPS : il croise 197 et 200 (12/11)
                for k in [LH_OPQUAST.get(aid)] + (["200"] if aid == "is-on-https" else []):
                    if k is None or sc is None:
                        continue
                    prev = par_regle.setdefault(k, {}).get("Lighthouse")
                    st = "C" if sc >= 0.9 else "NC"
                    par_regle[k]["Lighthouse"] = "NC" if "NC" in (st, prev) else "C"
                    if st == "NC":
                        preuves.setdefault((k, "Lighthouse"), []).append(f"{aid} échoué sur {pg['gabarit'].split(' (')[0]}")
        # SSL Labs, Observatory, sitemap
        ssl = en_ligne.get(nom, {}).get("ssllabs", {})
        if ssl.get("notes"):
            ok = all(n_.startswith(("A", "B")) for n_ in ssl["notes"])
            for k in ("197", "198"):
                par_regle.setdefault(k, {})["Qualys SSL Labs"] = "C" if ok else "NC"
        obs = en_ligne.get(nom, {}).get("observatory", {})
        if obs.get("penalites") is not None:
            pen = {r_: m_ for _, r_, m_ in obs["penalites"]}
            par_regle.setdefault("199", {})["MDN HTTP Observatory"] = "NC" if any(r_.startswith("hsts") and m_ < 0 for r_, m_ in pen.items()) else "C"
            par_regle.setdefault("212", {})["MDN HTTP Observatory"] = "NC" if any(r_.startswith("csp") and m_ < 0 for r_, m_ in pen.items()) else "C"
            par_regle.setdefault("214", {})["MDN HTTP Observatory"] = "NC" if any(r_.startswith("sri-not-implemented") for r_ in pen) else "C"
            par_regle.setdefault("211", {})["MDN HTTP Observatory"] = "NC" if any(r_.startswith("x-frame") and m_ < 0 for r_, m_ in pen.items()) else "C"
            for r_, m_ in pen.items():
                if m_ < 0 and r_.split("-")[0] in ("hsts", "csp"):
                    preuves.setdefault(("199" if r_.startswith("hsts") else "212", "MDN HTTP Observatory"), []).append(r_)
        sm = j2.get(nom, {}).get("sitemap", {})
        if "bien_forme" in sm:
            par_regle.setdefault("220", {})["Sitemap (xmllint)"] = "C" if sm["bien_forme"] and sm["statut_http"] == 200 else "NC"
        for rid, x in axe.get(nom, {}).get("regles", {}).items():
            if rid in AXE_OPQUAST:
                par_regle.setdefault(AXE_OPQUAST[rid], {})["axe-core"] = "NC"
                preuves.setdefault((AXE_OPQUAST[rid], "axe-core"), []).append(f"{rid} : {x['elements']} élément(s) sur {x['pages']} page(s)")
        ibm = {}
        for pg in pages.get(nom, {}).get("pages", {}).values():
            for rid, k in pg.get("ibm", {}).get("par_regle", {}).items():
                ibm[rid] = ibm.get(rid, 0) + k
        for rid, k in ibm.items():
            if rid in IBM_OPQUAST:
                par_regle.setdefault(IBM_OPQUAST[rid], {})["IBM Equal Access"] = "NC"
                preuves.setdefault((IBM_OPQUAST[rid], "IBM Equal Access"), []).append(f"{rid} : {k} élément(s)")
        lus = [n for n in en_ligne.get(nom, {}).get("nu", {}).values() if "erreurs" in n]
        if lus:
            dup = sum(k for n in lus for m, k in n.get("principales", []) if m.startswith("Duplicate ID"))
            if dup:  # Nu ne garde que ses 5 erreurs les plus fréquentes : l'absence ne prouve rien
                par_regle.setdefault("236", {})["Validateur Nu (W3C)"] = "NC"
            if dup:
                preuves[("236", "Validateur Nu (W3C)")] = [f"{dup} identifiant(s) en double sur {len(lus)} page(s) lue(s)"]
        # Deuxièmes sources (12/11) : relevé navigateur, règles axe et IBM complémentaires, données publiques Shopify,
        # lecture IA indépendante des textes (probabiliste, citation obligatoire)
        def poser(k, outil, st, preuve=""):
            if st not in ("C", "NC", "NA"):
                return
            prev = par_regle.setdefault(k, {}).get(outil)
            par_regle[k][outil] = "NC" if "NC" in (st, prev) else "C" if "C" in (st, prev) else "NA"
            if st == "NC" and preuve:
                preuves.setdefault((k, outil), []).append(preuve[:160])
        for k, v in releve.get(nom, {}).items():
            poser(k, "Relevé navigateur (Claude)", v[0], v[1])
        for url, rr in sources_pages.get(nom, {}).items():
            for k, l in rr.items():
                if k.startswith("_"):
                    continue
                for st, preuve, outil in l:
                    poser(k, outil, st, f"{rr.get('_gabarit', '')} : {preuve}")
        for url, rr in sources_html.get(nom, {}).items():
            for k, v in rr.items():
                if not k.startswith("_"):
                    poser(k, v[2], v[0], f"{rr.get('_gabarit', '')} : {v[1]}")
        for url, rr in sources_tiers.get(nom, {}).items():
            for k, l in rr.items():
                if not k.startswith("_"):
                    for st, preuve, outil in l:
                        poser(k, outil, st, f"{rr.get('_gabarit', '')} : {preuve}")
        for url, rr in sources_html2.get(nom, {}).items():
            for k, v in rr.items():
                if not k.startswith("_"):
                    poser(k, v[2], v[0], f"{rr.get('_gabarit', '')} : {v[1]}")
        for src_ in (sources_curl, sources_panier):
            for k, v in src_.get(nom, {}).items():
                if not k.startswith("_"):
                    poser(k, v[2], v[0], v[1])
        # 185 : le résultat « aria » réunit deux outils ; chacun compte pour sa propre source
        for pg_ in aria_res.get(nom, {}).get("pages", []):
            for c_ in pg_.get("controles", []):
                if c_["rule_number"] == 185:
                    st_ = {"conforme": "C", "non-conforme": "NC"}.get(c_["status"])
                    com_ = c_.get("comment", "")
                    if st_ == "NC":
                        if "axe-core aria-hidden-focus" in com_: poser("185", "axe-core", "NC", com_)
                        if "IBM aria_hidden_nontabbable" in com_: poser("185", "IBM Equal Access", "NC", com_)
                    elif st_ == "C":
                        if "axe-core" in com_: poser("185", "axe-core", "C")
                        if "IBM" in com_: poser("185", "IBM Equal Access", "C")
        par_regle.get("185", {}).pop("axe-core et IBM (aria-hidden, tableaux)", None)
        p404 = sources_shopify.get(nom, {}).get("223")
        if p404:
            m_ = _re.match(r"Code (\d+)", p404[1])
            if m_:
                poser("222", "HTML brut de la page 404", "C" if m_.group(1) == "404" else "NC", p404[1])
        for k, v in sources_shopify.get(nom, {}).items():
            if not k.startswith("_"):
                poser(k, v[2], v[0], v[1])
        for k, v in lecture_ia.get(nom, {}).items():
            if v[0] == "C" and (len(v) < 4 or v[3] != "citation vérifiée"):
                continue  # conforme sans citation retrouvée dans les textes : non retenu (scripts/verifier_citations.py)
            poser(k, "Lecture IA indépendante (probabiliste)", v[0], v[1])
        for k, v in lecture_dom.get(nom, {}).items():
            if len(v) > 3 and v[3] in ("extrait vérifié", "jugement visuel"):
                poser(k, "Lecture IA du DOM et des captures (probabiliste)", v[0], v[1])
        for k, v in lecture_vis.get(nom, {}).items():
            poser(k, "Lecture visuelle IA des captures (probabiliste)", v[0], v[1])
        compte_sources = {k: sorted(a for a, x in src.items() if x in ("C", "NC", "NA")) for k, src in par_regle.items()}
        for k, src in sorted(par_regle.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999):
            if k not in regles and k not in {l_ for l_ in []}:
                pass
            vals = {x for x in src.values() if x in ("C", "NC")}
            if vals != {"C", "NC"}:
                continue
            v = regles.get(k, {})
            titre = v.get("titre") or next((l["titre"] for l in fiche.get(nom, []) if str(l["regle"]) == k), f"Règle {k}")
            nc = [a for a, x in src.items() if x == "NC"]; c = [a for a, x in src.items() if x == "C"]
            base = [[a, x] for a, x in src.items()]
            ev = "; ".join(p for a in nc for p in preuves.get((k, a), []))
            constat = f"Non conforme selon {', '.join(nc)} ; conforme selon {', '.join(c)}." + (f" Détail : {ev}." if ev else "")
            final = v.get("statut")
            ce = src.get("Contre-examen (validé par Mattea)")
            if k in ANALYSE_CE and ce:
                typ, st, pq, reco = ANALYSE_CE[k]
                l = next(l for l in fiche[nom] if str(l["regle"]) == k)
                constat = f"Le robot dit {STATUT_LIB.get(src.get('Opquast basics (robot)'), 'non mesuré')}. Dans le navigateur : {l['constat_navigateur'].rstrip('.')}."
                items.append(item(typ, k, titre, "robot / contre-examen navigateur", constat, pq, reco, st, base)); continue
            if k == "232":
                items.append(item("faux négatif", k, titre, "nos outils entre eux", constat,
                                  "Notre script vérifie la présence de la balise meta charset, pas sa position ; or HTML5 exige qu'elle tienne dans les 1 024 premiers octets.",
                                  "Placer <meta charset=\"utf-8\"> en tête du <head> ; ajouter le contrôle de position à controles_page.js.", "NC", base)); continue
            if k in ANALYSE and set(src) <= {"Opquast basics (robot)", "Script code de la page (controles_page.js)", "Script réseau (controles_reseau.py)", "REDbot", "W3C i18n Checker", "axe-core", "IBM Equal Access"} and src.get("Opquast basics (robot)") == "NC" and src.get("Script code de la page (controles_page.js)", src.get("Script réseau (controles_reseau.py)")) == "C":
                typ, st, fait, pq, reco = ANALYSE[k]
                items.append(item(typ, k, titre, "robot / scripts", constat + " " + fait, pq, reco, st, base)); continue
            an = ANALYSE_SOURCES.get((nom, k)) or ANALYSE_SOURCES.get(("*", k))
            if an and set(src) & NOUVELLES:
                typ, st, pq, reco, arb = an
                if st == "BASE":
                    st = v.get("statut") if v.get("statut") in ("C", "NC", "NA") else (releve.get(nom, {}).get(k, ["NT"])[0])
                    if st not in ("C", "NC", "NA"):
                        st = "NC" if "NC" in src.values() else "C"
                it = item(typ, k, titre, " / ".join(sorted(a for a, x in src.items() if x in ("C", "NC"))), constat, pq, reco, st, base)
                if arb:
                    it["a_arbitrer"] = True
                items.append(it); continue
            ao = analyse_outils(k, src)
            if ao:
                typ, st, pq, reco = ao
                items.append(item(typ, k, titre, " / ".join(sorted(src)), constat, pq, reco, st, base)); continue
            det_nc = [a for a in nc if a in OUTILS_DETERMINISTES]
            det_c = [a for a in c if a in OUTILS_DETERMINISTES]
            if ce:
                typ, st = ("faux positif" if ce == "C" else "faux négatif"), ce
                pq = f"Le contre-examen dans le navigateur, validé par Mattea, tranche : {STATUT_LIB[ce]}. " + ("Les outils qui disaient non conforme se fondaient sur un indice indirect." if ce == "C" else "Les outils qui disaient conforme ne voyaient pas ce cas.")
                reco = "Retenir le contre-examen." + ("" if ce == "C" else " Voir la recommandation de la règle.")
            elif det_nc:
                typ, st = "faux négatif", "NC"
                pl = lambda l_, sg, pl_: pl_ if len(l_) > 1 else sg
                pq = (f"{', '.join(det_nc)} {pl(det_nc, 'relève', 'relèvent')} des éléments précis en défaut ; {', '.join(c)} {pl(c, 'ne contrôle', 'ne contrôlent')} pas ces éléments "
                      "(autres pages, éléments masqués, popups, ou critère jugé plus largement).")
                reco = "Retenir non conforme et corriger les éléments relevés ; étendre le contrôle qui les a laissés passer."
            elif det_c and nc == ["Opquast basics (robot)"]:
                typ, st = "écart à vérifier", final or "NT"
                pq = "Seul le robot (IA) dit non conforme, nos outils déterministes disent conforme : faux positif probable du robot, ou défaut sur une page que nos outils ne regardent pas."
                reco = "Lire la preuve du robot dans eServices Manager et vérifier la page citée."
            else:
                typ, st = "écart", final or "NT"
                pq = "Les sources se contredisent sans indice clair."
                reco = "Vérifier à la main."
            items.append(item(typ, k, titre, " / ".join(sorted(src)), constat, pq, reco, st, base))
        pre = [c for c in parcours.get(nom, {}).get("paiement", {}).get("cases_precochees", [])
               if any(k in c.lower() for k in ("offre", "offer", "nouvelle", "news", "newsletter", "e-mail", "email", "sms"))]
        if pre:
            items.append(item("inattendu pertinent", "33", "L'inscription à des services annexes n'est pas activée par défaut", "parcours réel (paiement)",
                              f"À la page de paiement, la case « {pre[0]} » est cochée d'avance. Le client est inscrit aux offres s'il ne la décoche pas.",
                              "Aucun outil automatique ne va jusqu'au paiement : seul le parcours réel le montre. C'est aussi un sujet RGPD (consentement actif) et CRM (qualité de la base Klaviyo).",
                              "Décocher la case par défaut (Paramètres > Paiement > Marketing).", "NC",
                              [["Opquast scripts sans IA", "non mesuré (règle écartée)"], ["Opquast basics (robot)", "non mesuré"], ["Parcours réel", "NC"]]))
        nu = en_ligne.get(nom, {}).get("nu", {})
        vides = [n["gabarit"] for n in nu.values() if "lue" in n.get("erreur", "")]
        if vides:
            items.append(item("faux négatif", "Nu", "Validateur Nu : pages à « 0 erreur » non lues", "validateur Nu",
                              f"Le validateur W3C a renvoyé 0 erreur et 0 avertissement sur {len(vides)} page(s) ({', '.join(vides)}). Les autres pages du même thème en comptent des dizaines ou des centaines.",
                              "Le validateur n'a pas pu lire ces pages (vérification Cloudflare ou limite d'appels) ; notre script comptait cette réponse vide comme une page valide.",
                              "Script corrigé : une réponse vide est désormais « non testée ». Refaire ces pages avec le validateur installé en local (vnu.jar), sans dépendre du service en ligne.", "NT",
                              [["Validateur Nu (brut)", "0 erreur"], ["Après vérification", "page non lue"]]))
        items.append(item("limite d'outil", "-", "Mention « Assisté par IA » sur des résultats de script", "eServices Manager",
                          "Dans l'audit « scripts sans IA », eServices Manager affiche « Jugé par une IA, résultat indicatif » sous nos résultats. Or ces résultats viennent de scripts, sans IA.",
                          "La mention dépend du type d'évaluation du critère Opquast natif, pas de la façon dont le résultat a été obtenu.",
                          "Le signaler à la restitution ; le commentaire de chaque résultat nomme l'outil réel.", "",
                          [["Opquast scripts sans IA", "résultats de scripts, affichés « Assisté par IA »"]]))

        def choisir(*types):
            return next((i for i in items if i["type"] in types), None)
        inatt = next((i for i in items if i["regle"] == "33"), None) or choisir("inattendu pertinent")
        top = [x for x in (choisir("faux positif"), choisir("faux négatif"), inatt) if x]
        sortie[nom] = {"accords_robot_scripts": accords, "ecarts": items, "trois_interessants": top,
                       "statut_sources": {k: (lambda v: ("NC" if v == {"NC"} else "C" if v == {"C"} else None))({x for x in par_regle[k].values() if x in ("C", "NC")}) or
                                          ("NA" if par_regle[k] and all(x == "NA" for x in par_regle[k].values()) else None)
                                          for k in par_regle},
                       "sources_par_regle": {k: compte_sources.get(k, []) for k in sorted((set(regles) | set(releve.get(nom, {}))) - ECARTEES - {str(x) for x in EXCL_SITES.get(nom, [])}, key=lambda x: int(x) if x.isdigit() else 999)},
                       "recoupement": {k: v for k, v in par_regle.items() if len([x for x in v.values() if x in ("C", "NC", "NA")]) >= 1}}
    # baromètre e-mail : recoupement des critères de la checklist par axe-core (HTML des e-mails) et checkdmarc (DNS)
    AXE_EM = {"html-has-lang": ["EM01"], "image-alt": ["EM02", "EM03"], "link-name": ["EM04", "EM08"], "color-contrast": ["EM06"]}
    sortie["_emails"] = {}
    em = lire("resultats/etat-*/etat.json").get("emails", {})
    out_em = lire("resultats/email-*/outils.json")
    dm = lire("resultats/email-*/checkdmarc.json").get("domaines", {})
    sec_em = lire("resultats/email-*/sources_secondes.json")
    for code_, crit_ in lire("resultats/email-*/lecture_ia_independante.json").items():
        for c_, v_ in crit_.items():
            sec_em.setdefault(code_, {}).setdefault(c_, []).append(v_ if len(v_) == 3 else [v_[0], v_[1], "Lecture IA indépendante (probabiliste)"])
    preuves_em: dict = {}
    for compte, crits in em.items():
        rec, ecarts = {}, []
        for code, o in out_em.items():
            viol = {v["regle"]: v["elements"] for v in o["axe"]["violations"]}
            for rid, cs in AXE_EM.items():
                for c in cs:
                    if c in crits and code in crits[c]["ecrans"]:
                        rec.setdefault(c, {}).setdefault(code, {})["Checklist (script et IA)"] = crits[c]["ecrans"][code][0]
                        rec[c][code]["axe-core"] = "NC" if rid in viol else "C"
        # deuxièmes sources e-mail (12/11) : IBM, axe target-size, mesures Playwright, popup affichée sur le site
        for code, par in sec_em.items():
            for c, l in par.items():
                if c.startswith("_") or c not in crits or code not in crits[c]["ecrans"]:
                    continue
                for st, preuve, outil in l:
                    if st not in ("C", "NC", "NA"):
                        continue
                    d_ = rec.setdefault(c, {}).setdefault(code, {})
                    d_["Checklist (script et IA)"] = crits[c]["ecrans"][code][0]
                    prev = d_.get(outil)
                    d_[outil] = "NC" if "NC" in (st, prev) else st
                    if st == "NC":
                        preuves_em.setdefault((c, code, outil), preuve)
        racine = next((v for k, v in dm.items() if k.count(".") == 1), None)
        sous = next((v for k, v in dm.items() if k.count(".") > 1), None)
        if racine and "EM25" in crits:
            ok = racine["spf"]["valide"] and racine["dmarc"]["valide"]
            for code, v in crits["EM25"]["ecrans"].items():
                if v[0] in ("C", "NC"):
                    rec.setdefault("EM25", {}).setdefault(code, {})["Checklist (script et IA)"] = v[0]
                    rec["EM25"][code]["checkdmarc"] = "C" if ok and (sous is None or sous["spf"]["valide"]) else "NC"
        for c, par in rec.items():
            for code, src in par.items():
                if {x for x in src.values() if x in ("C", "NC")} != {"C", "NC"}:
                    continue
                titre = crits[c]["titre"]
                base = [[a_, x] for a_, x in src.items()]
                if c == "EM25":
                    ecarts.append(item("limite d'outil", c, titre, "checkdmarc", f"Sur {code} : la checklist dit conforme (SPF et DMARC du domaine racine en place). checkdmarc ne trouve pas d'enregistrement SPF sur le sous-domaine d'envoi.",
                                       "Le sous-domaine est délégué à Klaviyo, qui envoie avec sa propre adresse de retour : le SPF se vérifie sur ce domaine de retour, que checkdmarc ne connaît pas. L'alignement DMARC passe par DKIM.",
                                       "Lire les en-têtes Authentication-Results d'un e-mail reçu (spf, dkim, dmarc = pass) pour trancher.", "C", base))
                elif src.get("axe-core") == "NC":
                    ecarts.append(item("faux négatif", c, titre, "axe-core / checklist", f"Sur {code} : axe-core relève un défaut, la checklist disait conforme.",
                                       "axe-core contrôle chaque élément du HTML ; la checklist juge par échantillon ou par IA.", "Retenir non conforme et corriger les éléments relevés.", "NC", base))
                elif "axe-core" not in src or len(src) > 2:
                    autres = [a_ for a_, x in src.items() if a_ != "Checklist (script et IA)" and x in ("C", "NC")]
                    nc_ = [a_ for a_ in autres if src[a_] == "NC"]; c_ = [a_ for a_ in autres if src[a_] == "C"]
                    det = "; ".join(preuves_em.get((c, code, a_), "") for a_ in nc_)
                    chk = src.get("Checklist (script et IA)")
                    retenu = "NC" if nc_ and (chk == "NC" or len(nc_) >= len(c_)) else chk if chk in ("C", "NC") else ("NC" if nc_ else "C")
                    ecarts.append(item("écart à vérifier" if retenu == chk else ("faux négatif" if retenu == "NC" else "faux positif"), c, titre, " / ".join(sorted(src)),
                                       f"Sur {code} : la checklist dit {STATUT_LIB.get(chk, chk)} ; non conforme selon {', '.join(nc_) or 'aucun outil'}, conforme selon {', '.join(c_) or 'aucun outil'}." + (f" Détail : {det}." if det else ""),
                                       "Les outils ne mesurent pas la même chose : présence ou calcul automatique d'un côté, jugement de pertinence de la checklist de l'autre. Un échec mesuré sur un élément précis l'emporte sur un jugement global.",
                                       "Vérifier l'élément cité ; retenir le statut indiqué et le corriger s'il est non conforme.", retenu, base))
                else:
                    ecarts.append(item("écart à vérifier", c, titre, "axe-core / checklist", f"Sur {code} : la checklist dit non conforme, axe-core ne relève rien.",
                                       "Le critère de la checklist est plus large que le test d'axe-core (pertinence de l'alternative, du libellé ou du contraste sur image), qu'aucun outil ne juge.",
                                       "Garder le jugement de la checklist (IA puis humain) ; axe-core ne couvre que la présence.", "NC", base))
        sources_em = {c: sorted({a_ for par in rec.get(c, {}).values() for a_, x in par.items() if x in ("C", "NC", "NA")} or {"Checklist (script et IA)"}) for c in crits}
        sortie["_emails"][compte] = {"recoupement": rec, "ecarts": ecarts, "sources_par_critere": sources_em}
    d = RACINE / "resultats" / f"lecture-critique-{date.today():%Y-%m-%d}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "lecture.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: (v["accords_robot_scripts"], len(v["ecarts"]), [x["regle"] for x in v["trois_interessants"]]) for k, v in sortie.items() if not k.startswith("_")})
    print({k: [(x["regle"], x["type"]) for x in v["ecarts"]] for k, v in sortie["_emails"].items()})


if __name__ == "__main__":
    main()
