// Tests de scripts/parc.mjs : lecture du parc (fichier donné, variable BAROMETRE_PARC, fichier du kit, fichier absent).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { FICHIER, RESPONSABLE_DEFAUT, charger, sites, parNom, responsable } from '../../scripts/parc.mjs';

const tmp = mkdtempSync(join(tmpdir(), 'parc-'));
const ecrire = (nom, d) => { const f = join(tmp, nom); writeFileSync(f, JSON.stringify(d)); return f; };

test('parc : fichier donné, sites, noms et responsable', () => {
  const f = ecrire('parc.json', { responsable: 'Mattea', sites: [{ nom: 'Boutique D', prefixe_langue: '/fr' }, { nom: 'Boutique A' }] });
  assert.equal(responsable(f), 'Mattea');
  assert.deepEqual(sites(f).map(s => s.nom), ['Boutique D', 'Boutique A']);
  assert.equal(parNom(f)['Boutique D'].prefixe_langue, '/fr');
});

test('parc : valeurs par défaut (responsable vide, sans sites, fichier absent)', () => {
  const f = ecrire('vide.json', { responsable: '' });
  assert.equal(responsable(f), RESPONSABLE_DEFAUT);
  assert.deepEqual(sites(f), []);
  assert.deepEqual(charger(join(tmp, 'absent.json')), { responsable: RESPONSABLE_DEFAUT, sites: [] });
});

test('parc : BAROMETRE_PARC, sinon referentiel/parc.json du kit', () => {
  const avant = process.env.BAROMETRE_PARC;
  process.env.BAROMETRE_PARC = ecrire('env.json', { responsable: 'Alex', sites: [{ nom: 'X' }] });
  assert.equal(responsable(), 'Alex');
  assert.deepEqual(Object.keys(parNom()), ['X']);
  delete process.env.BAROMETRE_PARC;
  assert.ok(FICHIER.endsWith(join('referentiel', 'parc.json')));
  assert.ok(Array.isArray(charger().sites));
  if (avant !== undefined) process.env.BAROMETRE_PARC = avant;
  rmSync(tmp, { recursive: true, force: true });
});
