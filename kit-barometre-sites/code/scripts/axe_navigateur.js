// Contrôle automatique d'accessibilité avec axe-core (Deque, open source, MPL-2.0). Version 2.
//
// À exécuter dans le navigateur, sur une page du site à auditer (console des outils de développement,
// ou par l'agent dans le navigateur intégré). Le script charge axe-core 4.10.2 depuis cdnjs et lance :
//   - les règles WCAG 2.1 A et AA (étiquettes wcag2a, wcag2aa, wcag21a, wcag21aa) ;
//   - les 51 règles de la checklist native « axe-core — WCAG 2.1 A/AA » d'eServices Manager
//     (correspondance dans referentiel/axe-esm.csv), dont certaines sont des bonnes pratiques hors WCAG.
//
// v2 : chaque règle reçoit un statut (C conforme, N non conforme, A non applicable, I à vérifier par un humain),
// pour reporter les résultats critère par critère dans eServices Manager.
//
// Pour passer tous les écrans d'un coup, préférer scripts/axe_playwright.mjs (mêmes règles, sans intervention).
// Pourquoi le navigateur : la page est rendue comme pour un vrai visiteur, et Shopify ne bloque pas un navigateur.
(async () => {
  const VERSION = '4.10.2';
  const ESM = ['color-contrast', 'color-contrast-enhanced', 'image-alt', 'image-redundant-alt', 'input-image-alt',
    'object-alt', 'area-alt', 'empty-heading', 'heading-order', 'page-has-heading-one', 'label', 'label-title-only',
    'form-field-multiple-labels', 'select-name', 'autocomplete-valid', 'button-name', 'link-name', 'frame-title',
    'document-title', 'html-has-lang', 'html-lang-valid', 'html-xml-lang-mismatch', 'valid-lang', 'meta-viewport',
    'aria-allowed-attr', 'aria-allowed-role', 'aria-required-attr', 'aria-required-children', 'aria-required-parent',
    'aria-roles', 'aria-valid-attr', 'aria-valid-attr-value', 'aria-hidden-body', 'aria-hidden-focus',
    'aria-input-field-name', 'aria-toggle-field-name', 'bypass', 'duplicate-id', 'duplicate-id-active',
    'duplicate-id-aria', 'tabindex', 'landmark-one-main', 'landmark-unique', 'region', 'list', 'listitem',
    'definition-list', 'dlitem', 'td-headers-attr', 'th-has-data-cells', 'table-fake-caption'];
  const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];
  const charger = (win) => win.axe ? Promise.resolve() : new Promise((ok, ko) => {
    const s = win.document.createElement('script');
    s.src = `https://cdnjs.cloudflare.com/ajax/libs/axe-core/${VERSION}/axe.min.js`;
    s.onload = ok;
    s.onerror = () => ko(new Error('Chargement d’axe-core bloqué par la page'));
    win.document.head.appendChild(s);
  });
  const auditer = async (win) => {
    await charger(win);
    // Règles WCAG stables (ni expérimentales ni dépréciées, comme en v1) + les 51 règles d'eServices Manager.
    const regles = win.axe.getRules().filter(r => ESM.includes(r.ruleId) ||
      (r.tags.some(t => WCAG.includes(t)) && !r.tags.includes('experimental') && !r.tags.includes('deprecated'))).map(r => r.ruleId);
    const r = await win.axe.run(win.document, { runOnly: { type: 'rule', values: regles } });
    const statut = {};
    for (const [liste, code] of [[r.inapplicable, 'A'], [r.passes, 'C'], [r.incomplete, 'I'], [r.violations, 'N']]) {
      for (const v of liste) statut[v.id] = code;
    }
    return {
      url: win.location.href,
      outil: `axe-core ${win.axe.version}`,
      esm: ESM.map(id => statut[id] || '-').join(''),
      wcag_respectees: r.passes.filter(v => v.tags.some(t => WCAG.includes(t))).length,
      wcag_a_verifier: r.incomplete.filter(v => v.tags.some(t => WCAG.includes(t))).map(v => v.id),
      violations: r.violations.map(v => ({
        regle: v.id,
        gravite: v.impact,
        criteres_wcag: v.tags.filter(t => /^wcag\d{3,}$/.test(t)),
        wcag: v.tags.some(t => WCAG.includes(t)),
        elements: v.nodes.length,
      })),
    };
  };
  const resultat = await auditer(window);
  console.log(JSON.stringify(resultat, null, 2));
  return resultat;
})();
