"""Log viewer widget — read-only monospace text area for stdout/stderr."""

from __future__ import annotations

from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


class LogViewer(QWidget):
    """Read-only monospace log viewer with stdout/stderr coloring."""

    MAX_LINES = 100_000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Menlo", 11))
        self._text.setMaximumBlockCount(self.MAX_LINES)
        layout.addWidget(self._text)

        # Buttons.
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_all)
        btn_row.addWidget(copy_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._text.clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        # Formats.
        self._stderr_fmt = QTextCharFormat()
        self._stderr_fmt.setForeground(self._text.palette().text().color())
        # Stderr in red.
        from PyQt6.QtGui import QColor

        self._stderr_fmt.setForeground(QColor("#e53e3e"))

    def append_stdout(self, line: str) -> None:
        """Append a stdout line."""
        self._text.appendPlainText(line)

    def append_stderr(self, line: str) -> None:
        """Append a stderr line in red."""
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(line + "\n", self._stderr_fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def _copy_all(self) -> None:
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._text.toPlainText())
