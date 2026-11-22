/*
 * LSMX — Teaser Black Friday : TOUT ce qui se modifie est ici.
 *
 * Rendu :   node teaser/render.mjs teaser     (version teaser)
 *           node teaser/render.mjs jourj      (version « C'EST PARTI »)
 * Sorties : teaser/out/<version>/lsmx-bf-<version>.mp4, ...-muet.mp4, cover.png
 */
(function () {
  const CONFIG = {
    version: "teaser",          // version rendue par défaut
    fps: 30,
    duree: 18,                  // secondes (15 à 20 max)

    couleurs: {
      fond: "#050505",
      rouge: "#E3001B",
      rougeClair: "#ff6b6b",
      blanc: "#ffffff",
    },

    // L'OFFRE — ne rien inventer d'autre
    offre: {
      remise: 20,                                 // %
      site: "lsmx-pieces.com",
      debut: "2026-11-27T00:00:00+01:00",
      fin: "2026-11-30T23:59:59+01:00",
      prixExemple: 189,                           // € — barré puis -20 % (calcul automatique)
    },

    // Rythme (secondes). Les cuts de pièces sont calés sur 140 BPM (60/140 = 0,4286 s).
    bpm: 140,
    timeline: {
      impactHook: 0.55,   // le disque touche l'écran : flash + « STOP. »
      ligne2Hook: 0.95,   // 2e phrase du hook
      tension: 1.5,       // défilement des pièces
      revelation: 5.0,    // étiquette de prix
      griffe: 5.65,       // le prix se fait griffer
      compteur: [5.85, 6.85], // 189 → 151,20
      badge: 7.1,         // explosion -20 %
      surTout: 7.9,
      urgence: 9.0,       // compte à rebours
      dates: 9.35,
      jours: 11.0,
      fin: 13.0,          // BLACK FRIDAY + CTA
      fige: 16.5,         // dernière image fixe jusqu'à la fin (= miniature)
    },

    versions: {
      teaser: {
        hook1: "STOP.",
        hook2: ["TES PIÈCES VONT", "COÛTER MOINS CHER."],
        tension: ["MOTEUR.", "FREINAGE.", "SUSPENSIONS.", "TRANSMISSION."],
        etiquette: "PRIX EXEMPLE",
        surTout: "SUR TOUT LE SITE",
        compteLabel: "LANCEMENT DANS",
        compteVers: "debut",                        // compte à rebours jusqu'au début de l'offre
        publication: "2026-11-23T18:00:00+01:00",   // ⚠ heure de mise en ligne prévue : le compteur part de là
        dates: "DU 27 AU 30 NOVEMBRE",
        jours: "4 JOURS SEULEMENT",
        titre: ["BLACK", "FRIDAY"],
        sousTitre: "LSMX — PIÈCES CROSS & ENDURO",
        cta: "RENDEZ-VOUS LE 27 NOVEMBRE",
        derniere: "PRÉPARE TA LISTE.",
      },
      jourj: {
        hook1: "C'EST PARTI.",
        hook2: ["-20 % SUR TOUT", "JUSQU'À LUNDI."],
        tension: ["MOTEUR.", "FREINAGE.", "SUSPENSIONS.", "TRANSMISSION."],
        etiquette: "PRIX EXEMPLE",
        surTout: "SUR TOUT LE SITE",
        compteLabel: "FIN DANS",
        compteVers: "fin",
        publication: "2026-11-27T08:00:00+01:00",
        dates: "DU 27 AU 30 NOVEMBRE",
        jours: "JUSQU'À LUNDI 30",
        titre: ["BLACK", "FRIDAY"],
        sousTitre: "LSMX — PIÈCES CROSS & ENDURO",
        cta: "-20 % JUSQU'AU 30 NOVEMBRE",
        derniere: "FONCE SUR LE SITE.",
      },
    },
  };
  if (typeof module !== "undefined") module.exports = CONFIG;
  if (typeof window !== "undefined") window.CONFIG = CONFIG;
})();
