# Candidate dataset v0.1.0-preview.2

This package contains 109,556 edition-qualified identifiers, 955,185 candidate
links, original pinned KAGE records, dependency edges, source research, and
three scoped review decisions. Candidate presence is not glyph equivalence.

The dataset was regenerated from the locked inputs. Relative to preview.1,
the only mapping changes are the source ID `USAT05567` and search status
`no_candidate_in_searched_rules` for `babelstone:han-pua:1.473:U+EADD`.
All other mapping fields, inventory records, glyphs, edges and issues match
preview.1. The manifest records a full-table comparison against the exact
public baseline, followed by another comparison after review import.

There are 105,657 identifiers with candidates, 934 with no candidate under
the searched rules, and 2,965 requiring source evidence. No glyph is
automatically selected. Seven candidate links have dependency issues.

## Offline lookup

Python 3.11 or newer is required; no third-party Python package is needed.
Verify the ZIP using the external SHA256SUMS, extract it, then decompress:

```python
import gzip, shutil
with gzip.open('kanji-kage-map-v0.1.0-preview.2.sqlite3.gz', 'rb') as source:
    with open('dataset.sqlite3', 'xb') as target:
        shutil.copyfileobj(source, target)
```

```text
python -m kanji_kage_map lookup U+4E00 --dataset dataset.sqlite3 --glyph u4e00 --output one.json
python -m kanji_kage_map lookup U+6D77 --dataset dataset.sqlite3 --glyph u6d77 --output sea.json
python -m kanji_kage_map lookup babelstone:han-pua:1.473:U+EADD --dataset dataset.sqlite3 --output corrected.json
python -m kanji_kage_map lookup-source-leads babelstone:han-pua:1.473:U+E0C7 --dataset dataset.sqlite3 --unicode-target U+32580 --glyph u32580 --output pua-lead.json
```

Review history is embedded and returned under `review_decisions`. The U+4E00
decision is structural equivalence of u4e00@46 to Japanese source J0-306C only.
The U+6D77 decisions record difference from G0-3A23 and inconclusive whole-glyph
evidence for J0-3324. These are AI judgments, not independent human sign-off.
They do not change the original mapping review state or imply global equivalence.

PUA source-ID matches to Unicode are research leads. The PUA font/table edition
mismatch and unfinished reviews remain. See docs/GOAL-AUDIT.md and the source
and review records for the specific limits. Historical publication documents
refer to their named releases; this package's manifest identifies this build.

Fonts, original PUA HTML, Unicode chart images and original archives are not
included. See NOTICE.md and licenses/ for the separate code and data terms.
The internal SHA256SUMS covers ZIP contents; external SHA256SUMS covers assets.
