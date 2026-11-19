#!/usr/bin/env python3
"""Vérifie qu'un fichier Markdown tient sur une page A4 (10 pt, marges de 15 mm).

Convertit le Markdown simple de la note (titres, paragraphes, listes, tableaux,
gras, code) en HTML, l'imprime en PDF avec Chrome sans interface, puis compte
les pages avec pdfinfo.

Usage : python3 scripts/verifier_page_a4.py note_cadrage.md
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CSS = ("@page{size:A4;margin:15mm} body{font:10pt/1.35 -apple-system,Helvetica,sans-serif} "
       "h1{font-size:15pt;margin:0 0 4px} h2{font-size:11.5pt;margin:10px 0 3px} p,ul,ol{margin:3px 0} "
       "ul,ol{padding-left:18px} table{border-collapse:collapse;width:100%;font-size:9pt;margin:4px 0} "
       "th,td{border:1px solid #bbb;padding:2px 4px;text-align:left}")


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)


def md_vers_html(texte: str) -> str:
    lignes, out, i = texte.splitlines(), [], 0
    while i < len(lignes):
        l = lignes[i]
        if l.startswith("|"):
            rangs = []
            while i < len(lignes) and lignes[i].startswith("|"):
                rangs.append([c.strip() for c in lignes[i].strip("|").split("|")])
                i += 1
            out.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rangs[0]) + "</tr>")
            out += ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rangs[2:]]
            out.append("</table>")
            continue
        m = re.match(r"(#+) (.*)", l)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
        elif l.startswith("- "):
            out.append("<ul>")
            while i < len(lignes) and lignes[i].startswith("- "):
                out.append(f"<li>{inline(lignes[i][2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        elif re.match(r"\d+\. ", l):
            out.append("<ol>")
            while i < len(lignes) and re.match(r"\d+\. ", lignes[i]):
                out.append(f"<li>{inline(lignes[i].split('. ', 1)[1])}</li>")
                i += 1
            out.append("</ol>")
            continue
        elif l.strip():
            out.append(f"<p>{inline(l)}</p>")
        i += 1
    return f'<!doctype html><html lang="fr"><meta charset="utf-8"><style>{CSS}</style><body>' + "\n".join(out) + "</body></html>"


def main() -> int:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "note_cadrage.md")
    with tempfile.TemporaryDirectory() as d:
        page_html, pdf, profil = Path(d) / "page.html", Path(d) / "page.pdf", Path(d) / "chrome"
        page_html.write_text(md_vers_html(source.read_text(encoding="utf-8")), encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profil}",
                        f"--print-to-pdf={pdf}", page_html.as_uri()], capture_output=True, timeout=60)
        infos = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = int(re.search(r"Pages:\s+(\d+)", infos).group(1))
        if len(sys.argv) > 2:
            shutil.copy(pdf, sys.argv[2])
    print(f"{source} : {pages} page(s) A4")
    return 0 if pages == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
