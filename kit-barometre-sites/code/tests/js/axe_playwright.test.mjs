// Tests de scripts/axe_playwright.mjs : Playwright et @axe-core/playwright simulés, sorties dans un dossier temporaire.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { lancer, executerScenario, aujourdhui, RACINE_DEC } from './aide_parcours.mjs';

const REGLES_AXE = [
  { ruleId: 'color-contrast', tags: ['cat.color', 'wcag2aa'] },
  { ruleId: 'region', tags: ['best-practice'] },
  { ruleId: 'image-alt', tags: ['wcag2a'] },
  { ruleId: 'wcag-ok', tags: ['wcag21aa'] },
  { ruleId: 'wcag-exp', tags: ['wcag2a', 'experimental'] },
  { ruleId: 'wcag-dep', tags: ['wcag2a', 'deprecated'] },
  { ruleId: 'bp', tags: ['best-practice'] },
];
const RESULTAT_ACCUEIL = {
  inapplicable: [{ id: 'area-alt', tags: ['wcag2a'] }],
  passes: [{ id: 'image-alt', tags: ['wcag2a', 'wcag111'] }, { id: 'region', tags: ['best-practice'] }],
  incomplete: [{ id: 'color-contrast', tags: ['wcag2aa', 'wcag143'] }],
  violations: [
    { id: 'link-name', impact: 'serious', tags: ['wcag2a', 'wcag244', 'wcag412'], nodes: [{}, {}] },
    { id: 'landmark-one-main', impact: 'moderate', tags: ['best-practice'], nodes: [{}] },
  ],
};
const VIDE = { inapplicable: [], passes: [], incomplete: [], violations: [] };

const CSV = `service,gabarit,url
Boutique A,Accueil,https://a.fr
Boutique A,Panier,https://a.fr/cart
Boutique A,Compte,https://a.fr/account
Boutique A,Erreur,https://a.fr/introuvable
Boutique A,Vide,https://a.fr/vide
Boutique A,Lente,https://a.fr/lente
Boutique A,Crash,https://a.fr/crash
Boutique A,Crash 2,https://a.fr/crash2
"Boutique ""B"", bis",Accueil,https://b.fr/`;

function site(analyses, fermetureRatee = 0) {
  return {
    page: url => ({
      'https://a.fr/account': { finale: 'https://shopify.com/123/account' },
      'https://a.fr/introuvable': { status: 404 },
      'https://a.fr/vide': { status: null },
      'https://a.fr/crash': { erreur: 'Target page, context or browser has been closed\nlog' },
      'https://a.fr/crash2': { erreur: 'browser has crashed' },
    })[url] ?? {},
    script: (o, page) => { page.courant.win.axe = { getRules: () => REGLES_AXE }; },
    fermeture: n => { if (n === fermetureRatee) throw new Error('déjà fermé'); },
    analyses,
  };
}

const SCENARIOS = {
  complet: () => ({
    csv: CSV, args: [],
    site: site({ 'https://a.fr': RESULTAT_ACCUEIL, 'https://a.fr/cart': VIDE, 'https://a.fr/lente': 'attente', 'https://b.fr/': VIDE }, 1),
  }),
  service: () => ({
    csv: CSV, args: ['--service', 'Boutique "B", bis'],
    site: site({ 'https://b.fr/': VIDE }),
  }),
};

function mocks(sc) {
  return (m, j) => m.module('@axe-core/playwright', { defaultExport: class {
    constructor({ page }) { this.page = page; }
    withRules(r) { j.push(['withRules', r]); return this; }
    analyze() { const a = sc.site.analyses[this.page.url()]; return a === 'attente' ? new Promise(() => {}) : Promise.resolve(a); }
  } });
}

if (process.env.AIDE_SCENARIO) {
  const sc = SCENARIOS[process.env.AIDE_SCENARIO]();
  await executerScenario(mock, 'axe_playwright.mjs', { ...sc, mocks: mocks(sc) });
} else {
  const source = readFileSync(`${RACINE_DEC}scripts/axe_playwright.mjs`, 'utf8');
  const ESM = JSON.parse(source.match(/export const ESM = (\[[^\]]+\])/)[1].replace(/'/g, '"'));
  const tsv = t => t.replace(/\n$/, '').split('\n').map(l => l.split('\t'));
  const dossier = `resultats/axe-${aujourdhui()}`;

  test('axe_playwright : tous les cas de page (réussite, sortie du site, erreurs, délai, plantages)', () => {
    const r = lancer(import.meta.url, 'complet');
    assert.equal(r.status, 0, r.stderr);
    // règles retenues : ESM + WCAG stables, sans expérimentales ni obsolètes ni bonnes pratiques hors ESM
    assert.deepEqual(r.journal.find(x => x[0] === 'withRules')[1], ['color-contrast', 'region', 'image-alt', 'wcag-ok']);
    const brut = tsv(r.lire(`${dossier}/brut.tsv`));
    assert.deepEqual(brut[0], ['service', 'gabarit', 'chemin', 'regles_respectees', 'a_verifier', 'violations']);
    assert.deepEqual(brut[1], ['Boutique A', 'Accueil', '/', '1', '1', 'link-name:serious:wcag244 wcag412:2']);
    assert.deepEqual(brut[2], ['Boutique A', 'Panier', '/cart', '0', '0', '']);
    assert.deepEqual(brut[3], ['Boutique A', 'Compte', '/account', 'NT', 'NT', 'non testé : quitte le site (shopify.com), compte client hébergé par Shopify']);
    assert.deepEqual(brut[4], ['Boutique A', 'Erreur', '/introuvable', 'NT', 'NT', 'non testé : code 404']);
    assert.deepEqual(brut[5], ['Boutique A', 'Vide', '/vide', 'NT', 'NT', 'non testé : code aucune réponse']);
    assert.deepEqual(brut[6], ['Boutique A', 'Lente', '/lente', 'NT', 'NT', 'non testé : analyse axe-core interrompue après 120 s']);
    assert.deepEqual(brut[7], ['Boutique A', 'Crash', '/crash', 'NT', 'NT', 'non testé : Target page, context or browser has been closed']);
    assert.deepEqual(brut[8], ['Boutique A', 'Crash 2', '/crash2', 'NT', 'NT', 'non testé : browser has crashed']);
    assert.deepEqual(brut[9], ['Boutique "B", bis', 'Accueil', '/', '0', '0', '']);
    assert.equal(brut.length, 10);

    const esm = tsv(r.lire(`${dossier}/esm.tsv`));
    assert.deepEqual(esm[0], ['service', 'gabarit', 'url', 'url_finale', 'statuts']);
    const attendu = ESM.map(id => ({ 'area-alt': 'A', 'image-alt': 'C', region: 'C', 'color-contrast': 'I', 'link-name': 'N', 'landmark-one-main': 'N' })[id] || '-').join('');
    assert.deepEqual(esm[1], ['Boutique A', 'Accueil', 'https://a.fr', 'https://a.fr', attendu]);
    assert.equal(esm[2][4], '-'.repeat(ESM.length));
    assert.deepEqual(esm[3], ['Boutique A', 'Compte', 'https://a.fr/account', 'https://shopify.com/123/account', 'non testé']);
    assert.deepEqual(esm[4].slice(3), ['https://a.fr/introuvable', 'non testé']);
    assert.deepEqual(esm[7].slice(3), ['', 'non testé']);
    // deux plantages : deux relances (la première fermeture échoue sans bloquer), puis fermeture finale
    assert.equal(r.journal.filter(x => x[0] === 'launch').length, 3);
    assert.equal(r.journal.filter(x => x[0] === 'close').length, 3);
    assert.match(r.stdout, /Boutique A \| Panier \| aucune violation WCAG/);
    assert.match(r.stdout, /Boutique A \| Accueil \| link-name:serious/);
    assert.match(r.stdout, /axe-\d{4}-\d{2}-\d{2} : 9 écrans/);
  });

  test('axe_playwright : --service ne garde que le service demandé', () => {
    const r = lancer(import.meta.url, 'service');
    assert.equal(r.status, 0, r.stderr);
    const brut = tsv(r.lire(`${dossier}/brut.tsv`));
    assert.equal(brut.length, 2);
    assert.equal(brut[1][0], 'Boutique "B", bis');
    assert.match(r.stdout, / : 1 écrans/);
  });
}
