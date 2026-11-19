"""Tests de verifier_installation.py et barometre.py (commandes simulées)."""

from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

import barometre as bm
import verifier_installation as vi


# --- verifier_installation --------------------------------------------------

def test_sortie(monkeypatch):
    monkeypatch.setattr(vi.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=" v22.1.0\n"))
    assert vi.sortie(["node", "-v"]) == "v22.1.0"

    def leve(*a, **k):
        raise subprocess.TimeoutExpired("x", 1)

    monkeypatch.setattr(vi.subprocess, "run", leve)
    assert vi.sortie(["node"]) == ""


def test_version_et_outil(monkeypatch):
    assert vi.version("Python 3.12.4") == (3, 12)
    assert vi.version("rien") == (0, 0)
    monkeypatch.setattr(vi.shutil, "which", lambda n: None)
    monkeypatch.setattr(vi, "MAC", False)
    assert vi.outil_systeme("dig", "bind", "dnsutils") == ("dig", False, "absent", "sudo apt-get install -y dnsutils")
    monkeypatch.setattr(vi, "MAC", True)
    monkeypatch.setattr(vi.shutil, "which", lambda n: "/usr/bin/" + n)
    assert vi.outil_systeme("dig", "bind", "dnsutils") == ("dig", True, "présent", "brew install bind")


def kit(r, deps_installees=True, venv=True, paquets_py="redbot==2.8.1\nopenpyxl==3.1.5\n"):
    (r / "package.json").write_text(json.dumps({"dependencies": {"a": "1"}, "devDependencies": {"b": "1"}}), encoding="utf-8")
    (r / "requirements.txt").write_text("# commentaire\nredbot==2.8.1  # x\n\nopenpyxl==3.1.5\n", encoding="utf-8")
    if deps_installees:
        for n in ("a", "b"):
            (r / "node_modules" / n).mkdir(parents=True)
            (r / "node_modules" / n / "package.json").write_text("{}", encoding="utf-8")
    if venv:
        (r / ".venv/bin").mkdir(parents=True)
        (r / ".venv/bin/python").write_text("", encoding="utf-8")
    chrome = r / "chrome"
    chrome.write_text("", encoding="utf-8")

    def sortie(cmd):
        if cmd[:2] == ["node", "-v"]:
            return "v22.3.0"
        if cmd[:2] == ["npm", "-v"]:
            return "10.0.0"
        if cmd[0] == "node":
            return str(chrome)
        if cmd[1:2] == ["--version"]:
            return "Python 3.12.1"
        return paquets_py

    return sortie


def test_installation_complete(racine, monkeypatch, tmp_path, capsys):
    r = racine(vi)
    monkeypatch.setattr(vi, "sortie", kit(r))
    monkeypatch.setattr(vi.shutil, "which", lambda n: "/bin/" + n)
    moteur = tmp_path / "hors/opquast-devtools/public/engine"
    moteur.mkdir(parents=True)
    (moteur / "rules.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["vi", "--hors", str(tmp_path / "hors")])
    assert vi.main() == 0
    out = capsys.readouterr().out
    assert "Tout est prêt." in out and "MANQUE" not in out and "construit" in out


def test_installation_manquante(racine, monkeypatch, capsys):
    r = racine(vi)
    sortie = kit(r, deps_installees=False, venv=False)
    monkeypatch.setattr(vi, "sortie", lambda cmd: "" if cmd[:2] in (["node", "-v"], ["npm", "-v"]) or cmd[0] == "node" else sortie(cmd))
    monkeypatch.setattr(vi.shutil, "which", lambda n: None)
    monkeypatch.setattr(sys, "argv", ["vi", "--hors", str(r / "rien")])
    assert vi.main() == 1
    out = capsys.readouterr().out
    assert "manquants : a, b" in out and "élément(s) à installer" in out and "absent" in out


def test_installation_paquets_python_manquants(racine, monkeypatch, capsys):
    r = racine(vi)
    monkeypatch.setattr(vi, "sortie", kit(r, paquets_py="redbot==2.8.1\n"))
    monkeypatch.setattr(vi.shutil, "which", lambda n: "/bin/" + n)
    monkeypatch.setattr(sys, "argv", ["vi"])
    assert vi.main() == 1
    assert "manquants : openpyxl" in capsys.readouterr().out


def test_installer(racine, monkeypatch, capsys):
    r = racine(vi)
    monkeypatch.setattr(vi, "sortie", kit(r, deps_installees=False))
    presents = set()
    monkeypatch.setattr(vi.shutil, "which", lambda n: ("/bin/" + n) if n in presents else None)
    lances = []

    def run(cmd, shell, cwd):
        lances.append(cmd)
        if "poppler" in cmd or "dnsutils" in cmd or "bind" in cmd:
            presents.update({"pdftotext", "pdftoppm", "pdfinfo", "dig"})
        if "npm ci" in cmd:
            for n in ("a", "b"):
                (r / "node_modules" / n).mkdir(parents=True)
                (r / "node_modules" / n / "package.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(returncode=0 if "git" not in cmd else 1)

    monkeypatch.setattr(vi.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["vi", "--installer"])
    assert vi.main() == 1
    out = capsys.readouterr()
    assert "Installation (accord donné)" in out.out and "échec (1)" in out.err
    assert lances.count(lances[-1]) == 1 and sum("poppler" in c for c in lances) == 1
    assert "--installer" not in sys.argv


# --- barometre --------------------------------------------------------------

def test_etapes(tmp_path):
    plan = bm.etapes(tmp_path, ["--service", "A"])
    assert list(plan) == bm.ORDRE
    assert len(plan["moteur"]) == 2
    (tmp_path / "opquast-devtools/public/engine").mkdir(parents=True)
    (tmp_path / "opquast-devtools/public/engine/rules.json").write_text("[]", encoding="utf-8")
    assert bm.etapes(tmp_path, [])["moteur"] == []


def test_resoudre(racine):
    r = racine(bm)
    assert bm.resoudre(["x", "@dernier:axe"]) == ["x", "@dernier:axe"]
    (r / "resultats/axe-2026-11-12").mkdir()
    (r / "resultats/axe-2026-11-13").mkdir()
    assert bm.resoudre(["@dernier:axe"]) == [str(r / "resultats/axe-2026-11-13")]


@pytest.fixture
def lancer(monkeypatch):
    appels = []

    def fabriquer(codes=None):
        codes = codes or {}

        def run(cmd, **kw):
            appels.append(cmd)
            nom = cmd[1] if len(cmd) > 1 else cmd[0]
            if kw.get("capture_output"):
                return SimpleNamespace(stdout=codes.get("pmset", "Now drawing from 'AC Power'"), returncode=0)
            return SimpleNamespace(returncode=next((c for k, c in codes.items() if k in nom), 0))

        monkeypatch.setattr(bm.subprocess, "run", run)
        return appels

    return fabriquer


def test_main_essai(racine, monkeypatch, tmp_path, lancer, capsys):
    racine(bm)
    appels = lancer()
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path / "hors"), "--essai", "--service", "Ma boutique"])
    assert bm.main() == 0
    assert appels == []
    out = capsys.readouterr().out
    assert "=== synthese" in out and '"Ma boutique"' in out and "Bilan" not in out


def test_main_etape_inconnue(racine, monkeypatch, tmp_path, capsys):
    racine(bm)
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--etapes", "synthese,rien"])
    assert bm.main() == 2
    assert "Étape inconnue : rien" in capsys.readouterr().err


def test_main_prerequis_manquants(racine, monkeypatch, tmp_path, lancer, capsys):
    racine(bm)
    lancer({"verifier_installation": 1})
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--etapes", "mesure"])
    assert bm.main() == 3
    assert "Prérequis manquants" in capsys.readouterr().err


def test_main_synthese_ok(racine, monkeypatch, tmp_path, lancer, capsys):
    racine(bm)
    appels = lancer()
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--depuis", "synthese"])
    assert bm.main() == 0
    assert len(appels) == 6
    assert "ok  synthese" in capsys.readouterr().out


def test_main_echec_et_continuer(racine, monkeypatch, tmp_path, lancer, capsys):
    racine(bm)
    appels = lancer({"fusion_scripts": 5})
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--etapes", "synthese"])
    assert bm.main() == 5
    assert "Corriger puis relancer avec --depuis synthese" in capsys.readouterr().err
    appels.clear()
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--etapes", "synthese", "--continuer"])
    assert bm.main() == 0
    assert "ÉCHEC synthese" in capsys.readouterr().out


def test_main_moteur_et_commande_courte(racine, monkeypatch, tmp_path, lancer, capsys):
    racine(bm)
    lancer()
    monkeypatch.setattr(bm, "etapes", lambda hors, service: {e: [["seul"]] for e in bm.ORDRE})
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--etapes", "moteur,referentiel"])
    assert bm.main() == 0
    assert "seul" in capsys.readouterr().out


def test_main_toutes_etapes_avec_prerequis(racine, monkeypatch, tmp_path, lancer):
    racine(bm)
    appels = lancer()
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path)])
    assert bm.main() == 0
    assert any("verifier_installation.py" in " ".join(c) for c in appels)


@pytest.mark.parametrize("systeme, which, batterie, forcer, code", [
    ("Darwin", None, "Now drawing from 'AC Power'", False, 0),
    ("Darwin", None, "Now drawing from 'Battery Power'", False, 4),
    ("Darwin", None, "Now drawing from 'Battery Power'", True, 0),
    ("Linux", "/usr/bin/systemd-inhibit", "", False, 0),
    ("Windows", None, "", False, 0),
])
def test_nuit(racine, monkeypatch, tmp_path, lancer, capsys, systeme, which, batterie, forcer, code):
    r = racine(bm)
    appels = lancer({"pmset": batterie})
    monkeypatch.setattr(bm.platform, "system", lambda: systeme)
    monkeypatch.setattr(bm.shutil, "which", lambda n: which)
    monkeypatch.delenv("BAROMETRE_EVEILLE", raising=False)
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--nuit"] + (["--forcer"] if forcer else []))
    assert bm.main() == code
    sortie = capsys.readouterr()
    if code == 4:
        assert "sur batterie" in sortie.err
        return
    relance = appels[-1]
    assert "--nuit" not in relance and "--forcer" not in relance
    if systeme == "Darwin":
        assert relance[:2] == ["caffeinate", "-dimsu"]
    elif systeme == "Linux":
        assert relance[0] == "systemd-inhibit"
    else:
        assert "Mise en veille non bloquée" in sortie.err and "sans blocage de veille" in sortie.out
    journal = next((r / "resultats").glob("journal-barometre-*.log")).read_text(encoding="utf-8")
    assert "===== début" in journal and "code 0" in journal


def test_nuit_deja_eveille(racine, monkeypatch, tmp_path, lancer):
    racine(bm)
    lancer()
    monkeypatch.setenv("BAROMETRE_EVEILLE", "1")
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path), "--nuit", "--essai"])
    assert bm.main() == 0
