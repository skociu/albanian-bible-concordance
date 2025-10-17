import os
import sys
import time
import json
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSHB_DIR = os.path.join(ROOT, '.cache', 'sources', 'oshb', 'wlc')

# Ensure we can import sibling scripts
if os.path.join(ROOT, 'scripts') not in sys.path:
    sys.path.append(os.path.join(ROOT, 'scripts'))

try:
    from oshb_to_json import BOOK_MAP_OSHB, build_from_book_chapter  # type: ignore
except Exception as e:
    print('Failed to import oshb_to_json:', e, file=sys.stderr)
    sys.exit(1)

try:
    from build_interlinear import extract_albanian_by_book_chapter, build_strongs_gloss_hebrew  # type: ignore
except Exception as e:
    print('Failed to import build_interlinear helpers:', e, file=sys.stderr)
    sys.exit(1)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def list_chapters_for_osis(osis_code: str) -> int:
    """Return max chapter number for this OSIS code based on the XML."""
    path = os.path.join(OSHB_DIR, f'{osis_code}.xml')
    if not os.path.isfile(path):
        return 0
    ns = {'o': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        max_ch = 0
        # Prefer explicit chapter tags
        for ch in root.findall('.//o:chapter', ns):
            osis_id = ch.get('osisID') or ''
            if not osis_id.startswith(osis_code + '.'):
                continue
            parts = osis_id.split('.')
            if len(parts) >= 2:
                try:
                    c = int(parts[1])
                    if c > max_ch:
                        max_ch = c
                except Exception:
                    pass
        if max_ch:
            return max_ch
        # Fallback: scan verses
        for v in root.findall('.//o:verse', ns):
            osis_id = v.get('osisID') or ''
            if not osis_id.startswith(osis_code + '.'):
                continue
            parts = osis_id.split('.')
            if len(parts) >= 3:
                try:
                    c = int(parts[1])
                    if c > max_ch:
                        max_ch = c
                except Exception:
                    pass
        return max_ch
    except Exception:
        return 0


def main():
    # Optional args: --books <comma OSIS|all>  --limit <int>
    args = sys.argv[1:]
    only = None
    if '--books' in args:
        i = args.index('--books')
        if i + 1 < len(args):
            v = args[i+1]
            if v and v.lower() != 'all':
                only = [x.strip() for x in v.split(',') if x.strip()]

    # Preload gloss map (Hebrew) from TBESH; optional
    tbesh_path = os.path.join(ROOT, '.cache', 'sources', 'step', 'TBESH_Hebrew.txt')
    strongs_heb = build_strongs_gloss_hebrew(tbesh_path)

    books = list(BOOK_MAP_OSHB.keys())
    if only:
        books = [b for b in books if b in only]

    # Albanian verse data
    verses_path = os.path.join(ROOT, 'site', 'data', 'verses.json')
    books_path = os.path.join(ROOT, 'site', 'data', 'books.json')

    total = 0
    for osis in books:
        info = BOOK_MAP_OSHB[osis]
        slug = info['slug']
        book_sq = info['book_sq']
        xml_path = os.path.join(OSHB_DIR, f'{osis}.xml')
        if not os.path.isfile(xml_path):
            print(f'[skip] Missing OSHB XML for {osis} at {xml_path}')
            continue
        max_ch = list_chapters_for_osis(osis)
        if max_ch <= 0:
            print(f'[skip] Could not determine chapters for {osis}')
            continue
        print(f'[build] {osis} -> {slug} ({max_ch} chapters)')
        for chap in range(1, max_ch + 1):
            verses = build_from_book_chapter(xml_path, osis, chap)
            if not verses:
                continue
            # Extract Albanian verse lines for this book/chapter
            try:
                al_map = extract_albanian_by_book_chapter(book_sq, chap, verses_path, books_path)
            except Exception:
                al_map = {}
            verses_out = []
            for v in verses:
                vnum = v['v']
                sq = al_map.get(vnum, '')
                gloss_map = {}
                for tok in v['src']:
                    s_code = tok.get('s') or ''
                    if s_code and s_code.startswith('H') and s_code in strongs_heb and s_code not in gloss_map:
                        gloss_map[s_code] = strongs_heb[s_code]
                verses_out.append({
                    'v': vnum,
                    'sq': sq,
                    'src': v['src'],
                    'gloss': gloss_map,
                    'align_phrase': []
                })
            final = {
                'ref': {'book': info['book'], 'book_sq': book_sq, 'chapter': chap},
                'verses': verses_out,
                '_meta': {
                    'lang_src': 'heb',
                    'lang_tgt': 'sq',
                    'sources': {
                        'text': 'WLC (via OSHB)',
                        'morph': 'OSHB morphology',
                        'gloss': 'STEPBible TBESH (optional)'
                    },
                    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'license_notes': 'See LICENSES.md'
                }
            }
            out_path = os.path.join(ROOT, 'site', 'data', slug, f'{chap}.json')
            save_json(out_path, final)
            total += 1
            if total % 50 == 0:
                print(f'  ... {total} chapters written so far')
    print(f'Done. Wrote {total} chapter files.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

