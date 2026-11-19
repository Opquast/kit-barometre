// Tests de scripts/axe_navigateur.js : faux window.axe, aucun chargement réseau réel.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fenetre, executer } from './aide_navigateur.mjs';

const SCRIPT = 'axe_navigateur.js';

// Faux axe-core : règles déclarées, résultats imposés, appels à run() enregistrés.
function fauxAxe(resultats) {
  const appels = [];
  return {
    appels,
    version: '4.10.2-test',
    getRules: () => [
      { ruleId: 'image-alt', tags: ['cat.text-alternatives'] },                  // ESM, hors étiquette WCAG
      { ruleId: 'color-contrast-enhanced', tags: ['wcag2aaa', 'experimental'] },  // ESM même expérimentale
      { ruleId: 'nested-interactive', tags: ['wcag2a', 'wcag412'] },             // WCAG stable
      { ruleId: 'regle-experimentale', tags: ['wcag21aa', 'experimental'] },     // WCAG expérimentale : exclue
      { ruleId: 'regle-depreciee', tags: ['wcag2a', 'deprecated'] },             // WCAG dépréciée : exclue
      { ruleId: 'regle-aaa', tags: ['wcag2aaa'] },                               // ni ESM ni A/AA : exclue
    ],
    run: async (doc, options) => { appels.push({ doc, options }); return resultats; },
  };
}

const resultatsTypes = () => ({
  inapplicable: [{ id: 'frame-title', tags: ['wcag2a'] }],
  passes: [
    { id: 'image-alt', tags: ['wcag2a', 'wcag111'] },
    { id: 'html-has-lang', tags: ['wcag2a'] },
    { id: 'region', tags: ['best-practice'] },
  ],
  incomplete: [
    { id: 'color-contrast', tags: ['wcag2aa', 'wcag143'] },
    { id: 'heading-order', tags: ['best-practice'] },
  ],
  violations: [
    { id: 'link-name', impact: 'serious', tags: ['wcag2a', 'wcag244', 'wcag412', 'cat.name-role-value'], nodes: [{}, {}] },
    { id: 'landmark-one-main', impact: 'moderate', tags: ['best-practice'], nodes: [{}] },
  ],
});

test('axe déjà présent : sélection des règles, statuts C/N/A/I par règle ESM, synthèse WCAG', async () => {
  const w = fenetre('<main><p>Bonjour</p></main>', { url: 'https://www.boutique.fr/page' });
  const axe = fauxAxe(resultatsTypes());
  w.axe = axe;
  const sorties = [];
  w.console.log = s => sorties.push(s);

  const r = await executer(SCRIPT, w);

  // Règles lancées : ESM (même hors WCAG ou expérimentales) + WCAG A/AA stables.
  assert.equal(axe.appels.length, 1);
  assert.equal(axe.appels[0].doc, w.document);
  assert.deepEqual(JSON.parse(JSON.stringify(axe.appels[0].options)),
    { runOnly: { type: 'rule', values: ['image-alt', 'color-contrast-enhanced', 'nested-interactive'] } });

  assert.equal(r.url, 'https://www.boutique.fr/page');
  assert.equal(r.outil, 'axe-core 4.10.2-test');
  assert.equal(r.esm.length, 51);
  // Position dans la liste ESM : color-contrast 0, image-alt 2, heading-order 8, link-name 16,
  // frame-title 17, html-has-lang 19, landmark-one-main 41, region 43 ; le reste « - ».
  const attendu = Array(51).fill('-');
  Object.assign(attendu, { 0: 'I', 2: 'C', 8: 'I', 16: 'N', 17: 'A', 19: 'C', 41: 'N', 43: 'C' });
  assert.equal(r.esm, attendu.join(''));
  assert.equal(r.wcag_respectees, 2);
  assert.deepEqual([...r.wcag_a_verifier], ['color-contrast']);
  assert.deepEqual(JSON.parse(JSON.stringify(r.violations)), [
    { regle: 'link-name', gravite: 'serious', criteres_wcag: ['wcag244', 'wcag412'], wcag: true, elements: 2 },
    { regle: 'landmark-one-main', gravite: 'moderate', criteres_wcag: [], wcag: false, elements: 1 },
  ]);
  // Le résultat est aussi affiché en JSON dans la console.
  assert.equal(sorties.length, 1);
  assert.deepEqual(JSON.parse(sorties[0]), JSON.parse(JSON.stringify(r)));
});

test('une règle vue dans plusieurs listes garde le statut de la dernière (violation prioritaire)', async () => {
  const w = fenetre('<p>x</p>');
  w.axe = fauxAxe({
    inapplicable: [{ id: 'color-contrast', tags: [] }],
    passes: [{ id: 'color-contrast', tags: [] }],
    incomplete: [],
    violations: [{ id: 'color-contrast', impact: 'serious', tags: ['wcag2aa'], nodes: [] }],
  });
  const r = await executer(SCRIPT, w);
  assert.equal(r.esm[0], 'N');
  assert.equal(r.esm.slice(1), '-'.repeat(50));
  assert.equal(r.wcag_respectees, 0);
});

test('axe absent : chargement depuis cdnjs simulé (onload), puis audit', async () => {
  const w = fenetre('<p>x</p>');
  const ajoutes = [];
  const ajouter = w.document.head.appendChild.bind(w.document.head);
  w.document.head.appendChild = el => {
    ajoutes.push(el);
    ajouter(el);
    // Le « CDN » répond : axe-core est disponible, puis l'événement load.
    queueMicrotask(() => { w.axe = fauxAxe({ inapplicable: [], passes: [], incomplete: [], violations: [] }); el.onload(); });
    return el;
  };
  const r = await executer(SCRIPT, w);
  assert.equal(ajoutes.length, 1);
  assert.equal(ajoutes[0].tagName, 'SCRIPT');
  assert.equal(ajoutes[0].src, 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js');
  assert.equal(r.esm, '-'.repeat(51));
  assert.deepEqual([...r.violations], []);
});

test('axe absent et chargement bloqué (CSP) : la promesse est rejetée avec un message clair', async () => {
  const w = fenetre('<p>x</p>');
  w.document.head.appendChild = el => { queueMicrotask(() => el.onerror(new w.Event('error'))); return el; };
  await assert.rejects(executer(SCRIPT, w), { message: 'Chargement d’axe-core bloqué par la page' });
  assert.equal(w.axe, undefined);
});
