"""Rasterize original font text and KAGE polygons side by side for inspection."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / '.cache/review')]
from PIL import Image, ImageDraw, ImageFont
from kanji_kage_map.sources import verified_sources

font_record, _ = verified_sources(ROOT / 'review-sources.lock.json')['babelstone-han-pua-font']
font = ImageFont.truetype(str(ROOT / font_record['path']), 220)
labels = ImageFont.load_default(size=15)
records = json.loads((ROOT / 'data/generated/review/rendered.json').read_text(encoding='utf-8'))
sheet = Image.new('RGB', (1200, 4 * 330 + 60), 'white')
draw = ImageDraw.Draw(sheet)
draw.text((20, 10), 'DIAGNOSTIC ONLY: font 1.472 (left) vs KAGE (right); inventory 1.473 - edition mismatch', fill='black', font=labels)
for index, record in enumerate(records):
    x, y = (index % 3) * 400, 60 + (index // 3) * 330
    cp = int(record['entity_id'].split('U+')[-1], 16)
    draw.text((x + 10, y), f'U+{cp:04X}  {record["glyph"]}', fill='black', font=labels)
    draw.text((x + 10, y + 24), 'font 1.472              KAGE 0.7.0', fill='black', font=labels)
    box = font.getbbox(chr(cp))
    # Normalize both drawings into a comparable box. Preserve aspect ratio.
    tile = Image.new('RGB', (300, 300), 'white')
    ImageDraw.Draw(tile).text((10-box[0], 10-box[1]), chr(cp), font=font, fill='black')
    glyph = tile.crop((10, 10, 10 + box[2]-box[0], 10 + box[3]-box[1]))
    glyph.thumbnail((170, 230))
    sheet.paste(glyph, (x + 10, y + 65))
    if record['render_status'] == 'finite_nonempty':
        points = [p for contour in record['contours'] for p in contour]
        minx, maxx = min(p[0] for p in points), max(p[0] for p in points)
        miny, maxy = min(p[1] for p in points), max(p[1] for p in points)
        scale = min(170/(maxx-minx), 230/(maxy-miny))
        for contour in record['contours']:
            draw.polygon([(x + 210 + (px-minx)*scale, y + 65 + (py-miny)*scale) for px,py in contour], fill='black')
    else:
        draw.text((x + 210, y + 65), 'RENDER FAILED', fill='red', font=labels)
    draw.line((x, y+315, x+390, y+315), fill='#cccccc')
sheet.save(ROOT / 'data/generated/review/diagnostic.png')
