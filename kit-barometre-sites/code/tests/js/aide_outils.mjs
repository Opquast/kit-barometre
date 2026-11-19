// Aide commune aux tests de outils_page, outils_j2, nu_local et page_playwright.
//
// Chaque scénario tourne dans un processus enfant (le fichier de test relancé avec BAROMETRE_SCENARIO), qui importe
// le script sous son URL nue. node:test fusionne la couverture des processus par URL de script : un import
// « ?s=n » dans le même processus crée une seconde entrée pour le même fichier, et seule la dernière compte.
//
// Dans l'enfant, node:fs est remplacé par une version qui redirige les chemins du dépôt :
// - <racine>/scripts/ecrans_en_ligne.csv -> <tmp>/ecrans.csv (écrans fictifs du scénario) ;
// - <racine>/resultats/...               -> <tmp>/resultats/... (jamais le dossier resultats/ du dépôt) ;
// - tout autre chemin sous la racine est lu au vrai endroit (ex. scripts/controles_page.js).
// Les pauses (setTimeout) sont ramenées à 0 ms. Aucun accès réseau : playwright, pa11y, lighthouse, etc. sont
// remplacés par des faux dans chaque fichier de test.
import * as vraiFs from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Racine telle que les scripts la calculent (new URL('..', import.meta.url).pathname : encodée, %20 pour l'espace).
export const RACINE_SCRIPT = new URL('../../', import.meta.url).pathname;
export const RACINE = fileURLToPath(new URL('../../', import.meta.url));
export const DATE = new Date().toISOString().slice(0, 10);
export const enfant = !!process.env.BAROMETRE_SCENARIO;
export const scenario = process.env.BAROMETRE_SCENARIO;

export const urlScript = nom => new URL(`../../scripts/${nom}`, import.meta.url).href;

// ---- côté parent ----

// Lance le scénario `nom` du fichier de test `urlTest` dans un processus enfant.
// csv : contenu de ecrans_en_ligne.csv ; fichiers : { 'resultats/...': contenu (objet -> JSON) } déposés avant.
export function lancer(urlTest, nom, { csv, fichiers = {}, argv = [] } = {}) {
  const tmp = vraiFs.mkdtempSync(join(tmpdir(), 'barometre-test-'));
  vraiFs.writeFileSync(join(tmp, 'ecrans.csv'), csv);
  for (const [rel, contenu] of Object.entries(fichiers)) {
    const chemin = join(tmp, rel);
    vraiFs.mkdirSync(join(chemin, '..'), { recursive: true });
    vraiFs.writeFileSync(chemin, typeof contenu === 'string' ? contenu : JSON.stringify(contenu));
  }
  const r = spawnSync(process.execPath, ['--experimental-test-module-mocks', '--no-warnings', fileURLToPath(urlTest)], {
    encoding: 'utf8', timeout: 120000,
    env: { ...process.env, BAROMETRE_SCENARIO: nom, BAROMETRE_TMP: tmp, BAROMETRE_ARGV: JSON.stringify(argv) },
  });
  const chemin = rel => join(tmp, rel);
  return {
    tmp, statut: r.status, sortie: r.stdout, erreurs: r.stderr,
    chemin, existe: rel => vraiFs.existsSync(chemin(rel)),
    lire: rel => vraiFs.readFileSync(chemin(rel), 'utf8'),
    json: rel => JSON.parse(vraiFs.readFileSync(chemin(rel), 'utf8')),
    nettoyer: () => vraiFs.rmSync(tmp, { recursive: true, force: true }),
  };
}

// ---- côté enfant ----

// Installe le faux node:fs, les pauses instantanées et process.argv ; à appeler avant d'importer le script.
export function preparerEnfant(mock, script) {
  const tmp = process.env.BAROMETRE_TMP;
  const rediriger = p => {
    if (typeof p !== 'string' || !p.startsWith(RACINE_SCRIPT)) return p;
    const reste = p.slice(RACINE_SCRIPT.length);
    if (reste === 'scripts/ecrans_en_ligne.csv') return join(tmp, 'ecrans.csv');
    if (reste.startsWith('resultats/')) return join(tmp, reste);
    return RACINE + decodeURIComponent(reste);
  };
  const journal = [];
  const envelopper = nom => (p, ...a) => { journal.push([nom, p]); return vraiFs[nom](rediriger(p), ...a); };
  const faux = { ...vraiFs };
  for (const nom of ['readFileSync', 'writeFileSync', 'mkdirSync', 'existsSync', 'rmSync']) faux[nom] = envelopper(nom);
  mock.module('node:fs', { defaultExport: faux, namedExports: faux });
  const vraiSetTimeout = globalThis.setTimeout;
  globalThis.setTimeout = (f, _ms, ...a) => vraiSetTimeout(f, 0, ...a);
  process.argv = [process.execPath, fileURLToPath(urlScript(script)), ...JSON.parse(process.env.BAROMETRE_ARGV || '[]')];
  return { tmp, journal, rediriger };
}

// Faux document de navigateur : `n` éléments comptés par le script EcoIndex (dont un <svg>, plus un <path> intérieur
// au svg qui ne compte pas).
export function fauxDocument(n, { bandeau = true, hauteur = 1600 } = {}) {
  const svg = { tagName: 'SVG' };
  svg.closest = () => svg;
  const chemin = { tagName: 'path', closest: () => svg };
  const div = { tagName: 'DIV', closest: () => null };
  const elements = n > 0 ? [...Array(n - 1).fill(div), svg, chemin] : [];
  return {
    body: { scrollHeight: hauteur },
    getElementsByTagName: () => elements,
    querySelector: () => (bandeau ? {} : null),
  };
}
