import unittest
from kanji_kage_map.audit import propagate


class DependencyAuditTests(unittest.TestCase):
    def test_diamond_shared_reference_and_duplicate_edges_are_acyclic(self):
        self.assertEqual(propagate([[1, 2, 1], [3], [3], []], [0, 0, 0, 0]), [0, 0, 0, 0])

    def test_fault_reaches_all_ancestors_but_not_sibling(self):
        self.assertEqual(propagate([[1, 2], [3], [], []], [0, 0, 0, 1]), [1, 1, 0, 1])

    def test_cycle_marks_ancestors_not_unrelated_nodes(self):
        self.assertEqual(propagate([[1], [2], [1, 3], [], []], [0, 0, 0, 0, 0]), [64, 64, 64, 0, 0])

    def test_self_cycle_and_missing_reference_both_propagate(self):
        self.assertEqual(propagate([[1], [1, 2], []], [0, 0, 1]), [65, 65, 1])


if __name__ == '__main__':
    unittest.main()
