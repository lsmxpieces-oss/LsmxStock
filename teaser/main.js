/*
 * Moteur d'animation image par image (déterministe) : window.renderFrame(n) dessine l'image n.
 * Zones de sécurité Reels/TikTok : texte entre y=250 et y=1520, x < 960. Centre utile : x=510.
 */
(function () {
  const C = window.CONFIG;
  const VNAME = new URLSearchParams(location.search).get("v") || C.version;
  const V = C.versions[VNAME];
  const T = C.timeline, COL = C.couleurs, FPS = C.fps, DUR = C.duree;
  const W = 1080, H = 1920, CX = 510, CY = 880;
  const BEAT = 60 / C.bpm;
  const cv = document.getElementById("c");
  const ctx = cv.getContext("2d");

  // ---------------------------------------------------------------- outils
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const prog = (t, a, d) => clamp((t - a) / d);
  const lerp = (a, b, k) => a + (b - a) * k;
  const eOutExpo = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
  const eInExpo = (x) => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10));
  const eOutBack = (x) => { const c1 = 2.1, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const eOutCubic = (x) => 1 - Math.pow(1 - x, 3);
  function rng(seed) { let s = (seed * 2654435761) >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
  const euro = (v) => v.toFixed(2).replace(".", ",") + " €";
  const prixFinal = Math.round(C.offre.prixExemple * (1 - C.offre.remise / 100) * 100) / 100;

  // bruit / grain précalculé
  const grains = [];
  for (let g = 0; g < 6; g++) {
    const c = document.createElement("canvas"); c.width = 540; c.height = 960;
    const x = c.getContext("2d"), im = x.createImageData(540, 960), r = rng(g + 7);
    for (let i = 0; i < im.data.length; i += 4) { const v = r() * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
    x.putImageData(im, 0, 0); grains.push(c);
  }

  // ---------------------------------------------------------------- texte
  function setFont(size, font, weight) { ctx.font = `${weight || ""} ${size}px "${font}"`; }
  function txt(s, x, y, size, o = {}) {
    const font = o.font || "Anton", maxW = o.maxW || 860, weight = o.weight || (font === "Inter" ? 900 : 400);
    setFont(size, font, weight);
    if (o.spacing) ctx.letterSpacing = o.spacing + "px"; else ctx.letterSpacing = "0px";
    const w = ctx.measureText(s).width;
    if (w > maxW) { size *= maxW / w; setFont(size, font, weight); }
    ctx.textAlign = o.align || "center"; ctx.textBaseline = "middle";
    if (o.stroke) { ctx.lineJoin = "round"; ctx.lineWidth = o.stroke; ctx.strokeStyle = "#000"; ctx.strokeText(s, x, y); }
    if (o.glow) { ctx.shadowColor = o.glowCol || COL.rouge; ctx.shadowBlur = o.glow; }
    ctx.fillStyle = o.color || COL.blanc; ctx.fillText(s, x, y);
    if (o.glow) { ctx.shadowBlur = o.glow * 0.4; ctx.fillText(s, x, y); }
    ctx.shadowBlur = 0; ctx.letterSpacing = "0px";
    return size;
  }
  // texte qui « claque » : grossi → taille normale avec rebond
  function slam(t, t0, x, y, fn, from = 2.1, dur = 0.22) {
    if (t < t0) return;
    const k = prog(t, t0, dur), s = lerp(from, 1, eOutBack(k));
    ctx.save(); ctx.globalAlpha *= prog(t, t0, 0.05);
    ctx.translate(x, y); ctx.scale(s, s); fn(); ctx.restore();
  }

  // ---------------------------------------------------------------- décor
  function background(t, f) {
    ctx.fillStyle = COL.fond; ctx.fillRect(-200, -200, W + 400, H + 400);
    // rayures diagonales animées
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(-0.6);
    ctx.fillStyle = COL.rouge; ctx.globalAlpha = 0.055;
    const off = (t * 140) % 120;
    for (let x = -1800; x < 1800; x += 120) ctx.fillRect(x + off, -1600, 42, 3200);
    ctx.restore();
    // halo radial pulsé sur le tempo
    const pulse = t > T.tension ? Math.exp(-(((t - T.tension) % BEAT) * 7)) : 0;
    const g = ctx.createRadialGradient(CX, CY, 0, CX, CY, 950);
    g.addColorStop(0, `rgba(227,0,27,${0.34 + 0.16 * pulse})`); g.addColorStop(0.55, "rgba(227,0,27,0.08)"); g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g; ctx.fillRect(-200, -200, W + 400, H + 400);
  }
  function grid(alpha) {
    ctx.save(); ctx.strokeStyle = COL.rougeClair; ctx.globalAlpha = alpha; ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x <= W; x += 60) { ctx.moveTo(x, 0); ctx.lineTo(x, H); }
    for (let y = 0; y <= H; y += 60) { ctx.moveTo(0, y); ctx.lineTo(W, y); }
    ctx.stroke(); ctx.restore();
  }
  // bande « chantier » rouge/noir
  function tape(y, t, ang, alpha = 1) {
    ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(W / 2, y); ctx.rotate(ang);
    ctx.fillStyle = COL.rouge; ctx.fillRect(-900, -34, 1800, 68);
    ctx.beginPath(); ctx.rect(-900, -34, 1800, 68); ctx.clip();
    ctx.fillStyle = "#000"; const off = (t * 220) % 90;
    for (let x = -1000; x < 1000; x += 90) { ctx.beginPath(); ctx.moveTo(x + off, -34); ctx.lineTo(x + off + 40, -34); ctx.lineTo(x + off + 8, 34); ctx.lineTo(x + off - 32, 34); ctx.fill(); }
    ctx.restore();
  }
  function particles(t, t0, seed, n, cx, cy, power) {
    if (t < t0 || t > t0 + 1.4) return;
    const r = rng(seed), dt = t - t0;
    ctx.save();
    for (let i = 0; i < n; i++) {
      const a = r() * Math.PI * 2, v = (300 + r() * 1400) * power, life = 0.5 + r() * 0.8, sz = 3 + r() * 9;
      if (dt > life) continue;
      const k = dt / life, d = v * (1 - Math.pow(1 - Math.min(1, dt / life), 2)) * life * 0.9;
      const x = cx + Math.cos(a) * d, y = cy + Math.sin(a) * d + 300 * dt * dt;
      ctx.globalAlpha = (1 - k) * 0.95;
      ctx.fillStyle = r() < 0.35 ? "#fff" : r() < 0.6 ? COL.rougeClair : COL.rouge;
      ctx.shadowColor = COL.rouge; ctx.shadowBlur = 14;
      ctx.save(); ctx.translate(x, y); ctx.rotate(a); ctx.fillRect(-sz * 2, -sz / 3, sz * 4, sz / 1.5); ctx.restore();
    }
    ctx.restore();
  }
  function shockwave(t, t0, cx, cy) {
    if (t < t0 || t > t0 + 0.6) return;
    const k = prog(t, t0, 0.6);
    ctx.save(); ctx.globalAlpha = (1 - k) * 0.9; ctx.strokeStyle = COL.rougeClair;
    ctx.lineWidth = 40 * (1 - k) + 2; ctx.shadowColor = COL.rouge; ctx.shadowBlur = 40;
    ctx.beginPath(); ctx.arc(cx, cy, 80 + eOutExpo(k) * 900, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  }
  function flash(t, t0, dur = 0.18, max = 1) {
    if (t < t0 || t > t0 + dur) return;
    ctx.save(); ctx.globalAlpha = max * (1 - prog(t, t0, dur)); ctx.fillStyle = "#fff"; ctx.fillRect(-200, -200, W + 400, H + 400); ctx.restore();
  }

  // ---------------------------------------------------------------- scènes
  function sceneHook(t) {
    const imp = T.impactHook;
    // disque qui fonce vers la caméra en tournant (avec traînée = flou de mouvement)
    if (t < imp) {
      const k = prog(t, 0, imp);
      for (let i = 4; i >= 0; i--) {
        const kk = clamp(k - i * 0.035), s = 0.22 + eInExpo(kk) * 2.9;
        drawPart(ctx, "disque", { x: CX, y: CY - 40, s, a: t * 14 - i * 0.12, draw: 1, fill: 0.15, alpha: i ? 0.18 : 1, col: COL });
      }
    } else {
      const k = prog(t, imp, 0.5);
      drawPart(ctx, "disque", { x: CX, y: CY - 40, s: lerp(2.6, 1.7, eOutExpo(k)), a: t * 3, draw: 1, fill: 0.25, alpha: lerp(0.9, 0.22, eOutExpo(k)), glow: 0.6, col: COL });
    }
    flash(t, imp, 0.2);
    slam(t, imp, CX, CY - 250, () => txt(V.hook1, 0, 0, 330, { glow: 50, stroke: 0 }), 2.6, 0.2);
    slam(t, T.ligne2Hook, CX, CY + 40, () => txt(V.hook2[0], 0, 0, 120, { stroke: 10 }));
    slam(t, T.ligne2Hook + 0.14, CX, CY + 175, () => txt(V.hook2[1], 0, 0, 120, { color: COL.rouge, glow: 30, stroke: 10 }));
  }

  const SEQ = [["piston", "silencieux"], ["disque", "levier"], ["amortisseur", "jante"], ["couronne", "pignon"]];
  function sceneTension(t) {
    grid(0.07);
    const lt = t - T.tension, idx = Math.min(7, Math.floor(lt / BEAT)), pt = lt - idx * BEAT;
    const name = SEQ[Math.floor(idx / 2)][idx % 2], part = PARTS[name];
    const ent = eOutExpo(prog(pt, 0, 0.12));
    const s = lerp(1.18, 0.92, ent) * ({ pignon: 1.05, silencieux: 1.22, levier: 1.25 }[name] || 1);
    ctx.save(); if (pt < 0.07) ctx.filter = `blur(${(1 - pt / 0.07) * 8}px)`;
    drawPart(ctx, name, {
      x: CX + (1 - ent) * (idx % 2 ? -90 : 90), y: CY - 70, s,
      a: part.round ? pt * 2.4 + idx : (1 - ent) * 0.15,
      draw: eOutCubic(prog(pt, 0, 0.24)), fill: prog(pt, 0.2, 0.16), col: COL,
    });
    ctx.restore();
    txt(part.nom, CX, CY - 470, 34, { font: "Inter", color: COL.rougeClair, spacing: 6 });
    txt(`${String(idx + 1).padStart(2, "0")} / 08`, CX, CY - 420, 26, { font: "Inter", weight: 800, color: "#bbb", spacing: 4 });
    const grp = Math.floor(idx / 2), g0 = T.tension + grp * 2 * BEAT;
    slam(t, g0, CX, CY + 440, () => txt(V.tension[grp], 0, 0, 150, { stroke: 12, glow: 14 }), 1.6, 0.16);
    flash(t, T.tension + idx * BEAT, 0.07, 0.35);
  }

  function priceTag(x, y, scale, a, dim) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(a); ctx.scale(scale, scale);
    ctx.beginPath();
    ctx.moveTo(-330, 0); ctx.lineTo(-240, -130); ctx.lineTo(330, -130); ctx.lineTo(330, 130); ctx.lineTo(-240, 130); ctx.closePath();
    ctx.moveTo(-232, 0); ctx.arc(-252, 0, 20, 0, Math.PI * 2);
    ctx.fillStyle = dim ? "#cfcfcf" : "#fff"; ctx.shadowColor = "rgba(0,0,0,.6)"; ctx.shadowBlur = 30; ctx.fill("evenodd"); ctx.shadowBlur = 0;
    ctx.lineWidth = 6; ctx.strokeStyle = COL.rouge; ctx.stroke();
    txt(euro(C.offre.prixExemple).replace(",00", ""), 40, 6, 190, { color: "#0a0a0a", maxW: 520 });
    ctx.restore();
  }
  function sceneReveal(t) {
    const R = T.revelation, out = 1 - prog(t, T.badge, 0.1);
    if (out > 0) {
      ctx.save(); ctx.globalAlpha = out;
      const k = eOutBack(prog(t, R, 0.35));
      const tx = lerp(W + 400, CX, k), ty = CY - 260, dim = t > T.griffe + 0.1;
      txt(V.etiquette, CX, CY - 460, 34, { font: "Inter", color: COL.rougeClair, spacing: 6 });
      priceTag(tx, ty, 1, -0.1, dim);
      // griffe : 3 coups rouges
      if (t >= T.griffe) {
        for (let i = 0; i < 3; i++) {
          const kk = eOutExpo(prog(t, T.griffe + i * 0.035, 0.12));
          const x0 = CX - 300 + i * 70, y0 = ty - 170, x1 = x0 + 330 * kk, y1 = y0 + 340 * kk;
          ctx.save(); ctx.strokeStyle = COL.rouge; ctx.lineCap = "round"; ctx.shadowColor = COL.rouge; ctx.shadowBlur = 30;
          ctx.lineWidth = 26 - i * 4; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
          ctx.lineWidth = 5; ctx.strokeStyle = "#fff"; ctx.stroke(); ctx.restore();
        }
      }
      // compteur 189 → 151,20
      const [c0, c1] = T.compteur;
      if (t >= c0 - 0.1) {
        const k2 = eOutExpo(prog(t, c0, c1 - c0));
        const v = lerp(C.offre.prixExemple, prixFinal, k2);
        const done = t >= c1;
        const s = done ? 1 + 0.12 * (1 - eOutBack(prog(t, c1, 0.25))) : 1;
        ctx.save(); ctx.translate(CX, CY + 60); ctx.scale(s, s);
        txt(euro(v), 0, 0, 230, { color: done ? COL.blanc : COL.rougeClair, glow: done ? 50 : 20, stroke: 10 });
        ctx.restore();
      }
      ctx.restore();
    }
    // explosion -20 %
    shockwave(t, T.badge, CX, CY - 120);
    particles(t, T.badge, 11, 160, CX, CY - 120, 1);
    flash(t, T.badge, 0.16, 0.9);
    if (t >= T.badge) {
      const k = eOutBack(prog(t, T.badge, 0.3)), pulse = 1 + 0.035 * Math.sin((t - T.badge) * Math.PI * 2 / BEAT);
      ctx.save(); ctx.translate(CX, CY - 140); ctx.rotate(-4 * Math.PI / 180); ctx.scale(lerp(3, 1, k) * pulse, lerp(3, 1, k) * pulse);
      ctx.shadowColor = COL.rouge; ctx.shadowBlur = 70; ctx.fillStyle = COL.rouge;
      ctx.beginPath(); ctx.roundRect(-380, -190, 760, 380, 34); ctx.fill(); ctx.shadowBlur = 0;
      ctx.lineWidth = 8; ctx.strokeStyle = "#fff"; ctx.stroke();
      txt(`-${C.offre.remise} %`, 0, 8, 300, { maxW: 680 });
      ctx.restore();
    }
    slam(t, T.surTout, CX, CY + 230, () => txt(V.surTout, 0, 0, 130, { stroke: 10, glow: 12 }), 1.8, 0.2);
  }

  function sceneUrgence(t) {
    const U = T.urgence;
    tape(300, t, -0.05, prog(t, U, 0.15)); tape(1470, t, 0.04, prog(t, U, 0.15));
    txt(V.compteLabel, CX, CY - 360, 46, { font: "Inter", spacing: 10, color: COL.rougeClair });
    const target = new Date(C.offre[V.compteVers]).getTime(), from = new Date(V.publication).getTime();
    const elapsed = Math.floor(t - U), frac = (t - U) - elapsed;
    let rem = Math.max(0, Math.round((target - from) / 1000) - elapsed);
    const prev = rem + 1;
    const split = (r) => [Math.floor(r / 86400), Math.floor(r / 3600) % 24, Math.floor(r / 60) % 60, r % 60];
    const cur = split(rem), old = split(prev);
    const labels = ["JOURS", "HEURES", "MIN", "SEC"], bw = 192, gap = 22, x0 = CX - (4 * bw + 3 * gap) / 2;
    for (let i = 0; i < 4; i++) {
      const k = eOutBack(prog(t, U + 0.05 + i * 0.06, 0.25));
      if (k <= 0) continue;
      const bx = x0 + i * (bw + gap), by = CY - 300;
      ctx.save(); ctx.translate(bx + bw / 2, by + 115); ctx.scale(k, k); ctx.translate(-(bx + bw / 2), -(by + 115));
      ctx.fillStyle = "#111"; ctx.strokeStyle = COL.rouge; ctx.lineWidth = 5; ctx.shadowColor = COL.rouge; ctx.shadowBlur = 24;
      ctx.beginPath(); ctx.roundRect(bx, by, bw, 230, 18); ctx.fill(); ctx.stroke(); ctx.shadowBlur = 0;
      ctx.save(); ctx.beginPath(); ctx.rect(bx, by + 8, bw, 168); ctx.clip();
      const changed = cur[i] !== old[i] && elapsed > 0, fl = changed ? eOutExpo(clamp(frac / 0.18)) : 1;
      const s = (v) => String(v).padStart(2, "0");
      if (changed && fl < 1) txt(s(old[i]), bx + bw / 2, by + 95 + fl * 150, 130, { maxW: 170 });
      txt(s(cur[i]), bx + bw / 2, by + 95 - (1 - fl) * 150, 130, { maxW: 170, color: i === 3 ? COL.rougeClair : COL.blanc });
      ctx.restore();
      txt(labels[i], bx + bw / 2, by + 200, 28, { font: "Inter", weight: 800, spacing: 3, color: "#bbb", maxW: 180 });
      ctx.restore();
    }
    slam(t, T.dates, CX, CY + 110, () => txt(V.dates, 0, 0, 112, { stroke: 10 }), 1.7, 0.2);
    slam(t, T.jours, CX, CY + 310, () => {
      const p = 1 + 0.04 * Math.sin((t - T.jours) * Math.PI * 2 / BEAT);
      ctx.scale(p, p); ctx.rotate(-3 * Math.PI / 180);
      ctx.fillStyle = COL.rouge; ctx.shadowColor = COL.rouge; ctx.shadowBlur = 45;
      ctx.beginPath(); ctx.roundRect(-430, -95, 860, 190, 22); ctx.fill(); ctx.shadowBlur = 0;
      txt(V.jours, 0, 4, 140, { maxW: 780 });
    }, 2.2, 0.22);
  }

  function sceneFin(t) {
    const F = T.fin;
    drawPart(ctx, "couronne", { x: CX, y: CY - 160, s: 1.55, a: (t - F) * 0.35, draw: eOutCubic(prog(t, F, 0.8)), fill: 0, alpha: 0.16, glow: 0.4, col: COL });
    slam(t, F, CX, CY - 400, () => txt(V.titre[0], 0, 0, 330, { stroke: 0 }), 2.4, 0.22);
    slam(t, F + 0.16, CX, CY - 110, () => txt(V.titre[1], 0, 0, 330, { color: COL.rouge, glow: 28 }), 2.4, 0.22);
    if (t >= F + 0.45) { ctx.save(); ctx.globalAlpha = prog(t, F + 0.45, 0.25); txt(V.sousTitre, CX, CY + 105, 40, { font: "Inter", spacing: 3 }); ctx.restore(); }
    slam(t, F + 0.75, CX, CY + 215, () => txt(V.cta, 0, 0, 74, { color: COL.rougeClair }), 1.5, 0.2);
    // site + reflet qui balaie
    if (t >= F + 1.05) {
      const k = eOutBack(prog(t, F + 1.05, 0.3));
      ctx.save(); ctx.translate(CX, CY + 360); ctx.scale(k, k);
      ctx.fillStyle = COL.rouge; ctx.shadowColor = COL.rouge; ctx.shadowBlur = 50;
      ctx.beginPath(); ctx.roundRect(-410, -75, 820, 150, 75); ctx.fill(); ctx.shadowBlur = 0;
      txt(C.offre.site, 0, 2, 86, { font: "Inter", maxW: 720 });
      const sweep = prog(t, F + 1.5, 0.8);
      if (sweep > 0 && sweep < 1) {
        ctx.beginPath(); ctx.roundRect(-410, -75, 820, 150, 75); ctx.clip();
        const sx = lerp(-650, 650, eOutCubic(sweep));
        const g = ctx.createLinearGradient(sx - 120, 0, sx + 120, 0);
        g.addColorStop(0, "rgba(255,255,255,0)"); g.addColorStop(0.5, "rgba(255,255,255,0.75)"); g.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = g; ctx.transform(1, 0, -0.4, 1, 0, 0); ctx.fillRect(sx - 140, -90, 280, 180);
      }
      ctx.restore();
    }
    slam(t, F + 1.6, CX, CY + 545, () => txt(V.derniere, 0, 0, 96, { stroke: 8 }), 1.7, 0.2);
  }

  // ---------------------------------------------------------------- composition
  const IMPACTS = [[T.impactHook, 1], [T.ligne2Hook, 0.45], [T.griffe, 0.6], [T.badge, 1], [T.jours, 0.4], [T.fin, 0.7], [T.fin + 0.16, 0.5]];
  function shake(t, f) {
    let amp = 0;
    for (const [ti, s] of IMPACTS) if (t >= ti) amp += s * 34 * Math.exp(-(t - ti) * 13);
    const r = rng(f + 101);
    return [(r() - 0.5) * 2 * amp, (r() - 0.5) * 2 * amp, amp];
  }
  function rgbSplit(px) {
    const im = ctx.getImageData(0, 0, W, H), d = im.data, src = new Uint8ClampedArray(d);
    for (let y = 0; y < H; y++) {
      const row = y * W * 4;
      for (let x = 0; x < W; x++) {
        const i = row + x * 4, xr = Math.min(W - 1, x + px), xb = Math.max(0, x - px);
        d[i] = src[row + xr * 4]; d[i + 2] = src[row + xb * 4 + 2];
      }
    }
    ctx.putImageData(im, 0, 0);
  }

  function render(f) {
    let t = f / FPS;
    const frozen = t >= T.fige;
    if (frozen) t = T.fige;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1; ctx.filter = "none";
    const [sx, sy, amp] = frozen ? [0, 0, 0] : shake(t, f);
    // micro-zoom par scène (1 → 1,05)
    const scenes = [0, T.tension, T.revelation, T.urgence, T.fin, T.fige];
    let si = 0; while (si < scenes.length - 2 && t >= scenes[si + 1]) si++;
    const z = 1 + 0.05 * clamp((t - scenes[si]) / (scenes[si + 1] - scenes[si]));
    ctx.translate(W / 2 + sx, H / 2 + sy); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2);
    background(t, f);
    if (t < T.tension) sceneHook(t);
    else if (t < T.revelation) sceneTension(t);
    else if (t < T.urgence) sceneReveal(t);
    else if (t < T.fin) sceneUrgence(t);
    else sceneFin(t);
    // cut flash léger aux changements de scène
    for (const s0 of [T.tension, T.revelation, T.urgence]) flash(t, s0, 0.08, 0.28);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    // vignette + grain
    const v = ctx.createRadialGradient(W / 2, H / 2, 500, W / 2, H / 2, 1250);
    v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,0.65)");
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.globalAlpha = 0.07; ctx.globalCompositeOperation = "overlay";
    ctx.drawImage(grains[frozen ? 0 : f % grains.length], 0, 0, W, H); ctx.restore();
    if (amp > 6) rgbSplit(Math.round(Math.min(18, amp * 0.5)));
  }

  window.TOTAL_FRAMES = Math.round(DUR * FPS);
  window.renderFrame = render;
  window.VERSION = VNAME;
  window.ready = Promise.all([
    document.fonts.load('100px "Anton"'), document.fonts.load('900 40px "Inter"'), document.fonts.load('800 40px "Inter"'),
  ]).then(() => document.fonts.ready).then(() => { render(0); return true; });
})();
