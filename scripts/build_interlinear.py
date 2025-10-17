import json
import os
import sys
import time
import unicodedata


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def norm_greek(s: str) -> str:
    if not s:
        return s
    # NFC -> strip combining marks
    n = unicodedata.normalize('NFD', s)
    return ''.join(ch for ch in n if unicodedata.category(ch) != 'Mn')


def build_strongs_map_greek(tbesg_path: str):
    m_by_greek = {}
    m_by_translit = {}
    if not os.path.isfile(tbesg_path):
        return m_by_greek, m_by_translit
    with open(tbesg_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line or not line.startswith('G'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 5:
                continue
            code = parts[0].strip()
            # Heuristic positions
            greek = parts[3].strip() if len(parts) > 3 else ''
            translit = parts[4].strip() if len(parts) > 4 else ''
            gloss = parts[6].strip() if len(parts) > 6 else ''
            if greek:
                m_by_greek[norm_greek(greek)] = (code, gloss)
            if translit:
                m_by_translit[translit.lower()] = (code, gloss)
    return m_by_greek, m_by_translit


def build_strongs_gloss_hebrew(tbesh_path: str):
    code_to_gloss = {}
    if not os.path.isfile(tbesh_path):
        return code_to_gloss
    with open(tbesh_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line or not line.startswith('H'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2:
                continue
            code = parts[0].strip()
            # find first short gloss-like field
            gloss = ''
            for p in parts[1:]:
                if p and not p.startswith('<'):
                    gloss = p.strip()
                    break
            if gloss:
                code_to_gloss[code] = gloss.split(';')[0].split(',')[0]
    return code_to_gloss


def _norm_name(s: str) -> str:
    try:
        s = unicodedata.normalize('NFD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    except Exception:
        pass
    out = []
    for ch in (s or '').lower():
        if ch.isalnum() or ch.isspace():
            out.append(ch)
        # keep digits for books like "1 i Samuelit"
    return ' '.join(''.join(out).split())


def extract_albanian_by_book_chapter(book_sq: str, chapter: int, verses_path: str, books_path: str):
    books = load_json(books_path)
    # Match Albanian name (robust, accent/encoding-insensitive)
    bid = None
    target_raw = (book_sq or '').strip().lower()
    target = _norm_name(target_raw)
    for i, name in enumerate(books, start=1):
        n = (name or '').strip().lower()
        if n == target_raw or _norm_name(n) == target:
            bid = i
            break
    if not bid:
        raise RuntimeError(f'Could not locate book id for {book_sq}')
    data = load_json(verses_path)
    out = {}
    for row in data:
        b, c, v, text = row
        if b == bid and c == chapter:
            out[v] = text
    return out


def main():
    # Optional args: --input <path> --output <path>
    args = sys.argv[1:]
    greek_chapter_path = os.path.join(ROOT, '.cache', 'build', 'tr', 'john', '1.json')
    out_path = os.path.join(ROOT, 'site', 'data', 'john', '1.json')
    if '--input' in args:
        i = args.index('--input')
        if i + 1 < len(args):
            greek_chapter_path = args[i+1]
    if '--output' in args:
        i = args.index('--output')
        if i + 1 < len(args):
            out_path = args[i+1]
    if not os.path.isfile(greek_chapter_path):
        print(f'Missing Greek tokens JSON at {greek_chapter_path}.', file=sys.stderr)
        return 1
    src_ch = load_json(greek_chapter_path)
    ref = src_ch.get('ref', {})
    book_sq = ref.get('book_sq') or ''
    chapter = int(ref.get('chapter') or 1)
    albanian_map = extract_albanian_by_book_chapter(
        book_sq,
        chapter,
        os.path.join(ROOT, 'site', 'data', 'verses.json'),
        os.path.join(ROOT, 'site', 'data', 'books.json'),
    )

    strongs_greek, strongs_trans = build_strongs_map_greek(os.path.join(ROOT, '.cache', 'sources', 'step', 'TBESG_Greek.txt'))
    strongs_heb = build_strongs_gloss_hebrew(os.path.join(ROOT, '.cache', 'sources', 'step', 'TBESH_Hebrew.txt'))

    # Attach Albanian and Strongs where possible
    verses_out = []
    for verse in src_ch['verses']:
        vnum = verse['v']
        sq = albanian_map.get(vnum, '')
        gloss_map = {}
        for tok in verse['src']:
            s_code = tok.get('s') or ''
            # Try matching by lemma (Greek)
            if not s_code:
                lnorm = norm_greek(tok.get('l', ''))
                if lnorm in strongs_greek:
                    s_code, gloss = strongs_greek[lnorm]
                    if s_code and gloss and s_code not in gloss_map:
                        gloss_map[s_code] = gloss.split(';')[0].split(',')[0]
                else:
                    # Try by transliteration
                    t = tok.get('t', '').lower()
                    if t in strongs_trans:
                        s_code, gloss = strongs_trans[t]
                        if s_code and gloss and s_code not in gloss_map:
                            gloss_map[s_code] = gloss.split(';')[0].split(',')[0]
            tok['s'] = s_code
            # Hebrew gloss by Strong's direct
            if not s_code:
                continue
            if s_code.startswith('H') and s_code in strongs_heb and s_code not in gloss_map:
                gloss_map[s_code] = strongs_heb[s_code]
        verses_out.append({
            'v': vnum,
            'sq': sq,
            'src': verse['src'],
            'gloss': gloss_map,
            'align_phrase': []
        })

    # Build final chapter JSON
    # Data sources metadata
    # We have SBLGNT text + MorphGNT morph, and STEP gloss
    # Determine source language by inspecting token script
    def is_hebrew_token(tok_word: str) -> bool:
        return any('\u0590' <= ch <= '\u05FF' for ch in (tok_word or ''))

    lang_src = 'grc'
    try:
        # Peek first few tokens
        sample = []
        for v in src_ch.get('verses', [])[:3]:
            for t in v.get('src', [])[:5]:
                sample.append(t.get('w', ''))
        if any(is_hebrew_token(w) for w in sample):
            lang_src = 'heb'
    except Exception:
        pass

    # Source attribution
    sources_meta = {
        'text': 'Scrivener TR 1894 (Robinson edition)' if lang_src == 'grc' else 'WLC (via OSHB)',
        'morph': 'Robinson parsing (embedded)' if lang_src == 'grc' else 'OSHB morphology',
        'gloss': 'STEPBible TBESG (optional)'
    }

    meta = {
        'lang_src': lang_src,
        'lang_tgt': 'sq',
        'sources': sources_meta,
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'license_notes': 'See LICENSES.md'
    }

    final = {
        'ref': src_ch['ref'],
        'verses': verses_out,
        '_meta': meta
    }

    save_json(out_path, final)
    print(f'Wrote {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
