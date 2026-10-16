"""byteTuto — page admin des inscrits (/admin/), servie par le service d'inscription.

Sécurité :
- Mot de passe jamais stocké : seule son empreinte scrypt est dans ADMIN_PASSWORD_HASH (fichier .env de l'EC2),
  écrite par deploy/set-admin-password.sh.
- Session : cookie signé HMAC-SHA256 avec ADMIN_SECRET, HttpOnly + Secure + SameSite=Strict, 4 h.
  Changer ADMIN_SECRET déconnecte tout le monde.
- Formulaires protégés par un jeton CSRF lié à la session.
- 5 échecs de connexion par IP et par 15 min, puis blocage.
- Active seulement en HTTPS : nginx ne relaie /admin/ que dans la conf HTTPS et envoie X-Forwarded-Proto ;
  la page répond 404 sinon (ADMIN_ALLOW_HTTP=1 seulement pour les tests locaux).
"""
import base64, csv, hashlib, hmac, html, io, os, secrets, threading, time
from urllib.parse import parse_qs

PW_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
SECRET = os.environ.get("ADMIN_SECRET", "").strip().encode()
ALLOW_HTTP = os.environ.get("ADMIN_ALLOW_HTTP") == "1"
SESSION_TTL = 4 * 3600
COOKIE = "bt_admin"
FAIL_MAX, FAIL_WINDOW = 5, 900
LIST_MAX = 1000

_lock = threading.Lock()
_fails: dict[str, list[float]] = {}


# ---------------------------------------------------------------- mot de passe
def _b64(b: bytes) -> str: return base64.urlsafe_b64encode(b).decode().rstrip("=")
def _unb64(s: str) -> bytes: return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(pw: str) -> str:
    """Format sans « $ » (sinon interprété dans .env) : scrypt:N:r:p:sel:empreinte."""
    n, r, p, salt = 2 ** 15, 8, 1, secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32)
    return f"scrypt:{n}:{r}:{p}:{_b64(salt)}:{_b64(dk)}"


def check_password(pw: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split(":")
        if algo != "scrypt":
            return False
        got = hashlib.scrypt(pw.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p),
                             maxmem=64 * 1024 * 1024, dklen=len(_unb64(dk)))
        return hmac.compare_digest(got, _unb64(dk))
    except (ValueError, TypeError):
        return False


def configured() -> bool:
    return PW_HASH.startswith("scrypt:") and len(SECRET) >= 32


# ---------------------------------------------------------------- session
def _sign(msg: str) -> str: return _b64(hmac.new(SECRET, msg.encode(), hashlib.sha256).digest())


def new_session() -> str:
    exp = str(int(time.time()) + SESSION_TTL)
    return f"{exp}.{_sign('s' + exp)}"


def session_ok(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.split(".", 1)
    return exp.isdigit() and int(exp) > time.time() and hmac.compare_digest(sig, _sign("s" + exp))


def csrf_for(token: str) -> str: return _sign("csrf" + token)


def too_many_fails(ip: str, add: bool = False) -> bool:
    now = time.monotonic()
    with _lock:
        f = [t for t in _fails.get(ip, []) if now - t < FAIL_WINDOW]
        if add:
            f.append(now)
        _fails[ip] = f
        return len(f) >= FAIL_MAX


# ---------------------------------------------------------------- pages
CSS = """
:root{--s:#0E1116;--r:#171B22;--i:#F2F1EC;--m:#A3A8B3;--l:#2A2F38;--b:#B8F03C;--t:#24300F;--d:#FF7A5C;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--s);color:var(--i);font:400 16px/26px "IBM Plex Sans",system-ui,sans-serif}
main{width:min(960px,100%);margin:0 auto;padding:32px 16px 48px}
h1{font:700 32px/1.1 "Space Grotesk",system-ui,sans-serif;letter-spacing:-.02em;margin:0 0 4px}
.k{font:500 13px/18px "JetBrains Mono",monospace;color:var(--b);margin:0 0 8px}.mut{color:var(--m)}
.card{background:var(--r);border:1px solid var(--l);border-radius:24px;padding:24px 20px;margin-top:24px}
label{display:block;font-weight:600;margin-bottom:6px}
input[type=password],input[type=search]{width:100%;height:46px;padding:0 14px;background:var(--s);color:var(--i);border:1px solid var(--l);border-radius:12px;font:500 16px "JetBrains Mono",monospace}
input:focus{outline:2px solid var(--b);outline-offset:2px}
.btn{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 18px;border-radius:12px;border:1px solid var(--l);background:transparent;color:var(--i);font:600 15px "IBM Plex Sans",system-ui,sans-serif;text-decoration:none;cursor:pointer}
.btn:hover{border-color:var(--b)}.btn--p{background:var(--b);color:#0E1116;border-color:var(--b)}
.btn--d{min-height:36px;padding:0 12px;font-size:14px;color:var(--d)}.btn--d:hover{border-color:var(--d)}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.stat{font:700 56px/1 "Space Grotesk",system-ui,sans-serif;color:var(--b)}
.msg{padding:10px 14px;border-radius:12px;background:var(--t);color:var(--b);font:500 14px "JetBrains Mono",monospace;margin-top:16px}
.msg--e{background:#3a1a12;color:var(--d)}
.tw{overflow-x:auto;margin-top:16px}table{width:100%;border-collapse:collapse;font-size:15px}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--l);white-space:nowrap}
th{font:500 12px "JetBrains Mono",monospace;color:var(--m);text-transform:uppercase;letter-spacing:.06em}
td.e{font-family:"JetBrains Mono",monospace;white-space:normal;overflow-wrap:anywhere}
form.inl{margin:0}
@media (max-width:599px){thead{display:none}tr{display:grid;grid-template-columns:1fr auto;gap:2px 12px;padding:12px 0;border-bottom:1px solid var(--l)}
td{border:0;padding:0}td.e{grid-column:1/-1}td.d{color:var(--m);font-size:14px;align-self:center}}
"""


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">
<title>{html.escape(title)} — byteTuto admin</title><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=JetBrains+Mono:wght@500&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>{body}</main></body></html>""".encode()


def login_page(error: str = "") -> bytes:
    err = f'<p class="msg msg--e" role="alert">{html.escape(error)}</p>' if error else ""
    return page("Connexion", f"""<p class="k">$ sudo bytetuto admin</p><h1>Inscrits byteTuto</h1>
<p class="mut">Espace privé. Connecte-toi pour voir la liste.</p>
<div class="card"><form method="post" action="/admin/login">
<label for="pw">Mot de passe</label><input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
<p style="margin:16px 0 0"><button class="btn btn--p" type="submit">Se connecter</button></p></form>{err}</div>""")


def not_configured_page() -> bytes:
    return page("À configurer", """<p class="k">$ bytetuto admin</p><h1>Page admin pas encore configurée</h1>
<div class="card"><p>Sur le serveur, dans <code>/opt/bytetuto</code>, lance :</p>
<p><code>bash deploy/set-admin-password.sh</code></p><p class="mut">Le script te demande un mot de passe et n'enregistre que son empreinte.</p></div>""")


def dashboard(rows, total: int, token: str, q: str = "", flash: str = "") -> bytes:
    csrf = csrf_for(token)
    fl = f'<p class="msg" role="status">{html.escape(flash)}</p>' if flash else ""
    trs = "".join(
        f"""<tr><td class="e">{html.escape(e)}</td><td class="d">{html.escape(d[:16].replace("T", " "))}</td><td>
<form class="inl" method="post" action="/admin/delete"><input type="hidden" name="csrf" value="{csrf}">
<input type="hidden" name="email" value="{html.escape(e)}"><button class="btn btn--d" type="submit" aria-label="Supprimer {html.escape(e)}">Supprimer</button></form></td></tr>"""
        for e, d in rows)
    shown = f"{len(rows)} résultat(s) pour « {html.escape(q)} »" if q else (
        f"Les {LIST_MAX} plus récents (tout est dans le CSV)" if total > LIST_MAX else "Du plus récent au plus ancien")
    empty = '<p class="mut" style="margin-top:16px">Personne pour l\'instant.</p>' if not rows else ""
    return page("Inscrits", f"""<div class="row"><div><p class="k">$ bytetuto admin</p><h1>Inscrits byteTuto</h1></div>
<form class="inl" method="post" action="/admin/logout"><input type="hidden" name="csrf" value="{csrf}"><button class="btn" type="submit">Se déconnecter</button></form></div>
{fl}
<div class="card row"><div><div class="stat">{total}</div><div class="mut">personne(s) attendent le lancement</div></div>
<a class="btn btn--p" href="/admin/export.csv">Télécharger le CSV</a></div>
<div class="card"><form method="get" action="/admin/"><label for="q">Chercher un email</label>
<input id="q" name="q" type="search" value="{html.escape(q)}" placeholder="nom@exemple.fr"></form>
<p class="mut" style="margin:12px 0 0">{shown}</p>{empty}
<div class="tw"><table><thead><tr><th>Email</th><th>Inscrit le (UTC)</th><th></th></tr></thead><tbody>{trs}</tbody></table></div></div>
<p class="mut" style="font-size:13px;margin-top:24px">Supprime un email dès qu'une personne te le demande (RGPD). La suppression est définitive.</p>""")


def confirm_page(email: str, csrf: str) -> bytes:
    e = html.escape(email)
    return page("Confirmer", f"""<p class="k">$ rm {e}</p><h1>Supprimer cet email ?</h1>
<div class="card"><p class="e" style="font-family:'JetBrains Mono',monospace;overflow-wrap:anywhere">{e}</p>
<p class="mut">La suppression est définitive. Fais-le si la personne te l'a demandé (RGPD).</p>
<div class="row" style="justify-content:flex-start"><form class="inl" method="post" action="/admin/delete">
<input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{e}"><input type="hidden" name="confirm" value="1">
<button class="btn btn--p" type="submit">Oui, supprimer</button></form><a class="btn" href="/admin/">Annuler</a></div></div>""")


def export_csv(con) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["email", "created_at", "consent_version"])
    w.writerows(con.execute("SELECT email, created_at, consent_version FROM subscribers ORDER BY id"))
    return ("﻿" + buf.getvalue()).encode()   # BOM : Excel lit l'UTF-8 correctement


# ---------------------------------------------------------------- routage
def handle(h, method: str, db):
    """h : le BaseHTTPRequestHandler ; db : fonction qui ouvre la base."""
    path, _, query = h.path.partition("?")

    def send(status, body=b"", ctype="text/html; charset=utf-8", headers=()):
        h.send_response(status)
        h.send_header("Content-Type", ctype)
        h.send_header("Content-Length", str(len(body)))
        h.send_header("Cache-Control", "no-store")
        h.send_header("X-Robots-Tag", "noindex, nofollow")
        for k, v in headers:
            h.send_header(k, v)
        h.end_headers()
        h.wfile.write(body)

    def redirect(to, cookie=None):
        hs = [("Location", to)] + ([("Set-Cookie", cookie)] if cookie else [])
        send(303, headers=hs)

    if not (ALLOW_HTTP or h.headers.get("X-Forwarded-Proto") == "https"):
        return send(404, page("Introuvable", "<h1>404</h1>"))
    if path == "/admin":
        return redirect("/admin/")
    if not configured():
        return send(503, not_configured_page())

    cookies = dict(c.strip().split("=", 1) for c in (h.headers.get("Cookie") or "").split(";") if "=" in c)
    token = cookies.get(COOKIE)
    logged = session_ok(token)
    secure = "" if ALLOW_HTTP and h.headers.get("X-Forwarded-Proto") != "https" else " Secure;"
    ip = h.headers.get("X-Real-IP") or h.client_address[0]

    form = {}
    if method == "POST":
        try:
            n = int(h.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if not 0 < n <= 4096:
            return send(413, page("Erreur", "<h1>Requête trop grande</h1>"))
        form = {k: v[0] for k, v in parse_qs(h.rfile.read(n).decode("utf-8", "replace")).items()}

    if path == "/admin/login" and method == "POST":
        if too_many_fails(ip):
            return send(429, login_page("Trop d'essais. Réessaie dans 15 minutes."))
        if check_password(form.get("password", ""), PW_HASH):
            with _lock:
                _fails.pop(ip, None)
            return redirect("/admin/", f"{COOKIE}={new_session()}; Path=/admin; Max-Age={SESSION_TTL}; HttpOnly;{secure} SameSite=Strict")
        too_many_fails(ip, add=True)
        time.sleep(0.5)
        return send(401, login_page("Mot de passe incorrect."))

    if not logged:
        if path == "/admin/" and method == "GET":
            return send(200, login_page())
        return redirect("/admin/")

    if method == "POST" and not hmac.compare_digest(form.get("csrf", ""), csrf_for(token)):
        return send(403, page("Refusé", "<h1>Formulaire expiré</h1><p><a href=\"/admin/\">Recharger la page</a></p>"))

    if path == "/admin/logout" and method == "POST":
        return redirect("/admin/", f"{COOKIE}=; Path=/admin; Max-Age=0; HttpOnly;{secure} SameSite=Strict")

    if path == "/admin/delete" and method == "POST":
        email = form.get("email", "").strip().lower()
        if form.get("confirm") != "1":       # étape de confirmation : la suppression est définitive
            return send(200, confirm_page(email, csrf_for(token)))
        with db() as con:
            gone = con.execute("DELETE FROM subscribers WHERE email = ?", (email,)).rowcount
        return redirect("/admin/?ok=" + ("supprime" if gone else "introuvable"))

    if path == "/admin/export.csv" and method == "GET":
        with db() as con:
            body = export_csv(con)
        name = f"inscrits-bytetuto-{time.strftime('%Y-%m-%d')}.csv"
        return send(200, body, "text/csv; charset=utf-8", [("Content-Disposition", f'attachment; filename="{name}"')])

    if path == "/admin/" and method == "GET":
        qs = parse_qs(query)
        q = qs.get("q", [""])[0].strip()[:254]
        flash = {"supprime": "✔ Email supprimé.", "introuvable": "Cet email n'était plus dans la liste."}.get(qs.get("ok", [""])[0], "")
        with db() as con:
            total = con.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
            if q:
                rows = con.execute("SELECT email, created_at FROM subscribers WHERE email LIKE ? ESCAPE '\\' ORDER BY id DESC LIMIT ?",
                                   ("%" + q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%", LIST_MAX)).fetchall()
            else:
                rows = con.execute("SELECT email, created_at FROM subscribers ORDER BY id DESC LIMIT ?", (LIST_MAX,)).fetchall()
        return send(200, dashboard(rows, total, token, q, flash))

    send(404, page("Introuvable", '<h1>404</h1><p><a href="/admin/">Retour</a></p>'))
