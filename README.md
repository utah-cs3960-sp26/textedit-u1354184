# R1

## Core Editor Features

The text editor is built on PyQt6's `QPlainTextEdit`, providing a robust foundation for plain text editing. The core editing capabilities include:

- **Text editing**: Full text input with undo/redo support (Ctrl+Z, Ctrl+Shift+Z)
- **Selection**: Select word (Ctrl+D), select line (Ctrl+L), select all (Ctrl+A)
- **Clipboard**: Cut (Ctrl+X), copy (Ctrl+C), paste (Ctrl+V)
- **Line manipulation**: Duplicate line (Ctrl+Shift+D), delete line (Ctrl+Shift+K), move line up/down (Alt+Up/Down)

The editor uses a monospace font (Menlo, 12pt) with 4-space tab stops for code-friendly editing. Line wrapping is disabled by default to maintain code readability. The architecture separates the core editor widget (`TextEditor`) from the window management, allowing multiple independent editor instances to be created and managed by the tab and split systems.

Each editor instance maintains its own state including file path and modification tracking, emitting Qt signals when the cursor position or document modification state changes. This signal-based architecture allows the UI (tabs, status bar, window title) to stay synchronized with the editor state without tight coupling.

**Validation**: The `TestEditorBasics` and `TestLineOperations` test classes in `tests/test_editor.py` verify text insertion, modification tracking, and all line operations work correctly through programmatic testing.

## Opening and Saving Files

File I/O is handled through `load_file()` and `save_file()` methods on the `TextEditor` class. The implementation uses UTF-8 encoding for all files, ensuring compatibility with source code and text files containing international characters. Each editor tracks its associated file path and updates its modification state after successful saves.

The `EditorTabWidget` class handles the file dialogs via `QFileDialog`, supporting both "Save" (Ctrl+S) and "Save As" (Ctrl+Shift+S) workflows. When opening a file that's already open in another tab, the editor intelligently switches to that existing tab instead of creating a duplicate, preventing confusion about which tab contains which file.

Visual feedback is provided through tab titles with a ● (bullet) prefix for unsaved changes. Before closing any modified file, the user is prompted with a three-option dialog: Save, Discard, or Cancel. This prevents accidental data loss while allowing quick discard when desired.

The architecture cleanly separates concerns: the `TextEditor` class handles low-level file I/O and can work standalone, while the `EditorTabWidget` handles user-facing dialogs and tab management. This makes the editor components reusable and testable in isolation.

**Validation**: The `TestFileOperations` test class in `tests/test_editor.py` covers save/load round-trips, error handling for nonexistent files, and edge cases like saving without a specified path.

## Multi-file Support with Tabs and Split Views

The editor supports sophisticated multi-file editing through a tab system with optional split views, enabling side-by-side or top-bottom comparisons and editing.

### Tab Management

The `EditorTabWidget` class extends `QTabWidget` to manage multiple editor instances:

- **Closable tabs**: Each tab has a close button (Ctrl+W); prompts to save unsaved changes
- **Movable tabs**: Drag tabs to reorder them
- **Tab navigation**: Ctrl+Tab and Ctrl+Shift+Tab cycle through tabs
- **Smart file opening**: Reuses empty untitled tabs when opening files, avoids duplicate tabs for the same file
- **Modification indicators**: Tab title shows ● prefix for unsaved files
- **Empty tab handling**: Prevents creating empty tab widgets when closing the last tab

The tab widget is designed to be self-contained—it manages its own lifecycle without requiring external coordination. Each tab contains an independent `TextEditor` instance with its own undo/redo stack and file state.

### Split Views

The `SplitContainer` class provides a powerful split-view system for viewing multiple files simultaneously. This was implemented using Qt's `QSplitter` with dynamic nesting to support arbitrary split layouts:

- **Split horizontally** (Ctrl+\\): Create side-by-side editors
- **Split vertically** (Ctrl+Shift+\\): Create top-and-bottom editors  
- **Close split** (Ctrl+Shift+X): Remove the active split pane
- **Navigate splits**: Ctrl+Alt+Left/Right to move focus between panes
- **Nested splits**: Split panes can be further subdivided in either direction

The implementation uses a tree structure where each split can contain either tab widgets or more splits. When a split pane's last tab is closed, the split automatically collapses and removes itself from the tree. The container automatically rebalances splitter sizes to give equal space to all panes.

One interesting architectural challenge was managing focus and determining which split is "active" for operations like save or open. The solution tracks focus events on tab widgets and maintains an `_active_tabs` reference. Visual feedback could be added in the future to highlight the active split, but keyboard focus currently provides sufficient indication.

**Validation**: Tab and split functionality is validated through manual testing with the running application. The underlying editor and file operations are validated by the automated test suite, ensuring each tab and split operates correctly.

## Find and Replace

The `FindReplaceWidget` provides comprehensive in-file search and replace functionality with a clean, keyboard-friendly interface.

### Features

- **Find next/previous**: Navigate through matches with F3/Shift+F3 or arrow buttons
- **Replace single**: Replace current match and automatically advance to next match
- **Replace all**: Replace all occurrences in the document in one atomic operation
- **Search options**: Case-sensitive matching and whole-word matching
- **Match counter**: Real-time display of total number of matches
- **Wrap-around search**: Automatically wraps to beginning/end when reaching document boundaries
- **Smart initialization**: Auto-populates search field with current selection when opened

### Implementation Details

The find bar appears at the bottom of the main window and operates on the currently focused editor. The widget is shown/hidden on demand (Ctrl+F to open, Escape to close) and maintains its state between show/hide cycles, allowing users to quickly repeat previous searches.

Search uses Qt's `QTextDocument.find()` method with appropriate flags for case sensitivity and whole word matching. Replace operations handle edge cases like:
- Verifying the current selection matches the search term before replacing (prevents replacing wrong text)
- Handling case-insensitive matches correctly
- Using edit blocks for replace-all to make it a single undo operation

One interesting implementation detail: the match counter recalculates on every search text change by scanning the entire document. For very large files this could be slow, but it provides immediate feedback which improves the user experience. A future optimization would be to debounce the counter updates or cache results.

The find/replace bar integrates seamlessly with the split view system—it always operates on the currently active editor, and switching splits automatically redirects the find operations.

**Validation**: The `TestFindFunctionality` and `TestReplaceFunctionality` test classes in `tests/test_find_replace.py` provide 12 comprehensive tests covering:
- Basic search forward and backward
- Wrap-around behavior at document boundaries  
- Case-sensitive and case-insensitive searching
- Whole-word matching with punctuation boundaries
- Replace single occurrence
- Replace all occurrences
- Edge cases like empty strings and no matches

## Keyboard Shortcuts

The editor provides extensive keyboard shortcuts for efficient editing without reaching for the mouse. All shortcuts follow familiar conventions from popular editors like VS Code and Sublime Text.

### File Operations
| Action | Shortcut |
|--------|----------|
| New Tab | Ctrl+N |
| Open File | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Close Tab | Ctrl+W |
| Close All Tabs | Ctrl+Shift+W |

### Editing
| Action | Shortcut |
|--------|----------|
| Undo | Ctrl+Z |
| Redo | Ctrl+Shift+Z |
| Cut | Ctrl+X |
| Copy | Ctrl+C |
| Paste | Ctrl+V |
| Select All | Ctrl+A |
| Select Word | Ctrl+D |
| Select Line | Ctrl+L |
| Duplicate Line | Ctrl+Shift+D |
| Delete Line | Ctrl+Shift+K |
| Move Line Up | Alt+Up |
| Move Line Down | Alt+Down |

### Search
| Action | Shortcut |
|--------|----------|
| Find | Ctrl+F |
| Replace | Ctrl+H |
| Find Next | F3 |
| Find Previous | Shift+F3 |
| Go to Line | Ctrl+G |

### View & Navigation
| Action | Shortcut |
|--------|----------|
| Next Tab | Ctrl+Tab |
| Previous Tab | Ctrl+Shift+Tab |
| Split Right | Ctrl+\\ |
| Split Down | Ctrl+Shift+\\ |
| Close Split | Ctrl+Shift+X |
| Focus Next Split | Ctrl+Alt+Right |
| Focus Previous Split | Ctrl+Alt+Left |

Shortcuts are registered through Qt's action system (`QAction` with `setShortcut`), ensuring they work consistently across the application. Menu items display their shortcuts, making them discoverable for new users.

---

## Screenshots

*(Add screenshots here showing: the main editor window, tabs with multiple files open, split views, and the find/replace bar)*

## Architecture Summary

The editor follows a modular architecture with clear separation of concerns:

- **`TextEditor`**: Core editing widget with file I/O and text manipulation
- **`EditorTabWidget`**: Tab management for multi-file editing  
- **`SplitContainer`**: Split view system with dynamic layouts
- **`FindReplaceWidget`**: Search and replace functionality
- **`MainWindow`**: Top-level window with menu bar, keyboard shortcuts, and component integration

This structure makes each component independently testable and reusable. Communication between components uses Qt's signal/slot mechanism, keeping coupling loose and making it easy to add new features.

## Selected Features

For this assignment, I implemented **two** of the required advanced features:

1. **Multi-file support, tabs, and split views**: Full implementation including drag-to-reorder tabs, smart duplicate prevention, horizontal/vertical splits with arbitrary nesting, and automatic split cleanup.

2. **Find and replace**: Complete in-file find and replace with case-sensitive matching, whole-word search, replace single/all operations, match counting, and wrap-around navigation.

Both features are fully functional and well-integrated with the rest of the editor.

---

# R2

*Coming soon*

---

# R3

*Coming soon*
