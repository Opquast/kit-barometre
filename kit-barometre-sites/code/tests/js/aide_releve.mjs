// Aide aux tests de releve_regles.mjs, sources_page.mjs et sources_panier.mjs.
//
// Chaque scénario tourne dans un processus enfant (la couverture V8 des enfants est fusionnée par node --test, ce
// qui n'est pas le cas de deux imports du même script avec des requêtes différentes) :
//   node --experimental-test-module-mocks --import <fichier de test> scripts/<script>.mjs …
// Le fichier de test, préchargé avec AIDE_NOM défini, appelle installer(scenario) : 'playwright', 'node:fs' et
// 'node:child_process' sont remplacés par des faux, les pauses durent 0 ms, fetch est simulé (aucun réseau),
// et page.evaluate(fn, arg) exécute fn pour de vrai dans un DOM jsdom (globals document, location… posés le temps
// de l'appel). Les écritures sous resultats/ et la lecture du CSV des écrans sont redirigées vers un dossier temporaire.
import { spawnSync as vraiSpawnSync } from 'node:child_process';
import * as vraiFs from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mock } from 'node:test';
import { JSDOM } from 'jsdom';

export const RACINE = fileURLToPath(new URL('../../', import.meta.url));
// racine telle que les scripts la calculent (new URL('..', import.meta.url).pathname : encodée, %20 pour une espace)
export const RACINE_SCRIPT = new URL('../../', import.meta.url).pathname;
export const DATE = () => new Date().toISOString().slice(0, 10);

// ---------- côté test (processus parent) ----------

export function lancer(fichierTest, script, nom, { args = () => [], avant, env = {} } = {}) {
  const tmp = vraiFs.mkdtempSync(join(tmpdir(), 'aide-releve-'));
  avant?.(tmp);
  const e = { ...process.env, ...(typeof env === 'function' ? env(tmp) : env), AIDE_NOM: nom, AIDE_TMP: tmp };
  delete e.NODE_TEST_CONTEXT;
  const r = vraiSpawnSync(process.execPath, ['--no-warnings', '--experimental-test-module-mocks', '--import', fichierTest, join(RACINE, 'scripts', script), ...args(tmp)],
    { cwd: RACINE, env: e, encoding: 'utf8', timeout: 60000 });
  const lire = rel => JSON.parse(vraiFs.readFileSync(join(tmp, rel), 'utf8'));
  const journal = vraiFs.existsSync(join(tmp, 'journal.json')) ? lire('journal.json') : [];
  return { statut: r.status, sortie: r.stdout, erreurs: r.stderr, tmp, lire, journal, existe: rel => vraiFs.existsSync(join(tmp, rel)),
    texte: rel => vraiFs.readFileSync(join(tmp, rel), 'utf8'), nettoyer: () => vraiFs.rmSync(tmp, { recursive: true, force: true }) };
}

export const csv = lignes => 'service,gabarit,url\n' + lignes.map(l => l.join(',')).join('\n') + '\n';

// réponse HTTP simulée (page.goto, ctx.request)
export function rep({ statut = 200, json, type = 'application/json', jsonErreur = false } = {}) {
  return {
    status: () => statut, ok: () => statut < 400,
    headers: () => (type === null ? {} : { 'content-type': type }),
    json: async () => { if (jsonErreur) throw new Error('JSON invalide'); return json; },
  };
}

// ---------- côté enfant ----------

const journal = [];
const noter = (...x) => journal.push(x);

function parserStyle(t) {
  const o = {};
  for (const d of (t || '').split(';')) {
    const i = d.indexOf(':'); if (i < 0) continue;
    o[d.slice(0, i).trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = d.slice(i + 1).trim();
  }
  return o;
}
const DEFAUTS = { display: 'block', position: 'static', zIndex: 'auto', opacity: '1', visibility: 'visible', textDecorationLine: 'none', textTransform: 'none' };

function preparerFenetre(win, page) {
  // styles calculés : attribut style (ou data-style-print en émulation impression) sur des valeurs par défaut
  win.getComputedStyle = el => ({ ...DEFAUTS, ...parserStyle(page.media === 'print' && el.hasAttribute('data-style-print') ? el.getAttribute('data-style-print') : el.getAttribute('style')) });
  Object.defineProperty(win.HTMLElement.prototype, 'innerText', { configurable: true, get() { return this.textContent; } });
  // boîte : data-r="gauche haut largeur hauteur"
  win.Element.prototype.getBoundingClientRect = function () {
    const [left, top, width, height] = (this.getAttribute('data-r') || '0 0 0 0').split(' ').map(Number);
    return { left, top, width, height, right: left + width, bottom: top + height };
  };
  Object.defineProperty(win.HTMLImageElement.prototype, 'naturalWidth', { configurable: true, get() { return +(this.getAttribute('data-nw') || 0); } });
  Object.defineProperty(win.HTMLMediaElement.prototype, 'duration', { configurable: true, get() { return this.hasAttribute('data-duree') ? +this.getAttribute('data-duree') : NaN; } });
}

class FauxPage {
  constructor(sc, ctx) { this.sc = sc; this.ctx = ctx; this.ecoutes = {}; this.u = 'about:blank'; this.def = {}; this.media = 'screen'; }
  on(ev, f) { (this.ecoutes[ev] ??= []).push(f); }
  async goto(url) {
    noter('goto', url);
    const def = typeof this.sc.pages === 'function' ? this.sc.pages(url, this) : this.sc.pages?.[url];
    if (!def) throw new Error(`page non prévue : ${url}`);
    if (def.erreur) throw new Error(def.erreur);
    this.def = def; this.u = def.finale || url;
    this.dom = new JSDOM(def.html ?? '<body></body>', { url: this.u });
    preparerFenetre(this.dom.window, this);
    def.preparer?.(this.dom.window, this);
    for (const p of def.popups || []) for (const f of this.ecoutes.popup || []) f({ url: () => p });
    if (def.statut === null) return null;
    return rep({ statut: def.statut ?? 200 });
  }
  url() { return this.u; }
  async title() { return this.dom.window.document.title; }
  async evaluate(fn, arg) {
    if (this.def.evaluer) { const r = await this.def.evaluer(fn, arg, this); if (r !== undefined) return r; }
    const w = this.dom.window;
    Object.assign(globalThis, { window: w, document: w.document, location: w.location, getComputedStyle: w.getComputedStyle, NodeFilter: w.NodeFilter, Shopify: w.Shopify,
      fetch: async (u, o) => { const abs = new URL(u, w.location.href).href; noter('fetch', abs, o?.method || 'GET', o?.body ?? null); const f = this.def.fetch?.[abs]; if (!f) throw new Error('fetch non prévu ' + abs); return typeof f === 'function' ? f(o) : f; } });
    return await fn(arg);
  }
  locator(s) {
    const page = this;
    return { first: () => ({
      isVisible: async () => { const v = page.def.visibles?.[s]; if (v === 'erreur') throw new Error('locator'); return !!v; },
      click: async () => { noter('clic', s); if (page.def.visibles?.[s] === 'clic-erreur') throw new Error('clic'); },
    }) };
  }
  async emulateMedia({ media }) { this.media = media; noter('media', media); }
  async addScriptTag({ path }) {
    noter('script', path);
    if (path.endsWith('axe.min.js')) this.dom.window.axe = this.sc.axe;
    if (path.endsWith('ace.js')) this.dom.window.ace = this.sc.ace;
  }
  async screenshot(o) { noter('capture', o.path); if (this.def.captureErreur) throw new Error('capture'); }
  async pdf(o) { noter('pdf', o.path); }
  async close() { noter('page.close', this.u); this.dom?.window.close(); }
}

function fauxContexte(sc) {
  const ctx = {
    request: {
      get: async (url, o) => { noter('GET', url); return sc.requete('GET', url, o); },
      post: async (url, o) => { noter('POST', url, o?.data ?? null); return sc.requete('POST', url, o); },
    },
    pages: [],
    newPage: async () => { const p = new FauxPage(sc, ctx); ctx.pages.push(p); return p; },
    close: async () => { noter('ctx.close'); if (ctx.pages.some(p => p.def.ctxFermetureEchoue)) throw new Error('contexte déjà fermé'); },
  };
  return ctx;
}

export async function installer(sc) {
  const tmp = process.env.AIDE_TMP;
  vraiFs.writeFileSync(join(tmp, 'ecrans.csv'), sc.csv);
  process.on('exit', () => vraiFs.writeFileSync(join(tmp, 'journal.json'), JSON.stringify(journal)));
  const st = globalThis.setTimeout;
  globalThis.setTimeout = (f, ms, ...a) => st(f, 0, ...a);
  globalThis.fetch = async () => { throw new Error('réseau interdit'); };
  const redir = p => {
    if (typeof p !== 'string' || !p.startsWith(RACINE_SCRIPT)) return p;
    const rel = p.slice(RACINE_SCRIPT.length);
    if (rel === 'scripts/ecrans_en_ligne.csv') return join(tmp, 'ecrans.csv');
    if (rel.startsWith('resultats/')) return join(tmp, rel);
    throw new Error(`chemin du dépôt non prévu : ${rel}`);
  };
  const fs = {
    readFileSync: (p, ...a) => vraiFs.readFileSync(redir(p), ...a),
    writeFileSync: (p, ...a) => { noter('ecrit', p); return vraiFs.writeFileSync(redir(p), ...a); },
    mkdirSync: (p, ...a) => vraiFs.mkdirSync(redir(p), ...a),
    existsSync: p => vraiFs.existsSync(redir(p)),
    rmSync: (p, ...a) => { noter('rm', p); return vraiFs.rmSync(redir(p), ...a); },
  };
  mock.module('node:fs', { namedExports: fs, defaultExport: fs });
  mock.module('node:child_process', { namedExports: { spawnSync: (...a) => { noter('spawn', ...a.slice(0, 2)); return sc.spawnSync(...a); } } });
  let lancements = 0;
  mock.module('playwright', { namedExports: { chromium: { launch: async () => {
    const n = ++lancements; noter('launch', n);
    let contextes = 0;
    return {
      newContext: async o => { noter('newContext', n, o); if (sc.contexteEchoue?.(n, ++contextes)) throw new Error('Target closed'); return fauxContexte(sc); },
      close: async () => { noter('nav.close', n); if (sc.fermetureEchoue?.(n)) throw new Error('déjà fermé'); },
    };
  } } } });
}
