import unittest
from tools.extract_pua_source_links import TableLinks


class PuaSourceLinksTests(unittest.TestCase):
    def test_columns_entities_and_nested_labels(self):
        p=TableLinks();p.feed('<tr><td id="U_E080">U+E080</td><td>x</td><td>ids</td><td>note</td><td><a href="book?a=1&amp;b=2"><span>folio</span> 1</a></td><td><a href="ref">UK-1</a></td></tr>')
        self.assertEqual(p.rows[0]['code'],'U+E080')
        self.assertEqual([(x['column'],x['href'],x['label']) for x in p.rows[0]['links']],[(4,'book?a=1&b=2','folio 1'),(5,'ref','UK-1')])

    def test_empty_row_not_lost_and_navigation_not_a_character(self):
        p=TableLinks();p.feed('<tr><td><a href="download">font</a></td></tr><tr><td id="U_F55A">U+F55A</td><td></td><td></td><td></td><td></td><td></td></tr>')
        self.assertEqual(p.rows,[dict(code='U+F55A',links=[])])
