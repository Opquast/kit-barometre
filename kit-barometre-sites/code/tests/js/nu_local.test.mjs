// Tests de scripts/nu_local.mjs : requêtes Playwright et validateur vnu (spawnSync) remplacés par des faux.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { enfant, lancer, preparerEnfant, urlScript, DATE } from './aide_outils.mjs';

const json = o => JSON.stringify(o);
const MESSAGES = [
  { type: 'error', message: 'Duplicate ID “x”.' },
  { type: 'error', message: 'Stray end tag “div”.' },
  { type: 'error', message: 'Bad value “y” for attribute “href”.' },
  { type: 'error', message: 'Stray end tag “div”.' },
  { type: 'error', message: 'Duplicate ID “z”.' },
  { type: 'error', message: 'Stray end tag “p”.' },
  { type: 'info', subType: 'warning', message: 'Consider adding a lang attribute.' },
  { type: 'info', message: 'Trailing slash on void elements.' },
];
const PAGES = {
  'https://a.fr/': { corps: '<!doctype html><p>a', vnu: { stderr: json({ messages: MESSAGES }), stdout: '' } },
  'https://a.fr/p?x=1,2': { corps: '<p>b', vnu: { stderr: '', stdout: json({ messages: [{ type: 'error', message: 'Element “p” not allowed.' }] }) } },
  'https://a.fr/429': { statut: 429 },
  'https://a.fr/account': { final: 'https://shopify.com/account' },
  'https://a.fr/vide': { corps: '<p>', vnu: {} },
  'https://a.fr/java': { corps: '<p>', vnu: { stderr: 'Exception in thread "main"\n\tat nu.validator' } },
  'https://a.fr/douteux': { corps: 'x'.repeat(5001), vnu: { stderr: json({ messages: [] }) } },
  'https://a.fr/sm': { corps: '<p>court</p>', vnu: { stderr: '{}' } },
  'https://b.fr/': { lance: 'net::ERR_NAME_NOT_RESOLVED\nlog' },
};
const CSV = `service,gabarit,url
A,Accueil,https://a.fr/
A,Produit,https://a.fr/p?x=1,2
A,Limite,https://a.fr/429
A,Compte,https://a.fr/account
A,Vide,https://a.fr/vide
A,Java,https://a.fr/java
A,Douteux,https://a.fr/douteux
A,Sans messages,https://a.fr/sm
B,Accueil,https://b.fr/
`;
const VNU = '/opt/vnu-runtime-image/bin/vnu';

if (enfant) {
  const { tmp, rediriger } = preparerEnfant(mock, 'nu_local.mjs');
  const journal = { contexte: null, vnu: [], dispose: false };
  let courante = null;
  mock.module('playwright', { namedExports: { request: {
    newContext: async opts => {
      journal.contexte = opts;
      return {
        get: async (url, opts) => {
          const c = PAGES[url];
          assert.deepEqual(opts, { timeout: 45000 });
          if (c.lance) throw new Error(c.lance);
          courante = url;
          return { status: () => c.statut ?? 200, url: () => c.final ?? url, body: async () => Buffer.from(c.corps) };
        },
        dispose: async () => { journal.dispose = true; },
      };
    },
  } } });
  mock.module('node:child_process', { namedExports: { spawnSync: (cmd, a, opts) => {
    journal.vnu.push({ cmd, a, opts, contenu: readFileSync(rediriger(a.at(-1)), 'utf8') });
    return PAGES[courante].vnu;
  } } });
  process.on('exit', () => writeFileSync(join(tmp, 'journal.json'), JSON.stringify(journal)));
  await import(urlScript('nu_local.mjs'));
} else {
  const dossier = `resultats/outils-${DATE}`;

  test('validation de tous les écrans, erreurs du validateur et fusion dans en_ligne.json', t => {
    const r = lancer(import.meta.url, 'tous', { csv: CSV, argv: [VNU],
      fichiers: { [`${dossier}/en_ligne.json`]: { A: { http: { ok: true } } } } });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const res = r.json(`${dossier}/nu_local.json`);
    const a = res.A;
    assert.deepEqual(a['https://a.fr/'], {
      gabarit: 'Accueil', erreurs: 6, avertissements: 1,
      principales: [['Stray end tag', 3], ['Duplicate ID', 2], ['Bad value', 1]],
      identifiants_en_double: 2, details_url: 'https://validator.w3.org/nu/?doc=https%3A%2F%2Fa.fr%2F', source: 'validateur Nu local (vnu)' });
    // vnu sans rien sur stderr : la sortie standard est lue ; l'URL avec virgule est recomposée
    assert.equal(a['https://a.fr/p?x=1,2'].erreurs, 1);
    assert.equal(a['https://a.fr/p?x=1,2'].gabarit, 'Produit');
    assert.deepEqual(a['https://a.fr/429'], { gabarit: 'Limite', erreur: '429 : limité par le serveur' });
    assert.equal(a['https://a.fr/account'].erreur, 'quitte le site (compte client hébergé par Shopify)');
    assert.equal(a['https://a.fr/vide'].erreur, 'sortie du validateur illisible : ');
    assert.equal(a['https://a.fr/java'].erreur, 'sortie du validateur illisible : Exception in thread "main"');
    assert.equal(a['https://a.fr/douteux'].erreur, 'aucun message sur une page non vide : résultat douteux, non retenu');
    assert.deepEqual(a['https://a.fr/sm'], { gabarit: 'Sans messages', erreurs: 0, avertissements: 0, principales: [],
      identifiants_en_double: 0, details_url: 'https://validator.w3.org/nu/?doc=https%3A%2F%2Fa.fr%2Fsm', source: 'validateur Nu local (vnu)' });
    assert.deepEqual(res.B, { 'https://b.fr/': { gabarit: 'Accueil', erreur: 'net::ERR_NAME_NOT_RESOLVED' } });

    const enLigne = r.json(`${dossier}/en_ligne.json`);
    assert.deepEqual(enLigne.A.http, { ok: true });
    assert.deepEqual(enLigne.A.nu, a);
    assert.deepEqual(enLigne.B.nu, res.B);
    assert.ok(!r.existe(`${dossier}/.nu`), 'dossier temporaire du validateur supprimé');

    const j = r.json('journal.json');
    assert.equal(j.dispose, true);
    assert.equal(j.contexte.extraHTTPHeaders['Accept-Language'], 'fr-FR');
    assert.equal(j.vnu.length, 6);
    assert.equal(j.vnu[0].cmd, VNU);
    assert.deepEqual(j.vnu[0].a.slice(0, 2), ['--format', 'json']);
    assert.equal(j.vnu[0].a[2], '--exit-zero-always');
    assert.ok(j.vnu[0].a[3].endsWith(`${dossier}/.nu/page.html`));
    assert.equal(j.vnu[0].contenu, '<!doctype html><p>a');
    assert.match(r.sortie, /A \| Accueil \| 6 erreurs/);
    assert.match(r.sortie, /B \| Accueil \| net::ERR_NAME_NOT_RESOLVED/);
  });

  test('--service et reprise : les pages déjà validées ne sont pas refaites, sans en_ligne.json', t => {
    const r = lancer(import.meta.url, 'reprise', { csv: CSV, argv: [VNU, '--service', 'A'],
      fichiers: { [`${dossier}/nu_local.json`]: { A: { 'https://a.fr/': { gabarit: 'Accueil', erreurs: 0 },
        'https://a.fr/p?x=1,2': { gabarit: 'Produit', erreur: 'ancien' } } } } });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const res = r.json(`${dossier}/nu_local.json`);
    assert.deepEqual(Object.keys(res), ['A']);
    assert.deepEqual(res.A['https://a.fr/'], { gabarit: 'Accueil', erreurs: 0 });
    assert.equal(res.A['https://a.fr/p?x=1,2'].erreurs, 1);
    assert.equal(Object.keys(res.A).length, 8);
    assert.ok(!r.existe(`${dossier}/en_ligne.json`));
    assert.equal(r.json('journal.json').vnu.length, 5);
  });
}
