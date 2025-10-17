import hashlib
import json
import os
import sys
import time
from urllib.parse import urlparse
from urllib.request import urlopen, Request


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(ROOT, 'sources.yaml')
LOCK_PATH = os.path.join(ROOT, 'sources.lock')


def read_sources_yaml(path):
    # Minimal YAML parser for the tiny structure we use
    # Expect keys: sources: - name, kind, ref, url, license, dest
    sources = []
    cur = None
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.strip().startswith('#'):
                continue
            if line.startswith('sources:'):
                continue
            if line.strip().startswith('- '):
                if cur:
                    sources.append(cur)
                cur = {}
                line = line.strip()[2:]
                if line:
                    k, v = [x.strip() for x in line.split(':', 1)]
                    cur[k] = v
            else:
                if cur is None:
                    continue
                if ':' in line:
                    k, v = [x.strip() for x in line.strip().split(':', 1)]
                    cur[k] = v
    if cur:
        sources.append(cur)
    # Normalize types
    for s in sources:
        for k in list(s.keys()):
            s[k] = s[k].strip().strip('"')
    return sources


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def download(url: str) -> bytes:
    req = Request(url, headers={'User-Agent': 'albanian-bible-build/1.0'})
    with urlopen(req) as resp:
        return resp.read()


def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def main():
    if not os.path.isfile(YAML_PATH):
        print(f"Missing sources.yaml at {YAML_PATH}", file=sys.stderr)
        return 1
    sources = read_sources_yaml(YAML_PATH)
    locks = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'sources': []
    }
    for s in sources:
        name = s.get('name')
        url = s.get('url')
        dest = os.path.join(ROOT, s.get('dest'))
        ref = s.get('ref')
        license_info = s.get('license', '')
        if not url or not dest:
            print(f"Skipping invalid source entry: {s}")
            continue
        print(f"Fetching {name} from {url} ...")
        blob = download(url)
        digest = sha256_bytes(blob)
        ensure_dir(dest)
        with open(dest, 'wb') as f:
            f.write(blob)
        locks['sources'].append({
            'name': name,
            'url': url,
            'ref': ref,
            'license': license_info,
            'sha256': digest,
            'dest': os.path.relpath(dest, ROOT)
        })
        print(f"Saved to {dest} ({len(blob)} bytes, sha256={digest[:12]}...) ")
    with open(LOCK_PATH, 'w', encoding='utf-8') as f:
        json.dump(locks, f, ensure_ascii=False, indent=2)
    print(f"Wrote lock file {LOCK_PATH}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

