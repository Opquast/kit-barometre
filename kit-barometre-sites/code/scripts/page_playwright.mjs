// Passe scripts/controles_page.js sur tous les écrans du baromètre avec Playwright (Chromium, 1280 x 900).
//
// Même script que dans le navigateur, sans intervention : chaque écran de scripts/ecrans_en_ligne.csv est ouvert,
// rendu, puis controles_page.js est exécuté dans la page. Lecture seule (seules des requêtes HEAD vers 30 liens
// internes au plus, règle 152). Une page toutes les 6 secondes. Une page qui quitte le site (comptes clients
// hébergés par Shopify) ou renvoie une erreur est « non testée » : on ne contourne aucune protection.
//
// Sortie : resultats/page-AAAA-MM-JJ/resultats.json, au même format que les contrôles réseau
// ({ meta, services: { <service>: { pages: [{ gabarit, url, url_finale, statut_http, controles: [...] }] } } }),
// puis rapport.md.
//
// Usage : npm run page   (ou node scripts/page_playwright.mjs [--service "Boutique A"])
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const RACINE = new URL('..', import.meta.url).pathname;
const SCRIPT = readFileSync(`${RACINE}scripts/controles_page.js`, 'utf8');
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
const debut = new Date();
const date = debut.toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/page-${date}`;
mkdirSync(dossier, { recursive: true });

const navigateur = await chromium.launch();
const contexte = await navigateur.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
const page = await contexte.newPage();
const services = {};
let version = '';
for (const e of ecrans) {
  const s = (services[e.service] ??= { pages: [] });
  const fiche = { gabarit: e.gabarit, url: e.url, url_finale: '', statut_http: null, controles: [] };
  try {
    const rep = await page.goto(e.url, { waitUntil: 'load', timeout: 45000 });
    await pause(3000);
    fiche.url_finale = page.url();
    fiche.statut_http = rep ? rep.status() : null;
    if (new URL(fiche.url_finale).host !== new URL(e.url).host) {
      fiche.non_teste = `quitte le site (${new URL(fiche.url_finale).host}) : compte client hébergé par Shopify`;
    } else if (!rep || rep.status() >= 400) {
      fiche.non_teste = `code ${rep ? rep.status() : 'aucune réponse'}`;
    } else {
      // code source brut, tel qu'envoyé par le serveur : la position de la meta charset se mesure en octets (règle 232)
      const brut = await rep.text().catch(() => '');
      const octets = Buffer.from(brut, 'utf8');
      const m = /<meta[^>]+charset\s*=\s*["']?[\w-]+[^>]*>|<meta[^>]+http-equiv\s*=\s*["']?content-type[^>]*>/i.exec(brut);
      const fin = m ? Buffer.byteLength(brut.slice(0, m.index + m[0].length), 'utf8') : null;
      const declarations = (brut.match(/<meta[^>]+charset\s*=|<meta[^>]+http-equiv\s*=\s*["']?content-type/gi) || []).length;
      await page.evaluate(b => { window.__BRUT = b; }, { taille: octets.length, fin_meta_charset: fin, declarations });
      const r = await page.evaluate(SCRIPT);
      version = r.version;
      fiche.controles = Object.entries(r.resultats).map(([n, [statut, detail]]) =>
        ({ rule_number: Number(n), status: statut, comment: detail, evidence: '' }));
    }
  } catch (err) {
    fiche.non_teste = String(err.message).split('\n')[0];
  }
  s.pages.push(fiche);
  const nc = fiche.controles.filter(c => c.status === 'non-conforme').length;
  console.log(`${e.service} | ${e.gabarit} | ${fiche.non_teste ? 'non testé : ' + fiche.non_teste : `${fiche.controles.length} règles, ${nc} non conformes`}`);
  await pause(6000);
}
await navigateur.close();

const meta = { script: 'scripts/page_playwright.mjs', controles: version, date: debut.toISOString(), navigateur: 'Chromium (Playwright), 1280 x 900', referentiel: 'Opquast V5 qualite-numerique' };
writeFileSync(`${dossier}/resultats.json`, JSON.stringify({ meta, services }, null, 2));

// Rapport : par site, nombre de pages non conformes pour chaque règle.
const md = [`# Contrôles du code de la page (${version}) du ${date}`, '',
  'Script `scripts/controles_page.js` exécuté dans Chromium par `scripts/page_playwright.mjs` sur chaque écran. Aucune IA.', ''];
const regles = [...new Set(Object.values(services).flatMap(s => s.pages.flatMap(p => p.controles.map(c => c.rule_number)))) ].sort((a, b) => a - b);
md.push('| Règle | ' + Object.keys(services).join(' | ') + ' |', '|---|' + Object.keys(services).map(() => '---|').join(''));
for (const n of regles) {
  const cells = Object.values(services).map(s => {
    const st = s.pages.map(p => p.controles.find(c => c.rule_number === n)?.status).filter(Boolean);
    const nc = st.filter(x => x === 'non-conforme').length, c = st.filter(x => x === 'conforme').length;
    return nc ? `**${nc} NC** / ${st.length}` : c ? `C (${c})` : st.length ? st[0] : '';
  });
  md.push(`| ${n} | ${cells.join(' | ')} |`);
}
md.push('', 'Lecture : « 3 NC / 8 » = non conforme sur 3 des 8 pages testées ; « C (8) » = conforme sur 8 pages ; sinon non applicable ou non testé.', '');
for (const [nom, s] of Object.entries(services)) {
  for (const p of s.pages.filter(p => p.non_teste)) md.push(`- ${nom}, ${p.gabarit} : non testé (${p.non_teste}).`);
}
writeFileSync(`${dossier}/rapport.md`, md.join('\n') + '\n');
console.log(`${dossier} : ${ecrans.length} écrans`);
