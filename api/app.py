#!/usr/bin/env python3
"""byteTuto — service d'inscription « Préviens-moi du lancement » (Python 3, bibliothèque standard + SQLite).

Routes (derrière nginx, préfixe /api/) :
  GET  /api/health      -> {"ok": true}
  GET  /api/count       -> {"count": 42, "show": true}   (show = count >= COUNTER_MIN)
  POST /api/subscribe   -> JSON {"email": "...", "website": ""}  ou formulaire HTML classique (sans JS)

Administration (sur l'EC2) :
  docker compose exec api python app.py count
  docker compose exec api python app.py export > inscrits.csv
  docker compose exec api python app.py delete toi@exemple.fr     # droit à l'effacement (RGPD)

Variables : DB_PATH (/data/subscribers.db), COUNTER_MIN (30), RATE_MAX (5), PORT (8000).
Données gardées : email, date d'inscription, version du texte de consentement. Pas d'adresse IP.
"""
import csv, json, os, re, sqlite3, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

DB_PATH = os.environ.get("DB_PATH", "/data/subscribers.db")
COUNTER_MIN = int(os.environ.get("COUNTER_MIN", "30"))
PORT = int(os.environ.get("PORT", "8000"))
CONSENT_VERSION = "2026-10-16"           # à changer si le texte sous le formulaire change
MAX_BODY = 2048
RATE_MAX = int(os.environ.get("RATE_MAX", "5"))   # inscriptions par IP et par 10 minutes (en mémoire seulement)
RATE_WINDOW = 600
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        consent_version TEXT NOT NULL)""")
    return con


def count() -> int:
    with db() as con:
        return con.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]


def subscribe(email: str) -> tuple[bool, int]:
    """Ajoute l'email. Renvoie (nouveau ?, nombre total d'inscrits)."""
    with _lock, db() as con:
        cur = con.execute("INSERT OR IGNORE INTO subscribers (email, consent_version) VALUES (?, ?)",
                          (email, CONSENT_VERSION))
        return cur.rowcount == 1, con.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]


def valid_email(email: str) -> bool:
    return 6 <= len(email) <= 254 and EMAIL_RE.match(email) is not None


def rate_limited(ip: str) -> bool:
    now = time.monotonic()
    with _lock:
        hits = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
        if len(_hits) > 10000:
            _hits.clear()
        limited = len(hits) >= RATE_MAX
        if not limited:
            hits.append(now)
        _hits[ip] = hits
        return limited


class Handler(BaseHTTPRequestHandler):
    server_version = "bytetuto-api"
    sys_version = ""

    def log_message(self, fmt, *args):     # journal sans IP ni email
        sys.stderr.write(f"{self.log_date_time_string()} {self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")

    def _json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, fragment: str):
        # Formulaire sans JavaScript : retour sur l'accueil, le message s'affiche avec :target
        self.send_response(303)
        self.send_header("Location", f"/#{fragment}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            return self._json(200, {"ok": True})
        if path == "/api/count":
            n = count()
            return self._json(200, {"count": n, "show": n >= COUNTER_MIN})
        self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/subscribe":
            return self._json(404, {"ok": False, "error": "not_found"})
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        is_form = ctype == "application/x-www-form-urlencoded"
        fail = (lambda code, err, frag: self._redirect(frag)) if is_form else \
               (lambda code, err, frag: self._json(code, {"ok": False, "error": err}))

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            return fail(413, "too_large", "oups")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        try:
            if is_form:
                data = {k: v[0] for k, v in parse_qs(raw).items()}
            elif ctype == "application/json":
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError
            else:
                return fail(415, "unsupported", "oups")
        except ValueError:
            return fail(400, "bad_request", "oups")

        ip = self.headers.get("X-Real-IP") or self.client_address[0]
        if rate_limited(ip):
            return fail(429, "too_many", "oups")

        # Pot de miel : champ invisible que seuls les robots remplissent -> on fait semblant d'accepter
        if str(data.get("website", "")).strip():
            return self._redirect("merci") if is_form else self._json(200, {"ok": True, "new": False, "count": count()})

        email = str(data.get("email", "")).strip().lower()
        if not valid_email(email):
            return fail(422, "invalid_email", "email-invalide")

        new, n = subscribe(email)
        if is_form:
            return self._redirect("merci")
        # Même réponse que l'email soit nouveau ou déjà inscrit (ne révèle pas qui est inscrit),
        # sauf le rang, donné seulement pour une nouvelle inscription.
        out = {"ok": True, "new": new, "count": n, "show": n >= COUNTER_MIN}
        if new:
            out["rank"] = n
        self._json(201 if new else 200, out)


def admin(cmd: str, arg: str | None):
    if cmd == "count":
        print(count())
    elif cmd == "export":
        with db() as con:
            w = csv.writer(sys.stdout)
            w.writerow(["email", "created_at", "consent_version"])
            w.writerows(con.execute("SELECT email, created_at, consent_version FROM subscribers ORDER BY id"))
    elif cmd == "delete" and arg:
        with db() as con:
            n = con.execute("DELETE FROM subscribers WHERE email = ?", (arg.strip().lower(),)).rowcount
        print("supprimé" if n else "introuvable")
    else:
        sys.exit("usage : app.py [serve | count | export | delete <email>]")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "serve":
        admin(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        count()  # crée la base au démarrage
        srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
        print(f"bytetuto-api sur :{PORT} (base {DB_PATH}, compteur affiché dès {COUNTER_MIN})", flush=True)
        srv.serve_forever()
