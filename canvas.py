#!/usr/bin/env python
# encoding: utf-8

"""Classes used for rendering (parts) of the canvas.

Every parsed :class:`.html_element.HtmlElement` writes its
textual content to the canvas which is managed by the following three classes:

  - :class:`Canvas` provides the drawing board on which the HTML page is
    serialized and annotations are recorded.
  - :class:`Block` contains the current line to which text is written.
  - :class:`Prefix` handles indentation and bullets that prefix a line.
"""

from __future__ import annotations

from contextlib import suppress
from html import unescape

from html_element import HtmlElement
from html_properties import Display, WhiteSpace


class Prefix:
    """Class Prefix manages paddings and bullets that prefix an HTML block.

    Attributes:
        current_padding: the number of characters used for the current
                         left-indentation.
        paddings: the list of paddings for the current and all previous tags.
        bullets: the list of bullets in the current and all previous tags.
        consumed: whether the current bullet has already been consumed.
    """

    __slots__ = ("current_padding", "paddings", "bullets", "consumed")

    def __init__(self):
        self.current_padding = 0
        self.paddings = []
        self.bullets = []
        self.consumed = False

    def register_prefix(self, padding_inline: int, bullet: str) -> None:
        """Register the given prefix.

        Args:
            padding_inline: the number of characters used for padding_inline
            bullet: an optional bullet.
        """
        self.current_padding += padding_inline
        self.paddings.append(padding_inline)
        self.bullets.append(bullet if bullet else "")

    def remove_last_prefix(self) -> None:
        """Remove the last prefix from the list."""
        with suppress(IndexError):
            self.current_padding -= self.paddings.pop()
            del self.bullets[-1]

    def pop_next_bullet(self) -> str:
        """Pop the next bullet to use, if any bullet is available."""
        next_bullet_idx = (
            next((-idx for idx, val in enumerate(reversed(self.bullets)) if val), 1) - 1
        )

        if not next_bullet_idx:
            return ""

        bullet = self.bullets[next_bullet_idx]
        self.bullets[next_bullet_idx] = ""
        return bullet

    @property
    def first(self) -> str:
        """Return the prefix used at the beginning of a tag.

        Note::
            A new block needs to be prefixed by the current padding and bullet.
            Once this has happened (i.e., :attr:`consumed` is set to `True`) no
            further prefixes should be used for a line.
        """
        if self.consumed:
            return ""

        self.consumed = True
        bullet = self.pop_next_bullet()
        return " " * (self.current_padding - len(bullet)) + bullet

    @property
    def unconsumed_bullet(self) -> str:
        """Yield any yet unconsumed bullet.

        Note::
            This function yields the previous element's bullets, if they have
            not been consumed yet.
        """
        if self.consumed:
            return ""

        bullet = self.pop_next_bullet()
        if not bullet:
            return ""

        padding = self.current_padding - self.paddings[-1]
        return " " * (padding - len(bullet)) + bullet

    @property
    def rest(self) -> str:
        """Return the prefix used for new lines within a block.

        This prefix is used for pre-text that contains newlines. The lines
        need to be prefixed with the right padding to preserver the
        indentation.
        """
        return " " * self.current_padding


class Block:
    """The current block of text.

    A block usually refers to one line of output text.

    .. note::
        If pre-formatted content is merged with a block, it may also contain
        multiple lines.

    Args:
        idx: the current block's start index.
        prefix: prefix used within the current block.
    """

    __slots__ = ("idx", "prefix", "_content", "collapsable_whitespace")

    def __init__(self, idx: int, prefix: Prefix):
        self.idx = idx
        self.prefix = prefix
        self._content = ""
        self.collapsable_whitespace = True

    def merge(self, text: str, whitespace: WhiteSpace) -> None:
        """Merge the given text with the current block.

        Args:
            text: the text to merge.
            whitespace: whitespace handling.
        """
        if whitespace == WhiteSpace.pre:
            self.merge_pre_text(text)
        else:
            self.merge_normal_text(text)

    def merge_normal_text(self, text: str) -> None:
        """Merge the given text with the current block.

        Args:
            text: the text to merge

        Note:
            If the previous text ended with a whitespace and text starts with one, both
             will automatically collapse into a single whitespace.
        """
        normalized_text = []

        for ch in text:
            if not ch.isspace():
                normalized_text.append(ch)
                self.collapsable_whitespace = False
            elif not self.collapsable_whitespace:
                normalized_text.append(" ")
                self.collapsable_whitespace = True

        if normalized_text:
            text = (
                "".join((self.prefix.first, *normalized_text))
                if not self._content
                else "".join(normalized_text)
            )
            text = unescape(text)
            self._content += text
            self.idx += len(text)

    def merge_pre_text(self, text: str) -> None:
        """Merge the given pre-formatted text with the current block.

        Args:
            text: the text to merge
        """
        text = "".join((self.prefix.first, text.replace("\n", "\n" + self.prefix.rest)))
        text = unescape(text)
        self._content += text
        self.idx += len(text)
        self.collapsable_whitespace = False

    def is_empty(self) -> bool:
        return len(self.content) == 0

    @property
    def content(self):
        if not self.collapsable_whitespace:
            return self._content

        if self._content.endswith(" "):
            self._content = self._content[:-1]
            self.idx -= 1
        return self._content

    def new_block(self) -> "Block":
        """Return a new Block based on the current one."""
        self.prefix.consumed = False
        return Block(idx=self.idx + 1, prefix=self.prefix)


class Canvas:
    r"""The text Canvas on which we writes the HTML page.

    Attributes:
        margin: the current margin to the previous block (this is required to
            ensure that the `margin_after` and `margin_before` constraints of
            HTML block elements are met).
        current_block: A :class:`Block` which
            merges the input text into a block (i.e., line).
        blocks: a list of strings containing the completed blocks (i.e.,
            text lines). Each block spawns at least one line.
    """

    __slots__ = (
        "blocks",
        "current_block",
        "margin",
    )

    def __init__(self):
        self.margin = 1000  # margin to the previous block
        self.current_block = Block(0, Prefix())
        self.blocks = []

    def open_tag(self, tag: HtmlElement) -> None:
        """Register that a tag is opened.

        Args:
            tag: the tag to open.
        """

        if tag.display == Display.block:
            self.open_block(tag)

    def open_block(self, tag: HtmlElement) -> None:
        """Open an HTML block element."""
        # write missing bullets, if no content has been written
        if not self.flush_inline() and tag.list_bullet:
            self.write_unconsumed_bullet()
        self.current_block.prefix.register_prefix(tag.padding_inline, tag.list_bullet)

        # write the block margin
        required_margin = max(tag.previous_margin_after, tag.margin_before)
        if required_margin > self.margin:
            required_newlines = required_margin - self.margin
            self.current_block.idx += required_newlines
            self.blocks.append("\n" * (required_newlines - 1))
            self.margin = required_margin

    def write_unconsumed_bullet(self) -> None:
        """Write unconsumed bullets to the blocks list."""
        bullet = self.current_block.prefix.unconsumed_bullet
        if bullet:
            self.blocks.append(bullet)
            self.current_block.idx += len(bullet)
            self.current_block = self.current_block.new_block()
            self.margin = 0

    def write(self, tag: HtmlElement, text: str, whitespace: WhiteSpace = None) -> None:
        """Write the given text to the current block."""
        self.current_block.merge(text, whitespace or tag.whitespace)

    def close_tag(self, tag: HtmlElement) -> None:
        """Register that the given tag tag is closed.

        Args:
            tag: the tag to close.
        """
        if tag.display == Display.block:
            # write missing bullets, if no content has been written so far.
            if not self.flush_inline() and tag.list_bullet:
                self.write_unconsumed_bullet()
            self.current_block.prefix.remove_last_prefix()
            self.close_block(tag)

    def close_block(self, tag: HtmlElement) -> None:
        """Close the given HtmlElement by writing its bottom margin.

        Args:
            tag: the HTML Block element to close
        """
        if tag.margin_after > self.margin:
            required_newlines = tag.margin_after - self.margin
            self.current_block.idx += required_newlines
            self.blocks.append("\n" * (required_newlines - 1))
            self.margin = tag.margin_after

    def write_newline(self) -> None:
        if not self.flush_inline():
            self.blocks.append("")
            self.current_block = self.current_block.new_block()

    def get_text(self) -> str:
        """Provide a text representation of the Canvas."""
        self.flush_inline()
        return "\n".join(self.blocks)

    def flush_inline(self) -> bool:
        """Attempt to flush the content in self.current_block into a new block.

        Notes:
            - If self.current_block does not contain any content (or only
              whitespaces) no changes are made.
            - Otherwise the content of current_block is added to blocks and a
              new current_block is initialized.

        Returns:
            True if the attempt was successful, False otherwise.
        """
        if not self.current_block.is_empty():
            self.blocks.append(self.current_block.content)
            self.current_block = self.current_block.new_block()
            self.margin = 0
            return True

        return False

    @property
    def left_margin(self) -> int:
        """Return the length of the current line's left margin."""
        return self.current_block.prefix.current_padding
