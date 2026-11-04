"""Attach scoped visual observations without changing mapping decisions."""
import hashlib
import json
from pathlib import Path
import re


def attach_feature_reviews(result, path):
    raw = Path(path).read_bytes()
    review = json.loads(raw)
    if review['format'] != 'visual-feature-review-v1':
        raise ValueError('Unsupported visual review format')
    if review['snapshot_sha256'] != result['snapshot_sha256']:
        raise ValueError('Review and dataset snapshots differ')
    if review['full_glyph_match_status'] != 'not_determined' or review['selected_glyph'] is not None:
        raise ValueError('Feature reviews cannot certify whole-glyph matches')
    if not review['reviewer'] or not review['review_date'] or not review['scope']:
        raise ValueError('Review attribution and scope are required')
    if not re.fullmatch('[0-9a-f]{64}', review['source']['sha256']):
        raise ValueError('Pinned source hash required')
    candidates = {f"{c['name']}@{c['revision']}" for c in result['candidates']}
    requested = result['bundle']['root'] if result.get('bundle') else None
    observations = []
    for item in review['observations']:
        if item['entity_id'] != result['entity_id']:
            continue
        if item['glyph_reference'] not in candidates:
            raise ValueError('Reviewed glyph revision is not a recorded candidate')
        equal = item['chart_feature'] == item['kage_feature']
        if item['result'] != ('feature_agreement' if equal else 'feature_conflict'):
            raise ValueError('Feature decision contradicts recorded observations')
        if not item['source_id'] or not re.fullmatch('[0-9a-f]{64}', item['svg_sha256']):
            raise ValueError('Source location and rendered artifact hash required')
        if requested is None or requested == item['glyph_reference']:
            observations.append(item)
    return dict(result, feature_reviews=dict(
        file_sha256=hashlib.sha256(raw).hexdigest(), source=review['source'],
        reviewer=review['reviewer'], review_date=review['review_date'], scope=review['scope'],
        render_engine=review['render_engine'], render_options=review['render_options'],
        observations=observations, full_glyph_match_status='not_determined'))
