import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSHB_DIR = os.path.join(ROOT, '.cache', 'sources', 'oshb', 'wlc')

# OSIS -> { slug, book_sq (Albanian), book (English+source) }
BOOK_MAP_OSHB = {
    'Gen':  {'slug': 'genesis',       'book_sq': 'Zanafilla',          'book': 'Genesis (WLC)'},
    'Exod': {'slug': 'exodus',        'book_sq': 'Eksodi',              'book': 'Exodus (WLC)'},
    'Lev':  {'slug': 'leviticus',     'book_sq': 'Levitiku',            'book': 'Leviticus (WLC)'},
    'Num':  {'slug': 'numbers',       'book_sq': 'Numrat',              'book': 'Numbers (WLC)'},
    'Deut': {'slug': 'deuteronomy',   'book_sq': 'Ligji i Përtërirë',   'book': 'Deuteronomy (WLC)'},
    'Josh': {'slug': 'joshua',        'book_sq': 'Jozueu',              'book': 'Joshua (WLC)'},
    'Judg': {'slug': 'judges',        'book_sq': 'Gjyqtarët',           'book': 'Judges (WLC)'},
    'Ruth': {'slug': 'ruth',          'book_sq': 'Ruthi',               'book': 'Ruth (WLC)'},
    '1Sam': {'slug': '1samuel',       'book_sq': '1 i Samuelit',        'book': '1 Samuel (WLC)'},
    '2Sam': {'slug': '2samuel',       'book_sq': '2 i Samuelit',        'book': '2 Samuel (WLC)'},
    '1Kgs': {'slug': '1kings',        'book_sq': '1 i Mbretërve',       'book': '1 Kings (WLC)'},
    '2Kgs': {'slug': '2kings',        'book_sq': '2 i Mbretërve',       'book': '2 Kings (WLC)'},
    '1Chr': {'slug': '1chronicles',   'book_sq': '1 i Kronikave',       'book': '1 Chronicles (WLC)'},
    '2Chr': {'slug': '2chronicles',   'book_sq': '2 i Kronikave',       'book': '2 Chronicles (WLC)'},
    'Ezra': {'slug': 'ezra',          'book_sq': 'Ezra',                'book': 'Ezra (WLC)'},
    'Neh':  {'slug': 'nehemiah',      'book_sq': 'Nehemia',             'book': 'Nehemiah (WLC)'},
    'Esth': {'slug': 'esther',        'book_sq': 'Estera',              'book': 'Esther (WLC)'},
    'Job':  {'slug': 'job',           'book_sq': 'Jobi',                'book': 'Job (WLC)'},
    'Ps':   {'slug': 'psalms',        'book_sq': 'Psalmet',             'book': 'Psalms (WLC)'},
    'Prov': {'slug': 'proverbs',      'book_sq': 'Fjalët e Urta',       'book': 'Proverbs (WLC)'},
    'Eccl': {'slug': 'ecclesiastes',  'book_sq': 'Predikuesi',          'book': 'Ecclesiastes (WLC)'},
    'Song': {'slug': 'songofsongs',   'book_sq': 'Kënga e Këngëve',     'book': 'Song of Songs (WLC)'},
    'Isa':  {'slug': 'isaiah',        'book_sq': 'Isaia',               'book': 'Isaiah (WLC)'},
    'Jer':  {'slug': 'jeremiah',      'book_sq': 'Jeremia',             'book': 'Jeremiah (WLC)'},
    'Lam':  {'slug': 'lamentations',  'book_sq': 'Vajtimet',            'book': 'Lamentations (WLC)'},
    'Ezek': {'slug': 'ezekiel',       'book_sq': 'Ezekieli',            'book': 'Ezekiel (WLC)'},
    'Dan':  {'slug': 'daniel',        'book_sq': 'Danieli',             'book': 'Daniel (WLC)'},
    'Hos':  {'slug': 'hosea',         'book_sq': 'Osea',                'book': 'Hosea (WLC)'},
    'Joel': {'slug': 'joel',          'book_sq': 'Joeli',               'book': 'Joel (WLC)'},
    'Amos': {'slug': 'amos',          'book_sq': 'Amosi',               'book': 'Amos (WLC)'},
    'Obad': {'slug': 'obadiah',       'book_sq': 'Abdia',               'book': 'Obadiah (WLC)'},
    'Jonah':{'slug': 'jonah',         'book_sq': 'Jona',                'book': 'Jonah (WLC)'},
    'Mic':  {'slug': 'micah',         'book_sq': 'Mika',                'book': 'Micah (WLC)'},
    'Nah':  {'slug': 'nahum',         'book_sq': 'Nahumi',              'book': 'Nahum (WLC)'},
    'Hab':  {'slug': 'habakkuk',      'book_sq': 'Habakuku',            'book': 'Habakkuk (WLC)'},
    'Zeph': {'slug': 'zephaniah',     'book_sq': 'Sofonia',             'book': 'Zephaniah (WLC)'},
    'Hag':  {'slug': 'haggai',        'book_sq': 'Hagaiu',              'book': 'Haggai (WLC)'},
    'Zech': {'slug': 'zechariah',     'book_sq': 'Zakaria',             'book': 'Zechariah (WLC)'},
    'Mal':  {'slug': 'malachi',       'book_sq': 'Malakia',             'book': 'Malachi (WLC)'},
}


def strip_diacritics(s: str) -> str:
    n = unicodedata.normalize('NFD', s)
    return ''.join(ch for ch in n if unicodedata.category(ch) != 'Mn')


def heb_to_latin(s: str) -> str:
    # Simple MVP transliteration; keeps it deterministic
    base = strip_diacritics(s)
    table = {
        'א':'ʾ','ב':'b','ג':'g','ד':'d','ה':'h','ו':'w','ז':'z','ח':'ḥ','ט':'ṭ','י':'y','כ':'k','ך':'k','ל':'l','מ':'m','ם':'m','נ':'n','ן':'n','ס':'s','ע':'ʿ','פ':'p','ף':'p','צ':'ṣ','ץ':'ṣ','ק':'q','ר':'r','ש':'š','ת':'t',
        'ּ':'','־':'-','׀':'','׳':'','״':'','׳':'', ' ':' '
    }
    return ''.join(table.get(ch, ch) for ch in base)


def extract_strongs_from_lemma(lemma: str) -> str:
    # OSHB lemma formats like: "b/7225", "5921 a", "430"; pick first number
    if not lemma:
        return ''
    m = re.search(r"(\d{1,5})", lemma)
    if not m:
        return ''
    num = int(m.group(1))
    return f"H{num:04d}"


def build_from_book_chapter(path: str, osis_book: str, chapter: int):
    ns = {'o': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
    tree = ET.parse(path)
    root = tree.getroot()
    verses = []
    # Verse osisID sample: Gen.1.1
    # Find the chapter element, then gather its verses
    ch_el = root.find(f".//o:chapter[@osisID='{osis_book}.{chapter}']", ns)
    if ch_el is None:
        # Some OSIS files nest verses without explicit chapter tags; fallback to all verses with prefix
        candidates = root.findall(".//o:verse", ns)
    else:
        candidates = ch_el.findall(".//o:verse", ns)
    for v_el in candidates:
        osis_id = v_el.get('osisID') or ''
        if not osis_id.startswith(f"{osis_book}.{chapter}.") and osis_id != f"{osis_book}.{chapter}":
            continue
        parts = osis_id.split('.')
        if len(parts) < 3:
            continue
        try:
            vnum = int(parts[2])
        except Exception:
            continue
        tokens = []
        idx = 0
        # iterate child nodes; capture <w> elements only
        for w_el in v_el.findall('.//o:w', ns):
            surface = ''.join(w_el.itertext()).strip()
            lemma = w_el.get('lemma') or ''
            morph = w_el.get('morph') or ''
            strong = extract_strongs_from_lemma(lemma)
            tokens.append({
                'i': idx,
                'w': surface,
                'l': lemma,
                'm': morph,
                's': strong,
                't': heb_to_latin(surface)
            })
            idx += 1
        verses.append({'v': vnum, 'src': tokens})
    verses.sort(key=lambda x: x['v'])
    return verses


def main():
    # Args: --book <OSIS e.g., Gen|Exod> --chapter <int>
    args = sys.argv[1:]
    osis = 'Gen'
    chap = 1
    if '--book' in args:
        i = args.index('--book')
        if i + 1 < len(args):
            osis = args[i+1]
    if '--chapter' in args:
        i = args.index('--chapter')
        if i + 1 < len(args):
            chap = int(args[i+1])
    path = os.path.join(OSHB_DIR, f"{osis}.xml")
    if not os.path.isfile(path):
        print('Missing OSHB WLC source. Run scripts/fetch_sources.py.', file=sys.stderr)
        return 1
    verses = build_from_book_chapter(path, osis, chap)
    info = BOOK_MAP_OSHB.get(osis, {'slug': osis.lower(), 'book_sq': osis, 'book': osis})
    slug = info['slug']
    out_dir = os.path.join(ROOT, '.cache', 'build', 'ot', slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{chap}.json")
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
