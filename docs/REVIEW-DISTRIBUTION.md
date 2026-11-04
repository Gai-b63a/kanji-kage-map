# Review supplement v0.1.0-review.1

This package adds three scoped review decisions to the unchanged candidate data
from v0.1.0-preview.1. It contains lookup code, a compressed portable database,
source-ID research records, provenance, examples, and licenses.

The U+4E00 / u4e00@46 decision is structural equivalence to the Japanese source
J0-306C only. The two U+6D77 / u6d77@19 decisions are difference from G0-3A23
and insufficient whole-glyph evidence for J0-3324. These are AI judgments,
not independent human sign-off or global glyph equivalence claims.

## Offline use

Requires Python 3.11 or newer. No third-party Python package is needed.

Verify the ZIP against the external SHA256SUMS, extract it, then decompress:

```python
import gzip, shutil
with gzip.open('kanji-kage-map-v0.1.0-review.1.sqlite3.gz', 'rb') as source:
    with open('dataset.sqlite3', 'xb') as target:
        shutil.copyfileobj(source, target)
```

```text
python -m kanji_kage_map lookup U+4E00 --dataset dataset.sqlite3 --glyph u4e00 --output one.json
python -m kanji_kage_map lookup U+6D77 --dataset dataset.sqlite3 --glyph u6d77 --output sea.json
python -m kanji_kage_map lookup-source-leads babelstone:han-pua:1.473:U+E0C7 --dataset dataset.sqlite3 --unicode-target U+32580 --glyph u32580 --output pua-lead.json
```

Review history is returned in `review_decisions`; no sidecar is required.
Original `selected_glyph`, candidate and coverage values are unchanged.
The full base population is 109,556 identifiers. The initial database's
confirmed count remains zero; the separate ledger has one scoped equivalence,
one difference and one inconclusive judgment.

The known U+EADD source-ID extraction correction is included as documentation
and in the source-relation records, but the original mapping row deliberately
retains preview.1 values. This supplement is not a regenerated candidate release.

The font/table edition mismatch and unfinished reviews remain. Fonts, original
PUA HTML, Unicode chart images and original archives are not bundled.
See NOTICE.md and licenses/ for the distinct data and code terms.

The package manifest records the exact base and derived DB hashes and verifies
every original data row remained identical. SHA256SUMS inside the ZIP covers
its payload; the external SHA256SUMS covers all release assets.
