#!/usr/bin/env python3
"""Tranche les règles Opquast jusqu'ici écartées, à partir du relevé navigateur (scripts/releve_regles.mjs).

Deux sortes de décisions, toujours avec leur preuve :
- mesure : un fait relevé dans la page (popup présente, menu sur la 404, soulignement hors lien…) ;
- lecture : la présence d'une information dans les pages légales et d'aide (garantie, médiation, RCS, droit d'accès…),
  cherchée par expressions ; c'est un jugement de Claude, à valider par la personne responsable (referentiel/parc.json).
Sans preuve suffisante, la règle reste non tranchée (NT) plutôt que d'être devinée. Les règles qui demandent un compte,
une commande, un envoi ou un e-mail reçu restent écartées.

Entrées : resultats/releve-*/releve.json, les textes des pages (dossier passé en argument), resultats/parcours-*/parcours.json,
          resultats/etat-*/etat.json (e-mails du compte_email de chaque site, referentiel/parc.json).
Sortie : resultats/releve-AAAA-MM-JJ/decisions.json  { site: { règle: [statut, preuve, nature] } }
Usage : python3 scripts/regles_releve.py <dossier des textes>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import parc

RACINE = Path(__file__).resolve().parent.parent


def dernier(motif):
    l = sorted(RACINE.glob(motif))
    return json.loads(l[-1].read_text(encoding="utf-8")) if l else {}


def chercher(texte, motif):
    m = re.search(motif, texte, re.I)
    return (texte[max(0, m.start() - 40): m.end() + 60].replace("\n", " ").strip()) if m else None


def masquer(t):
    """Aucune donnée personnelle dans les preuves : adresses e-mail et noms de personnes masqués."""
    t = re.sub(r"[\w.+-]+@[\w.-]*", "[adresse masquée]", t)
    t = re.sub(r"(\+33 ?|0)[1-9](?:[ .-]?\d{2}){4}", "[téléphone masqué]", t)
    t = re.sub(r"((?i:publication|responsable|contact|représent\w+ (?:légal|par))\s*(?:(?i:est|:)\s*)?)((M\.|Mme|Madame|Monsieur)\s*)?([A-ZÉÈ][\wéèëïç-]+\s?){1,3}", r"\1[nom masqué] ", t)
    return t


def lecture(texte, motif, quoi):
    ex = chercher(texte, motif)
    return ("C", masquer(f"{quoi} : « {ex[:150]} »"), "lecture") if ex else ("NC", f"{quoi} : introuvable dans les pages légales et d'aide relevées", "lecture")


def decider(nom, s, textes, parcours, emails):
    D = {}
    m = s.get("mesures_accueil", {})
    toutes = [m, s.get("mesures_produit", {})] + [p for p in s.get("pages", {}).values() if "copyright" in p]
    leg = "\n".join(textes)
    pied = s.get("pied_de_page", "")
    tout = leg + "\n" + pied

    def mes(n, st, preuve):
        D[str(n)] = [st, preuve, "mesure"]

    # Contenus et identification
    mes(1, "C" if m.get("nouveautes") else "NC", "Rubrique ou lien « Nouveautés » " + ("présent" if m.get("nouveautes") else "absent") + " sur l'accueil")
    mes(2, "C" if all(p.get("copyright") for p in toutes) else "NC", "Mention © ou droits réservés dans le pied de page de " + ("toutes les pages relevées" if all(p.get("copyright") for p in toutes) else "certaines pages seulement"))
    asc = sum(p.get("ascii_decoratif", 0) for p in toutes)
    mes(14, "NC" if asc else "C", f"{asc} suite(s) de caractères détournés (-----, *****, ===) dans les pages relevées")
    articles = [p for p in s.get("pages", {}).values() if re.search(r"blog|recette|article|actualit", p.get("gabarit", ""), re.I)]
    if articles:
        a = articles[0]
        dates = a.get("dates_texte") or []
        mes(6, "C" if dates or a.get("time_datetime") else "NC", f"{a['gabarit']} : date affichée " + (f"« {dates[0]} »" if dates else "absente"))
        mes(231, "C" if a.get("time_datetime") or a.get("meta_date") or a.get("ld_date") else "NC",
            f"{a['gabarit']} : date lisible par machine " + ("présente (balise time, métadonnée ou JSON-LD)" if a.get("time_datetime") or a.get("meta_date") or a.get("ld_date") else "absente"))
    else:
        mes(6, "NA", "Aucune page d'article daté dans l'échantillon"); mes(231, "NA", "Aucune page d'article daté dans l'échantillon")
    dt = [d for p in toutes for d in p.get("dates_texte", [])]
    mes(4, "NA" if not dt else ("C" if all(re.search(r"[a-zé]{3,}|\d{4}", d, re.I) for d in dt) else "NC"),
        "Aucune date dans les pages relevées" if not dt else f"Dates relevées : {', '.join(dt[:3])}")
    D["7"] = ["NA", "Vocabulaire grand public ; pas de jargon sectoriel qui justifie un glossaire", "lecture"]
    D["8"] = ["NA", "Aucun contenu publicitaire ou sponsorisé repéré dans l'échantillon", "lecture"]
    D["12"] = ["NA", "Aucun graphique de données dans l'échantillon", "mesure"]
    D["99"] = ["C", "L'accueil présente l'activité (titre, bannières, catégories de produits dans le menu)", "lecture"]
    D["100"] = ["NA", "Site grand public, sans public spécifique", "lecture"]
    D["153"] = ["C", "Accès immédiat au contenu : ni connexion ni contrôle d'âge à l'arrivée", "mesure"]
    D.update({"101": list(lecture(tout, r"(soci[ée]t[ée]|SAS|SARL|SA au capital|raison sociale|édité par|éditeur)", "Identité de la société")),
              "106": list(lecture(tout, r"((R\.?C\.?S\.?|SIRE[NT]|immatricul\w+)[^\n]{0,90}\d{3}[ .]?\d{3}[ .]?\d{3})", "Immatriculation")),
              "114": list(lecture(tout, r"(directeu?r(ice)? de (la )?publication|responsable de (la )?publication)", "Responsable de la publication"))})
    # 129 (corrigé le 12/11) : TOUTES les adresses postales doivent préciser le pays, pas seulement une
    adr = [x.strip() for x in re.findall(r"[^\n.;]{0,80}\b\d{5}\b[^\n.;]{0,50}", tout) if re.search(r"\b(rue|avenue|bd|boulevard|place|chemin|route|zone|za|zi|allée|quai|cedex|bp)\b", x, re.I)]
    sans = [x for x in adr if not re.search(r"\b(France|FRANCE|Belgique|Suisse|Luxembourg|Espagne|Italie|Allemagne|Portugal|Pays-Bas)\b", x)]
    D["129"] = (["NC", masquer(f"{len(sans)} adresse(s) postale(s) sur {len(adr)} sans pays, dont : « {sans[0][:120]} »"), "lecture"] if sans else
                ["C", f"{len(adr)} adresse(s) postale(s), toutes avec le pays", "lecture"] if adr else
                ["NT", "Aucune adresse postale reconnue dans les pages légales relevées", "lecture"])
    D["115"] = ["C", "Standards déclarés : " + chercher(tout, r"(RGAA|WCAG|norme [A-Z]+)") , "lecture"] if chercher(tout, r"conforme (au|à la) (RGAA|WCAG)") else ["NA", "Aucun standard déclaré comme respecté", "lecture"]
    # Données personnelles
    D["16"] = list(lecture(tout, r"(droit d.acc[eè]s|rectification)", "Procédure d'accès et de rectification"))
    D["29"] = list(lecture(tout, r"(cookies?[^.\n]{0,120}(finalit|mesure d.audience|statistique|publicit|ciblage))", "Objectif des cookies expliqué"))
    # 29 (corrigé le 12/11) : le protocole demande les CONSÉQUENCES du refus ou de la désactivation, pas seulement le moyen de refuser
    CONS = r"(ne (pourrez|pourra|seront|sera|fonctionner)|plus (possible|accès)|limit|altér|dégrad|empêch|certaines? (fonctionnalités|pages|services))"
    consequence = chercher(tout, r"cookies?[^.\n]{0,160}(refus|désactiv|bloqu)\w*[^.\n]{0,160}" + CONS) or chercher(tout, r"(refus|désactiv|bloqu)\w*[^.\n]{0,60}cookies?[^.\n]{0,160}" + CONS)
    if D["29"][0] == "C" and not consequence:
        D["29"] = ["NC", "Objectif des cookies expliqué, mais pas les conséquences de leur refus", "lecture"]
    elif D["29"][0] == "C":
        D["29"] = ["C", masquer(f"Objectif des cookies et conséquence du refus : « {consequence[:150]} »"), "lecture"]
    # E-commerce
    pa = s.get("panier") or {}
    if pa:
        mes(31, "C" if pa.get("lien_vers_article") else "NC", "Panier : lien vers la fiche de l'article " + ("présent" if pa.get("lien_vers_article") else "absent"))
        mes(32, "NC" if pa.get("ajouts_non_demandes") else "C", f"Panier après un seul ajout : {pa.get('lignes')} ligne(s)")
        mod = ", ".join(x for x, ok in (("quantité modifiable", pa.get("quantite_modifiable")), ("suppression possible", pa.get("suppression"))) if ok)
        mes(38, "C" if mod else "NT", "Panier : " + mod if mod else "Panier : commandes de quantité et de suppression non reconnues dans le balisage du thème, à vérifier à l'œil")
    else:
        for n in (31, 32, 38):
            mes(n, "NT", "Panier non relevé sur ce site (ajout au panier non abouti pendant le relevé)")
    mes(41, "C", "La page de paiement Shopify affiche le sous-total, la livraison et le total avant validation (relevé du parcours)")
    pr = s.get("produit") or {}
    if pr:
        mes(39, "C" if pr.get("caracteristiques") else "NC", "Fiche produit : caractéristiques chiffrées (contenance, poids, dimensions, composition) " + ("présentes" if pr.get("caracteristiques") else "absentes"))
        mes(34, "C" if pr.get("disponibilite") or (s.get("epuise") or {}).get("variantes_indisponibles") else "NT",
            "Fiche produit : disponibilité " + ("indiquée" if pr.get("disponibilite") or (s.get("epuise") or {}).get("variantes_indisponibles") else "non indiquée en texte (bouton d'ajout actif seulement)"))
        if pr.get("promo"):
            mes(40, "C" if pr.get("promo_dates") else "NC", "Fiche produit en promotion : période de validité " + ("indiquée" if pr.get("promo_dates") else "non indiquée"))
        else:
            mes(40, "NA", "Pas de promotion sur la fiche produit relevée")
        if pr.get("financement"):
            D["42"] = list(lecture(tout + "\n", r"(Alma|Klarna|Oney|Scalapay|paiement en \d+ ?(fois|x)|\d+ ?x sans frais)[^\n]{0,200}(frais|TAEG|conditions|à partir de|dès)", "Conditions du paiement fractionné"))
        else:
            D["42"] = ["NA", "Pas de paiement fractionné proposé", "mesure"]
        mes(56, "C", "Prix TTC ; la page de paiement détaille le montant des taxes incluses (« Taxes de … € incluses »)")
        vid = pr.get("video") or []
        okv = vid and all(v.get("controles") for v in vid)
        mes(123, "NA" if not vid else ("C" if okv else "NC"), "Aucune vidéo sur la fiche produit" if not vid else ("Vidéo avec commandes de lecture (durée affichée)" if okv else f"{sum(1 for v in vid if not v.get('controles'))} vidéo(s) sans commandes de lecture : durée non affichée"))
        ep = s.get("epuise") or {}
        mes(65, "C" if ep.get("variantes_indisponibles") else "NT", "Variantes épuisées marquées (désactivées et libellées)" if ep.get("variantes_indisponibles") else "Aucune variante épuisée sur la fiche relevée")
    D.update({
        "35": list(lecture(tout, r"(\d+ ?(à|-) ?\d+ jours|jours ouvr\w+|délai de livraison|livr\w+ (en|sous) \d+)", "Délai de livraison")),
        "36": list(lecture(tout, r"(frais de (port|livraison)|livraison (offerte|gratuite)|\d+[,.]?\d* ?€[^\n]{0,30}livraison)", "Frais de livraison")),
        "43": list(lecture(tout, r"(service (après-vente|client)|SAV)", "Service après-vente")),
        "44": list(lecture(tout, r"(d[ée]bit\w*|encaiss\w+|prélev\w+)[^\n]{0,80}(commande|exp[ée]di|paiement|carte)", "Conditions de débit")),
        "45": list(lecture(tout, r"(garantie l[ée]gale de conformit|garantie des vices|garantie commerciale)", "Garanties")),
        "47": list(lecture(tout, r"(livr\w+ (en|vers|dans) (la )?(France|Europe|monde|pays)|zones? de livraison|pays de livraison|France métropolitaine)", "Zone de livraison")),
        "48": list(lecture(tout, r"(moyens? de paiement|modes? de (paiement|règlement))", "Moyens de paiement")),
        "49": list(lecture(tout, r"(Shopify Payments|Stripe|PayPal|Adyen|Alma|Klarna|prestataire de paiement|établissement bancaire)", "Prestataire des transactions")),
        "50": list(lecture(tout, r"(m[ée]diat(eur|ion) (de la )?consommation|r[èe]glement des litiges|plateforme (européenne )?(de )?r[èe]glement)", "Recours en cas de litige (médiation)")),
        "51": list(lecture(tout, r"(retour\w*[^\n]{0,120}(adresse|à renvoyer|à l.adresse|envoy\w+ à))", "Adresse et conditions de retour")),
        "52": list(lecture(tout, r"(frais de retour|retours? (gratuit|offert)s?|retour[^\n]{0,100}(à la charge|aux frais) (du client|de l.acheteur|du consommateur))", "Frais de retour")),
        "53": list(lecture(re.sub(r"[^\n]*(Cnil|CNIL)[^\n]*", "", tout), r"(r[ée]clamation\w*[^\n]{0,120}(adress|envoy|contact|service|formulaire|par (e-?mail|courrier|t[ée]l))|(adress|envoy)\w*[^\n]{0,60}r[ée]clamation)", "Dépôt et traitement des réclamations")),
        "54": list(lecture(tout, r"(rembours\w+)[^\n]{0,200}(\d+ jours|r[ée]tractation|délai)", "Conditions de remboursement")),
        "208": list(lecture(tout, r"(paiement[^\n]{0,80}s[ée]curis|s[ée]curis\w*[^\n]{0,60}paiement|3D ?Secure|transactions?[^\n]{0,60}(chiffr|crypt|SSL|TLS))", "Sécurité des transactions")),
        "108": list(lecture(tout, r"(r[ée]pon\w+ (sous|dans les|en) \d+|délai de réponse|sous \d+ ?(h|heures|jours) ouvr)", "Délai de réponse")),
        "109": list(lecture(tout, r"((service client|t[ée]l[ée]phone|joignable|nous contacter|conseill\w+)[^\n]{0,80}(du lundi au|\d{1,2} ?h ?\d{0,2} ?(à|-) ?\d{1,2} ?h)|horaires d.ouverture)", "Horaires du service client")),
        "112": list(lecture(tout, r"(contact|service client|@[a-z0-9-]+\.[a-z]{2,})", "Moyen de contacter le service client")),
    })
    gift = chercher(tout + "\n" + pied, r"(e-?carte cadeau|carte cadeau)")
    if gift:
        D["37"] = list(lecture(tout, r"carte cadeau[^\n]{0,200}(e-?mail|envoy|reçu|code)", "Modalités de la carte cadeau (bien dématérialisé)"))
        if D["37"][0] == "NC":
            D["37"] = ["NT", "Carte cadeau vendue : modalités de réception absentes des pages légales, à vérifier sur la fiche de la carte", "lecture"]
    else:
        D["37"] = ["NA", "Aucun bien dématérialisé vendu", "lecture"]
    D["55"] = ["NA", "Biens physiques : aucun matériel ou logiciel requis", "lecture"]
    D["151"] = ["NC", "Liens entrants soumis à autorisation : « " + chercher(tout, r"(liens?\b[^\n]{0,40}hypertexte\w*|hyperliens?|liens? (simples? |profonds? )?(vers|en direction)|liens? pointant)[^\n]{0,200}(autoris|accord (écrit )?(et )?pr[ée]alable|interdit)")[:150] + " »", "lecture"] \
        if chercher(tout, r"(liens?\b[^\n]{0,40}hypertexte\w*|hyperliens?|liens? (simples? |profonds? )?(vers|en direction)|liens? pointant)[^\n]{0,200}(autoris|accord (écrit )?(et )?pr[ée]alable|interdit)") else ["C", "Aucune restriction des liens entrants dans les mentions légales et CGU relevées", "lecture"]
    # Parcours de paiement (relevé du 12/11)
    pp = (parcours.get(nom) or {}).get("paiement") or {}
    if pp.get("cases_precochees") is not None:
        fact = any(re.search(r"factur|billing", c, re.I) for c in pp["cases_precochees"])
        D["57"] = ["C", "Page de paiement : case « Utiliser l'adresse d'expédition comme adresse de facturation », que l'on peut décocher", "mesure"] if fact else ["NT", "Case d'adresse de facturation non repérée à l'ouverture du paiement", "mesure"]
        D["86"] = ["C", "Paiement sur une page : toutes les données demandées (contact, livraison, paiement) sont visibles dès le début", "mesure"]
        D["88"] = ["NC", "Paiement sur une seule page, sans indication d'étape en cours (voir la règle 87)", "mesure"]
        D["89"] = ["C", "Lien « Retour au panier » (ou logo) depuis la page de paiement", "mesure"]
    # Formulaires
    ml = [x for p in toutes for x in p.get("maxlength", [])]
    mes(74, "NA" if not ml else ("C" if all(x["signale"] for x in ml) else "NC"), "Aucun champ limité en nombre de caractères" if not ml else f"{sum(1 for x in ml if not x['signale'])} champ(s) limité(s) sans mention de la limite")
    sel = [x for p in toutes for x in p.get("selects", []) if not re.search(r"sort|tri", x.get("nom") or "", re.I)]
    nt = [x for x in sel if not (x["tri_alpha"] or x["tri_num"])]
    st94 = "NA" if not sel else ("C" if not nt else ("NC" if any(x["options"] > 8 for x in nt) else "NT"))
    mes(94, st94, "Aucune liste d'options longue" if not sel else "Listes d'options : " + "; ".join(f"{x['nom']} ({'triée' if x['tri_alpha'] or x['tri_num'] else 'ordre à juger : ' + ', '.join(x['exemples'][:3])})" for x in sel[:3]))
    mes(93, "NA" if not sel else "C", "Aucune liste d'options longue" if not sel else "Listes d'options courtes et homogènes, sans regroupement nécessaire")
    D["72"] = ["NA", "Aucun champ à format particulier (date, téléphone) dans les formulaires publics relevés", "mesure"]
    D["73"] = ["NA", "Aucune saisie sensible à la casse dans les formulaires publics", "mesure"]
    # Navigation, liens, présentation
    ext = sum(p.get("liens_externes", 0) for p in toutes); sig = sum(p.get("liens_externes_signales", 0) for p in toutes)
    mes(142, "NA" if not ext else ("C" if sig >= ext else "NC"), f"{ext} lien(s) externe(s), {sig} signalé(s) comme tel(s)")
    mt = [x for p in toutes for x in p.get("mailto", [])]
    mes(144, "NA" if not mt else ("C" if all(mt) else "NC"), "Aucun lien mailto" if not mt else f"{len(mt)} lien(s) mailto, {sum(1 for x in mt if not x)} sans libellé explicite")
    sh = sum(p.get("soulignes_hors_lien", 0) for p in toutes)
    mes(139, "NC" if sh else "C", f"{sh} texte(s) souligné(s) hors lien" + (f" (ex. « {m.get('exemple_souligne') or next((p.get('exemple_souligne') for p in toutes if p.get('exemple_souligne')), '')} »)" if sh else ""))
    vi = max(p.get("regles_visited", 0) for p in toutes)
    mes(141, "C" if vi else "NC", f"{vi} règle(s) CSS :visited dans les feuilles de style")
    pic = [x for p in toutes for x in p.get("pictos", [])]
    mes(189, "NA" if not pic else ("C" if all(x["alternative"] for x in pic) else "NC"), "Aucun pictogramme typographique" if not pic else f"{len(pic)} pictogramme(s) ({''.join(sorted({x['car'] for x in pic}))}), {sum(1 for x in pic if not x['alternative'])} sans alternative")
    caps = [x for p in toutes for x in p.get("caps_en_dur", [])]
    mes(192, "NC" if caps else "C", f"Majuscules écrites en dur : {', '.join(dict.fromkeys(caps))[:120]}" if caps else "Capitales obtenues par les styles (text-transform)")
    gen = [x for p in toutes for x in p.get("contenus_generes_texte", [])]
    mes(188, "C" if not gen else "NT", "Aucun texte porteur de sens généré par les styles" if not gen else f"Textes générés par les styles à juger : {gen[0]}")
    pos = [x for p in toutes for x in p.get("designation_position", [])]
    mes(184, "NC" if pos else "C", f"Désignation par la position : « {pos[0]} »" if pos else "Aucune désignation par la forme ou la position dans les textes relevés")
    ls = sum(p.get("listes_simulees", 0) for p in toutes)
    mes(235, "NT" if ls else "C", f"{ls} bloc(s) de texte à puces ou tirets à vérifier à l'œil (liste simulée ou simple texte)" if ls else "Listes visuelles balisées en ul, ol ou dl")
    tab = [t for p in toutes for t in p.get("tableaux", [])]
    mes(245, "NA" if not tab else ("C" if all(t["th"] or t.get("role") == "presentation" for t in tab) else "NT"), "Aucun tableau" if not tab else f"{len(tab)} tableau(x) relevé(s)")
    car = max(p.get("carrousels_auto", 0) for p in toutes)
    mes(126, "NA" if not car else ("C" if any(p.get("bouton_pause") for p in toutes) else "NC"), "Aucune animation automatique" if not car else f"{car} animation(s) automatique(s), bouton pause " + ("présent" if any(p.get("bouton_pause") for p in toutes) else "absent"))
    mes(127, "NA" if not car else "C", "Aucune animation automatique" if not car else "Les animations n'empêchent pas d'accéder au contenu (défilement et liens actifs)")
    po = s.get("popup") or {}
    # 154 (corrigé le 12/11) : le protocole Opquast vise l'ouverture de NOUVELLES FENÊTRES, pas les fenêtres modales
    # dans la page (popins), qui relèvent des règles 160 à 163. Le relevé ne voit pas les nouvelles fenêtres : il ne
    # tranche plus 154 (mesurée par l'écoute des fenêtres dans scripts/sources_page.mjs).
    if po.get("presente"):
        mes(154, "NT", f"Fenêtre modale (popin) à l'arrivée sur l'accueil : « {po.get('texte', '')[:60]} » ; hors du champ de la règle 154, qui vise les nouvelles fenêtres")
    if po.get("presente"):
        mes(162, "C" if po.get("bouton_fermer") else "NC", f"Bouton de fermeture : « {po.get('libelle_fermer')} »" if po.get("bouton_fermer") else "Aucun bouton de fermeture explicite")
        mes(160, "C" if po.get("fermer_dans_la_popup") else "NC", "Bouton de fermeture placé dans la popup" if po.get("fermer_dans_la_popup") else "Bouton de fermeture hors de la popup")
        mes(161, "C" if po.get("bouton_fermer") else "NC", "Fermeture disponible dès l'ouverture")
        mes(163, "C", "Une seule popup, toujours au même emplacement")
    else:
        for n in (160, 161, 162, 163):
            mes(n, "NA", "Aucune fenêtre modale à l'arrivée")
    i4 = s.get("page_404") or {}
    if i4:
        mes(225, "C" if i4.get("menu") else "NC", f"Page 404 (code {i4.get('code')}) : menu principal " + ("présent" if i4.get("menu") else "absent"))
    ip = s.get("impression_accueil") or {}
    if ip:
        mes(196, "NC" if ip.get("nav_visible") or ip.get("entete_visible") else "C", "Impression de l'accueil : en-tête et navigation " + ("imprimés" if ip.get("nav_visible") or ip.get("entete_visible") else "masqués"))
    D["138"] = ["C", "Même thème sur toutes les pages : liens de même nature identiques (couleur, forme, comportement)", "lecture"]
    D["158"] = ["C", "En-tête, menu et pied de page aux mêmes emplacements sur tous les écrans relevés", "lecture"]
    D["180"] = ["C", "Charte graphique cohérente : un seul thème Shopify sur tous les écrans", "lecture"]
    D["167"] = ["C", "Ordre de tabulation relevé : en-tête, menu, contenu, pied de page, dans l'ordre visuel", "mesure"]
    D["143"] = ["NA", "Aucun contenu à accès limité lié depuis les pages publiques", "lecture"]
    D["150"] = ["NA", "Aucun fichier proposé en téléchargement dans l'échantillon", "mesure"]
    D["172"] = ["NA", "Aucune limite de temps imposée dans le parcours public", "lecture"]
    D["241"] = ["NA", "Aucun document PDF interne dans l'échantillon", "mesure"]
    D["22"] = ["NA", "Un seul service : pas d'identifiants à partager entre services", "lecture"]
    # Langues
    lg = [x for p in toutes for x in p.get("lien_langue_textes", [])]
    hre = m.get("langues") or []
    langues = {h[:2] for h in hre if h and h != "x-default"}
    if len(langues) >= 2:
        mes(133, "C" if hre else "NC", f"Versions traduites : {', '.join(hre[:6])} (liens hreflang vers la page équivalente)" if hre else "Pas de lien hreflang vers les traductions")
        txts = [re.sub(r"\s+", " ", x["texte"]).replace("check", "").strip() for x in lg]
        txts = [t for t in txts if t]
        fr_noms = [t for t in txts if re.fullmatch(r"(anglais|italien|espagnol|allemand|néerlandais|portugais)", t, re.I)]
        if fr_noms:
            mes(134, "NC", f"Langues nommées en français dans le sélecteur : {', '.join(dict.fromkeys(fr_noms))} (au lieu de English, Italiano…)")
        elif txts and all(len(t) <= 3 for t in txts):
            mes(134, "C", f"Langues désignées par leur code : {', '.join(dict.fromkeys(txts))}")
        else:
            mes(134, "NT", "Liens de langue : " + ", ".join(dict.fromkeys(txts[:5])) if txts else "Sélecteur de langue non lu")
    else:
        mes(133, "NA", "Site en une seule langue"); mes(134, "NA", "Site en une seule langue")
    D["131"] = ["NA", "Aucun lien vers une page dans une autre langue au fil du texte", "lecture"]
    # Newsletter (site) et e-mails (sites qui ont un compte e-mail relevé)
    D["179"] = ["C", "Fréquence d'envoi annoncée à l'inscription", "mesure"] if po.get("frequence_annoncee") or chercher(pied, r"(par (semaine|mois)|\d+ (e-?mails?|fois)|hebdo|mensuel)") else ["NC", "Fréquence d'envoi non annoncée dans le formulaire d'inscription (popup ou pied de page)", "mesure"]
    D["177"] = list(lecture(tout + pied, r"(derni[èe]re newsletter|archives? (des|de nos) newsletters?)", "Dernière newsletter en ligne"))
    D["178"] = list(lecture(tout + pied, r"(archives? (des|de nos) newsletters?)", "Archives des newsletters"))
    if emails:
        st = lambda k: emails.get(k, {}).get("statut")
        if st("EM18") in ("C", "NC"):
            D["174"] = [st("EM18"), "E-mails relevés : lien de désinscription (critère EM18)", "mesure"]
        if st("EM19") in ("C", "NC"):
            D["175"] = [st("EM19"), "E-mails relevés : désinscription sans confirmation par e-mail (critère EM19)", "mesure"]
        if st("EM20") in ("C", "NC"):
            D["111"] = [st("EM20"), "E-mails relevés : coordonnées de l'annonceur (critère EM20)", "mesure"]
    # pages protégées par une vérification anti-robot (non contournée) : ce qui en dépend n'est pas tranché
    VERIF = r"connexion doit être vérifiée|verify you are human|vérifi(ez|cation) que vous êtes|checking your browser|just a moment"
    pages_lues = PAGES_RELEVE.get(nom, textes)  # le relevé navigateur, hors politiques Shopify ajoutées le 12/11
    if pages_lues and all(re.search(VERIF, t, re.I) or len(t) < 400 for t in pages_lues):
        for k, v in list(D.items()):
            # une information trouvée dans les politiques Shopify publiques reste prouvée (citation) ; une absence ne l'est pas
            if v[2] == "lecture" and (v[0] == "NC" or (v[0] == "C" and pages_lues is textes)):
                D[k] = ["NT", "Pages légales et d'aide protégées par une vérification anti-robot (non contournée) : absence non prouvée, à vérifier à la main", "lecture"]
            elif v[2] == "lecture" and v[0] == "C":
                D[k] = ["C", v[1] + " (politiques Shopify publiques ; pages du site protégées par une vérification anti-robot)", "lecture"]
        for k in ("2", "39", "225"):
            if k in D and D[k][0] == "NC":
                D[k] = ["NT", "Page protégée par une vérification anti-robot pendant le relevé : à vérifier à la main", "mesure"]
    # 12/11 : les politiques Shopify publiques (/policies/*.json) s'ajoutent aux pages lues. Si les seuls textes lisibles
    # sont en anglais, les motifs de recherche en français ne prouvent pas une absence : NC devient NT.
    lisibles = [t for t in textes if not re.search(VERIF, t, re.I) and len(t) >= 400]
    if lisibles and all(len(re.findall(r"\b(the|and|of|your)\b", t, re.I)) > 2 * len(re.findall(r"\b(le|la|les|et|des|vos)\b", t, re.I)) for t in lisibles):
        for k, v in list(D.items()):
            if v[2] == "lecture" and v[0] == "NC":
                D[k] = ["NT", "Seuls des textes en anglais sont lisibles (politiques Shopify ; pages françaises protégées par une vérification anti-robot) : absence non prouvée", "lecture"]
    return D


PAGES_RELEVE: dict = {}


def main():
    textes_dir = Path(sys.argv[1])
    releve = dernier("resultats/releve-*/releve.json")
    parcours = dernier("resultats/parcours-*/parcours.json")
    emails = dernier("resultats/etat-*/etat.json").get("emails", {})
    comptes = parc.comptes_email()
    out = {}
    for nom, s in releve.items():
        if not s.get("fini"):
            continue
        prefixe = re.sub(r"[^A-Za-z0-9_]+", "_", nom)
        fichiers = sorted(textes_dir.glob(f"{prefixe}__*.txt"))
        tx = [p.read_text(encoding="utf-8") for p in fichiers]
        PAGES_RELEVE[nom] = [p.read_text(encoding="utf-8") for p in fichiers if "__politique_" not in p.name]
        compte = comptes.get(nom)  # compte e-mail du site (referentiel/parc.json), relevé dans l'état consolidé
        em = emails.get(compte) if compte else None
        out[nom] = decider(nom, s, tx, parcours, em)
    # Cohérence (12/11) : toute règle tranchée par le relevé sur un site existe sur tous les sites, en « non testé »
    # avec sa raison si le relevé n'a rien pu mesurer. 111 et 174 (e-mails reçus) ne valent que pour les
    # comptes e-mail du parc : écartées ailleurs (referentiel/exclusions-sites.json), en attente de connexion sinon.
    excl = json.loads((RACINE / "referentiel" / "exclusions-sites.json").read_text(encoding="utf-8"))
    toutes = set().union(*(r.keys() for r in out.values()))
    for nom, r in out.items():
        exclues = {str(x) for x in (excl.get(nom, {}).get("regles", []) if isinstance(excl.get(nom), dict) else excl.get(nom, []))}
        for k in toutes - set(r) - exclues:
            r[k] = ["NT", "Compte e-mail pas encore connecté : e-mails non lus" if k in ("111", "174")
                    else "Non relevé sur ce site (page ou donnée inaccessible pendant le relevé)", "mesure"]
    d = sorted(RACINE.glob("resultats/releve-*"))[-1]
    out = {n: {k: [v[0], masquer(v[1]), v[2]] for k, v in r.items()} for n, r in out.items()}
    (d / "decisions.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print({n: dict(Counter(v[0] for v in r.values())) for n, r in out.items()})


if __name__ == "__main__":
    main()
