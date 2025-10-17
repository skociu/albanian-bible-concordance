import json
import math
import os
import sys


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def naive_align_tokens(src_len, sq_text):
    words = (sq_text or '').split()
    if src_len <= 0 or not words:
        return []
    n = len(words)
    # Even segmentation: cover all target tokens with contiguous ranges per src
    aligns = []
    for i in range(src_len):
        start = math.floor(i * n / src_len)
        end = max(start, math.floor((i + 1) * n / src_len) - 1)
        if start < n:
            aligns.append({'src': i, 'tgt': [start, min(end, n - 1)]})
    return aligns


def main():
    # Usage: make_naive_align.py --input site/data/genesis/1.json [--output site/data/genesis/1.json] [--force]
    args = sys.argv[1:]
    if '--input' not in args:
        print('Usage: make_naive_align.py --input <chapter.json> [--output <out.json>] [--force]')
        return 2
    in_path = args[args.index('--input') + 1]
    out_path = in_path
    if '--output' in args:
        out_path = args[args.index('--output') + 1]
    force = '--force' in args
    data = load_json(in_path)
    changed = 0
    for verse in data.get('verses', []):
        if not force and verse.get('align_tok'):
            continue
        src_len = len(verse.get('src', []))
        sq = verse.get('sq', '')
        verse['align_tok'] = naive_align_tokens(src_len, sq)
        changed += 1
    save_json(out_path, data)
    print(f'Aligned verses: {changed} -> {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())


