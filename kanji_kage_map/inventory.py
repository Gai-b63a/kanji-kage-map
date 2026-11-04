"""Loss-aware enumeration, not IDS-to-glyph conversion."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

from .sources import verified_sources, write_json

ARITY = {**{chr(c): 2 for c in range(0x2FF0, 0x2FFE)}, '⿲': 3, '⿳': 3,
         '⿾': 1, '⿿': 1, '㇯': 2}
COMPONENT_BLOCKS = {'CJK Radicals Supplement', 'Kangxi Radicals', 'CJK Strokes'}
COMPAT_BLOCKS = {'CJK Compatibility Ideographs', 'CJK Compatibility Ideographs Supplement'}


def codepoint(cp):
    return f'U+{cp:04X}'


def is_pua(cp):
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0xFFFFD or 0x100000 <= cp <= 0x10FFFD


def ranges(text, property_name=None):
    for line in text.splitlines():
        body = line.split('#', 1)[0].strip()
        if not body:
            continue
        span, name = (p.strip() for p in body.split(';', 1))
        if property_name is not None and name != property_name:
            continue
        bounds = span.split('..')
        yield int(bounds[0], 16), int(bounds[-1], 16), name


def unicode_sets(unicode_data, prop_list, blocks):
    assigned = set()
    start = None
    for line in unicode_data.splitlines():
        fields = line.split(';')
        cp, name = int(fields[0], 16), fields[1]
        if name.endswith(', First>'):
            start = cp
        elif name.endswith(', Last>'):
            if start is None:
                raise ValueError('UnicodeData range missing First')
            assigned.update(range(start, cp + 1))
            start = None
        else:
            assigned.add(cp)
    if start is not None:
        raise ValueError('UnicodeData range missing Last')
    han = set()
    for lo, hi, _ in ranges(prop_list, 'Unified_Ideograph'):
        han.update(range(lo, hi + 1))
    components = set()
    for lo, hi, name in ranges(blocks):
        if name in COMPAT_BLOCKS:
            han.update(assigned.intersection(range(lo, hi + 1)))
        if name in COMPONENT_BLOCKS:
            components.update(assigned.intersection(range(lo, hi + 1)))
    if not han <= assigned:
        raise ValueError('UCD property contains unassigned codepoints')
    return han, components, assigned


class PuaTable(HTMLParser):
    """Read only the first (character) table, retaining cells and source links."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.table = 0
        self.active = False
        self.cell = None
        self.row = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table += 1
            self.active = self.table == 1
        if not self.active:
            return
        if tag == 'tr':
            self.row = {'line': self.getpos()[0], 'cells': [], 'links': []}
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif tag == 'a' and self.row is not None:
            href = dict(attrs).get('href')
            if href:
                self.row['links'].append(href)
        elif tag == 'br' and self.cell is not None:
            self.cell.append('\n')

    def handle_data(self, data):
        if self.active and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag in ('td', 'th') and self.cell is not None:
            self.row['cells'].append(''.join(self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == 'table':
            self.active = False


class Inventory:
    def __init__(self, sources):
        self.sources = sources
        self.entities = {}
        self.occurrences = []
        self.issues = []
        self.rows = []
        self.line_counts = {}
        self.definitions = []
        self.han, self.components, self.assigned = unicode_sets(
            sources['unicode-data'][1], sources['prop-list'][1], sources['blocks'][1])
        self.known_leaves = self.han | self.components

    def issue(self, source, line, reason, raw):
        self.issues.append(dict(source_id=source, line=line, reason=reason, raw=raw))

    def entity(self, token, source, membership):
        record = self.sources[source][0]
        cp = ord(token) if len(token) == 1 else None
        if cp is not None and not is_pua(cp):
            key = 'unicode:' + codepoint(cp)
            provider, version, local_id = 'Unicode', self.sources['unicode-data'][0]['version'], codepoint(cp)
            kind = 'han' if cp in self.han else 'component' if cp in self.components else 'other_unicode'
        else:
            # Numbered components belong to the IDS edition, not the font edition.
            namespace = 'ids-component' if cp is None else 'han-pua'
            version = record['version']
            local_id = token if cp is None else codepoint(cp)
            key = f'babelstone:{namespace}:{version}:{local_id}'
            provider, kind = 'BabelStone', 'numbered_component' if cp is None else 'pua'
        if key not in self.entities:
            self.entities[key] = dict(entity_id=key, provider=provider, version=version,
                                      local_id=local_id, kind=kind, character=token,
                                      unicode_assigned=cp in self.assigned if cp is not None and not is_pua(cp) else None,
                                      memberships=set(), source_ids=set(), mapping_status='unreviewed')
        self.entities[key]['memberships'].add(membership)
        self.entities[key]['source_ids'].add(source)
        return key

    def occurrence(self, token, source, line, role, **kwargs):
        key = self.entity(token, source, role)
        self.occurrences.append(dict(entity_id=key, source_id=source, line=line, role=role, **kwargs))
        return key

    def expression(self, expression, source, line, owner, variant, label=''):
        if ' or ' in expression:
            # This is source notation for alternatives, not Latin component leaves.
            for alternative, part in enumerate(expression.split(' or '), 1):
                self.expression(part, source, line, owner, f'{variant}.{alternative}', label)
            return
        tokens = list(re.finditer(r'\{[0-9]+\}|.', expression))
        pending = 1
        for match in tokens:
            token = match.group()
            position = match.start()
            if token == '〾':
                continue
            if token.isspace():
                self.issue(source, line, 'whitespace_in_ids', expression)
                continue
            if pending == 0:
                self.issue(source, line, 'extra_ids_operand', expression)
            pending -= 1
            if token in ARITY:
                pending += ARITY[token]
                continue
            context = dict(owner=owner, variant=variant, label=label, position=position, raw_token=token)
            if token == '？':
                self.occurrences.append(dict(entity_id=None, source_id=source, line=line,
                                             role='unknown_component', **context))
            elif token.startswith('{') and token.endswith('}'):
                self.occurrence(token, source, line, 'ids_component', **context)
            elif len(token) == 1 and (ord(token) >= 0x80 or token.isalnum()):
                # Preserve unusual Unicode leaves, but flag them for review.
                self.occurrence(token, source, line, 'ids_component', **context)
                if ord(token) not in self.known_leaves and not is_pua(ord(token)):
                    self.issue(source, line, 'unclassified_leaf', token)
            else:
                self.issue(source, line, 'unexpected_ids_token', token)
        if pending != 0:
            self.issue(source, line, 'ids_arity_mismatch', expression)

    def parse_ids(self, source):
        counts = Counter()
        seen = set()
        for line_number, raw in enumerate(self.sources[source][1].splitlines(), 1):
            if not raw.strip():
                counts['blank'] += 1
                continue
            if raw.startswith('#'):
                definition = re.match(r'#\s*(\{\d+\})\t([^\t]+)\t(.*)', raw)
                if definition:
                    counts['definition'] += 1
                    token, description, replacement = definition.groups()
                    key = self.occurrence(token, source, line_number, 'numbered_definition', raw=raw)
                    pua = re.search(r'\(([A-F0-9]{4,6})\s', description)
                    self.definitions.append(dict(entity_id=key, source_id=source, line=line_number,
                                                 description=description, replacement=replacement,
                                                 pua_codepoint_claim='U+' + pua[1] if pua else None,
                                                 pua_link_status='edition_alignment_unverified'))
                    # Description characters are context, not automatically constituent parts.
                    if replacement:
                        self.expression(replacement, source, line_number, key, 0, 'definition-replacement')
                else:
                    counts['comment'] += 1
                continue
            fields = raw.split('\t')
            if not re.fullmatch(r'U\+[0-9A-F]{4,6}', fields[0]):
                counts['unparsed'] += 1
                self.issue(source, line_number, 'unrecognized_line', raw)
                continue
            counts['entry'] += 1
            cp = int(fields[0][2:], 16)
            if cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
                self.issue(source, line_number, 'invalid_codepoint', raw)
                continue
            token = chr(cp)
            if len(fields) < 2 or fields[1] != token:
                self.issue(source, line_number, 'codepoint_character_mismatch', raw)
            if cp in seen:
                counts['duplicate'] += 1
                self.issue(source, line_number, 'duplicate_heading', raw)
            seen.add(cp)
            key = self.occurrence(token, source, line_number, source + '_heading')
            self.rows.append(dict(source_id=source, line=line_number, entity_id=key, fields=fields))
            variants = 0
            for field in fields[2:]:
                if not field.strip() or field.startswith('*'):
                    continue
                match = re.fullmatch(r'\^(.*?)\$(.*)', field)
                if not match:
                    self.issue(source, line_number, 'unparsed_ids_field', field)
                    continue
                variants += 1
                self.expression(match[1], source, line_number, key, variants, match[2])
            if not variants:
                counts['empty_ids'] += 1
        counts['total_lines'] = len(self.sources[source][1].splitlines())
        self.line_counts[source] = dict(counts)

    def parse_html(self):
        parser = PuaTable()
        parser.feed(self.sources['pua-page'][1])
        seen = set()
        for row in parser.rows:
            cells, line = row['cells'], row['line']
            if cells and cells[0] == 'Code Point':
                continue
            if not cells or not re.fullmatch(r'U\+[0-9A-F]{4,6}\*?', cells[0]):
                self.issue('pua-page', line, 'unrecognized_table_row', cells)
                continue
            cp = int(cells[0].rstrip('*')[2:], 16)
            if cp in seen:
                self.issue('pua-page', line, 'duplicate_heading', cells)
            seen.add(cp)
            key = self.occurrence(chr(cp), 'pua-page', line, 'pua-page_heading')
            self.rows.append(dict(source_id='pua-page', line=line, entity_id=key, **{'cells': cells, 'links': row['links']}))
            if len(cells) != 6:
                self.issue('pua-page', line, 'unexpected_column_count', cells)
            if len(cells) >= 3 and cells[2]:
                self.expression(cells[2], 'pua-page', line, key, 1)
        self.line_counts['pua-page'] = dict(table_rows=len(parser.rows), unique_headings=len(seen),
                                          total_lines=len(self.sources['pua-page'][1].splitlines()),
                                          scope='first character table; other HTML retained in source snapshot')

    def build(self):
        for cp in sorted(self.han):
            self.entity(chr(cp), 'unicode-data', 'unicode_han')
        for cp in sorted(self.components):
            self.entity(chr(cp), 'unicode-data', 'unicode_component')
        self.parse_ids('ids')
        self.parse_ids('ids-pua')
        self.parse_html()
        defined = {d['entity_id'] for d in self.definitions}
        for entity in self.entities.values():
            if entity['kind'] == 'numbered_component' and entity['entity_id'] not in defined:
                self.issue('ids', 0, 'undefined_numbered_component', entity['entity_id'])
        return self


def jsonl(path, rows):
    with Path(path).open('w', encoding='utf-8', newline='\n') as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def classify_issues(directory, output):
    """Group duplicated source observations without claiming to correct them."""
    directory = Path(directory)
    source_rows = {}
    with (directory / 'source-rows.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            source_rows[(row['source_id'], row['line'])] = row
    queue = defaultdict(lambda: {'evidence': [], 'reasons': set()})
    with (directory / 'parse-issues.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            issue = json.loads(line)
            row = source_rows.get((issue['source_id'], issue['line']))
            key = row['entity_id'] if row else f"unlocated:{issue['source_id']}:{issue['line']}"
            queue[key]['evidence'].append(issue)
            queue[key]['reasons'].add(issue['reason'])
    result = []
    for entity, item in sorted(queue.items()):
        reasons = sorted(item['reasons'])
        if any(r in reasons for r in ('extra_ids_operand', 'ids_arity_mismatch')):
            classification = 'source_structure_review'
        elif set(reasons) <= {'unclassified_leaf'}:
            classification = 'non_han_component'
        elif set(reasons) <= {'whitespace_in_ids'}:
            classification = 'source_whitespace'
        else:
            classification = 'parser_review'
        result.append(dict(entity_id=entity, classification=classification, reasons=reasons,
                           evidence=item['evidence'], status='unreviewed',
                           action='preserve identifiers and raw source; do not infer glyph equivalence'))
    write_json(output, result)
    return result


def build_inventory(lock, output):
    sources = verified_sources(lock)
    # Reject stale manifest version labels; identity must follow actual source bytes.
    checks = [('ids', '# File Date: ' + sources['ids'][0]['version']),
              ('ids-pua', '# Version ' + sources['ids-pua'][0]['version'] + ' '),
              ('pua-page', 'v. ' + sources['pua-page'][0]['version']),
              ('ucd-readme', 'final data files for version ' + sources['unicode-data'][0]['version'])]
    for source, expected in checks:
        if expected not in sources[source][1]:
            raise ValueError(f'Source version assertion failed: {source}')
    for source, prefix in [('blocks', '# Blocks-'), ('prop-list', '# PropList-')]:
        if prefix + sources['unicode-data'][0]['version'] + '.txt' not in sources[source][1]:
            raise ValueError(f'UCD version mismatch: {source}')
    inventory = Inventory(sources).build()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for key, row in sorted(inventory.entities.items()):
        rows.append({**row, 'memberships': sorted(row['memberships']), 'source_ids': sorted(row['source_ids'])})
    jsonl(output / 'inventory.jsonl', rows)
    jsonl(output / 'occurrences.jsonl', inventory.occurrences)
    jsonl(output / 'source-rows.jsonl', inventory.rows)
    jsonl(output / 'component-definitions.jsonl', inventory.definitions)
    jsonl(output / 'parse-issues.jsonl', inventory.issues)
    def members(group):
        return {r['entity_id'] for r in rows if group in r['memberships']}
    u, b = members('unicode_han'), members('ids_heading')
    p, h = members('ids-pua_heading'), members('pua-page_heading')
    differences = {'unicode_and_babelstone': sorted(u & b), 'unicode_only': sorted(u - b),
                   'babelstone_only': sorted(b - u), 'pua_txt_only': sorted(p - h), 'pua_html_only': sorted(h - p)}
    txt_ids, html_ids = {}, {}
    for row in inventory.rows:
        if row['source_id'] == 'ids-pua':
            txt_ids[row['entity_id']] = [f[1:f.index('$')] for f in row['fields'][2:] if f.startswith('^') and '$' in f]
        elif row['source_id'] == 'pua-page':
            html_ids[row['entity_id']] = [row['cells'][2]] if len(row['cells']) > 2 and row['cells'][2] else []
    differences['pua_ids_text_mismatches'] = sorted(k for k in p & h if txt_ids[k] != html_ids[k])
    write_json(output / 'source-differences.json', differences)
    summary = dict(schema_version=1, unicode_version=sources['unicode-data'][0]['version'],
                   source_hashes={key: value[0]['sha256'] for key, value in sorted(sources.items())},
                   entities=len(rows), kinds=dict(Counter(r['kind'] for r in rows)),
                   memberships=dict(Counter(g for r in rows for g in r['memberships'])),
                   occurrences=len(inventory.occurrences), source_rows=len(inventory.rows),
                   numbered_definitions=len(inventory.definitions), line_accounting=inventory.line_counts,
                   differences={key: len(value) for key, value in differences.items()},
                   parse_issues=dict(Counter(i['reason'] for i in inventory.issues)),
                   mapping_status={'unreviewed': len(rows)}, coverage_claim='inventory only; no glyph matching performed')
    write_json(output / 'summary.json', summary)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())
              if p.name in {'inventory.jsonl', 'occurrences.jsonl', 'source-rows.jsonl', 'component-definitions.jsonl',
                            'parse-issues.jsonl', 'source-differences.json', 'summary.json'}}
    write_json(output / 'checksums.json', hashes)
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return summary
