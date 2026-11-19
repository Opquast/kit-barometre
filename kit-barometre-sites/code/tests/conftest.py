"""Fixtures communes : une racine de kit temporaire, pour que les scripts n'écrivent jamais dans le dépôt."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parent.parent


@pytest.fixture
def racine(tmp_path, monkeypatch):
    """Copie referentiel/ et scripts/ecrans_en_ligne.csv dans un dossier temporaire.

    Utilisation : `racine(module)` remplace module.RACINE et renvoie le dossier.
    """
    (tmp_path / "scripts").mkdir()
    shutil.copy(KIT / "scripts" / "ecrans_en_ligne.csv", tmp_path / "scripts")
    shutil.copytree(KIT / "referentiel", tmp_path / "referentiel")
    (tmp_path / "resultats").mkdir()

    def appliquer(*modules):
        for m in modules:
            monkeypatch.setattr(m, "RACINE", tmp_path)
        return tmp_path

    return appliquer


def ecrire_json(chemin: Path, donnees) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    return chemin


def lire_json(chemin: Path):
    return json.loads(chemin.read_text(encoding="utf-8"))
