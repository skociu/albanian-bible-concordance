import argparse
import os
import re
import sqlite3
from typing import Dict, Iterable, List, Tuple
import unicodedata
import csv
import json

# English → Albanian book name mapping
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


SQL_LINE_BOOK = re.compile(r"INSERT INTO `Alb_books` \(`name`\) VALUES \('(.+?)'\);")
SQL_LINE_VERSE = re.compile(
    r"INSERT INTO `Alb_verses` \(`book_id`, `chapter`, `verse`, `text`\) VALUES \((\d+),\s*(\d+),\s*(\d+),\s*'((?:[^'\\]|\\.)*)'\);"
)


def unescape_sql_string(s: str) -> str:
    # Handle common SQL single-quoted string escapes
    # Replace escaped backslash first
    s = s.replace("\\\\", "\\")
    # Replace escaped single quote
    s = s.replace("\\'", "'")
    # Replace escaped double quote
    s = s.replace('\"', '"')
    # Replace escaped newline/tab just in case
    s = s.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    return s


def fix_encoding_artifacts(text: str) -> str:
    # The source text contains artifacts like 'eI^' for 'ë' and 'cI\x15' for 'ç'.
    # Normalize the most common patterns and strip leftover markers.
    # Map 'eI^' -> 'ë' (lowercase) and 'EI^' -> 'Ë' (uppercase)
    text = text.replace("eI^", "ë").replace("EI^", "Ë")

    # Replace 'cI\x15' and 'CI\x15' with 'ç'/'Ç'
    text = re.sub(r"cI\x15", "ç", text)
    text = re.sub(r"CI\x15", "Ç", text)

    # In case there are stray markers left, drop them
    text = text.replace("I^", "")
    text = text.replace("\x15", "")

    # Collapse excess whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_token(token: str) -> str:
    # Lower-case and strip Albanian diacritics so searches are accent-insensitive
    token = token.lower()
    token = token.replace("ë", "e").replace("ç", "c")
    return token


def tokenize(clean_text: str) -> List[str]:
    # Normalize to NFC to avoid combining marks splitting tokens (e + ◌̈)
    clean_text = unicodedata.normalize("NFC", clean_text)
    # Extract word-like tokens including Albanian letters, after cleanup
    return re.findall(r"[A-Za-zËÇëç]+", clean_text)


def parse_sql_dump(sql_path: str) -> Tuple[List[str], List[Tuple[int, int, int, str]]]:
    books: List[str] = []
    verses: List[Tuple[int, int, int, str]] = []  # (book_id, chapter, verse, text)

    with open(sql_path, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            m_book = SQL_LINE_BOOK.match(line)
            if m_book:
                en = m_book.group(1)
                books.append(ENG_TO_ALB.get(en, en))
                continue

            m_verse = SQL_LINE_VERSE.match(line)
            if m_verse:
                book_id = int(m_verse.group(1))
                chapter = int(m_verse.group(2))
                verse_no = int(m_verse.group(3))
                text_sql = m_verse.group(4)
                text = unescape_sql_string(text_sql)
                text = fix_encoding_artifacts(text)
                text = unicodedata.normalize("NFC", text)
                verses.append((book_id, chapter, verse_no, text))
                continue

    return books, verses


def init_db(db_path: str) -> sqlite3.Connection:
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    # Speed-focused PRAGMAs for bulk load (sacrifice durability during build)
    conn.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA locking_mode=EXCLUSIVE;
        PRAGMA cache_size=-200000; -- ~200k pages in memory if available
        PRAGMA foreign_keys=OFF;
        """
    )
    # Schema
    conn.executescript(
        """
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE verses (
            id INTEGER PRIMARY KEY,
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(book_id) REFERENCES books(id)
        );

        CREATE TABLE tokens (
            id INTEGER PRIMARY KEY,
            verse_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            token TEXT NOT NULL,
            normalized TEXT NOT NULL,
            FOREIGN KEY(verse_id) REFERENCES verses(id)
        );

        CREATE INDEX idx_verses_bcv ON verses(book_id, chapter, verse);
        CREATE INDEX idx_tokens_norm ON tokens(normalized);
        CREATE INDEX idx_tokens_verse ON tokens(verse_id);
        """
    )
    # Re-enable FKs after schema creation
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def ensure_strongs_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS strongs (
            id INTEGER PRIMARY KEY,
            verse_id INTEGER NOT NULL,
            code TEXT NOT NULL,  -- e.g., H07225, G3056
            FOREIGN KEY(verse_id) REFERENCES verses(id)
        );
        CREATE INDEX IF NOT EXISTS idx_strongs_code ON strongs(code);
        CREATE INDEX IF NOT EXISTS idx_strongs_verse ON strongs(verse_id);
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_strongs_verse_code ON strongs(verse_id, code);
        """
    )


def insert_books(conn: sqlite3.Connection, books: List[str]) -> None:
    conn.executemany("INSERT INTO books(id, name) VALUES (?, ?)", [(i + 1, name) for i, name in enumerate(books)])


def insert_verses(conn: sqlite3.Connection, verses: List[Tuple[int, int, int, str]]) -> None:
    conn.executemany(
        "INSERT INTO verses(book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
        [(b, c, v, t) for (b, c, v, t) in verses],
    )


def build_tokens(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT id, text FROM verses ORDER BY id")
    to_insert: List[Tuple[int, int, str, str]] = []  # (verse_id, position, token, normalized)
    for verse_id, vtext in cur.fetchall():
        toks = tokenize(vtext)
        for pos, tok in enumerate(toks, start=1):
            to_insert.append((verse_id, pos, tok, normalize_token(tok)))
    conn.executemany(
        "INSERT INTO tokens(verse_id, position, token, normalized) VALUES (?, ?, ?, ?)",
        to_insert,
    )
    return len(to_insert)


def cmd_build(args: argparse.Namespace) -> None:
    sql_path = args.sql
    db_path = args.db
    print(f"Parsing SQL from {sql_path} ...")
    books, verses = parse_sql_dump(sql_path)
    print(f"Found {len(books)} books and {len(verses)} verses.")

    print(f"Initializing database at {db_path} ...")
    conn = init_db(db_path)
    with conn:
        insert_books(conn, books)
        insert_verses(conn, verses)
        token_count = build_tokens(conn)
    print(f"Inserted tokens: {token_count}")
    print("Done.")


# ---------- Strong's (Hebrew/Greek) indexing from site/data ----------

_RE_STRONGS = re.compile(r"^[HG]\d{4}$", re.IGNORECASE)


def _norm_name(s: str) -> str:
    try:
        s = unicodedata.normalize('NFD', s or '')
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    except Exception:
        pass
    out = []
    for ch in (s or '').lower():
        if ch.isalnum() or ch.isspace():
            out.append(ch)
    return ' '.join(''.join(out).split())


def load_book_name_to_id(conn: sqlite3.Connection) -> Dict[str, int]:
    m: Dict[str, int] = {}
    for bid, name in conn.execute("SELECT id, name FROM books").fetchall():
        raw = (name or '').strip()
        m[raw] = bid
        m[_norm_name(raw)] = bid
    return m


def iter_chapter_json(site_dir: str):
    data_root = os.path.join(site_dir, 'data')
    if not os.path.isdir(data_root):
        return
    for sub in os.listdir(data_root):
        subdir = os.path.join(data_root, sub)
        if not os.path.isdir(subdir):
            continue
        for fname in os.listdir(subdir):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(subdir, fname)
            # skip large global files
            base = os.path.basename(path).lower()
            if base in ('books.json', 'verses.json'):
                continue
            yield path


def build_strongs_index(conn: sqlite3.Connection, site_dir: str) -> int:
    ensure_strongs_schema(conn)
    book_name_to_id = load_book_name_to_id(conn)
    cur = conn.cursor()
    inserted = 0
    batch: List[Tuple[int, str]] = []

    def flush():
        nonlocal batch, inserted
        if not batch:
            return
        cur.executemany("INSERT OR IGNORE INTO strongs(verse_id, code) VALUES (?, ?)", batch)
        inserted += len(batch)
        batch = []

    for path in iter_chapter_json(site_dir):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                obj = json.load(f)
        except Exception:
            continue
        ref = obj.get('ref') or {}
        book_sq = (ref.get('book_sq') or '').strip()
        chapter = int(ref.get('chapter') or 0)
        if not book_sq or not chapter:
            continue
        bid = book_name_to_id.get(book_sq) or book_name_to_id.get(_norm_name(book_sq))
        if not bid:
            # fallback: try partials
            bid = book_name_to_id.get(_norm_name(book_sq).split(' ')[0] or '')
        if not bid:
            continue
        verses = obj.get('verses') or []
        for v in verses:
            vnum = int(v.get('v') or 0)
            if not vnum:
                continue
            # lookup verse_id
            row = cur.execute("SELECT id FROM verses WHERE book_id=? AND chapter=? AND verse=?", (bid, chapter, vnum)).fetchone()
            if not row:
                continue
            vid = int(row[0])
            for tok in (v.get('src') or []):
                code = (tok.get('s') or '').strip().upper()
                if not code or not _RE_STRONGS.match(code):
                    continue
                batch.append((vid, code))
            if len(batch) >= 5000:
                flush()
    flush()
    conn.commit()
    return inserted


def cmd_build_strongs(args: argparse.Namespace) -> None:
    db_path = args.db
    site_dir = args.site
    if not os.path.exists(db_path):
        raise SystemExit(f"Database not found: {args.db}. Build it first with: python scripts/build_concordance.py build")
    if not os.path.isdir(site_dir):
        raise SystemExit(f"Site directory not found: {site_dir}")
    conn = sqlite3.connect(db_path)
    with conn:
        ensure_strongs_schema(conn)
        # Use INSERT OR IGNORE semantics; table can be rebuilt by clearing it
        created = build_strongs_index(conn, site_dir)
    print(f"Indexed Strong's occurrences: ~{created} rows (duplicates ignored)")


def search_lemma(conn: sqlite3.Connection, word: str, limit: int = 50) -> List[Tuple[str, int, int, int, str]]:
    norm = normalize_token(fix_encoding_artifacts(word))
    rows = conn.execute(
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
    return rows


def search_strongs(conn: sqlite3.Connection, code: str, limit: int = 200) -> List[Tuple[str, int, int, int, str]]:
    code = (code or '').strip().upper()
    if not _RE_STRONGS.match(code):
        return []
    rows = conn.execute(
        """
        SELECT b.name, v.book_id, v.chapter, v.verse, v.text
        FROM strongs s
        JOIN verses v ON v.id = s.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE s.code = ?
        GROUP BY v.id
        ORDER BY v.book_id, v.chapter, v.verse
        LIMIT ?
        """,
        (code, limit),
    ).fetchall()
    return rows


def cmd_search(args: argparse.Namespace) -> None:
    db_path = args.db
    word = args.word
    limit = args.limit
    conn = sqlite3.connect(db_path)
    # If query looks like a Strong's code (H####/G####), run Strong's search
    if _RE_STRONGS.match((word or '').strip().upper()):
        res = search_strongs(conn, word, limit=limit)
    else:
        res = search_lemma(conn, word, limit=limit)
    if not res:
        print("No results.")
        return
    print(f"Results for '{word}' ({len(res)} verses):")
    for book_name, book_id, chap, verse_no, text in res:
        safe_text = unicodedata.normalize("NFC", text)
        print(f"- {book_name} {chap}:{verse_no} – {safe_text}")


def highlight_text(text: str, query: str) -> str:
    # Highlight tokens matching the normalized query using <mark>
    norm_q = normalize_token(fix_encoding_artifacts(query))
    s = text
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


def ensure_exports_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def sanitize_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("._") or "export"


def export_search(conn: sqlite3.Connection, word: str, fmt: str, out_path: str, limit: int = 1000) -> str:
    if _RE_STRONGS.match((word or '').strip().upper()):
        rows = search_strongs(conn, word, limit=limit)
    else:
        rows = search_lemma(conn, word, limit=limit)
    ensure_exports_dir(out_path)
    if fmt == "txt":
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"Results for '{word}' ({len(rows)} verses)\n")
            for book, _, chap, ver, text in rows:
                f.write(f"- {book} {chap}:{ver} - {text}\n")
    elif fmt == "csv":
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["book", "chapter", "verse", "text"]) 
            for book, _, chap, ver, text in rows:
                w.writerow([book, chap, ver, unicodedata.normalize("NFC", text)])
    else:  # html
        style = """
        <style>
        body { font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 2rem; }
        h1 { font-size: 1.4rem; }
        .meta { color: #666; margin-bottom: 1rem; }
        .result { margin: 0.5rem 0; line-height: 1.5; }
        mark { background: #fff3a3; }
        @media print { 
          a { text-decoration: none; color: #000; }
          .meta, .controls { display: none; }
          body { margin: 0.5in; }
        }
        </style>
        """
        html = ["<!doctype html><meta charset='utf-8'>", style, f"<h1>Results for “{word}”</h1>"]
        html.append(f"<div class='meta'>{len(rows)} verses</div>")
        for book, _, chap, ver, text in rows:
            h = highlight_text(unicodedata.normalize("NFC", text), word)
            html.append(f"<div class='result'><strong>{book} {chap}:{ver}</strong> — {h}</div>")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
    return out_path


def cmd_export(args: argparse.Namespace) -> None:
    db_path = args.db
    word = args.word
    fmt = args.format
    limit = args.limit
    out = args.out
    if not out:
        base = sanitize_name(word)
        ext = fmt
        out = os.path.join("exports", f"search_{base}.{ext}")
    conn = sqlite3.connect(db_path)
    path = export_search(conn, word, fmt, out, limit=limit)
    print(f"Exported {fmt} -> {path}")


def cmd_top(args: argparse.Namespace) -> None:
    db_path = args.db
    limit = args.limit
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT normalized, COUNT(*) as cnt
        FROM tokens
        GROUP BY normalized
        HAVING cnt > 1
        ORDER BY cnt DESC, normalized ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    for norm, cnt in rows:
        print(f"{norm}\t{cnt}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build and query an Albanian Bible concordance (SQLite)")
    p.add_argument("command", choices=["build", "build-strongs", "search", "top", "export"], help="Action to run")
    p.add_argument("word", nargs="?", help="Word to search (for 'search')")
    p.add_argument("--sql", default="Alb.sql.txt", help="Path to source SQL dump (default: Alb.sql.txt)")
    p.add_argument("--db", default="alb_concordance.sqlite", help="Output SQLite DB path (default: alb_concordance.sqlite)")
    p.add_argument("--limit", type=int, default=50, help="Limit results for listing/search")
    p.add_argument("--format", choices=["html", "txt", "csv"], default="html", help="Export format (for 'export')")
    p.add_argument("--out", help="Output file path (for 'export')")
    p.add_argument("--site", default="site", help="Path to static site root (for 'build-strongs')")
    return p


def main() -> None:
    p = build_arg_parser()
    args = p.parse_args()
    if args.command == "build":
        cmd_build(args)
    elif args.command == "build-strongs":
        cmd_build_strongs(args)
    elif args.command == "search":
        if not args.word:
            print("Please provide a word to search.")
            return
        cmd_search(args)
    elif args.command == "top":
        cmd_top(args)
    elif args.command == "export":
        if not args.word:
            print("Please provide a word to export.")
            return
        cmd_export(args)


if __name__ == "__main__":
    main()
