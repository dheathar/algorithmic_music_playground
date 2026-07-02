/* scenes.js — the lab's hand-built Canvas-2D visualizations (shared registry).
   SCENES[key] = { name, create() -> { draw(ctx, F), read?() } }
   F = {W,H,t,pos,dur,bass,low,lomid,mid,hi,level,centroid,flux,onset,beat,freq}.
   Letters are rendered in GFS Didot (OFL) as 'GreekLab'. */
(function () {
  // embed the OFL Greek font once (used by any scene, both the standalone page and the library)
  if (!document.getElementById('greeklab-font')) {
    const st = document.createElement('style'); st.id = 'greeklab-font';
    st.textContent = `@font-face{font-family:'GreekLab';src:url('fonts/greek-didot.ttf') format('truetype');font-display:swap}`;
    document.head.appendChild(st);
    try { document.fonts.load("48px GreekLab"); } catch (e) {}
  }
  const FONT = size => `${size}px GreekLab, "GFS Didot", Georgia, serif`;
  const SCENES = {};
  function noise2(x, y, t) {
    return Math.sin(x * 0.6 + t * 0.7) * 0.5 + Math.sin(y * 0.5 - t * 0.5) * 0.3 + Math.sin((x + y) * 0.31 + t * 1.1) * 0.2;
  }
  const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
  const smooth = t => t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t);

  // ---- Greek Maxims: a maxim carved in dark marble; the music's wind erodes it to dust ----
  SCENES['greek-maxims'] = {
    name: 'Greek Maxims (carved in marble, eroded by the wind of the music)',
    create() {
      const SAY = [
        { gr: 'ΠΑΝΤΑ ΡΕΙ', en: 'everything flows — Herakleitos' },
        { gr: 'ΓΝΩΘΙ ΣΑΥΤΟΝ', en: 'know thyself — Delphi' },
        { gr: 'ΜΗΔΕΝ ΑΓΑΝ', en: 'nothing in excess — Delphi' },
        { gr: 'ΕΝ ΟΙΔΑ ΟΤΙ ΟΥΔΕΝ ΟΙΔΑ', en: 'I know that I know nothing — Sokrates' },
        { gr: 'Ο ΧΡΟΝΟΣ ΠΑΝΤΑ ΛΥΕΙ', en: 'time undoes all things' },
      ];
      const WIND = {                       // the configurable wind model (all params music-coupled)
        dirBase: -0.12, dirDrift: 1.1, base: 26, levelGain: 240, gustGain: 560,
        turbBase: 55, turbMid: 320, buoyHi: 60, gravity: 22, drag: 0.986, gustDecay: 0.93,
      };
      const DWELL = 6.0, CARVE = 0.16, TRACK = 0.06;   // read-time, per-letter carve pace, letter tracking

      const marble = new Image(); let mOK = false; marble.onload = () => mOK = true; marble.src = 'assets/marble.jpg';
      let si = 0, phase = 'carve', layout = null, letters = [], lastCharT = 0, dwellStart = 0, erodeIdx = 0, lastPop = 0;
      let gust = 0, motes = [];

      function layoutWord(ctx, str, W, H) {
        let size = Math.min(W * 0.1, 128);
        const setF = () => ctx.font = FONT(size);
        setF();
        const meas = () => { let w = 0; for (const ch of str) w += ctx.measureText(ch).width + size * TRACK; return w - size * TRACK; };
        let tw = meas(); if (tw > W * 0.86) { size *= (W * 0.86) / tw; setF(); tw = meas(); }
        let px = (W - tw) / 2; const py = H * 0.46; const out = [];
        for (const ch of str) { const w = ctx.measureText(ch).width; out.push({ char: ch, x: px + w / 2, y: py, size }); px += w + size * TRACK; }
        return { out, size };
      }
      function newSaying(ctx, W, H) {
        layout = layoutWord(ctx, SAY[si].gr, W, H);
        letters = layout.out.map(g => ({ char: g.char, x: g.x, y: g.y, size: g.size, bornT: -1, placed: true, vx: 0, vy: 0, rot: 0, vrot: 0, alpha: 0 }));
        phase = 'carve'; lastCharT = -1; erodeIdx = 0; gust = 0; motes = [];
      }
      function background(ctx, F) {
        if (mOK) { const iw = marble.width, ih = marble.height, s = Math.max(F.W / iw, F.H / ih); ctx.drawImage(marble, (F.W - iw * s) / 2, (F.H - ih * s) / 2, iw * s, ih * s); }
        else { ctx.fillStyle = '#0b0a0e'; ctx.fillRect(0, 0, F.W, F.H); }
        ctx.fillStyle = `rgba(6,7,12,${0.68 - 0.14 * F.level})`; ctx.fillRect(0, 0, F.W, F.H);
        const g = ctx.createRadialGradient(F.W / 2, F.H * 0.46, 40, F.W / 2, F.H * 0.5, Math.max(F.W, F.H) * 0.72);
        g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(3,3,7,0.6)'); ctx.fillStyle = g; ctx.fillRect(0, 0, F.W, F.H);
      }
      function engrave(ctx, ch, x, y, size, a, lit) {           // carved into the stone (shadow + lit rim + cut)
        ctx.font = FONT(size); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillStyle = `rgba(0,0,0,${0.5 * a})`; ctx.fillText(ch, x + 2, y + 2.5);
        ctx.fillStyle = `rgba(236,230,218,${(0.28 + 0.5 * lit) * a})`; ctx.fillText(ch, x - 1.3, y - 1.5);
        ctx.fillStyle = `rgba(16,14,12,${0.74 * a})`; ctx.fillText(ch, x, y);
      }

      return {
        read() { return SAY[si].en; },
        draw(ctx, F) {
          const dt = 1 / 60;
          if (!layout) newSaying(ctx, F.W, F.H);

          // ---- WIND MODEL (music-coupled) ----
          gust *= WIND.gustDecay; if (F.onset) gust = Math.max(gust, 0.4 + F.bass);
          const mag = WIND.base + F.level * WIND.levelGain + gust * WIND.gustGain;
          const turb = WIND.turbBase + F.mid * WIND.turbMid, buoy = WIND.gravity - WIND.buoyHi * F.hi;
          const windAt = (x, y, tt) => {
            const dir = WIND.dirBase + noise2(x * 0.003, y * 0.003, tt * 0.22) * WIND.dirDrift;
            const nfx = noise2(x * 0.006 + 1, y * 0.006, tt * 0.4), nfy = noise2(x * 0.006, y * 0.006 + 7, tt * 0.4);
            return [Math.cos(dir) * mag + nfx * turb, Math.sin(dir) * mag + nfy * turb + buoy, nfx];
          };

          // ---- CHOREOGRAPHY: carve -> dwell (read) -> erode ----
          if (phase === 'carve') {
            if (lastCharT < 0) lastCharT = F.t;
            const carved = letters.filter(L => L.bornT >= 0).length;
            if (carved < letters.length && (F.t - lastCharT) >= CARVE) { letters[carved].bornT = F.t; lastCharT = F.t; }
            if (letters.every(L => L.bornT >= 0)) { phase = 'dwell'; dwellStart = F.t; }
          } else if (phase === 'dwell') {
            if (F.t - dwellStart > DWELL) { phase = 'erode'; lastPop = F.t; }
            if (Math.random() < 0.04 + F.level * 0.2) motes.push({ x: Math.random() * F.W, y: F.H * (0.3 + Math.random() * 0.4), vx: 0, vy: 0, a: 0.35 });
          } else if (phase === 'erode') {
            const gustStrong = (F.onset && F.beat > 0.4) || F.bass > 0.6;
            if (erodeIdx < letters.length && ((gustStrong && F.t - lastPop > 0.14) || F.t - lastPop > 1.8)) {
              const n = 1 + (F.bass > 0.6 ? 1 : 0) + (gustStrong && F.hi > 0.4 ? 1 : 0);
              for (let k = 0; k < n && erodeIdx < letters.length; k++, erodeIdx++) {
                const L = letters[erodeIdx]; L.placed = false;
                const [wx, wy] = windAt(L.x, L.y, F.t);
                L.vx = wx * 0.5 + (Math.random() - 0.5) * 30; L.vy = wy * 0.5 - 20 - Math.random() * 30; L.vrot = (Math.random() - 0.5) * 3;
                for (let m = 0; m < 4; m++) motes.push({ x: L.x + (Math.random() - 0.5) * L.size * 0.6, y: L.y + (Math.random() - 0.5) * L.size * 0.6, vx: L.vx * 0.7, vy: L.vy * 0.7, a: 0.6 });
              }
              lastPop = F.t;
            }
            if (erodeIdx >= letters.length && !letters.some(L => !L.placed && L.alpha > 0.02)) { si = (si + 1) % SAY.length; layout = null; }
          }

          for (const L of letters) {                              // integrate flying letters
            if (L.placed || L.alpha <= 0) continue;
            const [wx, wy, sw] = windAt(L.x, L.y, F.t);
            L.vx += wx * dt; L.vy += wy * dt; L.vx *= WIND.drag; L.vy *= WIND.drag; L.vrot += sw * 1.1 * dt;
            L.x += L.vx * dt; L.y += L.vy * dt; L.rot += L.vrot * dt; L.alpha -= 0.004 + 0.006 * F.level;
          }
          for (const m of motes) { if (m.a <= 0) continue; const [wx, wy] = windAt(m.x, m.y, F.t); m.vx += wx * dt; m.vy += wy * dt; m.vx *= WIND.drag; m.vy *= WIND.drag; m.x += m.vx * dt; m.y += m.vy * dt; m.a -= 0.006; }

          // ---- DRAW ----
          background(ctx, F);
          const lit = clamp(0.3 + 0.7 * F.level + 0.3 * F.hi, 0, 1);
          for (const L of letters) {
            if (L.placed) {
              if (L.bornT < 0) continue;
              const a = smooth((F.t - L.bornT) / 0.45);
              const flash = clamp(1 - (F.t - L.bornT) / 0.3, 0, 1);
              const sx = noise2(L.x * 0.006, F.t * 0.35) * 1.4, sy = noise2(L.y * 0.006 + 3, F.t * 0.3) * 0.8;
              engrave(ctx, L.char, L.x + sx, L.y + sy, L.size, a, clamp(lit + flash * 0.5, 0, 1));
            } else if (L.alpha > 0) {
              ctx.save(); ctx.translate(L.x, L.y); ctx.rotate(L.rot);
              ctx.font = FONT(L.size); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
              ctx.fillStyle = `rgba(226,220,206,${L.alpha * (0.55 + 0.45 * F.hi)})`; ctx.fillText(L.char, 0, 0);
              ctx.restore();
            }
          }
          for (const m of motes) { if (m.a <= 0) continue; ctx.fillStyle = `rgba(224,218,204,${m.a * 0.5})`; ctx.beginPath(); ctx.arc(m.x, m.y, 1.4, 0, 6.28); ctx.fill(); }
          if (phase === 'carve') {
            const idx = letters.filter(L => L.bornT >= 0).length;
            if (idx < letters.length) { const g = letters[idx]; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.strokeStyle = `rgba(234,228,216,${0.25 + 0.4 * Math.abs(Math.sin(F.t * 5))})`; ctx.beginPath(); ctx.moveTo(g.x - g.size * 0.22, g.y + g.size * 0.42); ctx.lineTo(g.x + g.size * 0.22, g.y + g.size * 0.42); ctx.stroke(); }
          }
          ctx.font = `${Math.min(F.W * 0.02, 18)}px ui-monospace, monospace`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
          ctx.fillStyle = `rgba(200,194,180,${0.3 + 0.12 * Math.sin(F.t * 0.7)})`; ctx.fillText(SAY[si].en, F.W / 2, F.H * 0.66);
        }
      };
    }
  };

  window.SCENES = SCENES;
})();
