"""Preserve source hyperlinks from the pinned PUA table, without asserting identity."""
from html.parser import HTMLParser
from urllib.parse import urljoin
from pathlib import Path
import gzip
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kanji_kage_map.glyphwiki import digest_file
from kanji_kage_map.sources import write_json


class TableLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.row=None;self.column=-1;self.anchor=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='tr': self.row=dict(code=None,links=[]);self.column=-1
        if self.row is None:return
        if tag=='td':
            self.column+=1
            if attrs.get('id','').startswith('U_'):self.row['code']='U+'+attrs['id'][2:]
        if tag=='a' and 'href' in attrs:
            self.anchor=dict(column=self.column,href=attrs['href'],label='',line=self.getpos()[0])
    def handle_data(self,data):
        if self.anchor is not None:self.anchor['label']+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.anchor is not None:
            self.anchor['label']=self.anchor['label'].strip()
            if self.row is not None:self.row['links'].append(self.anchor)
            self.anchor=None
        if tag=='tr' and self.row is not None:
            if self.row['code']:self.rows.append(self.row)
            self.row=None


def main():
    lock=json.loads(Path('sources.lock.json').read_text(encoding='utf-8'))
    source=next(s for s in lock['sources'] if s['id']=='pua-page')
    if digest_file(source['path'])!=source['sha256']:raise ValueError('Pinned table changed')
    parser=TableLinks();parser.feed(Path(source['path']).read_text(encoding='utf-8-sig'))
    expected={json.loads(line)['entity_id'] for line in Path('data/generated/inventory.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(line)['entity_id'].startswith('babelstone:han-pua:')}
    results=[];seen=set()
    for row in parser.rows:
        entity=f"babelstone:han-pua:{source['version']}:{row['code']}"
        if entity not in expected:continue
        if entity in seen:raise ValueError('Duplicate table identifier')
        seen.add(entity)
        links=[dict(column='source' if a['column']==4 else 'source_refs',url=urljoin(source['url'],a['href']),label=a['label'],html_line=a['line']) for a in row['links'] if a['column'] in {4,5}]
        results.append(dict(entity_id=entity,source_id=source['id'],source_sha256=source['sha256'],links=links,status='links_unverified' if links else 'no_source_hyperlink'))
    if seen!=expected:raise ValueError('PUA inventory and parsed table differ')
    out=Path('docs/pua-source-links.jsonl.gz')
    with out.open('wb') as dest,gzip.GzipFile(filename='',fileobj=dest,mode='wb',mtime=0) as packed:
        for row in sorted(results,key=lambda r:r['entity_id']):packed.write((json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n').encode())
    missing={r['entity_id'] for r in json.loads(Path('docs/pua-font-missing.json').read_text(encoding='utf-8'))}
    write_json('docs/pua-source-links-summary.json',dict(format='pua-source-links-v1',source_sha256=source['sha256'],output_sha256=digest_file(out),entities=len(results),entities_with_links=sum(bool(r['links']) for r in results),links=sum(len(r['links']) for r in results),missing_font_entities=[r for r in results if r['entity_id'] in missing],limitation='Hyperlinks are documentary leads. Target retrieval, source edition and glyph identity are not verified by extraction.'))


if __name__=='__main__':main()
