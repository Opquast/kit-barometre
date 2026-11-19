// Aide commune aux tests des scripts Playwright (axe_playwright, contre_examen, parcours, sources_tiers).
//
// Chaque scénario tourne dans un processus enfant : le fichier de test se relance lui-même avec AIDE_SCENARIO, y
// remplace 'playwright' (et les autres paquets) par des faux avec mock.module, puis importe le script. Un processus
// par scénario, parce que la couverture V8 ne fusionne pas deux instances du même module dans un processus, alors
// qu'elle fusionne bien les processus enfants (NODE_V8_COVERAGE est hérité).
//
// Le faux navigateur sert des pages jsdom : page.evaluate(fn, arg) exécute fn dans Node avec window, document,
// getComputedStyle… pointant sur la page courante, si bien que les fonctions passées au navigateur sont couvertes.
// Attributs de mise en page simulés : data-style (JSON lu par getComputedStyle), data-rect « x,y,l,h »
// (getBoundingClientRect), data-cache (offsetParent nul), data-texte (innerText imposé).
import { spawnSync } from 'node:child_process';
import * as fsReel from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setImmediate } from 'node:timers';
import { JSDOM, VirtualConsole } from 'jsdom';

// Racine telle que les scripts la calculent (new URL('..', import.meta.url).pathname, donc encodée : %20).
export const RACINE = new URL('../../', import.meta.url).pathname;
export const RACINE_DEC = fileURLToPath(new URL('../../', import.meta.url));
export const aujourdhui = () => new Date().toISOString().slice(0, 10);

// ---------- côté test (parent) ----------

export function lancer(urlTest, scenario, tmp = fsReel.mkdtempSync(join(tmpdir(), 'kit-js-'))) {
  const r = spawnSync(process.execPath, ['--experimental-test-module-mocks', '--no-warnings', fileURLToPath(urlTest)], {
    env: { ...process.env, AIDE_SCENARIO: scenario, AIDE_TMP: tmp }, encoding: 'utf8', timeout: 120000,
  });
  const lire = rel => fsReel.readFileSync(join(tmp, rel), 'utf8');
  const existe = rel => fsReel.existsSync(join(tmp, rel));
  let journal = [];
  if (existe('journal.json')) journal = JSON.parse(lire('journal.json'));
  return { status: r.status, stdout: r.stdout, stderr: r.stderr, tmp, lire, existe, journal };
}

// ---------- côté enfant ----------

// Page jsdom avec la mise en page simulée.
export function fenetre(html, url) {
  const w = new JSDOM(html, { url, virtualConsole: new VirtualConsole() }).window;
  Object.defineProperty(w.HTMLElement.prototype, 'innerText', {
    configurable: true, get() { return this.hasAttribute('data-texte') ? this.getAttribute('data-texte') : this.textContent; },
  });
  Object.defineProperty(w.HTMLElement.prototype, 'offsetParent', {
    configurable: true, get() { return this.closest('[data-cache]') ? null : this.parentElement; },
  });
  w.Element.prototype.getBoundingClientRect = function () {
    const [x, y, width, height] = (this.getAttribute('data-rect') || '0,0,100,20').split(',').map(Number);
    return { x, y, width, height, top: y, left: x, bottom: y + height, right: x + width };
  };
  w.getComputedStyle = el => ({ outlineStyle: 'none', outlineWidth: '0px', boxShadow: 'none', textDecorationLine: 'none',
    fontWeight: '400', ...JSON.parse(el.getAttribute('data-style') || '{}') });
  return w;
}

// Exécute fn comme le ferait page.evaluate, avec les globales du navigateur sur la fenêtre w.
export async function executer(fn, arg, w, extra = {}, cloner = true) {
  const g = { window: w, document: w.document, getComputedStyle: w.getComputedStyle, innerHeight: 900,
    XMLSerializer: w.XMLSerializer, location: w.location, fetch: () => Promise.reject(new Error('réseau interdit')), ...extra };
  for (const [k, v] of Object.entries(g)) Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  const v = await fn(arg);
  return v === undefined || !cloner ? v : structuredClone(v);
}

class Locator {
  constructor(page, desc) { this.page = page; this.desc = desc; }
  first() { return this; }
  filter(o) { return new Locator(this.page, { ...this.desc, filtre: o }); }
  async isVisible() { this.page.j.push(['visible?', this.page.url(), String(this.desc.name ?? this.desc.sel)]); return (await this.page.site.visible?.(this.desc, this.page)) ?? false; }
  async click(o) { this.page.j.push(['clic', this.page.url(), String(this.desc.name ?? this.desc.sel ?? this.desc.filtre?.hasText)]); return this.page.site.clic?.(this.desc, this.page, o); }
  async count() { return (await this.page.site.compte?.(this.desc, this.page)) ?? 0; }
}

// Page simulée. site.page(url, page) rend la définition d'une page :
//   { status (200 par défaut, null = aucune réponse), finale (URL après redirection), html, title, erreur,
//     focus: [sélecteur | 'body' | null, …] (éléments atteints par Tab, en boucle), preparer(win, page) }.
// Crochets facultatifs du site : evaluer(fn, arg, page), touche(k, page), visible, clic, compte, capture(o, page),
// script(o, page), globaux(page), fetch(url, opts, page).
export class FaussePage {
  constructor(site, j) {
    this.site = site; this.j = j; this.courant = null;
    this.keyboard = { press: async k => this.touche(k) };
    this.mouse = { click: async (x, y) => { this.j.push(['souris', x, y]); } };
  }
  async goto(url, opts) {
    this.j.push(['goto', url, opts?.timeout ?? null]);
    const d = this.site.page(url, this);
    if (d.erreur) throw new Error(d.erreur);
    const html = d.html ?? '<!doctype html><html><head><title>Page</title></head><body><main><p>Bienvenue</p></main></body></html>';
    const win = fenetre(html, d.finale ?? url);
    this.courant = { url, ...d, win, idx: -1 };
    const page = this;
    Object.defineProperty(win.document, 'activeElement', { configurable: true, get() {
      const c = page.courant;
      if (!c.focus || c.idx < 0) return win.document.body;
      const f = c.focus[c.idx % c.focus.length];
      return f === null ? null : f === 'body' ? win.document.body : win.document.querySelector(f);
    } });
    d.preparer?.(win, this);
    return d.status === null ? null : { status: () => d.status ?? 200 };
  }
  url() { return this.courant ? (this.courant.finale ?? this.courant.url) : 'about:blank'; }
  async title() { return this.courant.title ?? this.courant.win.document.title; }
  async content() { return this.courant.win.document.documentElement.outerHTML; }
  async touche(k) {
    this.j.push(['touche', k]);
    if (k === 'Tab' && this.courant) this.courant.idx++;
    return this.site.touche?.(k, this);
  }
  async evaluate(fn, arg) {
    const h = this.site.evaluer?.(fn, arg, this);
    if (h !== undefined) return h;
    const fetch = this.site.fetch ? (u, o) => { this.j.push(['fetch', u, o?.body ?? null]); return this.site.fetch(u, o, this); } : undefined;
    return executer(fn, arg, this.courant.win, { ...(fetch ? { fetch } : {}), ...this.site.globaux?.(this) });
  }
  async evaluateHandle(fn) { return { valeur: await executer(fn, undefined, this.courant.win, {}, false) }; }
  getByRole(role, o) { return new Locator(this, { role, ...o }); }
  locator(sel) { return new Locator(this, { sel }); }
  async screenshot(o) { this.j.push(['capture', o.path, o.clip ?? null, o.fullPage ?? false]); await this.site.capture?.(o, this); return Buffer.from(''); }
  async pdf(o) { this.j.push(['pdf', o.path]); fsReel.writeFileSync(o.path, '%PDF-faux'); }
  async addScriptTag(o) { this.j.push(['script', o.path]); return this.site.script?.(o, this); }
}

// chromium simulé : site.lancement(n), site.fermeture(n), site.nouveauContexte(n), site.fermerContexte(n) peuvent lever.
export function chromiumFaux(site, j) {
  let lancements = 0, fermetures = 0, contextes = 0, fermesCtx = 0;
  return {
    async launch() {
      lancements++; j.push(['launch', lancements]);
      site.lancement?.(lancements);
      return {
        async newContext(o) {
          contextes++; j.push(['newContext', contextes, o ?? null]);
          site.nouveauContexte?.(contextes);
          return { async newPage() { return new FaussePage(site, j); },
            async close() { fermesCtx++; j.push(['closeContext', fermesCtx]); site.fermerContexte?.(fermesCtx); } };
        },
        async close() { fermetures++; j.push(['close', fermetures]); site.fermeture?.(fermetures); },
      };
    },
  };
}

// Prépare le processus enfant puis importe le script. sc : { csv, args, site, mocks(mock, j), request(j) }.
export async function executerScenario(mock, nomScript, sc) {
  const TMP = process.env.AIDE_TMP;
  const j = [];
  process.on('exit', () => fsReel.writeFileSync(join(TMP, 'journal.json'), JSON.stringify(j)));
  const rediriger = (p, ecriture = false) => {
    const s = p instanceof URL ? fileURLToPath(p) : String(p);
    for (const r of [RACINE, RACINE_DEC]) {
      if (s.startsWith(`${r}resultats`)) return join(TMP, s.slice(r.length));
      if (ecriture && s.startsWith(r)) throw new Error(`écriture non prévue dans le dépôt : ${s}`);
    }
    return s;
  };
  const csv = `${RACINE}scripts/ecrans_en_ligne.csv`;
  const surcharges = {
    readFileSync: (p, ...a) => (String(p) === csv ? sc.csv : fsReel.readFileSync(rediriger(p), ...a)),
    writeFileSync: (p, ...a) => fsReel.writeFileSync(rediriger(p, true), ...a),
    mkdirSync: (p, ...a) => fsReel.mkdirSync(rediriger(p, true), ...a),
    existsSync: p => fsReel.existsSync(rediriger(p)),
  };
  const { default: defaut, ...nommes } = fsReel;
  mock.module('node:fs', { namedExports: { ...nommes, ...surcharges }, defaultExport: { ...defaut, ...surcharges } });
  mock.module('playwright', { namedExports: { chromium: chromiumFaux(sc.site, j), request: typeof sc.request === 'function' ? sc.request(j) : {} } });
  sc.mocks?.(mock, j);
  // Temps accéléré : les pauses et les délais maximaux des scripts passent aussitôt.
  globalThis.setTimeout = (f, ms, ...a) => setImmediate(f, ...a);
  const chemin = `${RACINE_DEC}scripts/${nomScript}`;
  process.argv = [process.argv[0], chemin, ...(sc.args ?? [])];
  await import(new URL(`../../scripts/${nomScript}`, import.meta.url).href);
}
