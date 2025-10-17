import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_json(schema, data):
    # Lightweight validator for required structure to avoid external deps if jsonschema not installed
    # If jsonschema is available, use it; otherwise do basic checks
    try:
        import jsonschema  # type: ignore
    except Exception:
        # Basic checks
        assert isinstance(data, dict), 'root must be object'
        assert 'ref' in data and 'verses' in data and '_meta' in data, 'missing keys'
        assert isinstance(data['verses'], list), 'verses must be list'
        for v in data['verses']:
            assert 'v' in v and 'sq' in v and 'src' in v, 'verse missing fields'
            assert isinstance(v['src'], list), 'src must be list'
            for t in v['src']:
                assert {'i','w','l','m','t'}.issubset(t.keys()), 'token missing fields'
        return []
    else:
        try:
            jsonschema.validate(instance=data, schema=schema)
            return []
        except jsonschema.exceptions.ValidationError as e:  # type: ignore
            return [str(e)]


def main():
    schema_path = os.path.join(ROOT, 'schemas', 'interlinear_verse.schema.json')
    # Optional argument: path to data JSON
    data_path = os.path.join(ROOT, 'site', 'data', 'john', '1.json')
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    if not os.path.isfile(schema_path) or not os.path.isfile(data_path):
        print('Schema or data not found', file=sys.stderr)
        return 1
    schema = load_json(schema_path)
    data = load_json(data_path)
    errs = validate_json(schema, data)
    if errs:
        print('Validation failed:')
        for e in errs:
            print('-', e)
        return 1
    # Extra semantic checks
    # Minimal sanity: has chapter=1
    if data['ref'].get('chapter') != 1:
        print('Unexpected chapter in data', file=sys.stderr)
        return 1
    if not data['verses']:
        print('No verses found', file=sys.stderr)
        return 1
    print('Schema validation OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
