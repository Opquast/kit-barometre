"""Vérifie la structure des skills Claude (dossiers contenant un SKILL.md).

- frontmatter YAML valide, avec `name` (égal au nom du dossier) et `description`
  (non vide, 1 024 caractères au plus) ;
- chaque fichier source cité dans les fichiers Markdown de la skill existe, cherché
  depuis le dossier de la skill puis depuis la racine du projet qui la contient
  (le dossier parent de `.claude/`).

Arguments : chemins de SKILL.md ou de fichiers d'une skill. Sans argument, toutes
les skills sous le dossier courant. Code de sortie 1 en cas de problème.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

DOSSIERS_SOURCES = ("scripts/", "referentiel/", "references/", "assets/", "./")
REFERENCE = re.compile(r"`([^`\s]+)`|\]\(([^)\s#]+)\)")
JOKERS = set("<>*{}$")
LONGUEUR_DESCRIPTION = 1024


def lire_frontmatter(texte: str) -> tuple[dict | None, str | None]:
    if not texte.startswith("---\n"):
        return None, "frontmatter absent (le fichier doit commencer par ---)"
    fin = texte.find("\n---", 4)
    if fin == -1:
        return None, "frontmatter non refermé"
    try:
        donnees = yaml.safe_load(texte[4:fin])
    except yaml.YAMLError as erreur:
        return None, f"frontmatter YAML invalide : {erreur}"
    if not isinstance(donnees, dict):
        return None, "frontmatter vide ou mal formé"
    return donnees, None


def controler_frontmatter(skill_md: Path) -> list[str]:
    donnees, erreur = lire_frontmatter(skill_md.read_text(encoding="utf-8"))
    if erreur:
        return [erreur]
    problemes = []
    nom = donnees.get("name")
    if not nom:
        problemes.append("champ « name » manquant")
    elif nom != skill_md.parent.name:
        problemes.append(f"« name » ({nom}) différent du dossier ({skill_md.parent.name})")
    description = donnees.get("description")
    if not description or not str(description).strip():
        problemes.append("champ « description » manquant ou vide")
    elif len(str(description)) > LONGUEUR_DESCRIPTION:
        problemes.append(f"« description » trop longue ({len(str(description))} > {LONGUEUR_DESCRIPTION} caractères)")
    return problemes


def racine_projet(dossier_skill: Path) -> Path:
    for parent in dossier_skill.parents:
        if parent.name == ".claude":
            return parent.parent
    return dossier_skill


def references(texte: str) -> set[str]:
    trouvees = set()
    for m in REFERENCE.finditer(texte):
        ref = m.group(1) or m.group(2)
        if "://" in ref or JOKERS & set(ref) or not ref.startswith(DOSSIERS_SOURCES):
            continue
        trouvees.add(ref)
    return trouvees


def controler_references(dossier_skill: Path) -> list[str]:
    bases = [dossier_skill, racine_projet(dossier_skill)]
    problemes = []
    for md in sorted(dossier_skill.rglob("*.md")):
        for ref in sorted(references(md.read_text(encoding="utf-8"))):
            if not any((base / ref).exists() for base in bases):
                problemes.append(f"{md.relative_to(dossier_skill)} cite « {ref} », introuvable")
    return problemes


def dossier_de_skill(chemin: Path) -> Path | None:
    for dossier in [chemin, *chemin.parents]:
        if (dossier / "SKILL.md").is_file():
            return dossier
    return None


def main(arguments: list[str]) -> int:
    if arguments:
        dossiers = {d for a in arguments if (d := dossier_de_skill(Path(a).resolve()))}
    else:
        dossiers = {p.parent.resolve() for p in Path.cwd().rglob("SKILL.md")}
    problemes = []
    for dossier in sorted(dossiers):
        for p in controler_frontmatter(dossier / "SKILL.md") + controler_references(dossier):
            problemes.append(f"{dossier.name} : {p}")
    for p in problemes:
        print(f"✖ Skill {p}", file=sys.stderr)
    return 1 if problemes else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
