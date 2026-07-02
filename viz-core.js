/* viz-core.js — the shared engine for the lab's hand-built visualizations.
   Canvas 2D + Web Audio AnalyserNode. Each visualization is a "scene" that
   implements draw(ctx, F); this core owns audio, analysis, bands, and the UI shell.

   Usage (a whole viz page):
     <script src="viz-core.js"></script>
     <script>Viz.run({
       title:'Excivilization', subtitle:'…', back:{href:'x.html', label:'← X'},
       tracks:[{value:'a.mp3', label:'A'}],
       scene:{ setup(ctx){}, draw(ctx, F){} }   // F = {W,H,t,pos,dur,bass,low,lomid,mid,hi,freq}
     });</script>
*/
(function () {
  const TOK = `:root{--bg:#05060c;--text:#E7E9F3;--muted:#8C92B2;--faint:#5A6088;--amber:#F4A659;--phosphor:#57E3C2;--phosphor-dim:#2E8C77;--violet:#9B8CFF;--rose:#E3859B;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--body:-apple-system,system-ui,sans-serif}`;
  const CSS = `${TOK}
    *{box-sizing:border-box;margin:0} html,body{height:100%;background:var(--bg);overflow:hidden;font-family:var(--body);color:var(--text)}
    #vzc{position:fixed;inset:0;display:block}
    .vz-back{position:fixed;top:16px;left:18px;z-index:5;font-family:var(--mono);font-size:12px;color:var(--faint);text-decoration:none}
    .vz-back:hover{color:var(--phosphor)}
    #vz-read{position:fixed;top:16px;right:18px;z-index:5;font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right}
    .vz-bar{position:fixed;left:0;right:0;bottom:0;z-index:4;display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:12px 16px;background:linear-gradient(0deg,rgba(5,6,12,.9),transparent);transition:opacity .5s}
    .vz-bar.dim{opacity:0;pointer-events:none}
    .vz-bar select{font-family:var(--mono);font-size:12px;background:rgba(18,21,42,.85);color:var(--text);border:1px solid #272C4C;border-radius:7px;padding:8px 11px;cursor:pointer}
    .vz-lab{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
    .vz-ov{position:fixed;inset:0;z-index:10;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;background:radial-gradient(circle at 50% 45%,rgba(20,16,40,.5),#05060c 70%);transition:opacity 1s}
    .vz-ov.hide{opacity:0;pointer-events:none}
    .vz-ttl{font-weight:800;letter-spacing:-.02em;font-size:clamp(28px,6vw,56px);text-align:center} .vz-ttl em{font-style:normal;color:var(--amber)}
    .vz-sub{color:var(--muted);max-width:54ch;text-align:center;font-size:15px;line-height:1.5}
    .vz-err{color:var(--amber);font-family:var(--mono);font-size:12px;max-width:52ch;text-align:center}
    .vz-play{width:74px;height:74px;border-radius:50%;border:1px solid var(--phosphor-dim);background:rgba(18,21,42,.7);color:var(--phosphor);cursor:pointer;display:grid;place-items:center;transition:.2s}
    .vz-play:hover{background:var(--phosphor);color:#05060c;box-shadow:0 0 40px rgba(87,227,194,.5)} .vz-play svg{width:30px;height:30px}`;

  function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  const Viz = {
    run(opts) {
      const style = el('style'); style.textContent = CSS; document.head.appendChild(style);
      if (opts.titleTag) document.title = opts.titleTag;
      const cv = el('canvas'); cv.id = 'vzc'; document.body.appendChild(cv);
      const ctx = cv.getContext('2d');
      const back = el('a', 'vz-back'); back.href = (opts.back && opts.back.href) || 'index.html';
      back.textContent = (opts.back && opts.back.label) || '← Signal Lab'; document.body.appendChild(back);
      const read = el('div'); read.id = 'vz-read'; document.body.appendChild(read);

      const bar = el('div', 'vz-bar dim');
      const tracks = opts.tracks || [];
      bar.appendChild(el('span', 'vz-lab', 'track'));
      const sel = el('select');
      sel.innerHTML = tracks.map(t => `<option value="${t.value}">${t.label}</option>`).join('');
      bar.appendChild(sel); document.body.appendChild(bar);

      const ov = el('div', 'vz-ov');
      ov.innerHTML = `<div class="vz-ttl">${opts.title || ''}</div><div class="vz-sub">${opts.subtitle || ''}</div>` +
        `<button class="vz-play" aria-label="Begin"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button><div class="vz-err"></div>`;
      document.body.appendChild(ov);
      const err = ov.querySelector('.vz-err');

      let DPR, W, H;
      function resize() { DPR = Math.min(devicePixelRatio || 1, 2); W = innerWidth; H = innerHeight; cv.width = W * DPR; cv.height = H * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0); }
      resize(); addEventListener('resize', resize);

      let AC, an, freq, src = null, buffers = {}, started = false, t0 = 0, dur = 1;
      let prev = null, fluxAvg = 0, lastOnset = 0, beat = 0;         // for onset/flux/beat
      const nband = (lo, hi) => { let s = 0; for (let i = lo; i < hi; i++) s += freq[i]; return s / ((hi - lo) * 255); };
      async function load(f) { if (buffers[f]) return buffers[f]; const r = await fetch(f); if (!r.ok) throw new Error(r.status + ' ' + f); buffers[f] = await AC.decodeAudioData(await r.arrayBuffer()); return buffers[f]; }
      async function play(f) { if (src) { try { src.stop(); } catch (e) {} } const b = await load(f); src = AC.createBufferSource(); src.buffer = b; src.loop = true; src.connect(an); an.connect(AC.destination); src.start(); t0 = AC.currentTime; dur = b.duration; }

      function loop() {
        requestAnimationFrame(loop);
        an.getByteFrequencyData(freq);
        const B = freq.length; if (!prev) prev = new Uint8Array(B);
        let flux = 0, sum = 0, csum = 0;
        for (let i = 0; i < B; i++) { const v = freq[i], d = v - prev[i]; if (d > 0) flux += d; prev[i] = v; sum += v; csum += i * v; }
        flux /= (B * 255); const level = sum / (B * 255); const centroid = sum > 0 ? (csum / sum) / B : 0;
        fluxAvg = fluxAvg * 0.95 + flux * 0.05;
        const tt = AC.currentTime; let onset = false;
        if (flux > fluxAvg * 1.6 + 0.006 && tt - lastOnset > 0.12) { onset = true; lastOnset = tt; beat = 1; }
        beat *= 0.90;
        const pos = dur ? ((tt - t0) % dur) : 0;
        const F = { W, H, DPR, t: tt, pos, dur,
          bass: nband(1, 8), low: nband(8, 24), lomid: nband(24, 80), mid: nband(80, 200), hi: nband(200, 500),
          level, centroid, flux, onset, beat, freq };
        if (opts.readout) read.textContent = opts.readout(F);
        try { opts.scene.draw(ctx, F); } catch (e) {}
      }
      async function begin() {
        AC = new (window.AudioContext || window.webkitAudioContext)();
        an = AC.createAnalyser(); an.fftSize = 2048; an.smoothingTimeConstant = 0.82; freq = new Uint8Array(an.frequencyBinCount);
        if (opts.scene.setup) opts.scene.setup(ctx);
        try { await play(sel.value); } catch (e) { err.textContent = 'Could not load audio (' + e.message + '). Open via the server: http://127.0.0.1:7700/'; return; }
        started = true; ov.classList.add('hide'); bar.classList.remove('dim'); loop();
      }
      ov.querySelector('.vz-play').onclick = begin;
      sel.onchange = e => { if (started) play(e.target.value).catch(() => {}); };
      let hideT; addEventListener('mousemove', () => { if (!started) return; bar.classList.remove('dim'); clearTimeout(hideT); hideT = setTimeout(() => bar.classList.add('dim'), 3500); });
    }
  };
  window.Viz = Viz;
})();
