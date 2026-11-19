// Contrôle automatique d'accessibilité des écrans du baromètre avec axe-core 4.10.2 et Playwright.
//
// Même logique que scripts/axe_navigateur.js (v2), mais sans intervention : Playwright ouvre chaque écran
// de scripts/ecrans_en_ligne.csv dans Chromium (1280 x 900), attend le rendu, lance axe-core et écrit :
//   - resultats/axe-AAAA-MM-JJ/brut.tsv : violations WCAG 2.1 A et AA par page (lu par scripts/synthese_axe.py) ;
//   - resultats/axe-AAAA-MM-JJ/esm.tsv  : statut de chaque page sur les 51 règles de la checklist native
//     « axe-core — WCAG 2.1 A/AA » d'eServices Manager (C conforme, N non conforme, A non applicable, I à vérifier).
//
// Lecture seule : aucune action sur la page (pas de clic, pas de formulaire). Une page toutes les 5 secondes.
// Une page qui quitte le site (comptes clients hébergés par Shopify) ou qui renvoie une erreur est « non testée » :
// on ne contourne aucune protection.
//
// Usage : npm run axe   (ou node scripts/axe_playwright.mjs [--service "Boutique A"])
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const RACINE = new URL('..', import.meta.url).pathname;
export const ESM = ['color-contrast', 'color-contrast-enhanced', 'image-alt', 'image-redundant-alt', 'input-image-alt',
  'object-alt', 'area-alt', 'empty-heading', 'heading-order', 'page-has-heading-one', 'label', 'label-title-only',
  'form-field-multiple-labels', 'select-name', 'autocomplete-valid', 'button-name', 'link-name', 'frame-title',
  'document-title', 'html-has-lang', 'html-lang-valid', 'html-xml-lang-mismatch', 'valid-lang', 'meta-viewport',
  'aria-allowed-attr', 'aria-allowed-role', 'aria-required-attr', 'aria-required-children', 'aria-required-parent',
  'aria-roles', 'aria-valid-attr', 'aria-valid-attr-value', 'aria-hidden-body', 'aria-hidden-focus',
  'aria-input-field-name', 'aria-toggle-field-name', 'bypass', 'duplicate-id', 'duplicate-id-active',
  'duplicate-id-aria', 'tabindex', 'landmark-one-main', 'landmark-unique', 'region', 'list', 'listitem',
  'definition-list', 'dlitem', 'td-headers-attr', 'th-has-data-cells', 'table-fake-caption'];
const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];
const pause = ms => new Promise(ok => setTimeout(ok, ms));

function lireCsv(chemin) {
  const [tete, ...lignes] = readFileSync(chemin, 'utf8').trim().split('\n');
  const cols = tete.split(',');
  return lignes.map(l => {
    const v = l.match(/("([^"]|"")*"|[^,]*)(,|$)/g).map(x => x.replace(/,$/, '').replace(/^"|"$/g, '').replace(/""/g, '"'));
    return Object.fromEntries(cols.map((c, i) => [c, v[i]]));
  });
}

const args = process.argv.slice(2);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const ecrans = lireCsv(`${RACINE}scripts/ecrans_en_ligne.csv`).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/axe-${date}`;
mkdirSync(dossier, { recursive: true });

let navigateur = await chromium.launch();
let contexte = await navigateur.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
let page = await contexte.newPage();
// relance du navigateur s'il a planté (mémoire saturée, 12/11) : sans elle, toutes les pages suivantes échouent
async function relancer() {
  try { await navigateur.close(); } catch {}
  navigateur = await chromium.launch();
  contexte = await navigateur.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
  page = await contexte.newPage();
}
// Règles WCAG stables + les 51 règles d'eServices Manager (certaines sont des bonnes pratiques hors WCAG).
await page.goto('about:blank');
await page.addScriptTag({ path: `${RACINE}node_modules/axe-core/axe.min.js` });
const toutes = await page.evaluate(() => window.axe.getRules().map(r => ({ id: r.ruleId, tags: r.tags })));
const regles = toutes.filter(r => ESM.includes(r.id) ||
  (r.tags.some(t => WCAG.includes(t)) && !r.tags.includes('experimental') && !r.tags.includes('deprecated'))).map(r => r.id);

const brut = [['service', 'gabarit', 'chemin', 'regles_respectees', 'a_verifier', 'violations']];
// Colonne statuts : un caractère par règle, dans l'ordre de ESM (voir referentiel/axe-esm.csv).
const esm = [['service', 'gabarit', 'url', 'url_finale', 'statuts']];
for (const e of ecrans) {
  const hote = new URL(e.url).host;
  const chemin = e.url.replace(/^https?:\/\/[^/]+/, '') || '/';
  let ligne;
  try {
    const rep = await page.goto(e.url, { waitUntil: 'load', timeout: 45000 });
    await pause(3000);
    const finale = page.url();
    if (new URL(finale).host !== hote) {
      ligne = ['NT', 'NT', `non testé : quitte le site (${new URL(finale).host}), compte client hébergé par Shopify`];
      esm.push([e.service, e.gabarit, e.url, finale, 'non testé']);
    } else if (!rep || rep.status() >= 400) {
      ligne = ['NT', 'NT', `non testé : code ${rep ? rep.status() : 'aucune réponse'}`];
      esm.push([e.service, e.gabarit, e.url, finale, 'non testé']);
    } else {
      // délai maximal : sur une page lourde, l'analyse peut ne jamais rendre la main (blocage du 12/11)
      const r = await Promise.race([new AxeBuilder({ page }).withRules(regles).analyze(),
        new Promise((_, ko) => setTimeout(() => ko(new Error('analyse axe-core interrompue après 120 s')), 120000))]);
      const st = {};
      for (const [l, c] of [[r.inapplicable, 'A'], [r.passes, 'C'], [r.incomplete, 'I'], [r.violations, 'N']]) for (const v of l) st[v.id] = c;
      const estWcag = v => v.tags.some(t => WCAG.includes(t));
      const viol = r.violations.filter(estWcag)
        .map(v => `${v.id}:${v.impact}:${v.tags.filter(t => /^wcag\d{3,}$/.test(t)).join(' ')}:${v.nodes.length}`);
      ligne = [r.passes.filter(estWcag).length, r.incomplete.filter(estWcag).length, viol.join(';')];
      esm.push([e.service, e.gabarit, e.url, finale, ESM.map(id => st[id] || '-').join('')]);
    }
  } catch (err) {
    if (/closed|crash|Target/.test(err.message)) await relancer();
    ligne = ['NT', 'NT', `non testé : ${String(err.message).split('\n')[0]}`];
    esm.push([e.service, e.gabarit, e.url, '', 'non testé']);
  }
  brut.push([e.service, e.gabarit, chemin, ...ligne]);
  console.log(`${e.service} | ${e.gabarit} | ${ligne[2] || 'aucune violation WCAG'}`);
  await pause(5000);
}
await navigateur.close();
writeFileSync(`${dossier}/brut.tsv`, brut.map(l => l.join('\t')).join('\n') + '\n');
writeFileSync(`${dossier}/esm.tsv`, esm.map(l => l.join('\t')).join('\n') + '\n');
console.log(`${dossier} : ${ecrans.length} écrans`);
