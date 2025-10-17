import sqlite3
import os

def inspect(db_path: str, norm: str = "perendia"):
    if not os.path.exists(db_path):
        print(db_path, "missing")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        total_tokens = cur.execute("select count(*) from tokens where normalized=?", (norm,)).fetchone()[0]
        total_verses = cur.execute("select count(distinct verse_id) from tokens where normalized=?", (norm,)).fetchone()[0]
        variants = {}
        for f in ["perendi","perendine","perendise","perendin","perendinë","perëndia","perëndi","perëndisë","perëndinë"]:
            variants[f] = cur.execute("select count(distinct verse_id) from tokens where normalized=?", (f.lower().replace("ë","e").replace("ç","c"),)).fetchone()[0]
        print({
            "db": db_path,
            "norm": norm,
            "tokens": total_tokens,
            "verses": total_verses,
            "variants": variants,
        })
        rows = cur.execute(
            """
            select b.name, v.chapter, v.verse, v.text
            from tokens t
            join verses v on v.id = t.verse_id
            join books b on b.id = v.book_id
            where t.normalized = ?
            group by v.id
            order by v.book_id, v.chapter, v.verse
            limit 5
            """,
            (norm,),
        ).fetchall()
        # skip printing snippets to avoid console encoding issues on Windows

        print("prefix perend% distribution:")
        for tok, cnt in cur.execute(
            "select normalized, count(distinct verse_id) as c from tokens where normalized like 'perend%' group by normalized order by c desc, normalized"
        ):
            print("  ", tok, cnt)
    finally:
        conn.close()

if __name__ == "__main__":
    for db in ("alb_concordance.sqlite", "alb_concordance_v2.sqlite"):
        inspect(db, "perendia")
