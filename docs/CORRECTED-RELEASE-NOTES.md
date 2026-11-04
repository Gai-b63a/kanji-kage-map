# v0.1.0-preview.2 — corrected candidates and scoped reviews

Rebuilt from the pinned original inputs. All 109,556 identifiers remain.
The only mapping changes from preview.1 are the source ID `USAT05567` and
the search state for BabelStone Han PUA 1.473 U+EADD. It still has no candidate
under the searched rules. All other mapping fields, original KAGE, inventory,
dependency edges and issues are verified against the exact public preview.1 DB.

This release also embeds the three scoped AI review records previously shipped
in review.1: structural equivalence for one Japanese source of U+4E00, difference
for one Chinese source of U+6D77, and inconclusive whole-glyph evidence for one
Japanese source of U+6D77. Reviews do not automatically select candidates.

105,657 identifiers have candidates; 934 have no candidate in the searched
rules; 2,965 require source evidence. Seven candidate links have dependency
issues. Full glyph review is unfinished. Source-ID matches to Unicode are
research leads, not certified PUA glyph equivalence. The PUA font/table edition
mismatch remains documented.

Download the offline ZIP for code, DB, research records, examples and licenses.
Verify it with SHA256SUMS, extract, and follow README.md. The compressed DB and
manifest are also available separately. The manifest records exact hashes and
all-table comparisons before and after review import. Internal ZIP checksums
cover every payload file. Original fonts, chart images and PUA HTML are excluded.

Earlier releases are unchanged. This is a provisional research dataset.
