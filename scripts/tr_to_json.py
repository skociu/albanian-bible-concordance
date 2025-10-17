import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR_DIR = os.path.join(ROOT, '.cache', 'sources', 'tr')


def ascii_to_greek(word: str) -> str:
    """Convert Robinson/TR ASCII transliteration to basic Greek letters (no diacritics).
    Uses explicit Unicode escapes to avoid encoding issues.
    """
    if not word:
        return ''
    s = str(word)
    # Digraphs first
    s = re.sub(r'PS', '\u03A8', s)
    s = re.sub(r'Ps', '\u03A8', s)
    s = re.sub(r'ps', '\u03C8', s)
    map1 = {
        'a': '\u03B1', 'b': '\u03B2', 'g': '\u03B3', 'd': '\u03B4', 'e': '\u03B5', 'z': '\u03B6',
        'h': '\u03B7', 'q': '\u03B8', 'i': '\u03B9', 'k': '\u03BA', 'l': '\u03BB', 'm': '\u03BC',
        'n': '\u03BD', 'x': '\u03BE', 'o': '\u03BF', 'p': '\u03C0', 'r': '\u03C1', 's': '\u03C3',
        't': '\u03C4', 'u': '\u03C5', 'f': '\u03C6', 'c': '\u03C7', 'w': '\u03C9', 'y': '\u03C5',
        'v': '\u03C2',
        'A': '\u0391', 'B': '\u0392', 'G': '\u0393', 'D': '\u0394', 'E': '\u0395', 'Z': '\u0396',
        'H': '\u0397', 'Q': '\u0398', 'I': '\u0399', 'K': '\u039A', 'L': '\u039B', 'M': '\u039C',
        'N': '\u039D', 'X': '\u039E', 'O': '\u039F', 'P': '\u03A0', 'R': '\u03A1', 'S': '\u03A3',
        'T': '\u03A4', 'U': '\u03A5', 'F': '\u03A6', 'C': '\u03A7', 'W': '\u03A9', 'Y': '\u03A5',
        'V': '\u03A3',
    }
    out = []
    for ch in s:
        out.append(map1.get(ch, ch))
    g = ''.join(out)
    # Final sigma normalization
    if g.endswith('\u03C3'):
        g = g[:-1] + '\u03C2'
    return g


def parse_utr_line_v2(line: str):
    """Parse a single joined verse line: groups of word [digits]? {MORPH}."""
    line = line.strip()
    m = re.match(r'^(\d+):(\d+)\s+(.*)$', line)
    if not m:
        return None
    chap = int(m.group(1))
    verse = int(m.group(2))
    rest = m.group(3)
    toks = []
    for wm in re.finditer(r"([A-Za-z'\-]+)\s*(?:([0-9]{1,5}))?\s*\{([^}]+)\}", rest):
        word = wm.group(1)
        strong = wm.group(2) or ''
        morph = wm.group(3) or ''
        s_code = f"G{int(strong):04d}" if strong else ''
        toks.append({'word_ascii': word, 'strong': s_code, 'morph': morph})
    return chap, verse, toks


def build_for_book_chapter(tr_path: str, target_chapter: int):
    verses = defaultdict(list)
    hdr_re = re.compile(r'^(\d+):(\d+)\s*(.*)$')
    buf = ''

    def flush():
        nonlocal buf
        s = buf.strip()
        if not s:
            buf = ''
            return
        parsed = parse_utr_line_v2(s)
        if parsed:
            chap, ver, toks = parsed
            if chap == target_chapter:
                for t in toks:
                    w_ascii = t['word_ascii']
                    w_greek = ascii_to_greek(w_ascii)
                    verses[ver].append({
                        'i': len(verses[ver]),
                        'w': w_greek,
                        'l': w_greek.lower(),
                        'm': t['morph'],
                        's': t['strong'],
                        't': w_ascii,
                    })
        buf = ''

    with open(tr_path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line:
                continue
            if hdr_re.match(line):
                flush()
                buf = line
            else:
                buf += ' ' + line.strip()
        flush()

    out = []
    for ver in sorted(verses.keys()):
        out.append({'v': ver, 'src': verses[ver]})
    return out


BOOK_MAP = {
    'MT':  {'slug': 'matthew',       'book': 'Matthew (TR1894)',    'book_sq': 'Mateu',                'file': 'MT.UTR'},
    'MR':  {'slug': 'mark',          'book': 'Mark (TR1894)',       'book_sq': 'Marku',                'file': 'MR.UTR'},
    'LU':  {'slug': 'luke',          'book': 'Luke (TR1894)',       'book_sq': 'Luka',                 'file': 'LU.UTR'},
    'JOH': {'slug': 'john',          'book': 'John (TR1894)',       'book_sq': 'Gjoni',                'file': 'JOH.UTR'},
    'ACT': {'slug': 'acts',          'book': 'Acts (TR1894)',       'book_sq': 'Veprat e Apostujve',   'file': 'ACT.UTR'},
    'ROM': {'slug': 'romans',        'book': 'Romans (TR1894)',     'book_sq': 'Romakëve',             'file': 'ROM.UTR'},
    '1CO': {'slug': '1corinthians',  'book': '1 Corinthians (TR1894)','book_sq': '1 Korintasve',       'file': '1CO.UTR'},
    '2CO': {'slug': '2corinthians',  'book': '2 Corinthians (TR1894)','book_sq': '2 Korintasve',       'file': '2CO.UTR'},
    'GAL': {'slug': 'galatians',     'book': 'Galatians (TR1894)',  'book_sq': 'Galatasve',            'file': 'GAL.UTR'},
    'EPH': {'slug': 'ephesians',     'book': 'Ephesians (TR1894)',  'book_sq': 'Efesianëve',           'file': 'EPH.UTR'},
    'PHP': {'slug': 'philippians',   'book': 'Philippians (TR1894)','book_sq': 'Filipianëve',          'file': 'PHP.UTR'},
    'COL': {'slug': 'colossians',    'book': 'Colossians (TR1894)', 'book_sq': 'Kolosianëve',          'file': 'COL.UTR'},
    '1TH': {'slug': '1thessalonians','book': '1 Thessalonians (TR1894)','book_sq':'1 Thesalonikasve',  'file': '1TH.UTR'},
    '2TH': {'slug': '2thessalonians','book': '2 Thessalonians (TR1894)','book_sq':'2 Thesalonikasve',  'file': '2TH.UTR'},
    '1TI': {'slug': '1timothy',      'book': '1 Timothy (TR1894)',  'book_sq': '1 Timoteut',           'file': '1TI.UTR'},
    '2TI': {'slug': '2timothy',      'book': '2 Timothy (TR1894)',  'book_sq': '2 Timoteut',           'file': '2TI.UTR'},
    'TIT': {'slug': 'titus',         'book': 'Titus (TR1894)',      'book_sq': 'Titit',                'file': 'TIT.UTR'},
    'PHM': {'slug': 'philemon',      'book': 'Philemon (TR1894)',   'book_sq': 'Filemonit',            'file': 'PHM.UTR'},
    'HEB': {'slug': 'hebrews',       'book': 'Hebrews (TR1894)',    'book_sq': 'Hebrenjve',            'file': 'HEB.UTR'},
    'JAS': {'slug': 'james',         'book': 'James (TR1894)',      'book_sq': 'Jakobi',               'file': 'JAS.UTR'},
    '1PE': {'slug': '1peter',        'book': '1 Peter (TR1894)',    'book_sq': '1 Pjetrit',            'file': '1PE.UTR'},
    '2PE': {'slug': '2peter',        'book': '2 Peter (TR1894)',    'book_sq': '2 Pjetrit',            'file': '2PE.UTR'},
    '1JO': {'slug': '1john',         'book': '1 John (TR1894)',     'book_sq': '1 Gjonit',             'file': '1JO.UTR'},
    '2JO': {'slug': '2john',         'book': '2 John (TR1894)',     'book_sq': '2 Gjonit',             'file': '2JO.UTR'},
    '3JO': {'slug': '3john',         'book': '3 John (TR1894)',     'book_sq': '3 Gjonit',             'file': '3JO.UTR'},
    'JUD': {'slug': 'jude',          'book': 'Jude (TR1894)',       'book_sq': 'Juda',                 'file': 'JUD.UTR'},
    'REV': {'slug': 'revelation',    'book': 'Revelation (TR1894)', 'book_sq': 'Zbulesa e Gjonit',     'file': 'REV.UTR'},
}


def main():
    args = sys.argv[1:]
    code = 'JOH'
    chap = 1
    if '--book' in args:
        i = args.index('--book')
        if i + 1 < len(args):
            code = args[i+1].upper()
    if '--chapter' in args:
        i = args.index('--chapter')
        if i + 1 < len(args):
            chap = int(args[i+1])
    info = BOOK_MAP.get(code)
    if not info:
        print(f'Unsupported book code: {code}', file=sys.stderr)
        return 1
    tr_path = os.path.join(TR_DIR, info['file'])
    if not os.path.isfile(tr_path):
        print('Missing TR source. Run scripts/fetch_sources.py first.', file=sys.stderr)
        return 1
    verses = build_for_book_chapter(tr_path, chap)
    out_dir = os.path.join(ROOT, '.cache', 'build', 'tr', info['slug'])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{chap}.json')
    payload = {
        'ref': {"book": info['book'], "book_sq": info['book_sq'], "chapter": chap},
        'verses': verses
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    print(f"Wrote {out_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

