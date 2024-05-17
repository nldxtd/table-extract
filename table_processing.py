from typing import Callable, Dict
from resiliparse.parse.html import HTMLTree
from inscriptis import get_text
# from haruka_parser.extract import extract_text

from canvas import Canvas
from html_state import HtmlDocumentState, ParserConfig

# from tags.a_tag import a_start_handler, a_end_handler
# from tags.br_tag import br_start_handler
# from tags.img_tag import img_start_handler
# from tags.list_tag import (
#     ul_start_handler,
#     ol_start_handler,
#     li_start_handler,
#     ul_end_handler,
#     ol_end_handler,
# )
from tags.table_tag import (
    table_start_handler,
    tr_start_handler,
    td_start_handler,
    table_end_handler,
    td_end_handler,
)

class TableExtractor():
    
    def __init__(self, html_tree, config: ParserConfig = None) -> None:
        
        config = config or ParserConfig()

        # setup start and end tag call tables
        self.start_tag_handler_dict: Dict[
            str, Callable[[HtmlDocumentState, Dict], None]
        ] = {
            "table": table_start_handler,
            "tr": tr_start_handler,
            "td": td_start_handler,
            "th": td_start_handler,
            # "ul": ul_start_handler,
            # "ol": ol_start_handler,
            # "li": li_start_handler,
            # "br": br_start_handler,
            # "a": a_start_handler if config.parse_a() else None,
            # "img": img_start_handler if config.display_images else None,
        }
        self.end_tag_handler_dict: Dict[str, Callable[[HtmlDocumentState], None]] = {
            "table": table_end_handler,
            # "ul": ul_end_handler,
            # "ol": ol_end_handler,
            "td": td_end_handler,
            "th": td_end_handler,
            # "a": a_end_handler if config.parse_a() else None,
        }

        self.canvas = self._parse_html_tree(HtmlDocumentState(config), html_tree)

    def _parse_html_tree(self, state: HtmlDocumentState, tree) -> Canvas:
        """Parse the HTML tree.

        Args:
            tree: the HTML tree to parse.
        """
        if isinstance(tree.tag, str):
            attrs = {}
            if tree.attrs:
                for attr in tree.attrs:
                    attrs[attr] = tree.getattr(attr)
            state.apply_starttag_layout(tree.tag, attrs)

            if handler := self.start_tag_handler_dict.get(tree.tag):
                handler(state, attrs)
            cur = state.tags[-1]
            cur.canvas.open_tag(cur)

            state.tags[-1].write(tree.value)

            for node in tree.child_nodes:
                self._parse_html_tree(state, node)

            # handle the endtag
            if handler := self.end_tag_handler_dict.get(tree.tag):
                handler(state)
            prev = state.tags.pop()
            prev.canvas.close_tag(prev)

        return state.canvas

    def get_text(self) -> str:
        """Return the text extracted from the HTML page."""
        return self.canvas.get_text()


# Extracting text including tables from HTML
def extract_tables(tree):

    tables = tree.document.query_selector_all("table")

    for table in tables:
        table_tree = HTMLTree.parse(str(table))
        table_text = TableExtractor(table_tree.body).get_text()
        new_p = tree.create_element('pre')
        new_p.html = table_text
        table.parent.replace_child(new_p, table)
  

if __name__ == "__main__":

    html_content = """
<html>
<head><title>Sample HTML with Table</title></head>
<body>
<table border="1">
  <tr>
    <th>Header 1</th>
    <th>Header 2</th>
    <th>Header 3</th>
  </tr>
  <tr>
    <td>Row 1, Col 1</td>
    <td>Row 1, Col 2</td>
    <td>Row 1, Col 3</td>
  </tr>
  <h1>this is a header</h1>
  <br/>
  <tr>
    <td>Row 2, Col 1</td>
    <td>Row 2, Col 2</td>
    <td>Row 2, Col 3</td>
  </tr>
  <h1>this is another header</h1>
</table>
</body>
</html>
"""

    tree = HTMLTree.parse(html_content)
    extract_tables(tree)
