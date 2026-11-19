"""Parc de test (le parc d'origine du kit : six boutiques Shopify) posé dans la racine temporaire des tests."""

from __future__ import annotations

import copy
from pathlib import Path

import parc
from conftest import ecrire_json


def _site(lettre: str, prefixe: str, hors_site: bool = False, langue: str = "", email: str = "") -> dict:
    return {"nom": f"Boutique {lettre}", "code_esm": f"WEB-BOUTIQUE{lettre}", "prefixe_pages": prefixe, "plateforme": "shopify",
            "compte_client_hors_site": hors_site, "prefixe_langue": langue, "compte_email": email}


PARC_ORIGINE = {
    "responsable": "Mattea",
    "auditeur_esm": "MLU",
    "sites": [
        _site("A", "BM"), _site("B", "MAG"), _site("C", "BOUTIQUEC", True, email="Klaviyo Boutique C"),
        _site("D", "DDM", True, "/fr"), _site("E", "TDA", True), _site("F", "MAJ", email="Klaviyo Boutique F"),
    ],
}


def poser_parc(racine, *modules, donnees: dict | None = None) -> Path:
    """Remplace RACINE des modules et de parc par la racine temporaire, puis y écrit referentiel/parc.json."""
    r = racine(parc, *modules)
    ecrire_json(r / "referentiel" / "parc.json", copy.deepcopy(donnees if donnees is not None else PARC_ORIGINE))
    return r
