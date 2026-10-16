(() => {
  "use strict";
  document.getElementById("year").textContent = new Date().getFullYear();
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* =====================================================================
     Fond animé : trame de points + pistes de circuit qui se dessinent
     vers le centre, avec des impulsions lumineuses qui les parcourent.
     ===================================================================== */
  const cv = document.getElementById("bg");
  const ctx = cv.getContext("2d");
  const C = { dot: "#2A2F38", byte: "#B8F03C", spark: "#FF6B33", paper: "#F2F1EC" };
  let W = 0, H = 0, DPR = 1, P = 32, traces = [], mouse = { x: -1e4, y: -1e4 };

  const rnd = (a, b) => a + Math.random() * (b - a);
  const pick = a => a[(Math.random() * a.length) | 0];

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    cv.width = W * DPR; cv.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    P = W < 600 ? 28 : 36;
    traces = [];
    for (let i = 0; i < (W < 600 ? 7 : 13); i++) traces.push(makeTrace(rnd(0, 6)));
  }

  // une piste en "Manhattan" sur la grille, du bord vers la zone centrale
  function makeTrace(delay = 0) {
    const cols = Math.floor(W / P), rows = Math.floor(H / P);
    const side = (Math.random() * 4) | 0;
    let gx, gy;
    if (side === 0) { gx = 0; gy = (Math.random() * rows) | 0; }
    else if (side === 1) { gx = cols; gy = (Math.random() * rows) | 0; }
    else if (side === 2) { gx = (Math.random() * cols) | 0; gy = 0; }
    else { gx = (Math.random() * cols) | 0; gy = rows; }
    const cx = cols / 2, cy = rows / 2;
    // s'arrête au bord d'une ellipse autour du contenu
    const stopR = 0.62;
    const pts = [[gx, gy]];
    let horiz = side < 2, guard = 0;
    while (guard++ < 12) {
      const dx = cx - gx, dy = cy - gy;
      const step = (Math.random() * 4 + 2) | 0;
      if (horiz) gx += Math.sign(dx) * Math.min(step, Math.abs(dx) | 0 || 1);
      else gy += Math.sign(dy) * Math.min(step, Math.abs(dy) | 0 || 1);
      pts.push([gx, gy]);
      horiz = !horiz;
      const nx = (gx - cx) / (cols / 2), ny = (gy - cy) / (rows / 2);
      if (nx * nx + ny * ny < stopR * stopR) break;
    }
    const poly = pts.map(([x, y]) => [x * P + P / 2, y * P + P / 2]);
    let len = 0; const segs = [];
    for (let i = 1; i < poly.length; i++) {
      const l = Math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1]);
      segs.push(l); len += l;
    }
    return {
      poly, segs, len,
      color: C.byte,             // l'orange reste réservé à un seul accent (charte)
      born: performance.now() / 1000 + delay,
      draw: rnd(1.2, 2.2),        // durée du tracé
      life: rnd(9, 16),           // durée de vie avant fondu
      speed: rnd(90, 170),        // vitesse des impulsions (px/s)
      phase: Math.random(),
    };
  }

  function pointAt(tr, d) {
    for (let i = 0; i < tr.segs.length; i++) {
      if (d <= tr.segs[i]) {
        const a = tr.poly[i], b = tr.poly[i + 1], k = d / tr.segs[i];
        return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k];
      }
      d -= tr.segs[i];
    }
    return tr.poly[tr.poly.length - 1];
  }

  function drawGrid(now) {
    const r = P < 32 ? 1.3 : 1.6;
    for (let x = P / 2; x < W; x += P) {
      for (let y = P / 2; y < H; y += P) {
        const dm = Math.hypot(x - mouse.x, y - mouse.y);
        const lit = dm < 180 ? 1 - dm / 180 : 0;
        if (lit > 0) {
          ctx.fillStyle = `rgba(184,240,60,${0.15 + lit * 0.6})`;
          ctx.beginPath(); ctx.arc(x, y, r + lit * 1.4, 0, 6.283); ctx.fill();
        } else {
          ctx.fillStyle = C.dot;
          ctx.fillRect(x - r, y - r, r * 2, r * 2);
        }
      }
    }
  }

  function frame(ms) {
    const now = ms / 1000;
    ctx.clearRect(0, 0, W, H);
    drawGrid(now);

    for (let i = 0; i < traces.length; i++) {
      const tr = traces[i];
      const age = now - tr.born;
      if (age < 0) continue;
      if (age > tr.life) { traces[i] = makeTrace(rnd(0.2, 2)); continue; }
      const fade = Math.min(1, (tr.life - age) / 1.2);
      const prog = Math.min(1, age / tr.draw);
      const eased = 1 - Math.pow(1 - prog, 3);
      const reveal = tr.len * eased;

      // piste en pointillés
      ctx.save();
      ctx.globalAlpha = 0.55 * fade;
      ctx.strokeStyle = tr.color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      ctx.moveTo(tr.poly[0][0], tr.poly[0][1]);
      let left = reveal;
      for (let s = 0; s < tr.segs.length && left > 0; s++) {
        const a = tr.poly[s], b = tr.poly[s + 1], k = Math.min(1, left / tr.segs[s]);
        ctx.lineTo(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k);
        left -= tr.segs[s];
      }
      ctx.stroke();
      ctx.restore();

      // tête du tracé / nœud final
      const head = pointAt(tr, reveal);
      ctx.globalAlpha = fade;
      ctx.fillStyle = tr.color;
      ctx.shadowColor = tr.color; ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.arc(head[0], head[1], prog < 1 ? 2.5 : 4, 0, 6.283); ctx.fill();

      // impulsions qui courent vers le centre
      if (prog >= 1) {
        const per = tr.len / tr.speed;
        const ph = (((age - tr.draw) / per) + tr.phase) % 1;
        const p = pointAt(tr, ph * tr.len);
        ctx.globalAlpha = fade * Math.sin(ph * Math.PI);
        ctx.beginPath(); ctx.arc(p[0], p[1], 3, 0, 6.283); ctx.fill();
      }
      ctx.shadowBlur = 0; ctx.globalAlpha = 1;
    }
    if (!reduce) requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resize, { passive: true });
  window.addEventListener("pointermove", e => { mouse.x = e.clientX; mouse.y = e.clientY; }, { passive: true });
  window.addEventListener("pointerleave", () => { mouse.x = mouse.y = -1e4; });
  resize();
  if (reduce) { traces.forEach(t => { t.born = -100; t.life = 1e9; }); frame(performance.now()); }
  else requestAnimationFrame(frame);

  /* =====================================================================
     Terminal : une fausse construction qui tourne en boucle
     ===================================================================== */
  const term = document.getElementById("term");
  const steps = [
    { cmd: "git clone bytetuto/site" },
    { out: '<span class="ok">✔</span> <span class="mut">logo ▶_, charte, intro néon</span>' },
    { cmd: "docker compose up -d" },
    { out: '<span class="ok">✔</span> <span class="mut">nginx</span> prêt' },
    { cmd: "npm run build -- --tutos" },
    { bar: true },
    { out: '<span class="sp">▶</span> premiers tutos en cours d\'écriture…' },
  ];
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  async function type(el, text) {
    for (const ch of text) { el.textContent += ch; await sleep(rnd(28, 70)); }
  }

  async function run() {
    while (true) {
      term.innerHTML = "";
      for (const s of steps) {
        const line = document.createElement("div");
        line.className = "term__line";
        term.appendChild(line);
        if (s.cmd) {
          line.innerHTML = '<span class="p">$</span> ';
          const t = document.createElement("span");
          const cur = document.createElement("span"); cur.className = "term__cursor";
          line.append(t, cur);
          await type(t, s.cmd);
          await sleep(350);
          cur.remove();
        } else if (s.bar) {
          line.innerHTML = '<span class="bar"><b></b></span><span class="mut">0%</span>';
          const b = line.querySelector("b"), pct = line.querySelector(".mut");
          const target = Math.round(rnd(68, 84));
          for (let p = 0; p <= target; p += Math.round(rnd(2, 6))) {
            b.style.width = p + "%"; pct.textContent = p + "%"; await sleep(rnd(60, 160));
          }
          b.style.width = target + "%"; pct.textContent = target + "%";
          await sleep(300);
        } else {
          line.innerHTML = s.out;
          await sleep(450);
        }
      }
      const end = document.createElement("div");
      end.className = "term__line";
      end.innerHTML = '<span class="p">$</span> <span class="term__cursor"></span>';
      term.appendChild(end);
      await sleep(5200);
    }
  }
  if (!reduce) setTimeout(run, 2000);
})();
