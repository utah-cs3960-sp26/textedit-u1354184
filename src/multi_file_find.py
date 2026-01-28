"""Multi-file find and replace functionality."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SearchResult:
    """Represents a single search result."""
    
    def __init__(self, file_path: str, line_number: int, line_text: str, match_start: int, match_end: int):
        self.file_path = file_path
        self.line_number = line_number
        self.line_text = line_text
        self.match_start = match_start
        self.match_end = match_end


class MultiFileFindDialog(QDialog):
    """Dialog for multi-file find and replace operations."""
    
    def __init__(self, split_container, parent=None):
        super().__init__(parent)
        self.split_container = split_container
        self.results = []
        self.file_results = {}
        
        self.setWindowTitle("Find in Files")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Search input section
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout()
        
        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Enter search text...")
        find_row.addWidget(self.find_input)
        search_layout.addLayout(find_row)
        
        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Enter replacement text...")
        replace_row.addWidget(self.replace_input)
        search_layout.addLayout(replace_row)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        checkbox_row = QHBoxLayout()
        self.case_sensitive_cb = QCheckBox("Case Sensitive")
        checkbox_row.addWidget(self.case_sensitive_cb)
        self.whole_word_cb = QCheckBox("Whole Word")
        checkbox_row.addWidget(self.whole_word_cb)
        checkbox_row.addStretch()
        options_layout.addLayout(checkbox_row)
        
        # Scope selection
        scope_label = QLabel("Search in:")
        options_layout.addWidget(scope_label)
        
        scope_row = QHBoxLayout()
        self.scope_group = QButtonGroup()
        self.open_tabs_radio = QRadioButton("Open Tabs")
        self.open_tabs_radio.setChecked(True)
        self.scope_group.addButton(self.open_tabs_radio)
        scope_row.addWidget(self.open_tabs_radio)
        
        self.directory_radio = QRadioButton("Directory:")
        self.scope_group.addButton(self.directory_radio)
        scope_row.addWidget(self.directory_radio)
        
        self.directory_input = QLineEdit()
        self.directory_input.setEnabled(False)
        scope_row.addWidget(self.directory_input)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setEnabled(False)
        scope_row.addWidget(self.browse_btn)
        options_layout.addLayout(scope_row)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Results section
        results_label = QLabel("Results:")
        layout.addWidget(results_label)
        
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Location", "Line", "Text"])
        self.results_tree.setColumnWidth(0, 300)
        self.results_tree.setColumnWidth(1, 60)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setFont(QFont("Menlo", 11))
        layout.addWidget(self.results_tree)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Buttons section
        buttons_row = QHBoxLayout()
        self.find_all_btn = QPushButton("Find All")
        self.find_all_btn.setDefault(True)
        buttons_row.addWidget(self.find_all_btn)
        
        self.replace_selected_btn = QPushButton("Replace Selected")
        buttons_row.addWidget(self.replace_selected_btn)
        
        self.replace_all_btn = QPushButton("Replace All")
        buttons_row.addWidget(self.replace_all_btn)
        
        buttons_row.addStretch()
        
        self.close_btn = QPushButton("Close")
        buttons_row.addWidget(self.close_btn)
        
        layout.addLayout(buttons_row)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        self.find_all_btn.clicked.connect(self.find_all)
        self.replace_selected_btn.clicked.connect(self.replace_selected)
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.close_btn.clicked.connect(self.close)
        self.browse_btn.clicked.connect(self._browse_directory)
        self.directory_radio.toggled.connect(self._on_scope_changed)
        self.results_tree.itemDoubleClicked.connect(self._on_result_double_clicked)
        self.find_input.returnPressed.connect(self.find_all)
    
    def _on_scope_changed(self, checked):
        """Handle scope radio button changes."""
        self.directory_input.setEnabled(checked)
        self.browse_btn.setEnabled(checked)
    
    def _browse_directory(self):
        """Browse for a directory to search in."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory", ""
        )
        if directory:
            self.directory_input.setText(directory)
    
    def find_all(self):
        """Find all occurrences across files."""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter search text")
            return
        
        self.results_tree.clear()
        self.results = []
        self.file_results = {}
        
        if self.open_tabs_radio.isChecked():
            files_to_search = self._get_open_tabs()
        else:
            files_to_search = self._get_directory_files()
        
        if not files_to_search:
            self.status_label.setText("No files to search")
            return
        
        total_matches = 0
        for file_path, content in files_to_search:
            matches = self._search_in_text(content, search_text, file_path)
            if matches:
                self.file_results[file_path] = matches
                total_matches += len(matches)
        
        self._display_results()
        
        if total_matches > 0:
            self.status_label.setText(
                f"Found {total_matches} match{'es' if total_matches != 1 else ''} "
                f"in {len(self.file_results)} file{'s' if len(self.file_results) != 1 else ''}"
            )
        else:
            self.status_label.setText("No matches found")
    
    def _get_open_tabs(self):
        """Get all open tabs and their content."""
        files = []
        all_tab_widgets = self.split_container.findChildren(type(self.split_container.active_tab_widget()))
        
        seen_paths = set()
        for tab_widget in all_tab_widgets:
            for i in range(tab_widget.count()):
                editor = tab_widget.widget(i)
                if editor:
                    file_path = editor.file_path or f"Untitled-{id(editor)}"
                    if file_path not in seen_paths:
                        seen_paths.add(file_path)
                        content = editor.toPlainText()
                        files.append((file_path, content))
        
        return files
    
    def _get_directory_files(self):
        """Get all text files in the specified directory."""
        directory = self.directory_input.text()
        if not directory or not Path(directory).exists():
            return []
        
        files = []
        dir_path = Path(directory)
        
        # Common text file extensions
        extensions = ['.txt', '.py', '.js', '.java', '.cpp', '.c', '.h', '.hpp',
                     '.css', '.html', '.xml', '.json', '.md', '.rst', '.yaml', '.yml']
        
        for ext in extensions:
            for file_path in dir_path.rglob(f'*{ext}'):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        files.append((str(file_path), content))
                    except (UnicodeDecodeError, OSError):
                        pass
        
        return files
    
    def _search_in_text(self, text: str, search_text: str, file_path: str):
        """Search for text in the given content."""
        results = []
        lines = text.split('\n')
        
        for line_num, line_text in enumerate(lines, 1):
            line_to_search = line_text if self.case_sensitive_cb.isChecked() else line_text.lower()
            search_term = search_text if self.case_sensitive_cb.isChecked() else search_text.lower()
            
            start = 0
            while True:
                pos = line_to_search.find(search_term, start)
                if pos == -1:
                    break
                
                # Check whole word if needed
                if self.whole_word_cb.isChecked():
                    if not self._is_whole_word(line_to_search, pos, len(search_term)):
                        start = pos + 1
                        continue
                
                result = SearchResult(
                    file_path=file_path,
                    line_number=line_num,
                    line_text=line_text.strip(),
                    match_start=pos,
                    match_end=pos + len(search_term)
                )
                results.append(result)
                self.results.append(result)
                start = pos + 1
        
        return results
    
    def _is_whole_word(self, text: str, pos: int, length: int):
        """Check if match is a whole word."""
        before_ok = pos == 0 or not text[pos - 1].isalnum()
        after_ok = pos + length >= len(text) or not text[pos + length].isalnum()
        return before_ok and after_ok
    
    def _display_results(self):
        """Display search results in the tree widget."""
        for file_path, matches in self.file_results.items():
            # Create parent item for file
            file_item = QTreeWidgetItem(self.results_tree)
            file_item.setText(0, str(Path(file_path).name) if Path(file_path).exists() else file_path)
            file_item.setToolTip(0, file_path)
            file_item.setText(1, f"({len(matches)})")
            
            # Add child items for each match
            for result in matches:
                match_item = QTreeWidgetItem(file_item)
                match_item.setText(0, "")
                match_item.setText(1, str(result.line_number))
                match_item.setText(2, result.line_text)
                match_item.setData(0, Qt.ItemDataRole.UserRole, result)
        
        self.results_tree.expandAll()
    
    def _on_result_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on a result to jump to location."""
        result = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(result, SearchResult):
            return
        
        # Try to find and open the file in the editor
        all_tab_widgets = self.split_container.findChildren(type(self.split_container.active_tab_widget()))
        
        # First, check if file is already open
        for tab_widget in all_tab_widgets:
            for i in range(tab_widget.count()):
                editor = tab_widget.widget(i)
                if editor and editor.file_path == result.file_path:
                    tab_widget.setCurrentIndex(i)
                    editor.go_to_line(result.line_number)
                    editor.setFocus()
                    return
        
        # If not open, try to open it
        if Path(result.file_path).exists():
            editor = self.split_container.open_file(result.file_path)
            if editor:
                editor.go_to_line(result.line_number)
                editor.setFocus()
    
    def replace_selected(self):
        """Replace selected occurrences."""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            self.status_label.setText("No results selected")
            return
        
        replacement = self.replace_input.text()
        search_text = self.find_input.text()
        
        # Group results by file
        files_to_update = {}
        for item in selected_items:
            result = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(result, SearchResult):
                if result.file_path not in files_to_update:
                    files_to_update[result.file_path] = []
                files_to_update[result.file_path].append(result)
        
        count = self._perform_replacements(files_to_update, search_text, replacement)
        self.status_label.setText(f"Replaced {count} occurrence{'s' if count != 1 else ''}")
        
        # Refresh results
        self.find_all()
    
    def replace_all(self):
        """Replace all occurrences."""
        if not self.results:
            self.status_label.setText("No results to replace")
            return
        
        replacement = self.replace_input.text()
        search_text = self.find_input.text()
        
        reply = QMessageBox.question(
            self, "Replace All",
            f"Replace all {len(self.results)} occurrence{'s' if len(self.results) != 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self._perform_replacements(self.file_results, search_text, replacement)
            self.status_label.setText(f"Replaced {count} occurrence{'s' if count != 1 else ''}")
            
            # Refresh results
            self.find_all()
    
    def _perform_replacements(self, files_results: dict, search_text: str, replacement: str):
        """Perform replacements in the specified files."""
        count = 0
        
        for file_path, results in files_results.items():
            # Try to find the editor if file is open
            editor = self._find_editor_for_file(file_path)
            
            if editor:
                # Replace in open editor
                text = editor.toPlainText()
                new_text = self._replace_in_text(text, results, search_text, replacement)
                editor.setPlainText(new_text)
                editor.set_modified(True)
                count += len(results)
            elif Path(file_path).exists():
                # Replace in file on disk
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    new_text = self._replace_in_text(text, results, search_text, replacement)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_text)
                    
                    count += len(results)
                except (OSError, IOError) as e:
                    QMessageBox.warning(
                        self, "Error",
                        f"Could not replace in {file_path}: {str(e)}"
                    )
        
        return count
    
    def _replace_in_text(self, text: str, results: list, search_text: str, replacement: str):
        """Replace occurrences in text, accounting for position changes."""
        lines = text.split('\n')
        offset = 0
        
        # Sort results by line number and position
        sorted_results = sorted(results, key=lambda r: (r.line_number, r.match_start))
        
        for result in sorted_results:
            line_idx = result.line_number - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                
                # Find the actual match considering case sensitivity
                if self.case_sensitive_cb.isChecked():
                    pos = line.find(search_text, result.match_start)
                else:
                    pos = line.lower().find(search_text.lower(), result.match_start)
                
                if pos != -1 and pos == result.match_start:
                    lines[line_idx] = line[:pos] + replacement + line[pos + len(search_text):]
        
        return '\n'.join(lines)
    
    def _find_editor_for_file(self, file_path: str):
        """Find an open editor for the given file path."""
        all_tab_widgets = self.split_container.findChildren(type(self.split_container.active_tab_widget()))
        
        for tab_widget in all_tab_widgets:
            for i in range(tab_widget.count()):
                editor = tab_widget.widget(i)
                if editor and editor.file_path == file_path:
                    return editor
        
        return None
