"""Represents the state of an HTML document.

The provided `HtmlDocumentState` class contains and exposes all fields required for
representing the current state of the HTML to text conversion.

Standard CSS profiles.

- `strict`: this profile corresponds to the defaults used by Firefox
- `relaxed`: this profile is more suited for text analytics, since it ensures
             that whitespaces are inserted between span and div elements
             preventing cases where two words stick together.
"""
from __future__ import annotations

from typing import Dict

from attribute import Attribute
from canvas import Canvas
from html_element import DEFAULT_HTML_ELEMENT, HtmlElement
from html_properties import Display, WhiteSpace

DEFAULT_CSS_PROFILE_NAME = "relaxed"

STRICT_CSS_PROFILE = {
    "body": HtmlElement(display=Display.inline, whitespace=WhiteSpace.normal),
    "head": HtmlElement(display=Display.none),
    "link": HtmlElement(display=Display.none),
    "meta": HtmlElement(display=Display.none),
    "script": HtmlElement(display=Display.none),
    "title": HtmlElement(display=Display.none),
    "style": HtmlElement(display=Display.none),
    "p": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "figure": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "h1": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "h2": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "h3": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "h4": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "h5": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "h6": HtmlElement(display=Display.block, margin_before=1, margin_after=1),
    "ul": HtmlElement(
        display=Display.block, margin_before=0, margin_after=0, padding_inline=4
    ),
    "ol": HtmlElement(
        display=Display.block, margin_before=0, margin_after=0, padding_inline=4
    ),
    "li": HtmlElement(display=Display.block),
    "address": HtmlElement(display=Display.block),
    "article": HtmlElement(display=Display.block),
    "aside": HtmlElement(display=Display.block),
    "div": HtmlElement(display=Display.block),
    "footer": HtmlElement(display=Display.block),
    "header": HtmlElement(display=Display.block),
    "hgroup": HtmlElement(display=Display.block),
    "layer": HtmlElement(display=Display.block),
    "main": HtmlElement(display=Display.block),
    "nav": HtmlElement(display=Display.block),
    "figcaption": HtmlElement(display=Display.block),
    "blockquote": HtmlElement(display=Display.block),
    "q": HtmlElement(prefix='"', suffix='"'),
    # Handling of <pre>
    "pre": HtmlElement(display=Display.block, whitespace=WhiteSpace.pre),
    "xmp": HtmlElement(display=Display.block, whitespace=WhiteSpace.pre),
    "listing": HtmlElement(display=Display.block, whitespace=WhiteSpace.pre),
    "plaintext": HtmlElement(display=Display.block, whitespace=WhiteSpace.pre),
}

RELAXED_CSS_PROFILE = STRICT_CSS_PROFILE.copy()
RELAXED_CSS_PROFILE["div"] = HtmlElement(display=Display.block, padding_inline=2)
RELAXED_CSS_PROFILE["span"] = HtmlElement(
    display=Display.inline, prefix=" ", suffix=" ", limit_whitespace_affixes=True
)


CSS_PROFILES = {"strict": STRICT_CSS_PROFILE, "relaxed": RELAXED_CSS_PROFILE}

class ParserConfig:
    """Encapsulate configuration options and CSS definitions."""

    def __init__(
        self,
        css: Dict[str, HtmlElement] = None,
        display_images: bool = False,
        deduplicate_captions: bool = False,
        display_links: bool = False,
        display_anchors: bool = False,
        table_cell_separator: str = "  ",
    ):
        """Create a ParserConfig configuration.

        Args:
            css: an optional custom CSS definition.
            display_images: whether to include image tiles/alt texts.
            deduplicate_captions: whether to deduplicate captions such as image
                titles (many newspaper include images and video previews with
                identical titles).
            display_links: whether to display link targets
                           (e.g. `[Python](https://www.python.org)`).
            display_anchors: whether to display anchors (e.g. `[here](#here)`).
            table_cell_separator: separator to use between table cells.
        """
        self.display_images = display_images
        self.deduplicate_captions = deduplicate_captions
        self.display_links = display_links
        self.display_anchors = display_anchors
        self.css = css or CSS_PROFILES[DEFAULT_CSS_PROFILE_NAME]
        self.attribute_handler = Attribute()
        self.table_cell_separator = table_cell_separator

    def parse_a(self) -> bool:
        """Indicate whether the text output should contain links or anchors.

        Returns
            Whether we need to parse <a> tags.
        """
        return self.display_links or self.display_anchors

class HtmlDocumentState:
    """Represents the state of the parsed html document."""

    def __init__(self, config: ParserConfig):
        # instance variables
        self.canvas = Canvas()
        self.config = config
        self.css = config.css
        self.apply_attributes = config.attribute_handler.apply_attributes

        self.tags = [self.css["body"].set_canvas(self.canvas)]
        self.current_table = []
        self.li_counter = []
        self.last_caption = None

        # used if display_links is enabled
        self.link_target = ""

    def apply_starttag_layout(self, tag, attrs):
        """Compute the layout of the tag.

        Compute the style of the current :class:`HtmlElement`, based on

        1. the used :attr:`css`,
        2. apply attributes and css with :meth:`~Attribute.apply_attributes`
        3. add the `HtmlElement` to the list of open tags.

        Args:
          tag: the HTML start tag to process.
          attrs: a dictionary of HTML attributes and their respective values.
        """
        # use the css to handle tags known to it :)
        cur = self.tags[-1].get_refined_html_element(
            self.apply_attributes(
                attrs,
                html_element=self.css.get(tag, DEFAULT_HTML_ELEMENT)
                .__copy__()
                .set_tag(tag),
            )
        )
        self.tags.append(cur)