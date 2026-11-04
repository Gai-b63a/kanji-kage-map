"""Optional JSON Schema validator; core dataset tooling stays stdlib-only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache' / 'validation'))
from jsonschema import Draft202012Validator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('schema')
    parser.add_argument('data')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    schema_bytes = Path(args.schema).read_bytes()
    schema = json.loads(schema_bytes)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    digest = hashlib.sha256()
    count = 0
    with Path(args.data).open('rb') as stream:
        for count, line in enumerate(stream, 1):
            digest.update(line)
            try:
                validator.validate(json.loads(line))
            except Exception as error:
                raise ValueError(f'{args.data}:{count}: {error}') from error
    if not count:
        raise ValueError('Cannot report success for an empty dataset')
    report = dict(schema=Path(args.schema).name, schema_sha256=hashlib.sha256(schema_bytes).hexdigest(),
                  data=Path(args.data).name, data_sha256=digest.hexdigest(), rows=count, status='passed')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
