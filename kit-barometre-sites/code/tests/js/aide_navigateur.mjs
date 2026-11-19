// Aide commune aux tests des scripts navigateur (scripts/controles_page.js, scripts/axe_navigateur.js).
//
// Ces scripts sont des IIFE async collées dans la console : on les exécute tels quels dans le contexte
// vm d'une fenêtre jsdom, avec `filename` = chemin absolu du script pour que la couverture V8
// (node --test --experimental-test-coverage) attribue le code exécuté au bon fichier.
//
// jsdom ne fait pas de mise en page : on simule ce que le navigateur fournirait.
//   - getBoundingClientRect : 100 x 100 par défaut, ou data-largeur / data-hauteur ;
//   - getComputedStyle : valeurs de jsdom (display, visibility), complétées par data-police
//     (font-family, « Arial, sans-serif » par défaut), data-alignement (text-align), data-selection (user-select) ;
//   - innerText : textContent (jsdom ne l'implémente pas) ;
//   - muted : reflète l'attribut muted à la création, comme dans un navigateur ;
//   - fetch : fourni par le test (aucun accès réseau).
import vm from 'node:vm';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const racine = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const cheminScript = nom => path.join(racine, 'scripts', nom);

const sources = new Map();
const contextes = new WeakMap();
const compiler = chemin => {
  if (!sources.has(chemin)) sources.set(chemin, new vm.Script(fs.readFileSync(chemin, 'utf8'), { filename: chemin }));
  return sources.get(chemin);
};

export function fenetre(html, { url = 'https://www.boutique.fr/produits/x' } = {}) {
  const dom = new JSDOM(html, { url, runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  contextes.set(w, dom.getInternalVMContext());
  w.Element.prototype.getBoundingClientRect = function () {
    const largeur = this.hasAttribute('data-largeur') ? +this.getAttribute('data-largeur') : 100;
    const hauteur = this.hasAttribute('data-hauteur') ? +this.getAttribute('data-hauteur') : 100;
    return { width: largeur, height: hauteur, top: 0, left: 0, right: largeur, bottom: hauteur, x: 0, y: 0 };
  };
  const styleJsdom = w.getComputedStyle.bind(w);
  w.getComputedStyle = el => {
    const s = styleJsdom(el);
    return {
      display: s.display,
      visibility: s.visibility,
      fontFamily: el.getAttribute('data-police') ?? 'Arial, sans-serif',
      textAlign: el.getAttribute('data-alignement') ?? 'start',
      userSelect: el.getAttribute('data-selection') ?? 'auto',
    };
  };
  Object.defineProperty(w.HTMLElement.prototype, 'innerText', { get() { return this.textContent; }, configurable: true });
  for (const m of w.document.querySelectorAll('video[muted], audio[muted]')) m.muted = true;
  w.fetch = async () => ({ status: 200 });
  w.console.log = () => {};
  return w;
}

// Exécute le script `nom` dans la fenêtre `w` et renvoie la promesse de l'IIFE.
export function executer(nom, w) {
  return compiler(cheminScript(nom)).runInContext(contextes.get(w));
}
