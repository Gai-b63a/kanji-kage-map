import unittest

from tools.report_dependency_issues import shortest_path


class DependencyTraceTests(unittest.TestCase):
    def test_path_keeps_raw_version_and_line_and_handles_cycle(self):
        edges = [dict(parent='a@1', target='b@2', raw_reference='b@2', line=4),
                 dict(parent='b@2', target='a@1', raw_reference='a', line=1),
                 dict(parent='b@2', target='missing', raw_reference='missing', line=2)]
        self.assertEqual(shortest_path('a@1', 'missing', edges), [edges[0], edges[2]])
        self.assertEqual(shortest_path('a@1', 'a@1', edges), [])
        with self.assertRaises(ValueError):
            shortest_path('a@1', 'unreachable', edges)

    def test_selects_shortest_path(self):
        edges = [dict(parent='a', target='b', line=1), dict(parent='b', target='c', line=1),
                 dict(parent='a', target='c', line=2)]
        self.assertEqual(shortest_path('a', 'c', edges), [edges[2]])
