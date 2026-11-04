import sqlite3
import unittest
from tools.audit_syntax_impact import propagate


class SyntaxImpactTests(unittest.TestCase):
    def test_transitive_diamond_cycle_and_revision_isolation(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE dependencies(parent,target)')
            db.executemany('INSERT INTO dependencies VALUES (?,?)', [
                ('root@1','left@1'), ('root@1','right@1'), ('left@1','bad@1'),
                ('right@1','bad@1'), ('bad@1','left@1'), ('other@1','bad@2'),
                ('root@1','second@3')])
            impact = propagate(db,['bad@1','second@3'])
            self.assertEqual(impact['root@1'],['bad@1','second@3'])
            self.assertEqual(impact['left@1'],['bad@1'])
            self.assertNotIn('other@1',impact)
            self.assertNotIn('bad@2',impact)
            self.assertEqual(propagate(db,[]),{})
