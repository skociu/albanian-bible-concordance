import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode
import os
import re
import sqlite3
import unicodedata
import base64

_RE_STRONGS = re.compile(r"^[HG]\d{4}$", re.IGNORECASE)


ENG_TO_ALB = {
    "Genesis": "Zanafilla",
    "Exodus": "Eksodi",
    "Leviticus": "Levitiku",
    "Numbers": "Numrat",
    "Deuteronomy": "Ligji i Përtërirë",
    "Joshua": "Jozueu",
    "Judges": "Gjyqtarët",
    "Ruth": "Ruthi",
    "I Samuel": "1 i Samuelit",
    "II Samuel": "2 i Samuelit",
    "I Kings": "1 i Mbretërve",
    "II Kings": "2 i Mbretërve",
    "I Chronicles": "1 i Kronikave",
    "II Chronicles": "2 i Kronikave",
    "Ezra": "Ezra",
    "Nehemiah": "Nehemia",
    "Esther": "Estera",
    "Job": "Jobi",
    "Psalms": "Psalmet",
    "Proverbs": "Fjalët e Urta",
    "Ecclesiastes": "Predikuesi",
    "Song of Solomon": "Kënga e Këngëve",
    "Isaiah": "Isaia",
    "Jeremiah": "Jeremia",
    "Lamentations": "Vajtimet",
    "Ezekiel": "Ezekieli",
    "Daniel": "Danieli",
    "Hosea": "Osea",
    "Joel": "Joeli",
    "Amos": "Amosi",
    "Obadiah": "Abdia",
    "Jonah": "Jona",
    "Micah": "Mika",
    "Nahum": "Nahumi",
    "Habakkuk": "Habakuku",
    "Zephaniah": "Sofonia",
    "Haggai": "Hagaiu",
    "Zechariah": "Zakaria",
    "Malachi": "Malakia",
    "Matthew": "Mateu",
    "Mark": "Marku",
    "Luke": "Luka",
    "John": "Gjoni",
    "Acts": "Veprat e Apostujve",
    "Romans": "Romakëve",
    "I Corinthians": "1 Korintasve",
    "II Corinthians": "2 Korintasve",
    "Galatians": "Galatasve",
    "Ephesians": "Efesianëve",
    "Philippians": "Filipianëve",
    "Colossians": "Kolosianëve",
    "I Thessalonians": "1 Thesalonikasve",
    "II Thessalonians": "2 Thesalonikasve",
    "I Timothy": "1 Timoteut",
    "II Timothy": "2 Timoteut",
    "Titus": "Titit",
    "Philemon": "Filemonit",
    "Hebrews": "Hebrenjve",
    "James": "Jakobi",
    "I Peter": "1 Pjetrit",
    "II Peter": "2 Pjetrit",
    "I John": "1 Gjonit",
    "II John": "2 Gjonit",
    "III John": "3 Gjonit",
    "Jude": "Juda",
    "Revelation of John": "Zbulesa e Gjonit",
}

def map_book(name: str) -> str:
    return ENG_TO_ALB.get(name, name)

def fix_encoding_artifacts(text: str) -> str:
    text = text.replace("eI^", "ë").replace("EI^", "Ë")
    text = re.sub(r"cI\x15", "ç", text)
    text = re.sub(r"CI\x15", "Ç", text)
    text = text.replace("I^", "").replace("\x15", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_token(token: str) -> str:
    token = token.lower()
    token = token.replace("ë", "e").replace("ç", "c")
    return token


def tokenize(clean_text: str):
    return re.findall(r"[A-Za-zËÇëç]+", clean_text)


def highlight_text(text: str, query: str) -> str:
    norm_q = normalize_token(fix_encoding_artifacts(query))
    s = unicodedata.normalize("NFC", text)
    out = []
    last = 0
    for m in re.finditer(r"[A-Za-zËÇëç]+", s):
        start, end = m.span()
        tok = m.group(0)
        norm_tok = normalize_token(tok)
        out.append(s[last:start])
        if norm_tok == norm_q:
            out.append(f"<mark>{tok}</mark>")
        else:
            out.append(tok)
        last = end
    out.append(s[last:])
    return "".join(out)


BASE_STYLE = """
<style>
body { font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 1.5rem; }
header { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }
header .brand { display:flex; align-items:center; gap:.6rem; }
/* hero image below header */
.hero { margin: 10px 0 12px; }
.hero-image { display:block; width:100%; max-width:300px; height:auto; border-radius:8px; }
/* intro layout */
.intro-row { display:flex; align-items:flex-start; gap:1rem; margin:.5rem 0 1rem; }
.intro-left { flex:0 0 auto; }
.intro-right { flex:1 1 auto; }
header a { text-decoration:none; color:#444; }
input[type=text] { padding:.4rem .6rem; font-size:1rem; width: min(550px, 90vw); }
button, input[type=submit] { padding:.45rem .7rem; font-size:1rem; }
.res { margin:.35rem 0; line-height:1.55; }
mark { background:#fff3a3; }
nav { margin:.5rem 0 1rem; color:#666; font-size:.95rem; }
.books a, .chapters a { display:inline-block; padding:.2rem .45rem; margin:.15rem; background:#f4f4f4; border-radius:4px; color:#333; text-decoration:none; }
.books a:hover, .chapters a:hover { background:#e9e9e9; }
.muted { color:#777; }
footer { margin-top:2rem; color:#777; font-size:.9rem; }
@media print { header, nav, footer, .controls { display:none; } body { margin:.5in; } }
/* Strong's highlight chip */
.tag { display:inline-block; margin-left:.35rem; padding:.05rem .35rem; border-radius:4px; font-size:.9em; color:#234; background:#eaf4ff; border:1px solid #d6e9ff; }
.tag.strongs mark { background:#cfe8ff; padding:0 .15rem; }
</style>
"""


class App:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

    def books(self):
        rows = self.conn.execute("SELECT id, name FROM books ORDER BY id").fetchall()
        return [(bid, map_book(name)) for (bid, name) in rows]

    def max_chapter(self, book_id: int) -> int:
        r = self.conn.execute("SELECT MAX(chapter) FROM verses WHERE book_id=?", (book_id,)).fetchone()
        return int(r[0] or 0)

    def verses_in_chapter(self, book_id: int, chap: int):
        return self.conn.execute(
            "SELECT v.text, v.verse, b.name FROM verses v JOIN books b ON b.id=v.book_id WHERE v.book_id=? AND v.chapter=? ORDER BY v.verse",
            (book_id, chap),
        ).fetchall()

    def search(self, q: str, limit: int = 100):
        norm = normalize_token(fix_encoding_artifacts(q))
        return self.conn.execute(
            """
            SELECT b.name, v.book_id, v.chapter, v.verse, v.text
            FROM tokens t
            JOIN verses v ON v.id = t.verse_id
            JOIN books b ON b.id = v.book_id
            WHERE t.normalized = ?
            GROUP BY v.id
            ORDER BY v.book_id, v.chapter, v.verse
            LIMIT ?
            """,
            (norm, limit),
        ).fetchall()

    def search_strongs_with_count(self, code: str, limit: int = 100, offset: int = 0):
        code = (code or '').strip().upper()
        if not _RE_STRONGS.match(code):
            return []
        try:
            return self.conn.execute(
                """
                SELECT b.name, v.book_id, v.chapter, v.verse, v.text, COUNT(*) as cnt
                FROM strongs s
                JOIN verses v ON v.id = s.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE s.code = ?
                GROUP BY v.id
                ORDER BY v.book_id, v.chapter, v.verse
                LIMIT ? OFFSET ?
                """,
                (code, limit, offset),
            ).fetchall()
        except Exception:
            return []

    def count_strongs(self, code: str) -> int:
        code = (code or '').strip().upper()
        if not _RE_STRONGS.match(code):
            return 0
        try:
            r = self.conn.execute("SELECT COUNT(DISTINCT verse_id) FROM strongs WHERE code=?", (code,)).fetchone()
            return int(r[0] or 0)
        except Exception:
            return 0

    def search_strongs(self, code: str, limit: int = 100, offset: int = 0):
        code = (code or '').strip().upper()
        if not _RE_STRONGS.match(code):
            return []
        try:
            return self.conn.execute(
                """
                SELECT b.name, v.book_id, v.chapter, v.verse, v.text
                FROM strongs s
                JOIN verses v ON v.id = s.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE s.code = ?
                GROUP BY v.id
                ORDER BY v.book_id, v.chapter, v.verse
                LIMIT ? OFFSET ?
                """,
                (code, limit, offset),
            ).fetchall()
        except Exception:
            return []


def html_page(title: str, body: str) -> bytes:
    doc = f"<!doctype html><meta charset='utf-8'><title>{title}</title>{BASE_STYLE}{body}"
    return doc.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    app: App = None  # set at server start
    logo_data_uri: str = None  # set at server start

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path

        if path in ("/", "/index"):
            self.respond_index()
        elif path == "/books":
            self.respond_books()
        elif path == "/chapter":
            self.respond_chapter(qs)
        elif path == "/search":
            self.respond_search_paged(qs)
        elif path == "/export":
            self.respond_export(qs)
        else:
            self.send_error(404, "Not Found")

    def respond_index(self):
        logo = self.logo_data_uri
        brand = "<div class='brand'><a href='/'><strong>Albanian Concordance</strong></a></div>"
        left = f"<div class='intro-left'><img class='hero-image' src='{logo}' alt='Albanian Concordance'/></div>" if logo else ""
        right = (
            "<div class='intro-right'>"
            + "<nav class='muted'>Search a word (accent-insensitive, e.g., 'dashuri')</nav>"
            + "<form method='get' action='/search'><input type='text' name='q' placeholder='Kerko fjalen...' autofocus><input type='submit' value='Search'></form>"
            + "</div>"
        )
        row = f"<div class='intro-row'>{left}{right}</div>"
        body = [
            f"<header>{brand}<a href='/books'>Books</a></header>",
            row,
            "<footer class='muted'>Use Export to save results for printing.</footer>",
        ]
        self.respond_html("Concordance", "\n".join(body))

    def respond_books(self):
        books = self.app.books()
        items = []
        for bid, name in books:
            items.append(f"<a href='/chapter?book_id={bid}&chap=1'>{name}</a>")
        brand = "<div class='brand'><a href='/'><strong>Albanian Concordance</strong></a></div>"
        body = [
            f"<header>{brand}<span class='muted'>Books</span></header>",
            f"<div class='books'>{''.join(items)}</div>",
        ]
        self.respond_html("Books", "\n".join(body))

    def respond_chapter(self, qs):
        try:
            bid = int(qs.get("book_id", [""])[0])
            chap = int(qs.get("chap", [""])[0])
        except Exception:
            self.send_error(400, "Invalid book_id/chap")
            return
        verses = self.app.verses_in_chapter(bid, chap)
        maxc = self.app.max_chapter(bid)
        nav = []
        for c in range(1, maxc + 1):
            if c == chap:
                nav.append(f"<strong>{c}</strong>")
            else:
                nav.append(f"<a href='/chapter?book_id={bid}&chap={c}'>{c}</a>")
        lines = []
        for text, vno, bname in verses:
            t = unicodedata.normalize("NFC", text)
            lines.append(f"<div class='res'><strong>{map_book(bname)} {chap}:{vno}</strong> — {t}</div>")
        brand = "<div class='brand'><a href='/'><strong>Albanian Concordance</strong></a></div>"
        body = [
            f"<header>{brand}<a href='/books'>Books</a></header>",
            f"<nav class='chapters'>{' '.join(nav)}</nav>",
            "\n".join(lines) or "<p class='muted'>No verses.</p>",
        ]
        self.respond_html("Chapter", "\n".join(body))

    def respond_search_paged(self, qs):
        q = (qs.get("q", [""])[0] or "").strip()
        if not q:
            self.redirect("/")
            return
        # paging params
        try:
            limit = int(qs.get("limit", ["100"])[0])
        except Exception:
            limit = 100
        try:
            page = int(qs.get("page", ["1"])[0])
        except Exception:
            page = 1
        if limit < 1:
            limit = 100
        if page < 1:
            page = 1

        # total results (Strong's vs Albanian word)
        is_strongs = _RE_STRONGS.match(q.upper()) is not None
        if is_strongs:
            total = self.app.count_strongs(q)
        else:
            conn = self.app.conn
            cur = conn.cursor()
            norm = normalize_token(fix_encoding_artifacts(q))
            total = cur.execute(
                """
                SELECT COUNT(*) FROM (
                  SELECT v.id
                  FROM tokens t
                  JOIN verses v ON v.id = t.verse_id
                  WHERE t.normalized = ?
                  GROUP BY v.id
                )
                """,
                (norm,),
            ).fetchone()[0]

        total_pages = max(1, (total + limit - 1) // limit)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        # fetch page
        if is_strongs:
            rows = self.app.search_strongs_with_count(q, limit=limit, offset=offset)
        else:
            conn = self.app.conn
            cur = conn.cursor()
            norm = normalize_token(fix_encoding_artifacts(q))
            rows = cur.execute(
                """
                SELECT b.name, v.book_id, v.chapter, v.verse, v.text
                FROM tokens t
                JOIN verses v ON v.id = t.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE t.normalized = ?
                GROUP BY v.id
                ORDER BY v.book_id, v.chapter, v.verse
                LIMIT ? OFFSET ?
                """,
                (norm, limit, offset),
            ).fetchall()

        items = []
        if is_strongs:
            Q = q.upper()
            for row in rows:
                # rows: (book, bid, chap, ver, text, cnt)
                book, bid, chap, ver, text, cnt = row
                safe = unicodedata.normalize('NFC', text)
                chip = f"<span class='tag strongs'>Strong's <mark>{Q}</mark> x {int(cnt or 1)}</span>"
                items.append(f"<div class='res'><strong>{book} {chap}:{ver}</strong> {chip} - {safe}</div>")
        else:
            for book, bid, chap, ver, text in rows:
                h = highlight_text(text, q)
                items.append(f"<div class='res'><strong>{book} {chap}:{ver}</strong> - {h}</div>")

        # header + pagination controls (no logo in header)
        brand = "<div class='brand'><a href='/'><strong>Albanian Concordance</strong></a></div>"

        base = {'q': q, 'limit': str(limit)}
        try:
            # Python 3.11 supports dict unpack in f-strings context as below using explicit dict()
            first_url = f"/search?{urlencode(dict(list(base.items()) + [('page','1')]))}"
            prev_url = f"/search?{urlencode(dict(list(base.items()) + [('page', str(page-1))]))}" if page > 1 else None
            next_url = f"/search?{urlencode(dict(list(base.items()) + [('page', str(page+1))]))}" if page < total_pages else None
            last_url = f"/search?{urlencode(dict(list(base.items()) + [('page', str(total_pages))]))}"
        except Exception:
            # fallback
            from urllib.parse import urlencode as _ue
            first_url = f"/search?{_ue({'q': q, 'limit': str(limit), 'page': '1'})}"
            prev_url = f"/search?{_ue({'q': q, 'limit': str(limit), 'page': str(page-1)})}" if page > 1 else None
            next_url = f"/search?{_ue({'q': q, 'limit': str(limit), 'page': str(page+1)})}" if page < total_pages else None
            last_url = f"/search?{_ue({'q': q, 'limit': str(limit), 'page': str(total_pages)})}"

        nav = []
        nav.append(f"<a href='{first_url}'>First</a>")
        if prev_url:
            nav.append(f"<a href='{prev_url}'>Prev</a>")
        nav.append(f"<span class='muted'>Page {page} of {total_pages} — {total} verses</span>")
        if next_url:
            nav.append(f"<a href='{next_url}'>Next</a>")
        nav.append(f"<a href='{last_url}'>Last</a>")

        export_link = f"/export?{urlencode({'q': q, 'format':'html', 'limit': str(total)})}"
        body = [
            f"<header>{brand}<a href='/books'>Books</a></header>",
            f"<nav class='controls'>{' | '.join(nav)} | <a href='{export_link}'>Export all (HTML)</a></nav>",
            ("\n".join(items) if items else "<p class='muted'>No results.</p>"),
        ]
        self.respond_html(f"Search: {q}", "\n".join(body))

    def respond_search(self, qs):
        q = (qs.get("q", [""])[0] or "").strip()
        if not q:
            self.redirect("/")
            return
        try:
            limit = int(qs.get("limit", ["100"])[0])
        except Exception:
            limit = 100
        # Strong's export: return Albanian verses for occurrences
        if _RE_STRONGS.match(q.upper()):
            rows = self.app.search_strongs(q, limit=limit, offset=0)
        else:
            rows = self.app.search(q, limit=limit)
        items = []
        for book, bid, chap, ver, text in rows:
            h = highlight_text(text, q)
            items.append(f"<div class='res'><strong>{book} {chap}:{ver}</strong> — {h}</div>")
        export_link = f"/export?{urlencode({'q': q, 'format':'html', 'limit': str(limit)})}"
        body = [
            f"<header><a href='/'>Albanian Concordance</a> | <a href='/books'>Books</a> | Results for “{q}”</header>",
            f"<nav class='controls'><a href='{export_link}'>Export HTML</a> · <a href='/export?{urlencode({'q': q, 'format':'txt', 'limit': str(limit)})}'>TXT</a> · <a href='/export?{urlencode({'q': q, 'format':'csv', 'limit': str(limit)})}'>CSV</a></nav>",
            "\n".join(items) or "<p class='muted'>No results.</p>",
        ]
        self.respond_html(f"Search: {q}", "\n".join(body))

    def respond_export(self, qs):
        q = (qs.get("q", [""])[0] or "").strip()
        fmt = (qs.get("format", ["html"])[0] or "html").lower()
        try:
            limit = int(qs.get("limit", ["1000"])[0])
        except Exception:
            limit = 1000
        rows = self.app.search(q, limit=limit)
        if fmt == "txt":
            content = [f"Results for '{q}' ({len(rows)} verses)"]
            for book, _, chap, ver, text in rows:
                content.append(f"- {book} {chap}:{ver} - {unicodedata.normalize('NFC', text)}")
            data = ("\n".join(content) + "\n").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename=search_{sanitize_name(q)}.txt")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if fmt == "csv":
            # Simple CSV; escape commas by quoting with double quotes
            lines = ["book,chapter,verse,text"]
            for book, _, chap, ver, text in rows:
                t = unicodedata.normalize('NFC', text).replace('"', '""')
                lines.append(f'"{book}",{chap},{ver},"{t}"')
            data = ("\n".join(lines) + "\n").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename=search_{sanitize_name(q)}.csv")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # HTML
        items = []
        for book, _, chap, ver, text in rows:
            h = highlight_text(text, q)
            items.append(f"<div class='res'><strong>{book} {chap}:{ver}</strong> — {h}</div>")
        body = [
            f"<h1>Results for “{q}”</h1>",
            f"<div class='muted'>{len(rows)} verses</div>",
            "\n".join(items)
        ]
        data = html_page(f"Export {q}", "\n".join(body))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename=search_{sanitize_name(q)}.html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_html(self, title: str, body: str):
        data = html_page(title, body)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, to: str):
        self.send_response(302)
        self.send_header("Location", to)
        self.end_headers()


def sanitize_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("._") or "export"


def main():
    ap = argparse.ArgumentParser(description="Minimal web UI for Albanian Bible concordance")
    ap.add_argument("--db", default="alb_concordance.sqlite", help="Path to SQLite DB")
    ap.add_argument("--host", default="127.0.0.1", help="Listen host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8000, help="Listen port (default 8000)")
    ap.add_argument("--logo", help="Path to a logo image (jpg/png) to show in header")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"Database not found: {args.db}. Build it first with: python scripts/build_concordance.py build")

    # Optional logo as data URI so no static route is needed
    # If --logo not provided, try the static site copy relative to this file
    logo_data_uri = None
    try:
        if args.logo:
            candidate = args.logo
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.abspath(os.path.join(here, "..", "site", "images", "albanian-concordance-image.jpg"))
        if candidate and os.path.exists(candidate):
            with open(candidate, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            ext = os.path.splitext(candidate)[1].lower()
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else ("image/png" if ext == ".png" else "application/octet-stream")
            logo_data_uri = f"data:{mime};base64,{b64}"
            try:
                print(f"Loaded hero image: {candidate}")
            except Exception:
                pass
    except Exception as e:
        try:
            print(f"Hero image load error: {e}")
        except Exception:
            pass
        logo_data_uri = None

    Handler.app = App(args.db)
    Handler.logo_data_uri = logo_data_uri
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving on http://{args.host}:{args.port} (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
