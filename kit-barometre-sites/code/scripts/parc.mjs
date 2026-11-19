// Lecture du parc mesuré (referentiel/parc.json) pour les scripts Node : même contenu que scripts/parc.py.
// Le chemin peut être remplacé par la variable d'environnement BAROMETRE_PARC (autre parc, ou parc de test).
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export const FICHIER = fileURLToPath(new URL('../referentiel/parc.json', import.meta.url));
export const RESPONSABLE_DEFAUT = 'la personne responsable du baromètre';

export function charger(chemin = process.env.BAROMETRE_PARC || FICHIER) {
  return existsSync(chemin) ? JSON.parse(readFileSync(chemin, 'utf8')) : { responsable: RESPONSABLE_DEFAUT, sites: [] };
}

export function sites(chemin) {
  return charger(chemin).sites || [];
}

export function parNom(chemin) {
  return Object.fromEntries(sites(chemin).map(s => [s.nom, s]));
}

export function responsable(chemin) {
  return charger(chemin).responsable || RESPONSABLE_DEFAUT;
}
