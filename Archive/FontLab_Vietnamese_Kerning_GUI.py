# -*- coding: utf-8 -*-
#FLM: Vietnamese Kerning Assistant (GUI)
"""
FontLab Vietnamese Kerning Assistant - GUI beta for FontLab 8
============================================================
Runs INSIDE FontLab's existing Qt5 / PythonQt application.
No tkinter, no new QApplication, no extra packages, no server.

Place this file alongside FontLab_Vietnamese_Kerning_Assistant_v1.py.
Launch THIS FILE from FontLab's Scripts/Scripting panel.

Every scan is read-only. Clicking "Export report" writes .fea/.diff/.json
files but does not change the font. "Apply" changes only the OpenType
"kern" feature of an explicitly confirmed disposable COPY; it NEVER
saves the font automatically. The core algorithm is the verified v1.0.

GUI beta still needs testing on FL8.4.3.8984; FL9 is not verified.
"""

from __future__ import print_function

import importlib
import json
import ntpath
import os
import sys
import time
import traceback


KEY = "_fontlab_vietnamese_kerning_gui"
TITLE = "Vietnamese Kerning Assistant"
CORE_MODULE = "FontLab_Vietnamese_Kerning_Assistant_v1"
ALLOW_ORIGINAL_FONT = True


def get_core():
    """Load the verified engine next to this launcher, without editing it."""
    directory = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
    if directory and directory not in sys.path:
        sys.path.insert(0, directory)
    try:
        return importlib.import_module(CORE_MODULE)
    except ImportError as exc:
        raise RuntimeError(
            "Missing " + CORE_MODULE + ".py beside the GUI script. "
            "Extract BOTH files from the ZIP into the same directory."
        ) from exc


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
        "tool": "FontLab Vietnamese Kerning Assistant GUI beta",
        "engine": "FontLab Vietnamese Kerning Assistant v1.0",
        "engine_verification": "Verified FL8.4.3.8984/Post Grotesk; GUI beta unverified",
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
            self.setWindowTitle(TITLE + "  /  BETA")
            self.resize(990, 710)
            self.setMinimumWidth(830)

            self._connections = []
            self._row_connections = []
            self.snapshot = None
            self.rows = []
            self.row_checks = []
            self.applied = False
            self.last_folder = ""

            self.setStyleSheet("""
                QDialog { background: #101725; color: #edf2fb; }
                QLabel { color: #e5ecf8; }
                QLineEdit, QTableWidget, QPlainTextEdit {
                    color: #f1f5fc; background: #162238;
                    border: 1px solid #33435e; border-radius: 5px;
                    selection-background-color: #b64e77;
                    selection-color: #ffffff;
                }
                QTableWidget { alternate-background-color: #1c2a42; }
                QHeaderView::section {
                    background: #26334b; color: #e3ebfb;
                    border: none; padding: 7px;
                }
                QPushButton {
                    background: #25334b; color: #f8f8ff;
                    border: 1px solid #354864; border-radius: 6px;
                    padding: 9px 15px;
                }
                QPushButton:hover { background: #324866; }
                QPushButton:disabled { color: #74839a; background: #182235; }
                QCheckBox { color: #e6eafa; spacing: 8px; }
                QCheckBox::indicator { width: 15px; height: 15px; }
            """)
            root = QtGui.QVBoxLayout(self)
            root.setContentsMargins(24, 20, 24, 22)
            root.setSpacing(11)

            badge = QtGui.QLabel("FONTLAB  /  VIETNAMESE KERNING")
            badge.setStyleSheet("color:#f2a6c6; font-weight:bold;")
            root.addWidget(badge)

            title = QtGui.QLabel("Vietnamese Kerning Assistant")
            title.setFont(QtGui.QFont("Segoe UI", 20, QtGui.QFont.Bold))
            root.addWidget(title)

            desc = QtGui.QLabel(
                "Scan the active font, review Vietnamese glyph memberships, "
                "and apply to a confirmed COPY only. No automatic font saving."
            )
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#a9bbd4;")
            root.addWidget(desc)

            self.info = QtGui.QLabel("No font scanned yet")
            self.info.setStyleSheet(
                "background:#1a2840; color:#eef4ff; border-radius:6px; "
                "padding:12px; font-weight:bold;"
            )
            root.addWidget(self.info)

            search_row = QtGui.QHBoxLayout()
            self.filter_input = QtGui.QLineEdit()
            self.filter_input.setPlaceholderText("Filter by class or glyph name...")
            search_row.addWidget(self.filter_input, 1)
            self.scan_button = QtGui.QPushButton("Scan active font")
            self.scan_button.setStyleSheet(
                "QPushButton {background:#e69abb;color:#172238;"
                "border:0;font-weight:bold;} "
                "QPushButton:hover {background:#f4afcd;}"
            )
            search_row.addWidget(self.scan_button)
            root.addLayout(search_row)

            self.table = QtGui.QTableWidget(0, 5)
            self.table.setHorizontalHeaderLabels(
                ["Use", "Class", "Side", "Glyph to add", "Detected by"]
            )
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            self.table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
            self.table.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
            self.table.setShowGrid(False)
            self.table.setColumnWidth(0, 54)
            self.table.setColumnWidth(1, 135)
            self.table.setColumnWidth(2, 105)
            self.table.setColumnWidth(3, 350)
            self.table.setColumnWidth(4, 130)
            root.addWidget(self.table, 1)

            quick = QtGui.QHBoxLayout()
            self.all_button = QtGui.QPushButton("Select all")
            self.none_button = QtGui.QPushButton("Select none")
            self.selection_label = QtGui.QLabel("0 selected")
            self.selection_label.setStyleSheet("color:#f2a6c6;")
            quick.addWidget(self.all_button)
            quick.addWidget(self.none_button)
            quick.addStretch()
            quick.addWidget(self.selection_label)
            root.addLayout(quick)

            self.copy_confirm = QtGui.QCheckBox(
                "I confirm I have a separate full-font backup"
            )
            self.name_confirm = QtGui.QCheckBox(
                "Allow name-only glyphs (after manually reviewing the list)"
            )
            root.addWidget(self.copy_confirm)
            root.addWidget(self.name_confirm)

            self.diagnostics = QtGui.QPlainTextEdit()
            self.diagnostics.setReadOnly(True)
            self.diagnostics.setMaximumHeight(105)
            self.diagnostics.setPlainText(
                "PREVIEW MODE — Scan to inspect the current font. "
                "Changes are not applied until you click Apply."
            )
            root.addWidget(self.diagnostics)

            footer = QtGui.QHBoxLayout()
            self.status = QtGui.QLabel("Ready")
            self.status.setWordWrap(True)
            self.status.setStyleSheet("color:#91dcb9;")
            footer.addWidget(self.status, 1)
            self.export_button = QtGui.QPushButton("Export FEA + Diff")
            self.apply_button = QtGui.QPushButton("Apply Changes")
            self.apply_button.setStyleSheet(
                "QPushButton {background:#e69abb;color:#172238;"
                "border:0;font-weight:bold;} "
                "QPushButton:hover {background:#f4afcd;} "
                "QPushButton:disabled {background:#6b5264;color:#aca3ad;}"
            )
            self.close_button = QtGui.QPushButton("Close")
            footer.addWidget(self.export_button)
            footer.addWidget(self.apply_button)
            footer.addWidget(self.close_button)
            root.addLayout(footer)

            self.export_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.all_button.setEnabled(False)
            self.none_button.setEnabled(False)
            self._connect(self.scan_button.clicked, self.scan)
            self._connect(self.filter_input.textChanged, self.filter_rows)
            self._connect(self.all_button.clicked, lambda: self.toggle_all(True))
            self._connect(self.none_button.clicked, lambda: self.toggle_all(False))
            self._connect(self.export_button.clicked, self.export_files)
            self._connect(self.apply_button.clicked, self.apply_changes)
            self._connect(self.close_button.clicked, self.close)
            self._safe(self.scan)

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
                "color:#ff9a9a;" if error else "color:#91dcb9;"
            )

        def scan(self):
            self.apply_button.setEnabled(False)
            self.export_button.setEnabled(False)
            for signal, slot in self._row_connections:
                try:
                    signal.disconnect(slot)
                except Exception:
                    pass
            self._row_connections = []
            self.snapshot = None
            self.applied = False
            self.rows = []
            self.row_checks = []
            self.table.setRowCount(0)
            self.copy_confirm.setChecked(False)
            self.name_confirm.setChecked(False)
            current_font = fontlab.CurrentFont()
            snap = scan_font(current_font, core)
            self.snapshot = snap

            self.rows = [
                (class_name, name, snap["provenance"].get(name, "unicode"))
                for class_name, names in sorted(snap["changes"].items())
                for name in names
            ]
            self.table.setRowCount(len(self.rows))
            for idx, (class_name, name, detected) in enumerate(self.rows):
                checkbox = QtGui.QCheckBox()
                checkbox.setChecked(True)
                self.table.setCellWidget(idx, 0, checkbox)
                self.row_checks.append(checkbox)
                role = "/".join(sorted(snap["roles"].get(class_name, []))) or "?"
                for col, value in enumerate(
                    ("@" + class_name, role, name, detected), start=1
                ):
                    item = QtGui.QTableWidgetItem(value)
                    self.table.setItem(idx, col, item)
                guarded = lambda *args: self._safe(self.refresh_selection)
                checkbox.toggled.connect(guarded)
                self._row_connections.append((checkbox.toggled, guarded))
            self.table.resizeRowsToContents()

            name = ntpath.basename(snap["font_path"]) or "(unsaved font)"
            self.info.setText(
                name + "    |    " + str(snap["glyph_count"]) + " glyphs"
                + "    |    " + str(len(snap["classes"])) + " classes"
                + "    |    " + str(snap["pos_rules"]) + " POS rules"
            )
            self.export_button.setEnabled(True)
            self.all_button.setEnabled(bool(self.rows))
            self.none_button.setEnabled(bool(self.rows))
            self.refresh_selection()
            if snap["issues"]:
                msg = "SAFETY ISSUES (" + str(len(snap["issues"])) + "):\n"
                msg += "\n".join(snap["issues"][:20])
                self.diagnostics.setPlainText(msg)
                self.set_status("Review safety issues before applying", error=True)
            else:
                fallback_count = sum(
                    detected == "name" for _, _, detected in self.rows
                )
                self.diagnostics.setPlainText(
                    "PASS: 0 safety issues. "
                    + str(len(snap["changes"])) + " classes / "
                    + str(len(self.rows)) + " proposed memberships.\n"
                    + str(fallback_count) + " name-only candidates. "
                    "No font edits have been made."
                )
                self.set_status("Preview ready; select members and export/Apply")
            self.filter_rows()

        def selected_pairs(self):
            return {
                (class_name, name)
                for (class_name, name, _), box in zip(self.rows, self.row_checks)
                if is_checked(box)
            }

        def refresh_selection(self):
            count = len(self.selected_pairs())
            self.selection_label.setText(str(count) + " / " + str(len(self.rows)) + " selected")
            self.apply_button.setEnabled(
                bool(count) and bool(self.snapshot)
                and not self.snapshot["issues"] and not self.applied
            )

        def toggle_all(self, state):
            for checkbox in self.row_checks:
                checkbox.setChecked(bool(state))
            self.refresh_selection()

        def filter_rows(self):
            query = qt_string(self.filter_input, "text").strip().lower()
            for i, row in enumerate(self.rows):
                match = not query or any(query in str(value).lower() for value in row)
                self.table.setRowHidden(i, not match)

        def make_selected_plan(self):
            if self.snapshot is None:
                raise RuntimeError("Scan the font first.")
            return filtered_plan(self.snapshot, self.selected_pairs(), core)

        def make_report(self, selected, changed, name_only, issues):
            return build_report(
                self.snapshot, selected, changed, name_only, issues, core
            )

        def export_files(self):
            selected, proposed, name_only, issues = self.make_selected_plan()
            report = self.make_report(selected, proposed, name_only, issues)
            report_file, folder = core.write_artifacts(
                self.snapshot["original"], proposed, report
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
            report_file, folder = core.write_artifacts(
                self.snapshot["original"], proposed, report
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
                    self.set_status("READBACK MISMATCH — DO NOT SAVE", error=True)
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
                self.set_status("APPLY ERROR — DO NOT SAVE", error=True)
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
            for signal, slot in self._row_connections + self._connections:
                try:
                    signal.disconnect(slot)
                except Exception:
                    pass
            self._row_connections = []
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
