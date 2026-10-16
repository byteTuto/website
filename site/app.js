(() => {
  "use strict";
  document.documentElement.classList.add("js");
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

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  /* =====================================================================
     Inscription + compteur (API /api/, voir api/app.py)
     ===================================================================== */
  const form = document.getElementById("inscription");
  const input = document.getElementById("email");
  const msg = document.getElementById("signup-msg");
  const countBox = document.getElementById("signup-count");
  const countN = document.getElementById("count-n");
  let shown = 0;

  function showCount(n, show) {
    if (!show) return;
    countBox.hidden = false;
    if (reduce || shown === 0 && n < 5) { countN.textContent = n; shown = n; return; }
    const from = shown, t0 = performance.now(), dur = 900;
    const step = now => {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      countN.textContent = Math.round(from + (n - from) * e);
      if (k < 1) requestAnimationFrame(step);
    };
    shown = n; requestAnimationFrame(step);
  }

  async function loadCount() {
    try {
      const r = await fetch("/api/count", { headers: { Accept: "application/json" } });
      if (r.ok) { const d = await r.json(); showCount(d.count, d.show); return d; }
    } catch (_) { /* API indisponible : on n'affiche rien */ }
    return null;
  }

  // Envoie l'inscription ; renvoie { ok, text } pour le formulaire et le terminal
  async function subscribe(email) {
    email = email.trim();
    if (!EMAIL_RE.test(email)) return { ok: false, text: "Cette adresse email ne semble pas valide." };
    try {
      const r = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ email, website: document.getElementById("website").value }),
      });
      const d = r.headers.get("content-type")?.includes("json") ? await r.json() : {};
      if (r.ok) {
        showCount(d.count, d.show);
        if (d.new && d.show && d.rank) return { ok: true, text: `✔ C'est noté ! Tu es le n°${d.rank} à attendre le lancement.` };
        if (d.new) return { ok: true, text: "✔ C'est noté ! On te prévient au lancement." };
        return { ok: true, text: "✔ Tu es déjà sur la liste, on te prévient au lancement." };
      }
      if (r.status === 422) return { ok: false, text: "Cette adresse email ne semble pas valide." };
      if (r.status === 429) return { ok: false, text: "Trop d'essais d'un coup. Réessaie dans quelques minutes." };
    } catch (_) { /* réseau */ }
    return { ok: false, text: "Oups, le serveur ne répond pas. Réessaie dans un instant ou écris à contact@bytetuto.com." };
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    if (location.hash && /merci|oups|email-invalide/.test(location.hash)) history.replaceState(null, "", location.pathname);
    btn.disabled = true; msg.className = "signup__msg"; msg.textContent = "";
    const res = await subscribe(input.value);
    btn.disabled = false;
    msg.className = "signup__msg " + (res.ok ? "is-ok" : "is-err");
    msg.textContent = res.text;
    if (res.ok) { form.classList.add("signup--done"); input.value = ""; }
    else input.focus();
  });
  loadCount();

  /* =====================================================================
     Teaser vidéo : lecture muette quand il est visible, boutons pause / son
     ===================================================================== */
  const video = document.getElementById("teaser");
  const ctrl = document.getElementById("teaser-ctrl");
  const bPlay = document.getElementById("teaser-play");
  const bSound = document.getElementById("teaser-sound");
  let userPaused = reduce, visible = false;
  video.removeAttribute("controls");
  ctrl.hidden = false;

  function syncButtons() {
    bPlay.setAttribute("aria-pressed", String(video.paused));
    bPlay.querySelector(".vbtn__txt").textContent = video.paused ? "Lecture" : "Pause";
    bSound.setAttribute("aria-pressed", String(!video.muted));
    bSound.querySelector(".vbtn__txt").textContent = video.muted ? "Activer le son" : "Couper le son";
  }
  const tryPlay = () => video.play().catch(() => {}).finally(syncButtons);

  bPlay.addEventListener("click", () => {
    if (video.paused) { userPaused = false; tryPlay(); } else { userPaused = true; video.pause(); }
  });
  bSound.addEventListener("click", () => {
    video.muted = !video.muted;
    if (!video.muted) { video.currentTime = 0; userPaused = false; tryPlay(); }  // repart du début pour entendre la signature
    syncButtons();
  });
  ["play", "pause", "volumechange"].forEach(ev => video.addEventListener(ev, syncButtons));
  syncButtons();

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([en]) => {
      visible = en.isIntersecting;
      if (visible && !userPaused) tryPlay();
      if (!visible && !video.paused) video.pause();
    }, { threshold: 0.4 }).observe(video);
  }

  /* apparition des sections au défilement */
  const reveals = document.querySelectorAll(".more .panel");
  reveals.forEach((el, i) => { el.classList.add("reveal"); el.style.transitionDelay = `${i * 120}ms`; });
  if (reduce || !("IntersectionObserver" in window)) reveals.forEach(el => el.classList.add("is-in"));
  else {
    const io = new IntersectionObserver(ens => ens.forEach(en => {
      if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); }
    }), { threshold: 0.12 });
    reveals.forEach(el => io.observe(el));
  }

  /* =====================================================================
     Terminal interactif : une courte « construction », puis le visiteur
     tape ses commandes (help, tutos, inscris…, teaser, clear…)
     ===================================================================== */
  const term = document.getElementById("term");
  const box = document.getElementById("term-box");
  const tForm = document.getElementById("term-form");
  const cmd = document.getElementById("term-cmd");
  const hist = []; let hi = 0, busy = false;

  function line(html, cls = "") {
    const el = document.createElement("div");
    el.className = "term__line" + (cls ? " " + cls : "");
    el.innerHTML = html;
    term.appendChild(el);
    term.scrollTop = term.scrollHeight;
    return el;
  }
  async function type(el, text) {
    if (reduce) { el.textContent = text; return; }
    const id = bootId;
    for (const ch of text) { if (id !== bootId) return; el.textContent += ch; await sleep(rnd(25, 60)); }
  }
  async function bar(label) {
    const el = line(`<span class="bar"><b></b></span><span class="mut">0%</span>`);
    const b = el.querySelector("b"), pct = el.querySelector(".mut");
    const target = Math.round(rnd(68, 84));
    const id = bootId;
    for (let p = 0; p <= target && !reduce && id === bootId; p += Math.round(rnd(3, 8))) {
      b.style.width = p + "%"; pct.textContent = p + "%"; await sleep(rnd(40, 110));
    }
    b.style.width = target + "%"; pct.textContent = `${target}% ${label}`;
  }

  let bootId = 0;   // une commande tapée pendant la construction l'interrompt
  async function boot() {
    const id = ++bootId;
    term.innerHTML = "";
    const steps = [
      { cmd: "git clone bytetuto/site" },
      { out: '<span class="ok">✔</span> <span class="mut">logo ▶_, charte, intro néon</span>' },
      { cmd: "npm run build -- --tutos" },
      { bar: "premiers tutos en cours d'écriture…" },
      { out: '<span class="sp">▶</span> Tape <span class="h">help</span> pour voir les commandes.' },
    ];
    for (const s of steps) {
      if (id !== bootId) return;
      if (s.cmd) {
        const el = line('<span class="p">$</span> <span class="cmd"></span>');
        await type(el.querySelector(".cmd"), s.cmd); await sleep(reduce ? 0 : 250);
      } else if (s.bar) await bar(s.bar);
      else { line(s.out); await sleep(reduce ? 0 : 300); }
    }
  }

  const LINKS = {
    youtube: "https://www.youtube.com/@bytetuto",
    tiktok: "https://www.tiktok.com/@bytetuto",
  };
  const HELP = [
    ["help", "liste des commandes"],
    ["whoami", "c'est quoi byteTuto ?"],
    ["tutos", "ce qui arrive bientôt"],
    ["inscris <email>", "être prévenu du lancement"],
    ["compteur", "combien attendent le lancement"],
    ["teaser", "lancer la vidéo avec le son"],
    ["youtube · tiktok", "ouvrir nos chaînes"],
    ["ls · cat · date · echo", "les classiques"],
    ["clear", "effacer l'écran"],
  ];
  const FILES = { "lisezmoi.txt": "Apprends la tech, un byte à la fois. Des tutos courts : on montre, puis on explique.", "tutos/": null, "teaser.mp4": null };

  const COMMANDS = {
    help: () => HELP.forEach(([c, d]) => line(`<span class="h">${esc(c.padEnd(22))}</span><span class="mut">${esc(d)}</span>`)),
    aide: () => COMMANDS.help(),
    whoami: () => {
      line("byteTuto : des tutos tech courts et concrets — code, outils, astuces.");
      line('<span class="mut">Sur YouTube (format long), TikTok (format court) et bientôt ici.</span>');
    },
    tutos: () => {
      line('<span class="p">▶</span> Au programme :');
      ["code — JavaScript, Python, Git", "outils — VS Code, terminal, Docker", "IA au quotidien — prompts, automatisations", "astuces PC — raccourcis, Excel, gain de temps"]
        .forEach(t => line(`  <span class="ok">•</span> ${esc(t)}`));
      line('<span class="mut">Un sujet à proposer ? Écris-nous : <a href="mailto:contact@bytetuto.com">contact@bytetuto.com</a></span>');
    },
    ls: () => line(Object.keys(FILES).map(f => f.endsWith("/") ? `<span class="p">${f}</span>` : esc(f)).join("  ")),
    cat: a => {
      if (!a) return line('<span class="err">cat : quel fichier ?</span> <span class="mut">essaie</span> cat lisezmoi.txt');
      if (FILES[a]) return line(esc(FILES[a]));
      if (a in FILES) return line(`<span class="err">cat : ${esc(a)} : ${a.endsWith("/") ? "c'est un dossier (vide… pour l'instant)" : "fichier binaire, tape teaser"}</span>`);
      line(`<span class="err">cat : ${esc(a)} : fichier introuvable</span>`);
    },
    cd: a => line(a === "tutos" || a === "tutos/" ? '<span class="mut">tutos/ est encore vide. Inscris-toi pour savoir quand il se remplit.</span>' : '<span class="mut">On reste ici, il y a tout ce qu\'il faut.</span>'),
    pwd: () => line("/home/visiteur/bytetuto.com"),
    date: () => line(esc(new Date().toLocaleString("fr-FR", { dateStyle: "full", timeStyle: "short" }))),
    echo: a => line(esc(a || "")),
    clear: () => { term.innerHTML = ""; },
    youtube: () => { window.open(LINKS.youtube, "_blank", "noopener"); line(`<span class="ok">✔</span> ouverture de <a href="${LINKS.youtube}" target="_blank" rel="noopener">youtube.com/@bytetuto</a>`); },
    tiktok: () => { window.open(LINKS.tiktok, "_blank", "noopener"); line(`<span class="ok">✔</span> ouverture de <a href="${LINKS.tiktok}" target="_blank" rel="noopener">tiktok.com/@bytetuto</a>`); },
    teaser: () => {
      line('<span class="ok">✔</span> lecture du teaser, son activé');
      video.muted = false; video.currentTime = 0; userPaused = false; tryPlay();
      video.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
    },
    inscris: async a => {
      if (!a) {
        line('<span class="mut">usage :</span> inscris ton@email.fr <span class="mut">(ou utilise le formulaire en haut)</span>');
        return;
      }
      const wait = line('<span class="mut">envoi…</span>');
      const res = await subscribe(a);
      wait.innerHTML = res.ok ? `<span class="ok">${esc(res.text)}</span>` : `<span class="err">${esc(res.text)}</span>`;
    },
    compteur: async () => {
      const d = await loadCount();
      if (!d) return line('<span class="err">compteur indisponible pour le moment</span>');
      line(d.show ? `<span class="p">▶</span> ${d.count} personnes attendent le lancement.`
                  : '<span class="p">▶</span> La liste démarre, tu peux être parmi les premiers : <span class="h">inscris ton@email.fr</span>');
    },
    sudo: () => line('<span class="err">Permission refusée.</span> <span class="mut">Même root attend le lancement ▶_</span>'),
    rm: () => line('<span class="err">Bien tenté.</span> <span class="mut">Le site est en lecture seule.</span>'),
    exit: () => line('<span class="mut">Impossible de partir maintenant, le meilleur arrive.</span>'),
    vim: () => line('<span class="mut">Tu es sûr ? Personne n\'est jamais ressorti de vim. (indice : :q!)</span>'),
    npm: () => { boot(); },
    hello: () => line("Salut ! 👋 Tape help pour commencer."),
  };
  Object.assign(COMMANDS, { subscribe: COMMANDS.inscris, inscription: COMMANDS.inscris, bonjour: COMMANDS.hello, salut: COMMANDS.hello, quit: COMMANDS.exit, about: COMMANDS.whoami, nano: COMMANDS.vim, emacs: COMMANDS.vim });
  const NAMES = Object.keys(COMMANDS);

  async function run(raw) {
    const text = raw.trim();
    line(`<span class="p">$</span> <span class="cmd">${esc(text)}</span>`);
    if (!text) return;
    hist.push(text); hi = hist.length;
    const [name, ...rest] = text.split(/\s+/);
    const fn = COMMANDS[name.toLowerCase()];
    if (!fn) return line(`<span class="err">commande introuvable : ${esc(name)}</span> <span class="mut">— tape</span> <span class="h">help</span>`);
    await fn(rest.join(" "));
  }

  tForm.addEventListener("submit", async e => {
    e.preventDefault();
    if (busy) return;           // une inscription est en cours d'envoi
    busy = true;
    bootId++;                   // arrête l'animation de démarrage si elle tourne encore
    const v = cmd.value; cmd.value = "";
    try { await run(v); } finally { busy = false; term.scrollTop = term.scrollHeight; }
  });
  cmd.addEventListener("keydown", e => {
    if (e.key === "ArrowUp" && hist.length) { e.preventDefault(); hi = Math.max(0, hi - 1); cmd.value = hist[hi]; }
    else if (e.key === "ArrowDown" && hist.length) { e.preventDefault(); hi = Math.min(hist.length, hi + 1); cmd.value = hist[hi] || ""; }
    else if (e.key === "Tab" && cmd.value && !cmd.value.includes(" ")) {
      const m = NAMES.filter(n => n.startsWith(cmd.value.toLowerCase()));
      if (m.length === 1) { e.preventDefault(); cmd.value = m[0] + " "; }
      else if (m.length > 1) { e.preventDefault(); line(`<span class="mut">${m.map(esc).join("  ")}</span>`); }
    } else if (e.key === "l" && e.ctrlKey) { e.preventDefault(); term.innerHTML = ""; }
  });
  // un clic dans le terminal place le curseur dans le champ (sauf sélection de texte ou lien)
  box.addEventListener("click", e => { if (!e.target.closest("a") && !String(window.getSelection())) cmd.focus({ preventScroll: true }); });

  // la construction démarre quand le terminal devient visible
  tForm.hidden = false;
  let booted = false;
  const startBoot = () => {
    if (booted) return;
    booted = true;
    boot();
  };
  if ("IntersectionObserver" in window && !reduce) {
    const io = new IntersectionObserver(([en]) => { if (en.isIntersecting) { startBoot(); io.disconnect(); } }, { threshold: 0.3 });
    io.observe(box);
  } else startBoot();
})();
