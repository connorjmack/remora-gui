"""Raw text editor with AMReX input file syntax highlighting."""

from __future__ import annotations

import re

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class InputFileSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for AMReX ParmParse input files."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)

        # Comment format — green.
        self._comment_fmt = QTextCharFormat()
        self._comment_fmt.setForeground(QColor("#6a9955"))

        # Key format — white/light.
        self._key_fmt = QTextCharFormat()
        self._key_fmt.setForeground(QColor("#e2e8f0"))

        # Equals sign — muted.
        self._eq_fmt = QTextCharFormat()
        self._eq_fmt.setForeground(QColor("#a0aec0"))

        # Value format — blue.
        self._value_fmt = QTextCharFormat()
        self._value_fmt.setForeground(QColor("#4299e1"))

        # Pattern: key = value  (# comment)
        self._line_re = re.compile(
            r"^(\s*)([\w.]+)(\s*=\s*)(.*?)(\s*#.*)?$"
        )
        self._comment_re = re.compile(r"^\s*#.*$")

    def highlightBlock(self, text: str) -> None:
        # Full-line comment.
        if self._comment_re.match(text):
            self.setFormat(0, len(text), self._comment_fmt)
            return

        m = self._line_re.match(text)
        if m:
            # Key.
            self.setFormat(m.start(2), len(m.group(2)), self._key_fmt)
            # Equals.
            self.setFormat(m.start(3), len(m.group(3)), self._eq_fmt)
            # Value.
            self.setFormat(m.start(4), len(m.group(4)), self._value_fmt)
            # Inline comment.
            if m.group(5):
                self.setFormat(m.start(5), len(m.group(5)), self._comment_fmt)


class RawEditor(QWidget):
    """Plain text editor for AMReX input files with syntax highlighting."""

    text_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._editor = QPlainTextEdit()
        self._editor.setFont(QFont("Menlo", 12))
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._editor)

        self._highlighter = InputFileSyntaxHighlighter(self._editor.document())
        self._editor.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self) -> None:
        self.text_changed.emit(self._editor.toPlainText())

    def get_text(self) -> str:
        """Return the full editor text."""
        return self._editor.toPlainText()

    def set_text(self, text: str) -> None:
        """Replace the editor text (blocks intermediate signals)."""
        self._editor.blockSignals(True)
        self._editor.setPlainText(text)
        self._editor.blockSignals(False)
