"""Reproduce E87D research leads without changing published mappings or KAGE."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import resolve_bundle

SNAPSHOT = 'fd3aebc0a3d3d6bdb7c6498e9f2a65f3abe316c23e59ed4a1dd73abd30fa2b72'
PUA_SHA = 'a31b6fa8b39f2258dcb64008971936a524bdc462f3b753b3e73d24fbbcec2417'
SQL = "SELECT name,revision,related,data,line FROM latest WHERE data LIKE ? AND data LIKE ? ORDER BY name"


def research(database, source):
    raw = Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PUA_SHA:
        raise ValueError('PUA source hash differs')
    text = raw.decode('utf-8')
    row = text.split('id="U_E87D"', 1)[1].split('</tr>', 1)[0]
    if '⿰飠盧' not in row or 'drs:428496451$35i' not in row:
        raise ValueError('Source row differs')
    with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as db:
        snapshot = db.execute("SELECT value FROM metadata WHERE key='snapshot_sha256'").fetchone()[0]
        if snapshot != SNAPSHOT:
            raise ValueError('GlyphWiki snapshot differs')
        population = db.execute('SELECT count(*) FROM latest').fetchone()[0]
        found = db.execute(SQL, ('%u98e0%', '%u76e7%')).fetchall()
    leads = []
    for name, revision, related, data, line in found:
        reference = f'{name}@{revision}'
        bundle = resolve_bundle(database, reference)
        if bundle['snapshot_sha256'] != SNAPSHOT or bundle['glyphs'][reference]['data'] != data:
            raise ValueError('Resolved root differs from discovery row')
        leads.append(dict(entity_id='babelstone:han-pua:1.473:U+E87D', candidate=reference,
                          related=related, source_line=line,
                          root_kage_sha256=hashlib.sha256(data.encode()).hexdigest(),
                          evidence_kind='component_token_search_lead_only', bundle=bundle))
    return dict(format='e87d-component-search-v1', source_table_sha256=PUA_SHA,
                snapshot_sha256=SNAPSHOT, sql=SQL, parameters=['%u98e0%', '%u76e7%'],
                searched_latest_rows=population, leads=leads,
                limitations=['Substring matches include aliases and are not independent glyphs.',
                             'Search does not cover all possible names or indirect component paths.',
                             'Source IDS is a discovery clue; no KAGE is generated or edited.',
                             'No glyph equivalence judgment or published mapping change.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    parser.add_argument('--source', default=f'data/raw/{PUA_SHA}/PUA.html')
    parser.add_argument('--output', required=True)
    parser.add_argument('--bundles', required=True)
    args = parser.parse_args()
    result = research(args.database, args.source)
    for destination, content in [(args.output, result), (args.bundles, result['leads'])]:
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(searched=result['searched_latest_rows'], leads=len(result['leads']))))
