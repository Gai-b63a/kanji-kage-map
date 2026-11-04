"""Conservative static checks against @kurgm/kage-engine 0.7.0 input reads.

This is not geometric validation or certification of full KAGE semantics.
Unconsumed trailing fields and comment payloads are deliberately not numeric fields.
"""
import math
import re

INTEGER = re.compile(r'[0-9]+\Z')
REFERENCE = re.compile(r'[a-z0-9_.-]+(?:@[0-9]+)?\Z')
POINT_FIELDS = {1: 7, 2: 9, 3: 9, 4: 9, 6: 11, 7: 11, 12: 11}


def inspect_line(raw):
    fields = raw.split(':')
    findings = []

    def flag(reason, **context):
        findings.append(dict(reason=reason, **context))

    def number(index, integer=False):
        if index >= len(fields):
            flag('missing_numeric_field', field=index + 1)
            return None
        if not fields[index].strip():
            flag('blank_numeric_zero_coercion', field=index + 1)
            return 0
        token = fields[index]
        try:
            value = float(token)
        except ValueError:
            flag('nonnumeric_field', field=index + 1, value=token)
            return None
        if not math.isfinite(value):
            flag('nonfinite_field', field=index + 1, value=token)
            return None
        if integer and not INTEGER.fullmatch(token):
            flag('noncanonical_nonnegative_integer', field=index + 1, value=token)
        return value

    if not INTEGER.fullmatch(fields[0]):
        flag('invalid_command_tag', field=1, value=fields[0])
        return findings
    command = int(fields[0])
    base = command % 100
    if command == 99:
        values = {i: number(i) for i in range(1, 7)}
        if len(fields) <= 7 or not REFERENCE.fullmatch(fields[7]):
            flag('invalid_reference_field', field=8)
        # sx=200, sy=0 becomes zero stretch and does not consume sx2/sy2.
        if (values[1] is not None and math.floor(values[1]) > 100
                and (math.floor(values[1]) != 200 or values[2] != 0)):
            number(9)
            number(10)
        return findings
    if base == 0:
        # Non-transform zero records are comments / no-op in this engine.
        if len(fields) > 1 and fields[1] in ('97', '98', '99'):
            for i in range(1, 7):
                number(i, integer=i < 3)
            if fields[1] == '99' and (len(fields) < 3 or fields[2] not in ('1', '2', '3')):
                flag('unsupported_rotation_mode')
        return findings
    if base == 9:
        flag('engine_noop_command', command=command)
        return findings
    if base not in POINT_FIELDS:
        flag('engine_unsupported_command', command=command)
        return findings
    for i in range(1, POINT_FIELDS[base]):
        number(i, integer=i < 3)
    return findings


def inspect_kage(data):
    if not data:
        return [dict(line=0, raw=data, reason='empty_kage')]
    return [dict(line=line, raw=raw, **finding)
            for line, raw in enumerate(data.split('$'), 1)
            for finding in inspect_line(raw)]


def inspect_bundle(bundle):
    """Report direct findings for every available dependency, deduplicating aliases."""
    checked, findings = set(), []
    for alias, record in bundle['glyphs'].items():
        reference = f"{record['name']}@{record['revision']}"
        if reference in checked:
            continue
        checked.add(reference)
        findings.extend(dict(reference=reference, **item) for item in inspect_kage(record['data']))
    return dict(engine='@kurgm/kage-engine@0.7.0',
                status='findings' if findings else 'no_findings',
                glyphs_checked=len(checked), findings=findings,
                scope='required numeric inputs and engine dispatch in available bundle glyphs; not geometry or equivalence')
