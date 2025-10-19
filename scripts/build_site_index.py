import argparse
import json
import os
import re
import sqlite3
import unicodedata
from collections import defaultdict


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

STOPWORDS = {
    # Common Albanian function words (normalized: ë->e, ç->c)
    "te", "e", "dhe", "ne", "i", "me", "se", "qe", "u", "per", "a", "nga", "si", "do", "po",
    "ka", "ke", "jam", "je", "eshte", "ishte", "jan", "nuk", "edhe", "por", "qe"
}


def normalize_token(token: str) -> str:
    token = token.lower()
    token = token.replace("ë", "e").replace("ç", "c")
    return token


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def export_strongs_indexes(conn: sqlite3.Connection, out_dir: str) -> None:
    """Export Strong's -> [verse_id] maps for Hebrew (H####) and Greek (G####).
    Writes two files: strongs_H.json and strongs_G.json under out_dir.
    """
    cur = conn.cursor()
    data_h = defaultdict(list)
    data_g = defaultdict(list)

    try:
        rows = cur.execute("SELECT code, verse_id FROM strongs ORDER BY code, verse_id").fetchall()
    except Exception:
        rows = []

    last_code = None
    last_vid = None
    for code, vid in rows:
        if not code or not isinstance(code, str):
            continue
        code = code.strip().upper()
        if not code or len(code) < 2:
            continue
        letter = code[0]
        # dedupe consecutive duplicates
        if last_code == code and last_vid == vid:
            continue
        last_code, last_vid = code, vid
        if letter == 'H':
            data_h[code].append(int(vid))
        elif letter == 'G':
            data_g[code].append(int(vid))

    ensure_dir(out_dir)
    path_h = os.path.join(out_dir, 'strongs_H.json')
    path_g = os.path.join(out_dir, 'strongs_G.json')
    with open(path_h, 'w', encoding='utf-8') as f:
        json.dump({"letter": "H", "version": 1, "index": data_h}, f, ensure_ascii=False)
    with open(path_g, 'w', encoding='utf-8') as f:
        json.dump({"letter": "G", "version": 1, "index": data_g}, f, ensure_ascii=False)


def build_site(db_path: str, out_dir: str, min_len: int = 3, include_stopwords: bool = False) -> None:
    ensure_dir(os.path.join(out_dir, "data", "index"))
    ensure_dir(os.path.join(out_dir, "data", "strongs"))

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Export books (array index book_id-1)
    books = [ENG_TO_ALB.get(name, name) for (name,) in cur.execute("SELECT name FROM books ORDER BY id").fetchall()]
    with open(os.path.join(out_dir, "data", "books.json"), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False)

    # Export verses as array where index = verse_id-1, item = [book_id, chapter, verse, text]
    verses = []
    for vid, bid, chap, ver, text in cur.execute("SELECT id, book_id, chapter, verse, text FROM verses ORDER BY id"):
        # Ensure the list is contiguous up to vid
        while len(verses) < vid - 1:
            verses.append(None)
        verses.append([bid, chap, ver, unicodedata.normalize("NFC", text)])
    with open(os.path.join(out_dir, "data", "verses.json"), "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False)

    # Build token -> unique verse_ids, sharded by first letter
    shards = {chr(c): {} for c in range(ord('a'), ord('z') + 1)}
    other = {}
    last_tok = None
    last_list = None

    for norm, vid in cur.execute("SELECT normalized, verse_id FROM tokens ORDER BY normalized, verse_id"):
        if len(norm) < min_len:
            continue
        if not include_stopwords and norm in STOPWORDS:
            continue
        if norm != last_tok:
            # finalize previous (noop here)
            last_tok = norm
            # pick shard
            first = norm[0]
            target = shards.get(first, other)
            lst = []
            target[norm] = lst
            last_list = lst
        # dedupe consecutive verse_ids
        if not last_list or last_list[-1] != vid:
            last_list.append(vid)

    # Write shards
    idx_dir = os.path.join(out_dir, "data", "index")
    for letter, mapping in shards.items():
        with open(os.path.join(idx_dir, f"index_{letter}.json"), "w", encoding="utf-8") as f:
            json.dump({"letter": letter, "version": 1, "tokens": mapping}, f, ensure_ascii=False)
    if other:
        with open(os.path.join(idx_dir, f"index_other.json"), "w", encoding="utf-8") as f:
            json.dump({"letter": "other", "version": 1, "tokens": other}, f, ensure_ascii=False)

    # Optional: export Strong's -> verse IDs for instant Hebrew/Greek lookup
    try:
        has_strongs = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strongs'").fetchone()
    except Exception:
        has_strongs = None
    if has_strongs:
        try:
            export_strongs_indexes(conn, os.path.join(out_dir, "data", "strongs"))
        except Exception:
            # Do not fail site build if strongs export fails
            pass


def main():
    ap = argparse.ArgumentParser(description="Build static site JSON (indexes + verses) for GitHub Pages")
    ap.add_argument("--db", default="alb_concordance.sqlite", help="Path to SQLite DB")
    ap.add_argument("--out", default="site", help="Output site directory (default: site)")
    ap.add_argument("--min-len", type=int, default=3, help="Minimum word length to include in index")
    ap.add_argument("--include-stopwords", action="store_true", help="Include stopwords in index")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"Database not found: {args.db}. Build it first with: python scripts/build_concordance.py build")

    build_site(args.db, args.out, min_len=args.min_len, include_stopwords=args.include_stopwords)
    print("Static site data built in:", args.out)


if __name__ == "__main__":
    main()
