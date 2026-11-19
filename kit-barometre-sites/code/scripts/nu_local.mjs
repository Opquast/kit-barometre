// Validateur Nu (W3C) en local, sur le code source brut des écrans du baromètre (lecture seule).
// Remplace l'appel au service en ligne validator.w3.org, désormais derrière une vérification Cloudflare.
// Le validateur (vnu-runtime-image, version officielle « latest », empreinte SHA-1 vérifiée) est installé hors du
// dépôt, utilisé puis supprimé : son chemin est passé en argument.
//
// Usage : node scripts/nu_local.mjs <chemin de vnu-runtime-image/bin/vnu> [--service "Boutique A"]
// Sortie : met à jour resultats/outils-AAAA-MM-JJ/en_ligne.json (clé nu, source « local ») et nu_local.json
import { request } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const RACINE = new URL('..', import.meta.url).pathname;
const VNU = process.argv[2];
const args = process.argv.slice(3);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const ecrans = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(','); return { service, gabarit, url: u.join(',') };
}).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/outils-${date}`;
const tmp = `${dossier}/.nu`; mkdirSync(tmp, { recursive: true });
const ctx = await request.newContext({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36', extraHTTPHeaders: { 'Accept-Language': 'fr-FR' } });
const deja = existsSync(`${dossier}/nu_local.json`) ? JSON.parse(readFileSync(`${dossier}/nu_local.json`, 'utf8')) : {};
const res = deja;
for (const e of ecrans) {
  const s = (res[e.service] ??= {});
  if (s[e.url]?.erreurs !== undefined) continue;  // déjà validée : on ne refait que les pages manquantes
  try {
    const r = await ctx.get(e.url, { timeout: 45000 });
    if (r.status() === 429) throw new Error('429 : limité par le serveur');
    if (new URL(r.url()).host !== new URL(e.url).host) throw new Error('quitte le site (compte client hébergé par Shopify)');
    const f = `${tmp}/page.html`; writeFileSync(f, await r.body());
    // vnu écrit ses messages sur la sortie d'erreur (lire stdout seul donnait « 0 erreur » partout : faux négatif du 12/11)
    const run = spawnSync(VNU, ['--format', 'json', '--exit-zero-always', f], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
    const brut = (run.stderr || '').trim() || (run.stdout || '').trim();
    if (!brut.startsWith('{')) throw new Error('sortie du validateur illisible : ' + brut.slice(0, 80));
    const msgs = JSON.parse(brut).messages || [];
    if (!msgs.length && (await r.body()).length > 5000) throw new Error('aucun message sur une page non vide : résultat douteux, non retenu');
    const err = msgs.filter(m => m.type === 'error');
    const top = {};
    for (const m of err) { const k = m.message.split('“')[0].trim().slice(0, 90); top[k] = (top[k] || 0) + 1; }
    s[e.url] = { gabarit: e.gabarit, erreurs: err.length, avertissements: msgs.filter(m => m.subType === 'warning').length,
      principales: Object.entries(top).sort((a, b) => b[1] - a[1]).slice(0, 8),
      identifiants_en_double: err.filter(m => m.message.startsWith('Duplicate ID')).length,
      details_url: `https://validator.w3.org/nu/?doc=${encodeURIComponent(e.url)}`, source: 'validateur Nu local (vnu)' };
  } catch (err) { s[e.url] = { gabarit: e.gabarit, erreur: String(err.message).split('\n')[0].slice(0, 120) }; }
  console.log(e.service, '|', e.gabarit, '|', s[e.url].erreur || `${s[e.url].erreurs} erreurs`);
  await pause(10000);
}
await ctx.dispose();
rmSync(tmp, { recursive: true, force: true });
writeFileSync(`${dossier}/nu_local.json`, JSON.stringify(res, null, 1));
const f = `${dossier}/en_ligne.json`;
if (existsSync(f)) {
  const d = JSON.parse(readFileSync(f, 'utf8'));
  for (const [nom, pages] of Object.entries(res)) { d[nom] ??= {}; d[nom].nu = pages; }
  writeFileSync(f, JSON.stringify(d, null, 1));
}
console.log(`${dossier}/nu_local.json`);
