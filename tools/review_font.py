"""Inspect the exact font bytes; never substitute the page's advertised version."""
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / '.cache/review')]
from fontTools.ttLib import TTFont
from kanji_kage_map.sources import verified_sources, write_json


def main():
    record, data = verified_sources(ROOT / 'review-sources.lock.json')['babelstone-han-pua-font']
    font = TTFont(io.BytesIO(data))
    names = {str(n): sorted({r.toUnicode() for r in font['name'].names if r.nameID == n})
             for n in (0, 1, 2, 3, 5, 8, 9, 14)}
    license_text = sorted({r.toUnicode() for r in font['name'].names if r.nameID == 13})
    if len(license_text) != 1:
        raise ValueError('Font license requires manual reconciliation')
    (ROOT / 'licenses/ARPHICPL.txt').write_text(license_text[0], encoding='utf-8', newline='\n')
    cmap = font.getBestCmap()
    missing = []
    with (ROOT / 'data/generated/source-rows.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['source_id'] == 'pua-page' and int(row['entity_id'].split('U+')[-1], 16) not in cmap:
                missing.append(dict(entity_id=row['entity_id'], cells=row['cells']))
    report = dict(source_sha256=record['sha256'], advertised_version=record['version'], names=names,
                  version_matches=names['5'] == ['Version ' + record['version']],
                  cmap_count=len(cmap), pua_count=sum(0xE000 <= c <= 0xF8FF for c in cmap),
                  missing_inventory_count=len(missing), license_path='licenses/ARPHICPL.txt')
    write_json(ROOT / 'docs/pua-font-metadata.json', report)
    write_json(ROOT / 'docs/pua-font-missing.json', missing)
    webfonts = []
    for source_id, (source, raw) in verified_sources(ROOT / 'review-webfonts.lock.json').items():
        webfont = TTFont(io.BytesIO(raw))
        webfonts.append(dict(id=source_id, sha256=source['sha256'],
                             version=sorted({r.toUnicode() for r in webfont['name'].names if r.nameID == 5}),
                             pua_count=sum(0xE000 <= c <= 0xF8FF for c in webfont.getBestCmap())))
    write_json(ROOT / 'docs/pua-webfont-metadata.json', webfonts)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
