"""Markdown preview widget."""

from PyQt6.QtWidgets import QTextBrowser, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


class MarkdownPreview(QTextBrowser):
    """Widget for previewing markdown content."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._markdown = None
        self._editor = None
        self._setup_ui()
        
        if MARKDOWN_AVAILABLE:
            # Initialize markdown with common extensions
            self._markdown = markdown.Markdown(
                extensions=['extra', 'codehilite', 'tables', 'fenced_code']
            )
    
    def set_editor(self, editor):
        """Set the associated editor to sync scroll position."""
        self._editor = editor
    
    def showEvent(self, event):
        """Handle widget show event - force update when shown."""
        super().showEvent(event)
        # Trigger an update when the widget becomes visible
        if self._editor:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self.update_preview(self._editor.toPlainText()))
    
    def _setup_ui(self):
        """Set up the preview widget."""
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        
        # Set a nice font for rendered content
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
    
    def _is_dark_theme(self):
        """Detect if the system is using a dark theme."""
        palette = QApplication.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        # Consider it dark if background is darker than midpoint
        return bg_color.lightness() < 128
    
    def _get_stylesheet(self):
        """Get the appropriate stylesheet based on theme."""
        is_dark = self._is_dark_theme()
        
        if is_dark:
            # Dark theme colors
            bg_color = "#1e1e1e"
            text_color = "#d4d4d4"
            code_bg = "#2d2d2d"
            border_color = "#404040"
            heading_color = "#e0e0e0"
            link_color = "#4a9eff"
            quote_color = "#808080"
            quote_border = "#505050"
        else:
            # Light theme colors
            bg_color = "#ffffff"
            text_color = "#333333"
            code_bg = "#f6f8fa"
            border_color = "#eaecef"
            heading_color = "#1a1a1a"
            link_color = "#0366d6"
            quote_color = "#6a737d"
            quote_border = "#dfe2e5"
        
        return f"""
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                padding: 20px;
                color: {text_color};
                background-color: {bg_color};
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
                color: {heading_color};
            }}
            h1 {{ font-size: 2em; border-bottom: 1px solid {border_color}; padding-bottom: 0.3em; }}
            h2 {{ font-size: 1.5em; border-bottom: 1px solid {border_color}; padding-bottom: 0.3em; }}
            h3 {{ font-size: 1.25em; }}
            code {{
                background-color: {code_bg};
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: {code_bg};
                padding: 16px;
                border-radius: 6px;
                overflow: auto;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            blockquote {{
                border-left: 4px solid {quote_border};
                padding-left: 16px;
                color: {quote_color};
                margin: 0;
            }}
            a {{
                color: {link_color};
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            table td, table th {{
                border: 1px solid {border_color};
                padding: 6px 13px;
            }}
            table th {{
                background-color: {code_bg};
                font-weight: 600;
            }}
            ul, ol {{
                padding-left: 2em;
            }}
            li {{
                margin-top: 0.25em;
            }}
        """
    
    def update_preview(self, markdown_text: str):
        """Update the preview with markdown text."""
        if not MARKDOWN_AVAILABLE:
            self.setHtml("""
                <div style="padding: 20px; color: #666;">
                    <h2>Markdown Library Not Available</h2>
                    <p>Install the markdown library to enable preview:</p>
                    <pre>pip install markdown</pre>
                </div>
            """)
            return
        
        if not markdown_text.strip():
            is_dark = self._is_dark_theme()
            color = "#999" if not is_dark else "#666"
            self.setHtml(f"<div style='padding: 20px; color: {color};'>Start typing markdown to see preview...</div>")
            return
        
        try:
            # Calculate scroll position based on cursor position in editor
            scroll_ratio = 0.5  # Default to middle
            if self._editor:
                # Get cursor position as ratio of document height
                cursor = self._editor.textCursor()
                cursor_pos = cursor.position()
                total_length = len(self._editor.toPlainText())
                if total_length > 0:
                    scroll_ratio = cursor_pos / total_length
            else:
                # Save current scroll position as fallback
                scrollbar = self.verticalScrollBar()
                scroll_max = scrollbar.maximum()
                if scroll_max > 0:
                    scroll_ratio = scrollbar.value() / scroll_max
            
            # Reset the markdown converter to clear state
            self._markdown.reset()
            # Convert markdown to HTML
            html = self._markdown.convert(markdown_text)
            # Get theme-appropriate stylesheet
            stylesheet = self._get_stylesheet()
            # Wrap in a styled container
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                {stylesheet}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """
            self.setHtml(full_html)
            
            # Restore scroll position based on ratio
            def restore_scroll():
                scrollbar = self.verticalScrollBar()
                target_pos = int(scrollbar.maximum() * scroll_ratio)
                scrollbar.setValue(target_pos)
            
            QTimer.singleShot(0, restore_scroll)
            
        except Exception as e:
            self.setHtml(f"<div style='padding: 20px; color: red;'>Error rendering markdown: {str(e)}</div>")
