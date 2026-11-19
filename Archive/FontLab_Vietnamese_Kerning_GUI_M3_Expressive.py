# -*- coding: utf-8 -*-
#FLM: Vietnamese Kerning (M3 Expressive GUI)
# NOTE: Keep this script ASCII-only. FontLab's macro editor can decode UTF-8
# source text incorrectly when it executes code as <string>. Write non-ASCII
# GUI labels with Python Unicode escapes (\uXXXX), not literal UTF-8.
"""
Vietnamese Kerning - Material 3 Expressive-inspired GUI experiment
===============================================================
Runs INSIDE FontLab's existing Qt5 / PythonQt application.
No tkinter, no new QApplication, no extra packages, no server.

Launch THIS FILE from FontLab's Scripts/Scripting panel. The original
FontLab_Vietnamese_Kerning_Assistant_v1.py can be kept in the same folder,
or selected from a file chooser if FontLab runs the GUI as <string>.

Every scan is read-only. Choose an output folder before exporting reports.
Export and the pre-Apply backup use that folder, not an implicit C: path.
Apply changes ONLY the OpenType "kern" feature after safety checks and
explicit confirmation; it NEVER saves the font automatically.

The original core source file remains unmodified. GUI needs real FL8/FL9
verification before replacing the previously tested GUI in production.
"""

from __future__ import print_function

import importlib
import json
import ntpath
import os
import sys
import time
import traceback


KEY = "_fontlab_vietnamese_kerning_gui_m3"
TITLE = "Vietnamese Kerning"
GUI_VERSION = "v1.0.0-beta.1 / UI rev3"
CORE_MODULE = "FontLab_Vietnamese_Kerning_Assistant_v1"
CORE_PATH_KEY = "_fontlab_vietnamese_kerning_core_path"
ALLOW_ORIGINAL_FONT = True


def get_core():
    """Find the unchanged core even when FontLab executes GUI as <string>.

    FontLab's macro editor often omits __file__. If Python cannot import the
    core normally, let the user choose its actual .py file using Qt.
    """
    directory = (
        os.path.dirname(os.path.abspath(__file__))
        if "__file__" in globals() else ""
    )
    remembered = sys.__dict__.get(CORE_PATH_KEY, "")
    search_directories = [directory]
    if remembered and os.path.isfile(remembered):
        search_directories.append(os.path.dirname(remembered))
    for folder in search_directories:
        if folder and folder not in sys.path:
            sys.path.insert(0, folder)
    try:
        return importlib.import_module(CORE_MODULE)
    except ModuleNotFoundError as exc:
        # Don't disguise a missing dependency INSIDE core as a missing core.
        if exc.name != CORE_MODULE:
            raise

    try:
        from PythonQt import QtGui
    except ImportError as exc:
        raise RuntimeError(
            "Kh\xf4ng t\xecm th\u1ea5y Core. H\xe3y ch\u1ea1y GUI b\xean trong FontLab v\xe0 ch\u1ecdn "
            "file " + CORE_MODULE + ".py."
        ) from exc

    file_name = CORE_MODULE + ".py"
    picked = QtGui.QFileDialog.getOpenFileName(
        None, "Ch\u1ecdn Core: " + file_name,
        os.path.dirname(remembered) if remembered else os.path.expanduser("~"),
        "Python scripts (*.py)",
    )
    # Some Qt bindings return a QString, others return (path, filter).
    if isinstance(picked, (tuple, list)):
        picked = picked[0]
    path = str(picked or "").strip()
    if not path:
        raise RuntimeError("B\u1ea1n ch\u01b0a ch\u1ecdn Core. \u0110\xe3 h\u1ee7y kh\u1edfi \u0111\u1ed9ng GUI.")
    if ntpath.basename(path).lower() != file_name.lower():
        raise RuntimeError("Vui l\xf2ng ch\u1ecdn \u0111\xfang file " + file_name)
    if not os.path.isfile(path):
        raise RuntimeError("Kh\xf4ng t\xecm th\u1ea5y file Core t\u1ea1i: " + path)
    folder = os.path.dirname(path)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    module = importlib.import_module(CORE_MODULE)
    sys.__dict__[CORE_PATH_KEY] = path
    return module


def scan_font(font, core):
    """Pure controller layer: never writes or changes any FontLab object."""
    if font is None:
        raise RuntimeError("Open a font in FontLab first.")
    layout = font.features
    if "kern" not in list(layout.keys()):
        raise RuntimeError("The open font has no text 'kern' feature.")
    original = core.read_kern(layout)
    if not isinstance(original, str):
        raise RuntimeError("Unable to read the kern feature as text.")

    prefix = layout.get_prefix()
    available, candidates, detection, glyph_issues = core.glyph_candidates(font)
    classes, class_issues = core.parse_classes(original)
    changes, provenance = core.plan_memberships(
        classes, available, candidates, detection
    )
    roles = core.pair_roles(original)
    issues = (
        glyph_issues
        + class_issues
        + core.class_overlap_issues(classes, changes, roles)
    )
    new_text = core.render_kern(original, changes)
    issues.extend(core.verify_render(original, new_text, classes, changes, available))

    return {
        "font": font,
        "font_path": str(getattr(font, "path", "") or ""),
        "original": original,
        "prefix": prefix,
        "available": available,
        "classes": classes,
        "roles": roles,
        "changes": changes,
        "provenance": provenance,
        "issues": issues,
        "pos_rules": len(core.pos_lines(original)),
        "glyph_count": len(available),
    }


def filtered_plan(snapshot, selected_pairs, core):
    """Validate a user-selected subset before report/export/apply."""
    source_changes = snapshot["changes"]
    allowed = {(cls, name) for cls, names in source_changes.items() for name in names}
    unknown = set(selected_pairs) - allowed
    if unknown:
        raise ValueError("Unknown selection: " + str(sorted(unknown)[:6]))

    selected = {}
    for cls, glyph in sorted(selected_pairs):
        selected.setdefault(cls, []).append(glyph)

    issues = list(snapshot["issues"])
    issues.extend(core.class_overlap_issues(
        snapshot["classes"], selected, snapshot["roles"]
    ))
    changed = core.render_kern(snapshot["original"], selected)
    issues.extend(core.verify_render(
        snapshot["original"], changed, snapshot["classes"],
        selected, snapshot["available"]
    ))
    name_only = sorted({
        glyph for names in selected.values() for glyph in names
        if snapshot["provenance"].get(glyph) == "name"
    })
    return selected, changed, name_only, sorted(set(issues))


def build_report(snapshot, plan, proposed, name_only, issues, core):
    original = snapshot["original"]
    return {
        "tool": "Vietnamese Kerning M3 Expressive GUI preview",
        "engine": "FontLab Vietnamese Kerning Assistant v1.0",
        "engine_verification": (
            "Core v1.0 previously verified; the M3 GUI still needs "
            "independent FL8/FL9 testing"
        ),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "font_path": snapshot["font_path"],
        "font_glyphs": snapshot["glyph_count"],
        "kern_classes": len(snapshot["classes"]),
        "kern_pos_rules": snapshot["pos_rules"],
        "classes_selected": len(plan),
        "memberships_selected": sum(map(len, plan.values())),
        "name_only_selected": name_only,
        "changes": plan,
        "issues": issues,
        "original_sha256": core.sha256_text(original),
        "proposed_sha256": core.sha256_text(proposed),
        "status": "GUI_PREVIEW",
    }


def qt_string(widget, attr):
    """PythonQt exposes some Qt properties directly, and some as methods."""
    value = getattr(widget, attr)
    return str(value() if callable(value) else value)


def is_checked(widget):
    method = getattr(widget, "isChecked", None)
    if callable(method):
        return bool(method())
    return bool(getattr(widget, "checked", False))


def write_reports_in_folder(core, folder, original, proposed, report):
    """Use the verified writer with a GUI-selected folder, restoring its setting.

    The writer runs synchronously on FontLab's UI thread. This changes only an
    in-memory module setting while the call runs; it does not edit core source.
    """
    if not folder or not os.path.isdir(folder):
        raise RuntimeError("Choose an existing report folder first.")
    old_folder = core.OUTPUT_FOLDER
    try:
        core.OUTPUT_FOLDER = folder
        return core.write_artifacts(original, proposed, report)
    finally:
        core.OUTPUT_FOLDER = old_folder


def start_gui(core, fontlab):
    try:
        from PythonQt import QtCore, QtGui
    except ImportError as exc:
        raise RuntimeError(
            "PythonQt is unavailable. Run from inside FontLab 8/9."
        ) from exc

    class Window(QtGui.QDialog):
        def __init__(self, parent=None):
            QtGui.QDialog.__init__(self, parent)
            self.setWindowTitle(TITLE + "  " + GUI_VERSION)
            # Windows sometimes adds a context-help '?' button to QDialog.
            try:
                self.setWindowFlags(
                    self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception as exc:
                print("GUI: could not remove context-help button:", str(exc))
            self.resize(1030, 790)
            self.setMinimumWidth(840)

            self._connections = []
            self.snapshot = None
            self.groups = {}
            self.entries = []
            self._updating_tree = False
            self.applied = False
            self.last_folder = ""
            self.output_folder = str(
                sys.__dict__.setdefault(KEY, {}).get("output_folder", "") or ""
            )
            if self.output_folder and not os.path.isdir(self.output_folder):
                self.output_folder = ""

            self.setStyleSheet("""
                QDialog { background: #faf8ef; color: #203c33;
                          font-family: "Segoe UI"; font-size: 12px; }
                QLabel { color: #203c33; }
                QLineEdit, QTreeWidget, QPlainTextEdit {
                    background: #fffef9; color: #203c33;
                    border: 1px solid #dfebdf; border-radius: 12px;
                    selection-background-color: #d7f1d7;
                    selection-color: #203c33;
                }
                QLineEdit { padding: 10px 13px; }
                QTreeWidget { alternate-background-color: #f3f8f1;
                              outline: none; }
                QTreeWidget::item { padding: 5px 3px; }
                QHeaderView::section { background: #e8f3eb; color: #506a5d;
                    border: none; border-bottom: 1px solid #dfebdf;
                    padding: 11px; font-weight: bold; }
                QPlainTextEdit { padding: 8px; }
                QPushButton { background: #e8f3eb; color: #135148;
                    border: 0; border-radius: 16px; padding: 10px 15px;
                    font-weight: bold; }
                QPushButton:hover { background: #d7f1d7; }
                QPushButton:disabled { color: #9aaba0; background: #edf1e9; }
                QPushButton#scanButton { background: #ffe4a1; color: #573f1f; }
                QPushButton#scanButton:hover { background: #ffda88; }
                QPushButton#applyButton { background: #ee7b61; color: #45281f; }
                QPushButton#applyButton:hover { background: #f48f77; }
                QPushButton#applyButton:disabled { background: #efd5ce;
                    color: #b99a91; }
                QCheckBox { color: #203c33; spacing: 8px; }
                QCheckBox::indicator { width: 16px; height: 16px; }
            """)
            root = QtGui.QVBoxLayout(self)
            root.setContentsMargins(22, 18, 22, 18)
            root.setSpacing(12)

            header = QtGui.QFrame()
            header.setStyleSheet("QFrame {background:#135148; border-radius:20px;}")
            header_row = QtGui.QHBoxLayout(header)
            header_row.setContentsMargins(20, 12, 20, 12)
            heading = QtGui.QLabel("Vietnamese Kerning")
            heading.setFont(QtGui.QFont("Segoe UI", 19, QtGui.QFont.Bold))
            heading.setStyleSheet("color:#fffdf1;background:transparent;")
            version = QtGui.QLabel("v1.0.0-beta.1")
            version.setStyleSheet(
                "color:#fff7d9;background:#28685e;border-radius:11px;"
                "padding:5px 11px;"
            )
            header_row.addWidget(heading)
            header_row.addWidget(version)
            header_row.addStretch()
            root.addWidget(header)

            font_row = QtGui.QHBoxLayout()
            self.info = QtGui.QLabel("Font \u0111ang m\u1edf: ch\u01b0a qu\xe9t")
            self.info.setStyleSheet("font-weight:bold;color:#135148;")
            font_row.addWidget(self.info, 1)
            self.scan_button = QtGui.QPushButton("Qu\xe9t font")
            self.scan_button.setObjectName("scanButton")
            # ASCII-only diagnostics: distinguishes source decoding from the
            # PythonQt str -> QString conversion in the user's FontLab build.
            print("M3_UI_REV3_PYTHON_TEXT:", ascii("Qu\xe9t font"))
            print(
                "M3_UI_REV3_QT_TEXT:",
                ascii(qt_string(self.scan_button, "text")),
            )
            font_row.addWidget(self.scan_button)
            root.addLayout(font_row)

            stats = QtGui.QHBoxLayout()
            stats.setSpacing(9)
            self.stat_values = {}
            for key, label, tint in (
                ("glyph_count", "Glyph", "#d7f1d7"),
                ("class_count", "Kerning class", "#d9f0ef"),
                ("pos_rules", "OT rules", "#ffdfd7"),
                ("proposals", "\u0110\u1ec1 xu\u1ea5t th\xeam", "#ffe4a1"),
            ):
                panel = QtGui.QFrame()
                panel.setStyleSheet(
                    "QFrame {background:" + tint + ";border-radius:18px;}"
                )
                box = QtGui.QVBoxLayout(panel)
                box.setContentsMargins(15, 12, 15, 12)
                caption = QtGui.QLabel(label)
                caption.setStyleSheet("color:#4c685b;background:transparent;")
                value = QtGui.QLabel("\u2014")
                value.setFont(QtGui.QFont("Segoe UI", 22, QtGui.QFont.Bold))
                value.setStyleSheet("color:#203c33;background:transparent;")
                box.addWidget(caption)
                box.addWidget(value)
                self.stat_values[key] = value
                stats.addWidget(panel, 1)
            root.addLayout(stats)

            table_header = QtGui.QHBoxLayout()
            section_title = QtGui.QLabel("\u0110\u1ec1 xu\u1ea5t kerning")
            section_title.setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Bold))
            table_header.addWidget(section_title)
            table_header.addStretch()
            self.filter_input = QtGui.QLineEdit()
            self.filter_input.setPlaceholderText("T\xecm class ho\u1eb7c glyph\u2026")
            self.filter_input.setMinimumWidth(245)
            table_header.addWidget(self.filter_input)
            root.addLayout(table_header)

            quick = QtGui.QHBoxLayout()
            self.all_button = QtGui.QPushButton("Ch\u1ecdn t\u1ea5t c\u1ea3")
            self.none_button = QtGui.QPushButton("B\u1ecf ch\u1ecdn")
            self.selection_label = QtGui.QLabel("0 / 0 glyph \u0111\xe3 ch\u1ecdn")
            self.selection_label.setStyleSheet("color:#64776c;")
            quick.addWidget(self.all_button)
            quick.addWidget(self.none_button)
            quick.addWidget(self.selection_label)
            quick.addStretch()
            self.safety_label = QtGui.QLabel("Ch\u01b0a qu\xe9t")
            self.safety_label.setStyleSheet("color:#237258;")
            quick.addWidget(self.safety_label)
            root.addLayout(quick)

            self.table = QtGui.QTreeWidget()
            self.table.setColumnCount(5)
            self.table.setHeaderLabels(
                ["Ch\u1ecdn", "Class", "Tr\xe1i/Ph\u1ea3i", "Glyph s\u1ebd th\xeam", "S\u1ed1 glyph"]
            )
            self.table.setRootIsDecorated(True)
            self.table.setIndentation(16)
            self.table.setAlternatingRowColors(True)
            self.table.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
            self.table.setColumnWidth(0, 73)
            self.table.setColumnWidth(1, 160)
            self.table.setColumnWidth(2, 116)
            self.table.setColumnWidth(3, 420)
            self.table.setColumnWidth(4, 100)
            root.addWidget(self.table, 1)

            footer = QtGui.QHBoxLayout()
            footer.setSpacing(12)
            output_panel = QtGui.QFrame()
            output_panel.setStyleSheet(
                "QFrame {background:#fffef9;border-radius:20px;}"
            )
            output_layout = QtGui.QVBoxLayout(output_panel)
            output_layout.setContentsMargins(17, 14, 17, 14)
            output_layout.setSpacing(8)
            output_title = QtGui.QLabel("Output")
            output_title.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
            output_layout.addWidget(output_title)
            self.diagnostics = QtGui.QPlainTextEdit()
            self.diagnostics.setReadOnly(True)
            self.diagnostics.setMaximumHeight(91)
            self.diagnostics.setPlainText("Qu\xe9t font \u0111\u1ec3 b\u1eaft \u0111\u1ea7u ki\u1ec3m tra.")
            output_layout.addWidget(self.diagnostics)
            self.folder_label = QtGui.QLabel("Th\u01b0 m\u1ee5c l\u01b0u: ch\u01b0a ch\u1ecdn")
            self.folder_label.setWordWrap(True)
            self.folder_label.setStyleSheet("font-size:11px;color:#687b70;")
            output_layout.addWidget(self.folder_label)
            export_row = QtGui.QHBoxLayout()
            self.choose_folder_button = QtGui.QPushButton("Ch\u1ecdn n\u01a1i l\u01b0u")
            self.export_button = QtGui.QPushButton("Export FEA + Diff")
            export_row.addWidget(self.choose_folder_button)
            export_row.addWidget(self.export_button)
            export_row.addStretch()
            output_layout.addLayout(export_row)
            footer.addWidget(output_panel, 3)

            apply_panel = QtGui.QFrame()
            apply_panel.setStyleSheet(
                "QFrame {background:#ffdfd7;border-radius:20px;}"
            )
            apply_layout = QtGui.QVBoxLayout(apply_panel)
            apply_layout.setContentsMargins(17, 14, 17, 14)
            apply_title = QtGui.QLabel("S\u1eb5n s\xe0ng \xe1p d\u1ee5ng")
            apply_title.setFont(QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold))
            apply_layout.addWidget(apply_title)
            self.copy_confirm = QtGui.QCheckBox(
                "T\xf4i x\xe1c nh\u1eadn \u0111\xe3 backup to\xe0n b\u1ed9 font"
            )
            self.name_confirm = QtGui.QCheckBox(
                "Cho ph\xe9p glyph ch\u1ec9 nh\u1eadn di\u1ec7n b\u1eb1ng t\xean"
            )
            apply_layout.addWidget(self.copy_confirm)
            apply_layout.addWidget(self.name_confirm)
            apply_layout.addStretch()
            self.apply_button = QtGui.QPushButton("\xc1p d\u1ee5ng thay \u0111\u1ed5i")
            self.apply_button.setObjectName("applyButton")
            apply_layout.addWidget(self.apply_button)
            footer.addWidget(apply_panel, 2)
            root.addLayout(footer)

            bottom = QtGui.QHBoxLayout()
            self.status = QtGui.QLabel("S\u1eb5n s\xe0ng")
            self.status.setWordWrap(True)
            self.status.setStyleSheet("color:#237258;")
            bottom.addWidget(self.status, 1)
            self.close_button = QtGui.QPushButton("\u0110\xf3ng")
            bottom.addWidget(self.close_button)
            root.addLayout(bottom)

            self._update_folder_label()
            self.export_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.all_button.setEnabled(False)
            self.none_button.setEnabled(False)
            self._connect(self.scan_button.clicked, self.scan)
            self._connect(self.filter_input.textChanged, self.filter_rows)
            self._connect(self.all_button.clicked, lambda: self.toggle_all(True))
            self._connect(self.none_button.clicked, lambda: self.toggle_all(False))
            self._connect(self.copy_confirm.toggled, self.refresh_selection)
            self._connect(self.choose_folder_button.clicked, self.choose_folder)
            self._connect(self.export_button.clicked, self.export_files)
            self._connect(self.apply_button.clicked, self.apply_changes)
            self._connect(self.close_button.clicked, self.close)
            changed = lambda item, col: self._safe(
                lambda: self.on_tree_item_changed(item, col)
            )
            self.table.itemChanged.connect(changed)
            self._connections.append((self.table.itemChanged, changed))
            self._safe(self.scan)

        def _update_folder_label(self):
            if self.output_folder:
                self.folder_label.setText("Th\u01b0 m\u1ee5c l\u01b0u: " + self.output_folder)
            else:
                self.folder_label.setText("Th\u01b0 m\u1ee5c l\u01b0u: ch\u01b0a ch\u1ecdn")

        def choose_folder(self):
            font_directory = (
                os.path.dirname(self.snapshot["font_path"])
                if self.snapshot else ""
            )
            initial = self.output_folder or (
                font_directory if os.path.isdir(font_directory)
                else os.path.expanduser("~")
            )
            picked = QtGui.QFileDialog.getExistingDirectory(
                self, "Ch\u1ecdn n\u01a1i l\u01b0u b\xe1o c\xe1o", initial
            )
            folder = str(picked or "").strip()
            if not folder:
                return
            if not os.path.isdir(folder):
                raise RuntimeError("Th\u01b0 m\u1ee5c v\u1eeba ch\u1ecdn kh\xf4ng t\u1ed3n t\u1ea1i: " + folder)
            self.output_folder = folder
            sys.__dict__.setdefault(KEY, {})["output_folder"] = folder
            self._update_folder_label()
            self.refresh_selection()
            self.set_status("\u0110\xe3 ch\u1ecdn th\u01b0 m\u1ee5c l\u01b0u b\xe1o c\xe1o")

        def _connect(self, signal, callback):
            guarded = lambda *args: self._safe(callback)
            signal.connect(guarded)
            self._connections.append((signal, guarded))

        def _safe(self, callback):
            try:
                callback()
            except Exception as exc:
                details = traceback.format_exc()
                print("FL KERN GUI ERROR:", details)
                self.status.setText(type(exc).__name__ + ": " + str(exc))
                self.status.setStyleSheet("color:#ff9a9a;")
                self.diagnostics.setPlainText(details[-2800:])
                self.apply_button.setEnabled(False)

        def set_status(self, message, error=False):
            self.status.setText(message)
            self.status.setStyleSheet(
                "color:#c64e3b;" if error else "color:#237258;"
            )

        def scan(self):
            self.apply_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.snapshot = None
            self.applied = False
            self.groups = {}
            self.entries = []
            self._updating_tree = True
            self.table.clear()
            self.copy_confirm.setChecked(False)
            self.name_confirm.setChecked(False)
            self._updating_tree = False
            current_font = fontlab.CurrentFont()
            snap = scan_font(current_font, core)
            self.snapshot = snap

            self._updating_tree = True
            try:
                for idx, (class_name, names) in enumerate(
                    sorted(snap["changes"].items())
                ):
                    parent = QtGui.QTreeWidgetItem(self.table)
                    parent.setFlags(
                        parent.flags() | QtCore.Qt.ItemIsUserCheckable
                    )
                    parent.setCheckState(0, QtCore.Qt.Checked)
                    parent.setText(1, "@" + class_name)
                    roles = sorted(snap["roles"].get(class_name, []))
                    parent.setText(
                        2, "/".join(
                            "Tr\xe1i" if role == "LEFT" else "Ph\u1ea3i"
                            for role in roles
                        ) or "?"
                    )
                    preview = ", ".join(names[:3])
                    if len(names) > 3:
                        preview += "  +" + str(len(names) - 3) + " kh\xe1c"
                    parent.setText(3, preview)
                    parent.setText(4, str(len(names)))
                    self.groups[class_name] = parent
                    for name in names:
                        detected = snap["provenance"].get(name, "unicode")
                        child = QtGui.QTreeWidgetItem(parent)
                        child.setFlags(
                            child.flags() | QtCore.Qt.ItemIsUserCheckable
                        )
                        child.setCheckState(0, QtCore.Qt.Checked)
                        child.setText(
                            3, name + ("  [name-only]" if detected == "name" else "")
                        )
                        self.entries.append((class_name, name, detected, child))
                    parent.setExpanded(idx == 0)
            finally:
                self._updating_tree = False

            name = ntpath.basename(snap["font_path"]) or "(unsaved font)"
            self.info.setText("Font \u0111ang m\u1edf: " + name)
            self.stat_values["glyph_count"].setText(str(snap["glyph_count"]))
            self.stat_values["class_count"].setText(str(len(snap["classes"])))
            self.stat_values["pos_rules"].setText(str(snap["pos_rules"]))
            self.stat_values["proposals"].setText(str(len(self.entries)))
            self.all_button.setEnabled(bool(self.entries))
            self.none_button.setEnabled(bool(self.entries))
            self.safety_label.setText(
                str(len(snap["issues"])) + " xung \u0111\u1ed9t / c\u1ea3nh b\xe1o"
            )
            self.safety_label.setStyleSheet(
                "color:#c64e3b;" if snap["issues"] else "color:#237258;"
            )
            fallback_count = sum(
                detected == "name" for _, _, detected, _ in self.entries
            )
            self.name_confirm.setVisible(bool(fallback_count))
            self.refresh_selection()
            if snap["issues"]:
                msg = "SAFETY ISSUES (" + str(len(snap["issues"])) + "):\n"
                msg += "\n".join(snap["issues"][:20])
                self.diagnostics.setPlainText(msg)
                self.set_status("Review safety issues before applying", error=True)
            else:
                self.diagnostics.setPlainText(
                    "PASS: 0 safety issues. "
                    + str(len(snap["changes"])) + " classes / "
                    + str(len(self.entries)) + " proposed memberships.\n"
                    + str(fallback_count) + " name-only candidates. "
                    "No font edits have been made."
                )
                self.set_status("\u0110\xe3 qu\xe9t xong; ki\u1ec3m tra glyph tr\u01b0\u1edbc khi \xe1p d\u1ee5ng")
            self.filter_rows()

        def selected_pairs(self):
            return {
                (class_name, name)
                for class_name, name, _detected, item in self.entries
                if item.checkState(0) == QtCore.Qt.Checked
            }

        def refresh_selection(self):
            count = len(self.selected_pairs())
            self.selection_label.setText(
                str(count) + " / " + str(len(self.entries)) + " glyph \u0111\xe3 ch\u1ecdn"
            )
            self.export_button.setEnabled(
                bool(self.snapshot) and bool(self.output_folder)
            )
            self.apply_button.setEnabled(
                bool(count) and bool(self.snapshot)
                and not self.snapshot["issues"] and not self.applied
                and is_checked(self.copy_confirm)
            )

        def on_tree_item_changed(self, item, column):
            if self._updating_tree or column != 0:
                return
            self._updating_tree = True
            try:
                parent = item.parent()
                if parent is None:
                    state = item.checkState(0)
                    if state != QtCore.Qt.PartiallyChecked:
                        for i in range(item.childCount()):
                            item.child(i).setCheckState(0, state)
                else:
                    states = [
                        parent.child(i).checkState(0)
                        for i in range(parent.childCount())
                    ]
                    if all(s == QtCore.Qt.Checked for s in states):
                        state = QtCore.Qt.Checked
                    elif all(s == QtCore.Qt.Unchecked for s in states):
                        state = QtCore.Qt.Unchecked
                    else:
                        state = QtCore.Qt.PartiallyChecked
                    parent.setCheckState(0, state)
            finally:
                self._updating_tree = False
            self.refresh_selection()

        def toggle_all(self, state):
            checked_state = (
                QtCore.Qt.Checked if state else QtCore.Qt.Unchecked
            )
            self._updating_tree = True
            try:
                for parent in self.groups.values():
                    parent.setCheckState(0, checked_state)
                    for i in range(parent.childCount()):
                        parent.child(i).setCheckState(0, checked_state)
            finally:
                self._updating_tree = False
            self.refresh_selection()

        def filter_rows(self):
            query = qt_string(self.filter_input, "text").strip().lower()
            for class_name, parent in self.groups.items():
                class_match = query in class_name.lower()
                visible_children = 0
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    match = (
                        not query or class_match
                        or query in str(child.text(3)).lower()
                    )
                    child.setHidden(not match)
                    visible_children += bool(match)
                parent.setHidden(bool(query) and not class_match and not visible_children)
                if query and not parent.isHidden():
                    parent.setExpanded(True)

        def make_selected_plan(self):
            if self.snapshot is None:
                raise RuntimeError("Scan the font first.")
            return filtered_plan(self.snapshot, self.selected_pairs(), core)

        def make_report(self, selected, changed, name_only, issues):
            return build_report(
                self.snapshot, selected, changed, name_only, issues, core
            )

        def export_files(self):
            if not self.output_folder:
                raise RuntimeError("Ch\u1ecdn n\u01a1i l\u01b0u tr\u01b0\u1edbc khi export.")
            selected, proposed, name_only, issues = self.make_selected_plan()
            report = self.make_report(selected, proposed, name_only, issues)
            report_file, folder = write_reports_in_folder(
                core, self.output_folder, self.snapshot["original"],
                proposed, report
            )
            self.last_folder = folder
            self.diagnostics.setPlainText(
                "Saved original FEA backup, proposed FEA, DIFF and JSON:\n"
                + folder
                + ("\nSafety issues: " + "; ".join(issues[:6]) if issues else "")
            )
            self.set_status("Reports exported (font unchanged)")
            print("FL GUI REPORT:", report_file)

        def apply_changes(self):
            if self.snapshot is None or self.applied:
                raise RuntimeError("Nothing to apply; scan a font again.")
            # Preserve the original safeguard: FEA backup must be written before
            # any kern mutation. Ask for a destination rather than defaulting C:.
            if not self.output_folder:
                self.choose_folder()
                if not self.output_folder:
                    self.set_status("Ch\u01b0a ch\u1ecdn n\u01a1i l\u01b0u backup; \u0111\xe3 h\u1ee7y Apply")
                    return
            selected, proposed, name_only, issues = self.make_selected_plan()
            count = sum(len(names) for names in selected.values())
            blockers = list(issues)
            if count == 0:
                blockers.append("No selected glyph memberships.")
            if not is_checked(self.copy_confirm):
                blockers.append("Confirm you saved a full-font backup first.")
            filename = ntpath.basename(self.snapshot["font_path"]).lower()
            if not filename or (not ALLOW_ORIGINAL_FONT and "copy" not in filename):
                blockers.append("Font filename is not allowed.")
            if name_only and not is_checked(self.name_confirm):
                blockers.append("Name-only members require explicit approval.")
            current = fontlab.CurrentFont()
            if current is None:
                blockers.append("No active font.")
            elif str(getattr(current, "path", "") or "") != self.snapshot["font_path"]:
                blockers.append("Active font changed since the scan.")
            layout = self.snapshot["font"].features
            if core.read_kern(layout) != self.snapshot["original"]:
                blockers.append("Kern feature changed since the scan.")
            if layout.get_prefix() != self.snapshot["prefix"]:
                blockers.append("Common FEA prefix changed since the scan.")
            if set(self.snapshot["font"].keys()) != self.snapshot["available"]:
                blockers.append("Glyph list changed since the scan.")
            if blockers:
                self.diagnostics.setPlainText(
                    "APPLY BLOCKED:\n" + "\n".join(blockers[:20])
                )
                self.set_status("Blocked: review the warnings", error=True)
                return

            prompt = (
                "Apply " + str(count) + " memberships to "
                + str(len(selected)) + " existing kerning classes?\n\n"
                "Font: " + filename + "\n\n"
                "Have you saved a full-font backup separately?\n"
                "The tool backs up only the kern FEA text. "
                "The font will NOT be saved automatically."
            )
            answer = QtGui.QMessageBox.question(
                self, "Apply to active font?", prompt,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if answer != QtGui.QMessageBox.Yes:
                self.set_status("Apply cancelled; font unchanged")
                return

            report = self.make_report(selected, proposed, name_only, issues)
            report["status"] = "BACKUP_BEFORE_APPLY"
            report_file, folder = write_reports_in_folder(
                core, self.output_folder, self.snapshot["original"],
                proposed, report
            )
            self.last_folder = folder
            try:
                method = core.write_kern(layout, proposed)
                readback = core.read_kern(layout)
                prefix_ok = layout.get_prefix() == self.snapshot["prefix"]
                report["write_method"] = method
                report["readback_exact"] = (readback == proposed)
                report["prefix_unchanged"] = prefix_ok
                if readback != proposed or not prefix_ok:
                    report["status"] = "READBACK_MISMATCH_DO_NOT_SAVE"
                    self.set_status("READBACK MISMATCH \u2014 DO NOT SAVE", error=True)
                    self.diagnostics.setPlainText(
                        "DO NOT SAVE. Close the font without saving.\n"
                        "Backup is available at:\n" + folder
                    )
                else:
                    report["status"] = "READBACK_PASS_NOT_YET_SAVED"
                    self.applied = True
                    self.apply_button.setEnabled(False)
                    self.set_status("APPLY READBACK: EXACT MATCH / " + str(count) + " added")
                    self.diagnostics.setPlainText(
                        "Success: " + str(count) + " memberships applied in memory.\n"
                        "NEXT: Compile Features, save font, close/reopen, "
                        "then Scan again (expect 0).\n"
                        "Backup + report: " + folder
                    )
                    print("FL GUI APPLY READBACK: EXACT MATCH")
            except Exception:
                report["status"] = "APPLY_ERROR_DO_NOT_SAVE"
                report["traceback"] = traceback.format_exc()
                self.set_status("APPLY ERROR \u2014 DO NOT SAVE", error=True)
                self.diagnostics.setPlainText(
                    report["traceback"][-2500:]
                    + "\nClose font without saving. Backup: " + folder
                )
            finally:
                try:
                    core.save_report(report_file, report)
                except Exception as exc:
                    print("FL GUI REPORT ERROR:", str(exc))

        def closeEvent(self, event):
            for signal, slot in self._connections:
                try:
                    signal.disconnect(slot)
                except Exception:
                    pass
            self._connections = []
            open_windows = getattr(sys, KEY, {})
            if open_windows.get("window") is self:
                open_windows.pop("window", None)
            QtGui.QDialog.closeEvent(self, event)

    windows = sys.__dict__.setdefault(KEY, {})
    old = windows.pop("window", None)
    if old is not None:
        try:
            old.close()
        except Exception:
            pass
    try:
        parent = fontlab.MainWindow()
    except Exception:
        parent = None
    dialog = Window(parent)
    windows["window"] = dialog
    dialog.show()
    dialog.raise_()
    return dialog


def main():
    try:
        import fontlab
        core = get_core()
        return start_gui(core, fontlab)
    except Exception:
        print("FontLab Vietnamese Kerning GUI failed to start:")
        print(traceback.format_exc())
        return None


if __name__ == "__main__":
    main()
