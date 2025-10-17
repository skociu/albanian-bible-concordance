import argparse
import json
import sqlite3


def main():
    ap = argparse.ArgumentParser(description="Concordance stats")
    ap.add_argument("--db", default="alb_concordance.sqlite")
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(DISTINCT normalized) FROM tokens')
    unique_words = cur.fetchone()[0]
    cur.execute('SELECT SUM(vcnt) FROM (SELECT normalized, COUNT(DISTINCT verse_id) AS vcnt FROM tokens GROUP BY normalized)')
    sum_verse_hits = cur.fetchone()[0]
    cur.execute('SELECT AVG(LENGTH(text)) FROM verses')
    avg_len = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM verses')
    verses = cur.fetchone()[0]
    cur.execute('SELECT normalized, COUNT(*) as cnt FROM tokens GROUP BY normalized ORDER BY cnt DESC LIMIT 5')
    top = cur.fetchall()
    # Words length >=3
    cur.execute('SELECT COUNT(*) FROM (SELECT normalized FROM tokens WHERE LENGTH(normalized) >= 3 GROUP BY normalized)')
    unique_ge3 = cur.fetchone()[0]
    cur.execute('SELECT SUM(vcnt) FROM (SELECT normalized, COUNT(DISTINCT verse_id) AS vcnt FROM tokens WHERE LENGTH(normalized) >= 3 GROUP BY normalized)')
    sum_hits_ge3 = cur.fetchone()[0]
    # Words length >=4
    cur.execute('SELECT COUNT(*) FROM (SELECT normalized FROM tokens WHERE LENGTH(normalized) >= 4 GROUP BY normalized)')
    unique_ge4 = cur.fetchone()[0]
    cur.execute('SELECT SUM(vcnt) FROM (SELECT normalized, COUNT(DISTINCT verse_id) AS vcnt FROM tokens WHERE LENGTH(normalized) >= 4 GROUP BY normalized)')
    sum_hits_ge4 = cur.fetchone()[0]
    print(json.dumps({
        'unique_words': unique_words,
        'sum_verse_hits': sum_verse_hits,
        'avg_verse_length': avg_len,
        'verses': verses,
        'top': top,
        'unique_words_len_ge3': unique_ge3,
        'sum_verse_hits_len_ge3': sum_hits_ge3,
        'unique_words_len_ge4': unique_ge4,
        'sum_verse_hits_len_ge4': sum_hits_ge4,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
