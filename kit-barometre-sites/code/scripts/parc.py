"""Lecture du parc mesuré (referentiel/parc.json), seule source de vérité des sites et de la personne responsable.

Chaque site : nom (identique à la colonne service de scripts/ecrans_en_ligne.csv), code_esm (code du service dans
eServices Manager), prefixe_pages (préfixe des codes de page ESM), plateforme (« shopify » ou autre : les sources
propres à Shopify ne tournent que sur les sites Shopify), compte_client_hors_site (compte client hébergé hors du site,
non testé), prefixe_langue (« /fr » si la version auditée est sous un préfixe), compte_email (compte e-mail associé, vide
sinon). Au niveau du parc : responsable (personne qui valide les décisions) et auditeur_esm (son code court dans
eServices Manager, Paramètres > Utilisateurs).

Le fichier est lu à chaque appel, depuis RACINE (remplacée par les tests) ou depuis le chemin donné : un fichier
.json, ou la racine d'un kit (son referentiel/parc.json est lu).
"""
from __future__ import annotations

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
RESPONSABLE_DEFAUT = "la personne responsable du baromètre"
CHAMPS = ("nom", "code_esm", "prefixe_pages", "plateforme", "compte_client_hors_site", "prefixe_langue", "compte_email")


def fichier(chemin: Path | None = None) -> Path:
    """Chemin de parc.json : le fichier donné, le parc.json d'une racine donnée, ou celui de RACINE."""
    c = Path(chemin) if chemin else RACINE
    return c if c.suffix == ".json" else c / "referentiel" / "parc.json"


def charger(chemin: Path | None = None) -> dict:
    """Contenu de parc.json (parc vide si le fichier manque)."""
    f = fichier(chemin)
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"responsable": RESPONSABLE_DEFAUT, "sites": []}


def sites(chemin: Path | None = None) -> list[dict]:
    return charger(chemin).get("sites", [])


def noms(chemin: Path | None = None) -> list[str]:
    return [s["nom"] for s in sites(chemin)]


def responsable(chemin: Path | None = None) -> str:
    return charger(chemin).get("responsable") or RESPONSABLE_DEFAUT


def auditeur_esm(chemin: Path | None = None) -> str:
    """Code court de la personne responsable dans eServices Manager (vide si non renseigné)."""
    return charger(chemin).get("auditeur_esm", "")


def par_nom(chemin: Path | None = None) -> dict[str, dict]:
    return {s["nom"]: s for s in sites(chemin)}


def codes_esm(chemin: Path | None = None) -> dict[str, str]:
    """Nom du site -> code du service dans eServices Manager."""
    return {s["nom"]: s["code_esm"] for s in sites(chemin)}


def shopify(chemin: Path | None = None) -> list[str]:
    """Noms des sites sur Shopify."""
    return [s["nom"] for s in sites(chemin) if s.get("plateforme", "shopify") == "shopify"]


def hors_site(chemin: Path | None = None) -> set[str]:
    """Noms des sites dont le compte client est hébergé hors du site."""
    return {s["nom"] for s in sites(chemin) if s.get("compte_client_hors_site")}


def comptes_email(chemin: Path | None = None) -> dict[str, str]:
    """Nom du site -> compte e-mail associé, pour les sites qui en ont un."""
    return {s["nom"]: s["compte_email"] for s in sites(chemin) if s.get("compte_email")}
