import json
import os
import sys
from typing import Dict, List, Tuple, Optional


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def norm_sq_token(s: str) -> str:
    s = (s or '').strip().lower()
    # normalize common Albanian diacritics + artifacts present in source
    s = s.replace('ë', 'e').replace('ç', 'c')
    s = s.replace('A�', 'e').replace('A\u0015', 'c')
    return s


def first_unused_index(tokens: List[str], target: str, used: List[bool]) -> Optional[int]:
    t = norm_sq_token(target)
    for i, tok in enumerate(tokens):
        if used[i]:
            continue
        if norm_sq_token(tok) == t:
            return i
    return None


def greedy_align_verse(src_tokens: List[Dict], sq_text: str, seed_map: Dict[str, str]) -> List[Dict]:
    """A simple monotonic greedy aligner:
    - Respects Strong's -> Albanian seed map when available (single-token matches)
    - Otherwise assigns remaining Albanian tokens in order, roughly even span
    """
    sq_tokens = (sq_text or '').split()
    n_sq = len(sq_tokens)
    if n_sq == 0 or not src_tokens:
        return []
    used = [False] * n_sq
    aligns: List[Dict] = []

    # First pass: place dictionary-backed tokens
    for t in src_tokens:
        i = int(t.get('i', 0))
        s_code = (t.get('s') or '').strip().upper()
        if s_code in seed_map:
            al_word = seed_map[s_code]
            if al_word:
                hit = first_unused_index(sq_tokens, al_word, used)
                if hit is not None:
                    used[hit] = True
                    aligns.append({'src': i, 'tgt': [hit, hit]})

    # Second pass: distribute remaining Albanian tokens to remaining Greek tokens in order
    remaining_src: List[int] = []
    for t in src_tokens:
        i = int(t.get('i', 0))
        if not any(a['src'] == i for a in aligns):
            remaining_src.append(i)

    # gather remaining indices
    remaining_tgt = [idx for idx, u in enumerate(used) if not u]
    m = len(remaining_src)
    k = len(remaining_tgt)
    if m > 0 and k > 0:
        # even segmentation of remaining target indices among remaining sources
        for pos, src_i in enumerate(remaining_src):
            start_pos = (pos * k) // m
            end_pos = max(start_pos, (((pos + 1) * k) // m) - 1)
            lo = remaining_tgt[start_pos]
            hi = remaining_tgt[end_pos]
            aligns.append({'src': src_i, 'tgt': [int(lo), int(hi)]})

    # sort by src index
    aligns.sort(key=lambda x: x['src'])
    return aligns


def load_seed(path: str) -> Dict[str, str]:
    try:
        return load_json(path)
    except Exception:
        # minimal defaults
        return {
            'G2532': 'dhe',
            'G1722': 'në',
            'G1519': 'në',
            'G1537': 'nga',
            'G4314': 'te',
            'G0575': 'nga',
            'G3754': 'që',
            'G1063': 'sepse',
            'G3779': 'kështu',
            'G2531': 'sikurse',
            'G3475': 'Moisiu',
            'G3789': 'gjarpri',
            'G2048': 'shkretëtirë',
            'G5207': 'bir',
            'G0444': 'njeri',
            'G2424': 'Jezusi',
        }


def align_chapter(in_path: str, seed_map: Dict[str, str]) -> Tuple[int, Dict]:
    data = load_json(in_path)
    changed = 0
    for verse in data.get('verses', []):
        src = verse.get('src', [])
        sq = verse.get('sq', '')
        aligns = greedy_align_verse(src, sq, seed_map)
        if aligns:
            verse['align_tok'] = aligns
            changed += 1
    return changed, data


def main():
    args = sys.argv[1:]
    if '--input' not in args:
        print('Usage: align_monotonic.py --input <site/data/book/chapter.json> [--seed <path>] [--output <path>]')
        return 2
    in_path = args[args.index('--input') + 1]
    seed_path = None
    if '--seed' in args:
        seed_path = args[args.index('--seed') + 1]
    else:
        seed_path = os.path.join(ROOT, 'site', 'data', 'strongs', 'strongs_sq_seed.json')
    out_path = in_path
    if '--output' in args:
        out_path = args[args.index('--output') + 1]

    seed_map = load_seed(seed_path)
    changed, data = align_chapter(in_path, seed_map)
    save_json(out_path, data)
    print(f'Aligned verses (seeded) in {os.path.basename(in_path)}: {changed}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

