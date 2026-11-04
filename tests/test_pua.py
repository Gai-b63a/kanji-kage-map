import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from kanji_kage_map.pua import discover_pua


class PuaDiscoveryTests(unittest.TestCase):
    def test_literal_source_is_searched_without_inventing_hyphen(self):
        cache = Path(__file__).resolve().parents[1] / '.cache/tests'
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as temp:
            root = Path(temp)
            database = root / 'index.sqlite3'
            with sqlite3.connect(database) as db:
                db.executescript("CREATE TABLE metadata(key,value);"
                                 "INSERT INTO metadata VALUES ('build_status','complete');"
                                 "INSERT INTO metadata VALUES ('snapshot_sha256','snapshot');"
                                 "CREATE TABLE latest(name,revision,related,line);")
                db.execute('INSERT INTO latest VALUES (?,?,?,?)', ('usat-05567', 2, 'u3013', 10))
            db.close()
            key = 'babelstone:han-pua:1.473:U+EADD'
            inventory = root / 'inventory.jsonl'
            inventory.write_text(json.dumps(dict(entity_id=key, provider='BabelStone')) + '\n')
            rows = root / 'rows.jsonl'
            rows.write_text(json.dumps(dict(entity_id=key, source_id='pua-page', line=21253,
                                             cells=['', '', '', '', '', 'USAT05567'], links=[])) + '\n')
            def run():
                with contextlib.redirect_stdout(io.StringIO()):
                    discover_pua(database, rows, inventory, root / 'out')
                return json.loads((root / 'out/pua-candidates.jsonl').read_text())
            missing = run()
            self.assertEqual(missing['source_refs'], ['USAT05567'])
            self.assertEqual(missing['search_status'], 'no_candidate_in_searched_rules')
            self.assertEqual(missing['candidates'], [])
            with sqlite3.connect(database) as db:
                db.execute('INSERT INTO latest VALUES (?,?,?,?)', ('usat05567', 3, 'u3013', 11))
            db.close()
            found = run()
            self.assertEqual(found['candidates'][0]['name'], 'usat05567')
            self.assertEqual(found['candidates'][0]['revision'], 3)
            self.assertEqual(found['review_status'], 'unreviewed')
            self.assertIsNone(found['selected_glyph'])
