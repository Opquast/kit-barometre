// Configuration ESLint du kit (format « flat config »).
// Sans import de paquet, pour fonctionner dans l'environnement isolé de pre-commit.
// Les scripts .mjs tournent dans Node et passent du code au navigateur (page.evaluate) ;
// les scripts .js s'exécutent dans la console du navigateur.

const commun = [
  'console', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'URL', 'URLSearchParams',
  'fetch', 'AbortController', 'AbortSignal', 'TextEncoder', 'TextDecoder', 'Blob', 'Response', 'Headers',
  'structuredClone', 'queueMicrotask', 'performance', 'atob', 'btoa', 'crypto',
];
const navigateur = [
  'window', 'document', 'navigator', 'location', 'getComputedStyle', 'HTMLElement', 'Element', 'Node',
  'NodeFilter', 'MutationObserver', 'DOMParser', 'XMLHttpRequest', 'CSS', 'innerWidth', 'innerHeight',
  'localStorage', 'sessionStorage', 'axe', 'matchMedia', 'requestAnimationFrame', 'Image', 'Event',
  'CustomEvent', 'XMLSerializer', 'Shopify', 'scrollTo', 'scrollX', 'scrollY', 'devicePixelRatio', 'screen', 'history', 'FormData',
];
const node = ['process', 'Buffer', 'global', 'globalThis', '__dirname', '__filename', 'module', 'require'];
const globaux = (noms) => Object.fromEntries(noms.map((n) => [n, 'readonly']));

const regles = {
  'no-undef': 'error',
  'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none' }],
  'no-redeclare': 'error',
  'no-dupe-keys': 'error',
  'no-duplicate-case': 'error',
  'no-unreachable': 'error',
  'no-const-assign': 'error',
  'no-func-assign': 'error',
  'no-self-assign': 'error',
  'no-unsafe-finally': 'error',
  'no-unsafe-negation': 'error',
  'use-isnan': 'error',
  'valid-typeof': 'error',
  'no-debugger': 'error',
};

export default [
  { ignores: ['node_modules/**', 'resultats/**', 'coverage/**'] },
  {
    files: ['**/*.mjs'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globaux([...commun, ...navigateur, ...node]),
    },
    rules: regles,
  },
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'script',
      globals: globaux([...commun, ...navigateur]),
    },
    rules: regles,
  },
];
