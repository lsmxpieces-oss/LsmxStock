/*
 * Pièces moto dessinées en code (style néon / blueprint).
 * Chaque pièce = liste de primitives { c:[x,y,r] } (cercle) ou { l:[[x,y]...], z:true } (polyligne, z = fermée),
 * dans un repère d'environ ±350 px. drawPart() gère le tracé progressif (0→1) puis le remplissage.
 */
(function () {
  const TAU = Math.PI * 2;
  const rot = (pts, a) => pts.map(([x, y]) => [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)]);
  const circlePts = (r, n = 96, f = null) => {
    const p = [];
    for (let i = 0; i < n; i++) { const t = (i / n) * TAU; const rr = f ? f(t) : r; p.push([rr * Math.cos(t), rr * Math.sin(t)]); }
    return p;
  };
  const polar = (r, a, cx = 0, cy = 0) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];

  function disque() {
    const P = [];
    P.push({ l: circlePts(300, 288, (t) => 300 + 9 * Math.sin(t * 14)), z: true }); // bord ondulé
    P.push({ c: [0, 0, 178] });                                                      // limite piste / support
    for (let k = 0; k < 6; k++) {                                                    // bras du support (lumières)
      const a = (k / 6) * TAU + TAU / 12;
      const slot = [polar(95, a - 0.32), polar(160, a - 0.2), polar(160, a + 0.2), polar(95, a + 0.32)];
      P.push({ l: slot, z: true });
    }
    for (let k = 0; k < 6; k++) P.push({ c: [...polar(80, (k / 6) * TAU), 11] });    // vis
    P.push({ c: [0, 0, 52] });                                                       // alésage
    [205, 235, 265].forEach((r, ring) => {                                           // perçages
      for (let k = 0; k < 20; k++) P.push({ c: [...polar(r, (k / 20) * TAU + ring * 0.105), 8.5] });
    });
    return { prims: P, round: true };
  }

  function couronne(N = 48, rIn = 272, rOut = 300) {
    const P = [], teeth = [], step = TAU / N;
    for (let i = 0; i < N; i++) {
      const a = i * step;
      teeth.push(polar(rIn, a), polar(rOut, a + 0.22 * step), polar(rOut, a + 0.5 * step), polar(rIn, a + 0.72 * step));
    }
    P.push({ l: teeth, z: true });
    P.push({ c: [0, 0, 228] });
    for (let k = 0; k < 6; k++) {                                                    // évidements
      const a = (k / 6) * TAU;
      P.push({ l: [polar(125, a - 0.33), polar(205, a - 0.4), polar(212, a), polar(205, a + 0.4), polar(125, a + 0.33)], z: true });
    }
    P.push({ c: [0, 0, 84] });
    for (let k = 0; k < 6; k++) P.push({ c: [...polar(103, (k / 6) * TAU + TAU / 12), 9] });
    return { prims: P, round: true };
  }

  function pignon() {
    const N = 13, P = [], teeth = [], step = TAU / N;
    for (let i = 0; i < N; i++) {
      const a = i * step;
      teeth.push(polar(205, a), polar(270, a + 0.2 * step), polar(270, a + 0.48 * step), polar(205, a + 0.7 * step));
    }
    P.push({ l: teeth, z: true });
    P.push({ c: [0, 0, 165] });
    const spl = [];
    for (let i = 0; i < 20; i++) { const a = (i / 20) * TAU; spl.push(polar(72, a), polar(72, a + 0.12), polar(60, a + 0.16), polar(60, a + 0.28)); }
    P.push({ l: spl, z: true });
    return { prims: P, round: true };
  }

  function piston() {
    const P = [], body = [[-140, -80]];
    for (let x = -140; x <= 140; x += 10) body.push([x, -285 - 28 * (1 - (x / 140) ** 2)]);
    body.push([140, -80]);
    P.push({ l: body, z: true });
    [-262, -240, -218].forEach((y) => P.push({ l: [[-140, y], [140, y]] }));
    P.push({ c: [0, -160, 54] }); P.push({ c: [0, -160, 30] });
    P.push({ l: [[-30, -112], [30, -112], [58, 95], [-58, 95]], z: true });       // corps de bielle
    P.push({ l: [[-12, -100], [12, -100], [24, 80], [-24, 80]], z: true });       // nervure (section en I)
    P.push({ c: [0, 185, 104] }); P.push({ c: [0, 185, 64] });                    // tête de bielle
    return { prims: P.map((p) => (p.l ? { ...p, l: p.l.map(([x, y]) => [x, y + 10]) } : { c: [p.c[0], p.c[1] + 10, p.c[2]] })) };
  }

  function amortisseur() {
    const P = [];
    P.push({ c: [0, -335, 36] }); P.push({ c: [0, -335, 15] });
    P.push({ l: [[-62, -300], [62, -300], [62, -40], [-62, -40]], z: true });     // corps
    P.push({ l: [[62, -280], [130, -280], [130, -150], [62, -150]], z: true });   // réservoir
    P.push({ c: [130, -215, 26] });
    [-270, -255].forEach((y) => P.push({ l: [[-62, y], [62, y]] }));
    P.push({ l: [[-112, -255], [112, -255]] }); P.push({ l: [[-112, 230], [112, 230]] }); // coupelles
    const spring = [];
    for (let i = 0; i <= 400; i++) { const s = i / 400; spring.push([102 * Math.sin(s * TAU * 8.5), -245 + s * 465]); }
    P.push({ l: spring });                                                        // ressort
    P.push({ l: [[-18, -40], [18, -40], [18, 250], [-18, 250]], z: true });       // tige
    P.push({ l: [[-44, 250], [44, 250], [44, 300], [-44, 300]], z: true });       // chape
    P.push({ c: [0, 330, 34] }); P.push({ c: [0, 330, 14] });
    return { prims: P };
  }

  function jante() {
    const P = [], knobs = [], N = 44;
    for (let i = 0; i < N; i++) {
      const a = (i / N) * TAU, s = TAU / N;
      knobs.push(polar(332, a), polar(352, a + 0.12 * s), polar(352, a + 0.55 * s), polar(332, a + 0.67 * s));
    }
    P.push({ l: knobs, z: true });                                                // pneu à crampons
    P.push({ c: [0, 0, 300] }); P.push({ c: [0, 0, 276] });                       // jante
    P.push({ c: [0, 0, 58] }); P.push({ c: [0, 0, 26] });                         // moyeu
    for (let k = 0; k < 36; k++) {                                                // rayons croisés
      const a = (k / 36) * TAU, off = k % 2 ? 0.42 : -0.42;
      P.push({ l: [polar(50, a), polar(274, a + off)] });
    }
    return { prims: P, round: true };
  }

  function silencieux() {
    const P = [], cap = [];
    for (let i = 0; i <= 20; i++) { const a = -Math.PI / 2 + (i / 20) * Math.PI; cap.push([-210 + 75 * Math.cos(a + Math.PI), 75 * Math.sin(a + Math.PI)]); }
    const body = [[-210, -75], [240, -75], [300, -42], [300, 42], [240, 75], [-210, 75], ...cap.slice(1, -1)];
    P.push({ l: body, z: true });
    P.push({ l: [[240, -75], [240, 75]] });
    P.push({ c: [318, 0, 24] }); P.push({ c: [318, 0, 13] });                     // sortie
    P.push({ l: [[-150, -75], [-150, 75]] }); P.push({ l: [[-130, -75], [-130, 75]] }); // collier
    for (let x = -90; x <= 210; x += 60) { P.push({ c: [x, -58, 6] }); P.push({ c: [x, 58, 6] }); } // rivets
    P.push({ l: [[-285, -30], [-330, -30], [-372, -2], [-396, 50]] });            // coude d'entrée
    P.push({ l: [[-285, 30], [-318, 30], [-345, 52], [-360, 86]] });
    return { prims: P.map((p) => (p.l ? { ...p, l: rot(p.l, -0.32) } : { c: [...rot([[p.c[0], p.c[1]]], -0.32)[0], p.c[2]] })) };
  }

  function levier() {
    const P = [];
    P.push({ l: [[-330, -70], [-245, -70], [-245, 70], [-330, 70]], z: true });   // collier de guidon
    P.push({ c: [-287, 0, 38] });
    P.push({ c: [-215, 42, 34] }); P.push({ c: [-215, 42, 12] });                 // pivot
    const top = [[-200, 12], [-60, 26], [90, 46], [210, 74], [292, 100]];
    const bot = [[300, 132], [205, 110], [85, 84], [-60, 66], [-190, 74]];
    P.push({ l: [...top, ...bot], z: true });                                     // levier
    P.push({ c: [306, 118, 24] });                                                // boule de bout
    P.push({ l: [[-40, 40], [60, 52], [60, 66], [-40, 56]], z: true });           // allègements
    P.push({ l: [[100, 62], [190, 84], [186, 96], [98, 76]], z: true });
    P.push({ l: [[-245, -30], [-160, -30], [-160, -10]] });                       // câble / réglage
    P.push({ c: [-160, -46, 16] });
    return { prims: P.map((p) => (p.l ? { ...p, l: rot(p.l, -0.12) } : { c: [...rot([[p.c[0], p.c[1]]], -0.12)[0], p.c[2]] })) };
  }

  const PARTS = {
    disque: { ...disque(), nom: "DISQUE DE FREIN" },
    couronne: { ...couronne(), nom: "COURONNE" },
    pignon: { ...pignon(), nom: "PIGNON DE SORTIE" },
    piston: { ...piston(), nom: "PISTON + BIELLE" },
    amortisseur: { ...amortisseur(), nom: "AMORTISSEUR" },
    jante: { ...jante(), nom: "JANTE À RAYONS" },
    silencieux: { ...silencieux(), nom: "SILENCIEUX" },
    levier: { ...levier(), nom: "LEVIER D'EMBRAYAGE" },
  };

  // longueur de chaque primitive (pour le tracé progressif)
  for (const k in PARTS) for (const p of PARTS[k].prims) {
    if (p.c) p.len = TAU * p.c[2];
    else { let L = 0; const pts = p.z ? [...p.l, p.l[0]] : p.l; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); p.len = L; }
  }

  function tracePrim(ctx, p, prog) {
    if (prog <= 0) return;
    if (p.c) { ctx.moveTo(p.c[0] + p.c[2] * Math.cos(-Math.PI / 2), p.c[1] - p.c[2]); ctx.arc(p.c[0], p.c[1], p.c[2], -Math.PI / 2, -Math.PI / 2 + TAU * prog); return; }
    const pts = p.z ? [...p.l, p.l[0]] : p.l, target = p.len * prog;
    ctx.moveTo(pts[0][0], pts[0][1]);
    let acc = 0;
    for (let i = 1; i < pts.length; i++) {
      const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      if (acc + seg >= target) { const r = (target - acc) / seg; ctx.lineTo(pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * r, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * r); return; }
      ctx.lineTo(pts[i][0], pts[i][1]); acc += seg;
    }
  }

  /**
   * draw : 0→1 tracé du contour ; fill : 0→1 passage filaire → plein ; glow : intensité néon
   */
  function drawPart(ctx, name, { x, y, s = 1, a = 0, draw = 1, fill = 0, glow = 1, alpha = 1, col }) {
    const part = PARTS[name];
    ctx.save();
    ctx.globalAlpha *= alpha;
    ctx.translate(x, y); ctx.rotate(a); ctx.scale(s, s);
    // remplissage (pair-impair : les trous restent vides)
    if (fill > 0) {
      ctx.beginPath();
      for (const p of part.prims) if (p.c || p.z) tracePrim(ctx, p, 1);
      const g = ctx.createRadialGradient(0, 0, 10, 0, 0, 380);
      g.addColorStop(0, col.rougeClair); g.addColorStop(1, col.rouge);
      ctx.fillStyle = g; ctx.globalAlpha = alpha * 0.85 * fill;
      ctx.fill("evenodd");
      ctx.globalAlpha = alpha;
    }
    ctx.lineJoin = "round"; ctx.lineCap = "round";
    ctx.beginPath();
    for (const p of part.prims) tracePrim(ctx, p, draw);
    ctx.shadowColor = col.rouge; ctx.shadowBlur = 34 * glow;
    ctx.strokeStyle = col.rouge; ctx.lineWidth = 11 / s; ctx.stroke();
    ctx.shadowBlur = 12 * glow;
    ctx.strokeStyle = fill > 0.5 ? "#fff" : "#ffd0d0"; ctx.lineWidth = 3.2 / s; ctx.stroke();
    ctx.restore();
  }

  window.PARTS = PARTS;
  window.drawPart = drawPart;
})();
