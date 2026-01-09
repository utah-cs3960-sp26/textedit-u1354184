# R1

## Core Editing

Built on PyQt6's `QPlainTextEdit` with all the basics working: text editing, undo/redo, cut/copy/paste, and some nice extras like duplicate line (Ctrl+Shift+D), delete line (Ctrl+Shift+K), and move lines up/down (Alt+Up/Down). Uses Menlo font with 4-space tabs.

The `TextEditor` class is pretty straightforward—it handles file I/O and emits signals when things change. This keeps the UI stuff (tabs, status bar) decoupled from the actual editing logic, which makes testing way easier.

**Tests**: `tests/test_editor.py` has `TestEditorBasics` and `TestLineOperations` covering the main functionality.

## Opening and Saving Files

Files are saved/loaded with UTF-8 encoding. The editor shows a ● in the tab title when you have unsaved changes, and prompts you before closing modified files so you don't lose work.

One nice touch: if you try to open a file that's already open in another tab, it just switches to that tab instead of opening it twice. Empty "Untitled" tabs get reused when you open files too.

The architecture splits things cleanly—`TextEditor` does the actual file I/O, while `EditorTabWidget` handles the dialogs and UI stuff.

**Tests**: `TestFileOperations` covers save/load, error handling, and edge cases.

## Tabs and Split Views

This is where things get more interesting. You can have multiple files open in tabs (drag to reorder, Ctrl+Tab to cycle), and you can split the window horizontally or vertically to view files side-by-side.

The split system uses Qt's `QSplitter` with a tree structure, so you can nest splits in any direction. When you close the last tab in a split, it automatically cleans itself up. The tricky part was tracking which split is "active" for operations like save—I ended up using focus events and keeping an `_active_tabs` reference.

Shortcuts: Ctrl+\\ to split right, Ctrl+Shift+\\ to split down, Ctrl+Shift+X to close a split.

**Tests**: Manual testing for splits. The underlying editor tests cover the tab functionality.

## Find and Replace

Built a find/replace bar that sits at the bottom of the window. Has all the standard features: find next/previous (F3/Shift+F3), case-sensitive search, whole-word matching, replace single, and replace all. Shows a match counter and auto-populates with your current selection when you open it.

The implementation uses Qt's `QTextDocument.find()` with the appropriate flags. Replace-all uses edit blocks so it's a single undo operation. One thing I noticed: the match counter recalculates on every keystroke by scanning the whole document, which could be slow for huge files but gives nice instant feedback.

**Tests**: 12 tests in `tests/test_find_replace.py` covering search directions, wrap-around, case sensitivity, whole words, and replace operations.

## Architecture

The code is split into modular pieces:
- `TextEditor` - core editing widget
- `EditorTabWidget` - manages tabs
- `SplitContainer` - handles split views
- `FindReplaceWidget` - search/replace
- `MainWindow` - ties it all together

Everything communicates via Qt signals/slots, which keeps things loosely coupled.

## What I Built

For this assignment I picked two features from the list:

1. **Multi-file support, tabs, and split views** - fully working with drag-to-reorder, nested splits, and smart duplicate handling
2. **Find and replace** - complete with case-sensitive/whole-word options, replace all, and match counting

---

# R2

*Coming soon*

---

# R3

*Coming soon*
