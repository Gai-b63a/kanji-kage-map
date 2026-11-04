"""Check the independent review JSON Schema with jsonschema (development only)."""
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.sources import write_json
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.review_decisions import validate


def main():
    path=Path('schemas/review-decisions.schema.json')
    schema=json.loads(path.read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema,format_checker=FormatChecker())
    originals=[]
    for name in ['docs/one-review-decision.jsonl','docs/sea-review-decisions.jsonl']:
        originals.extend(json.loads(line) for line in Path(name).read_text(encoding='utf-8').splitlines())
    cases=[('original-'+str(i),row,True) for i,row in enumerate(originals)]
    changes=[('unverified-edition',lambda r:r['source'].update(edition_alignment='unverified')),
             ('missing-aspect',lambda r:r['observations'].pop()),
             ('not-checked',lambda r:r['observations'][0].update(result='not_checked')),
             ('feature-cannot-certify-whole',lambda r:r['scope'].update(kind='feature')),
             ('no-timezone',lambda r:r.update(reviewed_at='2026-11-04T09:00:00')),
             ('missing-evidence',lambda r:r.update(evidence=[])),
             ('unknown-property',lambda r:r.update(approved=True)),
             ('unversioned-glyph',lambda r:r.update(glyph_reference='u4e00')),
             ('withdrawal-without-predecessor',lambda r:r.update(decision='withdrawn'))]
    for name,mutate in changes:
        row=deepcopy(originals[0]);mutate(row);cases.append((name,row,False))
    results=[]
    for name,row,expected in cases:
        accepted=validator.is_valid(row)
        try: validate(row);semantic=True
        except (ValueError,TypeError): semantic=False
        if accepted!=expected or semantic!=expected: raise ValueError('Contract mismatch: '+name)
        results.append(dict(case=name,accepted=accepted,semantic_validation=semantic))
    write_json('docs/review-schema-verification.json',dict(schema_sha256=digest_file(path),
               validator='jsonschema '+version('jsonschema'),date_time_format_asserted=True,
               cases=results,limitation='Single-record interoperability checks; history ordering, canonical scalar IDs, unique observation aspects and candidate membership remain semantic validation duties.'))
    print(len(results),'schema/semantic agreement cases passed')


if __name__=='__main__':main()
