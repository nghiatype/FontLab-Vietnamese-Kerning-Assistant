# -*- coding: utf-8 -*-
#FLM: NghiaType Native Kerning V2 (Tropical GUI Alpha 1)
"""NghiaType Native Kerning V2 GUI - FontLab 8/9, PythonQt.

Keep this file ASCII-only for FontLab's macro editor. Unicode UI strings use
Python escapes. This is a NEW experimental GUI; it does not change V1 Stable.

The companion Core is the *unchanged*:
    NghiaType_Native_Core_V2_Alpha1_4_1_SCOPED_GUARDED_FL8(1).py

Scan and selected Preview are read-only. The only font mutation is a guarded,
step-by-step native group write on a disposable, single-master FontLab 8 COPY,
following the same verification policy as Core Alpha.1.4.1. No auto Save.
FontLab 9 and unknown application versions are strictly PREVIEW ONLY.
"""

from __future__ import print_function

import importlib.util
import json
import ntpath
import os
import re
import sys
import time
import traceback


GUI_BUILD = "V2 Alpha.1.9"
GUI_VERSION = GUI_BUILD + " / Refined Layout"
KEY = "_nghiatype_native_v2_gui_alpha1"
CORE_PATH_KEY = "_nghiatype_native_v2_core_path"
CORE_PREFIX = "NghiaType_Native_Core_V2_Alpha1_4_1_SCOPED_GUARDED_FL8"


def qt_text(widget, name="text"):
    value = getattr(widget, name)
    return str(value() if callable(value) else value)


def qt_value(widget, name):
    """Read either PythonQt properties or callable Qt getters safely."""
    value = getattr(widget, name)
    return value() if callable(value) else value


def qt_checked(widget):
    value = getattr(widget, "isChecked", None)
    if callable(value):
        return bool(value())
    return bool(getattr(widget, "checked", False))


def native_core_path_hint():
    """Locate the supplied Alpha core, never the legacy OpenType V1 core."""
    remembered = str(sys.__dict__.get(CORE_PATH_KEY, "") or "")
    if remembered and os.path.isfile(remembered):
        return remembered
    directory = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
    if not directory or not os.path.isdir(directory):
        return ""
    matches = sorted(
        os.path.join(directory, item) for item in os.listdir(directory)
        if item.startswith(CORE_PREFIX) and item.lower().endswith(".py")
    )
    return matches[0] if len(matches) == 1 else ""


def load_native_core(path):
    """Explicit file-based import; importing does NOT execute the Core main()."""
    path = str(path or "").strip()
    if not os.path.isfile(path) or not ntpath.basename(path).startswith(CORE_PREFIX):
        raise RuntimeError("Select the unmodified Native Core V2 Alpha.1.4.1 .py file.")
    spec = importlib.util.spec_from_file_location("_nghiatype_native_v2_scoped_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load Native Core V2 from the selected file.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = (
        "current_package", "read_master_count", "snapshot_groups",
        "snapshot_pairs", "detect_vietnamese", "make_plan",
        "select_memberships", "plan_token", "direct_group_matches",
        "APPLY_TESTED_MODES", "MAX_CLASSES_PER_APPLY", "MAX_MEMBERSHIPS_PER_APPLY",
    )
    if any(not hasattr(module, attr) for attr in required):
        raise RuntimeError("Selected script is not the compatible Scoped Guarded V2 Core.")
    sys.__dict__[CORE_PATH_KEY] = path
    return module


def detect_major(fontlab, qtcore=None):
    """Only trust FontLab's application path or Qt's running executable path.

    Unknown/conflicting results deliberately mean no native writer.
    """
    paths = []
    try:
        value = fontlab.ApplicationPath()
        if value:
            paths.append(str(value))
    except Exception:
        pass
    if qtcore is not None:
        try:
            value = qtcore.QCoreApplication.applicationFilePath()
            if value:
                paths.append(str(value))
        except Exception:
            pass
    found = set()
    for path in paths:
        # A FontLab install path may end at the .app/.exe OR its parent folder.
        hits = re.findall(r"(?i)fontlab[ _-]*([89])(?=\W|$)", path)
        found.update(int(hit) for hit in hits)
    return (next(iter(found)) if len(found) == 1 else None), paths


def runtime_version_caption(fontlab, qtcore, major):
    """Display runtime versions without trusting them to authorize Apply.

    The FontLab application version is optional in some PythonQt builds.
    An unavailable full build number must never be guessed from a filename.
    """
    py_version = "Python %d.%d.%d" % (
        sys.version_info.major, sys.version_info.minor, sys.version_info.micro
    )
    fl_version = "FontLab %d" % major if major in (8, 9) else "FontLab unknown"
    if major in (8, 9):
        sources = [
            (fontlab, "ApplicationVersion"),
            (fontlab, "applicationVersion"),
            (fontlab, "__version__"),
        ]
        if qtcore is not None:
            sources.append((getattr(qtcore, "QCoreApplication", None),
                            "applicationVersion"))
        for source, attr in sources:
            try:
                value = getattr(source, attr, None)
                if value is None:
                    continue
                value = value() if callable(value) else value
                # Only show a concrete full version belonging to this major.
                match = re.search(r"(?<!\d)%d(?:\.\d+)+" % major, str(value))
                if match:
                    fl_version = "FontLab " + match.group(0)
                    break
            except Exception:
                continue
    return "%s  \u2022  %s  \u2022  Plugin %s" % (
        py_version, fl_version, GUI_BUILD
    )


def scan_native(fontlab, core):
    """Read native classes, pairs and glyphs; never mutate the font."""
    font = fontlab.CurrentFont()
    if font is None:
        raise RuntimeError("Open a font first.")
    path = str(getattr(font, "path", "") or "")
    package = core.current_package(fontlab, font)
    master = str(package.getLayerName())
    count = core.read_master_count(package)
    kerning = package.kerning(master)
    groups = core.snapshot_groups(kerning)
    pairs = core.snapshot_pairs(kerning)
    available, candidates, origin, scan_issues = core.detect_vietnamese(font)
    safe_all, blocked, plan_issues = core.make_plan(groups, available, candidates)
    return {
        "font_path": path,
        "master": master,
        "master_count": count,
        "groups": groups,
        "pairs": pairs,
        "available": available,
        "origin": origin,
        "safe_all": safe_all,
        "blocked": blocked,
        "issues": list(scan_issues) + list(plan_issues),
        "candidate_count": len(origin),
    }


def selected_preview(core, snap, pairs):
    """Bind a checked glyph/class allowlist to a full-state PLAN_TOKEN."""
    allowed = {(cls, glyph) for cls, names in snap["safe_all"].items() for glyph in names}
    pairs = set(pairs)
    if not pairs or not pairs.issubset(allowed):
        raise ValueError("Selection is empty or contains unavailable proposals.")
    mapping = {}
    for cls, glyph in sorted(pairs):
        mapping.setdefault(cls, []).append(glyph)
    selected, already_present, selection_issues, rules = core.select_memberships(
        snap["safe_all"], snap["groups"], mapping
    )
    issues = snap["issues"] + selection_issues
    name_only = sorted(
        glyph for names in selected.values() for glyph in names
        if snap["origin"].get(glyph.split(".", 1)[0], (None, "name"))[1] == "name"
    )
    token = core.plan_token(
        snap["font_path"], snap["master"], snap["groups"], snap["pairs"],
        snap["available"], snap["safe_all"], selected, rules,
        snap["blocked"], issues,
    )
    return {
        "selected": selected,
        "pairs": frozenset(pairs),
        "already_present": already_present,
        "issues": issues,
        "name_only": name_only,
        "token": token,
        "count": sum(len(names) for names in selected.values()),
    }


def apply_blockers(core, snap, preview, major, filename_text, master_text, confirmed):
    """All safety rules are enforced in backend, regardless of GUI state."""
    blockers = []
    filename = ntpath.basename(snap["font_path"])
    if major != 8:
        blockers.append("Native writer disabled: only verified FontLab 8 is supported.")
    if not filename or "copy" not in filename.casefold():
        blockers.append("The saved test filename MUST contain 'copy'.")
    if not filename_text or filename_text != filename:
        blockers.append("Typed copy filename must match exactly.")
    if not master_text or master_text != snap["master"]:
        blockers.append("Typed master name must match exactly.")
    if snap["master_count"] != 1:
        blockers.append("Only verified single-master fonts may be modified.")
    if not confirmed:
        blockers.append("Confirm you are working on a disposable test copy.")
    if snap["issues"] or preview["issues"] or snap["blocked"]:
        blockers.append("Global conflicts or scan/selection issues block ALL Apply.")
    if preview["name_only"]:
        blockers.append("Name-only candidates are not authorized for Apply in Alpha.1.")
    if not preview["count"]:
        blockers.append("Select one or more glyph memberships.")
    if len(preview["selected"]) > core.MAX_CLASSES_PER_APPLY:
        blockers.append("Too many selected classes in experimental batch.")
    if preview["count"] > core.MAX_MEMBERSHIPS_PER_APPLY:
        blockers.append("Too many memberships in experimental batch.")
    for key in preview["selected"]:
        if snap["groups"][key][1] not in core.APPLY_TESTED_MODES:
            blockers.append("Class %r uses an unverified writer mode." % key)
    if not snap["groups"] or not snap["available"]:
        blockers.append("Cannot apply to an empty font or with no native classes.")
    return blockers


def fresh_preflight(fontlab, core, snap, preview, major, filename_text,
                    master_text, confirmed):
    """Re-read *all* native state immediately before any write."""
    blockers = apply_blockers(
        core, snap, preview, major, filename_text, master_text, confirmed
    )
    if blockers:
        return None, blockers
    live = scan_native(fontlab, core)
    # Exact snapshots, including explicit pair amounts, must be identical.
    fields = ("font_path", "master", "master_count", "groups", "pairs",
              "available", "safe_all", "blocked", "issues", "origin")
    for field in fields:
        if live[field] != snap[field]:
            blockers.append("State changed after Scan (%s). Re-scan and Preview." % field)
    if blockers:
        return None, blockers
    live_preview = selected_preview(core, live, preview["pairs"])
    if live_preview["token"] != preview["token"]:
        blockers.append("PLAN_TOKEN mismatch. Re-scan and Preview.")
    blockers.extend(apply_blockers(
        core, live, live_preview, major, filename_text, master_text, confirmed
    ))
    return (live, []) if not blockers else (None, blockers)


def stepwise_native_apply(fontlab, core, live, preview, record=None):
    """Experimental FL8 writer: same guards/readback as Scoped Alpha.1.4.1.

    A failure after a write can leave PARTIAL in-memory changes: DO NOT SAVE.
    Calling code MUST run fresh_preflight() and request confirmation first.
    """
    package = core.current_package(fontlab, fontlab.CurrentFont())
    kerning = package.kerning(live["master"])
    expected_so_far = dict(live["groups"])
    initial_pairs = live["pairs"]
    keys = sorted(preview["selected"], key=lambda name: (name.casefold(), name))
    results = []
    if record is not None:
        record["write_attempted"] = False
    for key in keys:
        # Validate the current class and all other classes before each step.
        try:
            before = core.snapshot_groups(kerning)
            if before != expected_so_far or core.snapshot_pairs(kerning) != initial_pairs:
                raise RuntimeError("Unexpected native group/pair drift before %r" % key)
            old_members, mode = before[key]
            additions = set(preview["selected"][key])
            target = old_members + tuple(preview["selected"][key])
            if record is not None:
                record["write_attempted"] = True
            kerning.groups[key] = (list(target), mode)
            actual = core.snapshot_groups(kerning)
            actual_pairs = core.snapshot_pairs(kerning)
            actual_members, actual_mode = actual.get(key, ((), "<MISSING>"))
            members_ok = (
                len(actual_members) == len(target)
                and len(set(actual_members)) == len(actual_members)
                and set(actual_members) == set(target)
                and tuple(g for g in actual_members if g not in additions) == old_members
                and bool(old_members and actual_members and actual_members[0] == old_members[0])
                and actual_mode == mode
            )
            others_ok = (
                set(actual) == set(expected_so_far)
                and all(actual.get(other) == value for other, value in expected_so_far.items()
                        if other != key)
            )
            direct_ok = key in actual and core.direct_group_matches(
                kerning, key, actual[key]
            )
            if not (members_ok and others_ok and actual_pairs == initial_pairs and direct_ok):
                raise RuntimeError("READBACK MISMATCH at class %r" % key)
            results.append({
                "class": key, "added": list(preview["selected"][key]),
                "readback": "PASS", "actual_members": list(actual_members),
                "new_insertion_order_may_differ": tuple(actual_members) != target,
            })
            expected_so_far = dict(actual)
        except Exception as exc:
            return {
                "ok": False, "steps_passed": results, "failed_class": key,
                "error": "%s: %s" % (type(exc).__name__, exc),
                "status": "DO_NOT_SAVE_CLOSE_TEST_COPY",
            }
    return {
        "ok": True, "steps_passed": results,
        "status": "READBACK_PASS_IN_MEMORY_NOT_SAVED",
    }


def report_data(snap, preview, major, result=None):
    """Portable JSON preview/readback report; exported only on request."""
    return {
        "tool": "NghiaType Native Kerning V2 GUI Alpha.1",
        "created_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fontlab_major": major,
        "font_path": snap["font_path"],
        "master": snap["master"],
        "master_count": snap["master_count"],
        "glyph_count": len(snap["available"]),
        "native_classes": len(snap["groups"]),
        "native_explicit_pairs": len(snap["pairs"]),
        "vietnamese_candidates": snap["candidate_count"],
        "available_classes": len(snap["safe_all"]),
        "available_memberships": sum(len(x) for x in snap["safe_all"].values()),
        "selected_classes": len(preview["selected"]) if preview else 0,
        "selected_memberships": preview["count"] if preview else 0,
        "selected_additions": preview["selected"] if preview else {},
        "blocked_proposals": snap["blocked"],
        "issues": preview["issues"] if preview else snap["issues"],
        "name_only_selected": preview["name_only"] if preview else [],
        "plan_token": preview["token"] if preview else None,
        "readback": result,
        "status": result["status"] if result else "PREVIEW_ONLY_NO_MUTATIONS",
    }


def start_gui(fontlab, core, QtCore, QtGui):
    class Window(QtGui.QDialog):
        def __init__(self, parent=None):
            QtGui.QDialog.__init__(self, parent)
            self.setWindowTitle("NghiaType | Native Kerning V2 | " + GUI_VERSION)
            try:
                self.setWindowFlags(
                    self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception:
                pass
            self.resize(1220, 885)
            self.setMinimumWidth(860)
            self.major, self.runtime_paths = detect_major(fontlab, QtCore)
            self.snap = None
            self.preview = None
            self.apply_result = None
            self.entries = []
            self.parents = {}
            self.selected_glyphs = set()
            self.active_class = None
            self.glyph_widgets = {}
            self.updating_tree = False
            self.applied = False
            self.locked_after_failure = False
            self.focus_active = False
            self._saved_split_sizes = [550, 235]
            self.connections = []

            self.setStyleSheet("""
                QDialog { background:#FAF9F5; color:#1D1B16;
                    font-family:'Be Vietnam Pro','Segoe UI',Arial; font-size:12px; }
                QLabel { color:#1D1B16; }
                QLineEdit, QTreeWidget, QPlainTextEdit {
                    color:#1D1B16; background:#FAF9F5;
                    border:1px solid #E8E2D5; border-radius:15px;
                    selection-background-color:#CCEBE2;
                }
                QLineEdit { padding:10px 16px; }
                QLineEdit:focus { border:2px solid #004D40; }
                QTreeWidget { background:#FFFFFF;
                    alternate-background-color:#F7F8F3; outline:none; }
                QTreeWidget::item { padding:8px 5px; }
                QTreeWidget::item:selected { color:#00201A;
                    background:#CCEBE2; }
                QHeaderView::section { background:#F4F2EE; color:#625E55;
                    border:0; border-bottom:1px solid #E8E2D5;
                    padding:10px 7px; font-weight:bold; }
                QPlainTextEdit { padding:12px;
                    font-family:'Fragment Mono',Consolas,monospace;
                    font-size:11px; }
                QPushButton { color:#004D40; background:#E7EBDD; border:0;
                    border-radius:16px; padding:9px 14px; font-weight:bold; }
                QPushButton:hover { background:#CCEBE2; }
                QPushButton:disabled { background:#EEEDE7; color:#9C9A91; }
                QPushButton#scan { background:#004D40; color:white;
                    border-radius:21px; font-size:13px;
                    padding:10px 19px; font-weight:bold; }
                QPushButton#scan:hover { background:#006655; }
                QPushButton#apply { background:#BA1A1A; color:white;
                    border-radius:20px; font-weight:bold; }
                QPushButton#apply:hover { background:#941515; }
                QPushButton#apply:disabled { background:#E8E2D5;
                    color:#8B877F; }
                QPushButton#focus { background:#F4F2EE; color:#004D40; }
                QSplitter::handle:vertical { background:#FAF9F5;
                    border:0; }
                QCheckBox { spacing:9px; color:#410002; }
                QCheckBox::indicator { width:18px; height:18px; }
                QScrollBar:vertical { border:0; background:transparent;
                    width:8px; margin:3px 1px; }
                QScrollBar::handle:vertical { background:#D5D2CA;
                    border-radius:4px; min-height:24px; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height:0; border:0; }
                QScrollBar:horizontal { border:0; background:transparent;
                    height:8px; margin:1px 3px; }
                QScrollBar::handle:horizontal { background:#D5D2CA;
                    border-radius:4px; min-width:24px; }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width:0; border:0; }
            """)
            outer = QtGui.QVBoxLayout(self)
            outer.setContentsMargins(17, 14, 17, 13)
            outer.setSpacing(10)

            # The reference design's white app bar and dark green primary action.
            hero = QtGui.QFrame()
            hero.setObjectName("hero")
            hero.setStyleSheet(
                "QFrame#hero{background:#FFFFFF;border:1px solid #E8E2D5;"
                "border-radius:23px;}"
            )
            hero_layout = QtGui.QHBoxLayout(hero)
            hero_layout.setContentsMargins(18, 12, 18, 12)
            hero_layout.setSpacing(13)
            brand = QtGui.QVBoxLayout()
            brand.setSpacing(3)
            heading = QtGui.QLabel("NghiaType  /  Native Kerning")
            heading.setFont(QtGui.QFont("Plus Jakarta Sans", 16, QtGui.QFont.Bold))
            heading.setStyleSheet("color:#004D40;background:transparent;border:0;")
            subtitle = QtGui.QLabel(
                runtime_version_caption(fontlab, QtCore, self.major)
            )
            subtitle.setStyleSheet(
                "color:#79766E;background:transparent;border:0;font-size:10px;"
            )
            brand.addWidget(heading)
            brand.addWidget(subtitle)
            hero_layout.addLayout(brand, 1)
            version_text = (
                "FL8  /  GUARDED WRITER" if self.major == 8 else
                "FL9  /  PREVIEW ONLY" if self.major == 9 else
                "UNKNOWN  /  PREVIEW ONLY"
            )
            self.version_label = QtGui.QLabel(version_text)
            self.version_label.setStyleSheet(
                "color:#004D40;background:#CCEBE2;border-radius:12px;"
                "padding:10px 12px;font-size:10px;font-weight:bold;"
            )
            hero_layout.addWidget(self.version_label)
            self.scan_button = QtGui.QPushButton("01   Scan native classes")
            self.scan_button.setObjectName("scan")
            self.scan_button.setMinimumHeight(43)
            hero_layout.addWidget(self.scan_button)
            outer.addWidget(hero)

            context = QtGui.QFrame()
            context.setObjectName("fontContext")
            context.setStyleSheet(
                "QFrame#fontContext{background:#FFFFFF;border:1px solid #E8E2D5;"
                "border-radius:18px;}"
            )
            font_row = QtGui.QHBoxLayout(context)
            font_row.setContentsMargins(15, 9, 15, 9)
            context_label = QtGui.QLabel("ACTIVE FONT")
            context_label.setStyleSheet(
                "color:#79766E;font-size:10px;font-weight:bold;"
                "background:transparent;border:0;"
            )
            font_row.addWidget(context_label)
            self.font_info = QtGui.QLabel("Open a font, then Scan native classes")
            self.font_info.setStyleSheet(
                "color:#004D40;font-weight:bold;background:transparent;border:0;"
            )
            font_row.addWidget(self.font_info, 1)
            outer.addWidget(context)

            stats = QtGui.QHBoxLayout()
            stats.setSpacing(10)
            self.stats = {}
            for key, name, tint, stroke, ink, detail in (
                ("glyphs", "GLYPHS", "#FFFFFF", "#E8E2D5", "#1D1B16", "Font active glyphs"),
                ("classes", "NATIVE CLASSES", "#E7EBDD", "#CCEBE2", "#004D40", "Classes detected"),
                ("candidates", "VIET CANDIDATES", "#FFF0D8", "#FFDDB3", "#7A4D00", "Diacritic matches"),
                ("available", "AVAILABLE ADDS", "#FFF0EE", "#FFDAD6", "#BA1A1A", "Ready to include"),
            ):
                frame = QtGui.QFrame()
                frame.setObjectName("metricCard")
                frame.setMinimumHeight(96)
                frame.setStyleSheet(
                    "QFrame#metricCard{background:" + tint + ";border:1px solid " +
                    stroke + ";border-radius:21px;}"
                )
                column = QtGui.QVBoxLayout(frame)
                column.setContentsMargins(16, 9, 12, 9)
                column.setSpacing(2)
                caption = QtGui.QLabel(name)
                caption.setStyleSheet(
                    "background:transparent;border:0;color:" + ink +
                    ";font-size:10px;font-weight:bold;"
                )
                val = QtGui.QLabel("\u2014")
                val.setFont(QtGui.QFont("Plus Jakarta Sans", 23, QtGui.QFont.Bold))
                val.setStyleSheet(
                    "color:" + ink + ";background:transparent;border:0;"
                )
                tagline = QtGui.QLabel(detail)
                tagline.setStyleSheet(
                    "color:" + ink + ";background:transparent;border:0;font-size:9px;"
                )
                column.addWidget(caption)
                column.addWidget(val)
                column.addWidget(tagline)
                self.stats[key] = val
                stats.addWidget(frame, 1)
            outer.addLayout(stats)

            self.work_splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
            self.work_splitter.setChildrenCollapsible(False)
            # Keep vertical resizing, but hide the distracting divider stripe.
            self.work_splitter.setHandleWidth(6)
            top_widget = QtGui.QFrame()
            top_widget.setObjectName("workspace")
            top_widget.setStyleSheet(
                "QFrame#workspace{background:#FFFFFF;border:1px solid #E8E2D5;"
                "border-radius:23px;}"
            )
            workspace_layout = QtGui.QVBoxLayout(top_widget)
            workspace_layout.setContentsMargins(15, 13, 15, 12)
            workspace_layout.setSpacing(9)

            tree_top = QtGui.QHBoxLayout()
            tree_badge = QtGui.QLabel("02")
            tree_badge.setAlignment(QtCore.Qt.AlignCenter)
            tree_badge.setFixedSize(30, 30)
            tree_badge.setStyleSheet(
                "color:#FFFFFF;background:#004D40;border-radius:11px;"
                "font-weight:bold;"
            )
            tree_top.addWidget(tree_badge)
            tree_title = QtGui.QLabel("Browse classes  /  Select proposed glyphs")
            tree_title.setFont(QtGui.QFont("Plus Jakarta Sans", 13, QtGui.QFont.Bold))
            tree_title.setStyleSheet("color:#004D40;background:transparent;border:0;")
            tree_top.addWidget(tree_title)
            tree_top.addStretch()
            self.filter_input = QtGui.QLineEdit()
            self.filter_input.setMinimumWidth(190)
            self.filter_input.setMaximumWidth(300)
            self.filter_input.setPlaceholderText("Search classes or glyphs...")
            tree_top.addWidget(self.filter_input)
            workspace_layout.addLayout(tree_top)

            actions = QtGui.QHBoxLayout()
            self.all_button = QtGui.QPushButton("Select all")
            self.none_button = QtGui.QPushButton("Clear")
            self.selection_label = QtGui.QLabel("0 / 0 memberships")
            self.selection_label.setStyleSheet(
                "color:#004D40;background:#CCEBE2;border-radius:10px;"
                "padding:7px 11px;font-weight:bold;"
            )
            for widget in (self.all_button, self.none_button, self.selection_label):
                actions.addWidget(widget)
            actions.addStretch()
            self.focus_button = QtGui.QPushButton("Expand workspace")
            self.focus_button.setObjectName("focus")
            actions.addWidget(self.focus_button)
            workspace_layout.addLayout(actions)

            # Fixed 60/40 workspace widths: the user resizes only its height.
            top_layout = QtGui.QHBoxLayout()
            top_layout.setContentsMargins(0, 0, 0, 0)
            top_layout.setSpacing(12)

            class_panel = QtGui.QFrame()
            class_panel.setObjectName("classPanel")
            class_panel.setStyleSheet(
                "QFrame#classPanel{background:#FAF9F5;"
                "border:1px solid #E8E2D5;border-radius:18px;}"
            )
            class_layout = QtGui.QVBoxLayout(class_panel)
            class_layout.setContentsMargins(12, 12, 12, 10)
            class_layout.setSpacing(6)
            class_title = QtGui.QLabel("NATIVE CLASSES")
            class_title.setFont(QtGui.QFont("Plus Jakarta Sans", 11, QtGui.QFont.Bold))
            class_title.setStyleSheet(
                "color:#004D40;background:transparent;border:0;font-weight:bold;"
            )
            class_layout.addWidget(class_title)
            class_note = QtGui.QLabel(
                "Click to inspect  \u2022  Tick to select its glyphs"
            )
            class_note.setStyleSheet(
                "color:#79766E;background:transparent;border:0;font-size:10px;"
            )
            class_layout.addWidget(class_note)
            self.class_table = QtGui.QTreeWidget()
            self.class_table.setColumnCount(5)
            self.class_table.setHeaderLabels(
                ["Tick", "Class", "Mode", "Members", "+ Adds"]
            )
            self.class_table.setRootIsDecorated(False)
            self.class_table.setAlternatingRowColors(True)
            self.class_table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
            self.class_table.setColumnWidth(0, 48)
            self.class_table.setColumnWidth(1, 104)
            self.class_table.setColumnWidth(2, 100)
            self.class_table.setColumnWidth(3, 80)
            self.class_table.setColumnWidth(4, 70)
            class_layout.addWidget(self.class_table, 1)
            top_layout.addWidget(class_panel, 7)

            glyph_panel = QtGui.QFrame()
            glyph_panel.setObjectName("glyphPanel")
            glyph_panel.setStyleSheet(
                "QFrame#glyphPanel{background:#FAF9F5;"
                "border:1px solid #E8E2D5;border-radius:18px;}"
            )
            glyph_layout = QtGui.QVBoxLayout(glyph_panel)
            glyph_layout.setContentsMargins(12, 12, 12, 10)
            glyph_layout.setSpacing(6)
            self.glyph_title = QtGui.QLabel("PROPOSED GLYPHS  /  Select a class")
            self.glyph_title.setFont(QtGui.QFont("Plus Jakarta Sans", 11, QtGui.QFont.Bold))
            self.glyph_title.setWordWrap(True)
            self.glyph_title.setStyleSheet(
                "color:#004D40;background:transparent;border:0;font-weight:bold;"
            )
            glyph_layout.addWidget(self.glyph_title)
            self.glyph_note = QtGui.QLabel(
                "Tick glyphs here. Class checkbox selects all."
            )
            self.glyph_note.setWordWrap(True)
            self.glyph_note.setStyleSheet(
                "color:#79766E;background:transparent;border:0;font-size:10px;"
            )
            glyph_layout.addWidget(self.glyph_note)
            self.glyph_table = QtGui.QTreeWidget()
            self.glyph_table.setColumnCount(2)
            self.glyph_table.setHeaderLabels(["Tick", "Proposed glyph"])
            self.glyph_table.setRootIsDecorated(False)
            self.glyph_table.setAlternatingRowColors(True)
            self.glyph_table.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
            self.glyph_table.setColumnWidth(0, 50)
            self.glyph_table.setColumnWidth(1, 240)
            glyph_layout.addWidget(self.glyph_table, 1)
            top_layout.addWidget(glyph_panel, 5)
            workspace_layout.addLayout(top_layout, 1)
            # Allow compact laptop heights; the lower Apply card never collapses.
            top_widget.setMinimumHeight(195)
            self.work_splitter.addWidget(top_widget)

            bottom_widget = QtGui.QWidget()
            bottom = QtGui.QHBoxLayout(bottom_widget)
            bottom.setContentsMargins(0, 2, 0, 0)
            bottom.setSpacing(12)
            output_frame = QtGui.QFrame()
            output_frame.setObjectName("outputPanel")
            output_frame.setStyleSheet(
                "QFrame#outputPanel{background:#FFFFFF;border:1px solid #E8E2D5;"
                "border-radius:22px;}"
            )
            output_layout = QtGui.QVBoxLayout(output_frame)
            output_layout.setContentsMargins(15, 11, 15, 12)
            output_layout.setSpacing(8)
            output_header = QtGui.QHBoxLayout()
            output_badge = QtGui.QLabel("03")
            output_badge.setAlignment(QtCore.Qt.AlignCenter)
            output_badge.setFixedSize(27, 27)
            output_badge.setStyleSheet(
                "color:#FFFFFF;background:#004D40;border-radius:9px;"
                "font-weight:bold;"
            )
            output_header.addWidget(output_badge)
            output_title = QtGui.QLabel("Live Preview / Readback")
            output_title.setFont(QtGui.QFont("Plus Jakarta Sans", 11, QtGui.QFont.Bold))
            output_title.setStyleSheet(
                "color:#004D40;background:transparent;border:0;"
            )
            self.live_indicator = QtGui.QLabel("WAITING")
            self.live_indicator.setStyleSheet(
                "background:#CCEBE2;color:#004D40;border-radius:10px;"
                "padding:6px 9px;font-size:10px;font-weight:bold;"
            )
            output_header.addWidget(output_title)
            output_header.addStretch()
            output_header.addWidget(self.live_indicator)
            output_layout.addLayout(output_header)
            console_caption = QtGui.QLabel("READ-ONLY ENGINE REPORT")
            console_caption.setStyleSheet(
                "color:#79766E;font-size:9px;font-weight:bold;"
                "background:transparent;border:0;"
            )
            output_layout.addWidget(console_caption)
            self.diagnostics = QtGui.QPlainTextEdit()
            self.diagnostics.setReadOnly(True)
            self.diagnostics.setMinimumHeight(70)
            self.diagnostics.setPlainText(
                "Select glyphs above. Their read-only Preview will appear here automatically."
            )
            output_layout.addWidget(self.diagnostics, 1)
            output_footer = QtGui.QHBoxLayout()
            output_note = QtGui.QLabel("No font changes until guarded Apply.")
            output_note.setStyleSheet(
                "color:#79766E;font-size:10px;background:transparent;border:0;"
            )
            output_footer.addWidget(output_note)
            output_footer.addStretch()
            self.report_button = QtGui.QPushButton("Export JSON")
            output_footer.addWidget(self.report_button)
            output_layout.addLayout(output_footer)
            bottom.addWidget(output_frame, 7)

            guard_frame = QtGui.QFrame()
            guard_frame.setObjectName("guardPanel")
            guard_frame.setStyleSheet(
                "QFrame#guardPanel{background:#FFF8F7;border:1px solid #FFDAD6;"
                "border-radius:22px;}"
            )
            guard_frame.setMinimumHeight(244)
            guard_layout = QtGui.QVBoxLayout(guard_frame)
            guard_layout.setContentsMargins(14, 11, 14, 12)
            guard_layout.setSpacing(7)
            guard_header = QtGui.QHBoxLayout()
            guard_badge = QtGui.QLabel("04")
            guard_badge.setAlignment(QtCore.Qt.AlignCenter)
            guard_badge.setFixedSize(27, 27)
            guard_badge.setStyleSheet(
                "color:#FFFFFF;background:#BA1A1A;border-radius:9px;"
                "font-weight:bold;"
            )
            guard_header.addWidget(guard_badge)
            guard_heading = QtGui.QLabel("Guarded Apply")
            guard_heading.setFont(QtGui.QFont("Plus Jakarta Sans", 11, QtGui.QFont.Bold))
            guard_heading.setStyleSheet(
                "color:#410002;background:transparent;border:0;"
            )
            guard_header.addWidget(guard_heading, 1)
            guard_layout.addLayout(guard_header)
            guard_subtitle = QtGui.QLabel("FL8  /  PRE-COMMIT SAFETY GATE")
            guard_subtitle.setStyleSheet(
                "color:#BA1A1A;background:transparent;border:0;"
                "font-size:9px;font-weight:bold;"
            )
            guard_layout.addWidget(guard_subtitle)
            notice = QtGui.QFrame()
            notice.setObjectName("guardNotice")
            notice.setStyleSheet(
                "QFrame#guardNotice{background:#FFFFFF;border:1px solid #FFDAD6;"
                "border-radius:13px;}"
            )
            notice.setMinimumHeight(78)
            notice_layout = QtGui.QVBoxLayout(notice)
            notice_layout.setContentsMargins(10, 8, 10, 8)
            notice_layout.setSpacing(3)
            notice_title = QtGui.QLabel("BACKUP COPY REQUIRED")
            notice_title.setStyleSheet(
                "color:#BA1A1A;font-size:9px;font-weight:bold;"
                "background:transparent;border:0;"
            )
            notice_layout.addWidget(notice_title)
            self.guard_hint = QtGui.QLabel(
                "Review proposed changes. Use a saved test COPY with a separate "
                "backup. A final confirmation is required."
            )
            self.guard_hint.setWordWrap(True)
            self.guard_hint.setMinimumHeight(32)
            self.guard_hint.setStyleSheet(
                "color:#5E5550;font-size:10px;background:transparent;border:0;"
            )
            notice_layout.addWidget(self.guard_hint)
            guard_layout.addWidget(notice)
            self.consent_frame = QtGui.QFrame()
            self.consent_frame.setObjectName("consentCard")
            self.consent_frame.setStyleSheet(
                "QFrame#consentCard{background:#FFFFFF;border:1px solid #FFDAD6;"
                "border-radius:12px;}"
            )
            consent_layout = QtGui.QVBoxLayout(self.consent_frame)
            consent_layout.setContentsMargins(9, 6, 9, 6)
            self.confirm_copy = QtGui.QCheckBox(
                "Reviewed plan + saved test COPY / backup"
            )
            self.confirm_copy.setToolTip(
                "Confirm that your working font is a disposable COPY and "
                "you have a separate, recoverable backup."
            )
            consent_layout.addWidget(self.confirm_copy)
            guard_layout.addWidget(self.consent_frame)
            guard_layout.addStretch(1)
            self.apply_button = QtGui.QPushButton("Review & Apply to COPY...")
            self.apply_button.setObjectName("apply")
            self.apply_button.setMinimumHeight(42)
            guard_layout.addWidget(self.apply_button)
            if self.major != 8:
                guard_heading.setText("Preview only")
                guard_subtitle.setText("NATIVE WRITER LOCKED")
                notice_title.setText("FONT WILL REMAIN UNCHANGED")
                self.guard_hint.setText(
                    "Native Apply has not been verified for this FontLab version. "
                    "You can scan, select, preview and export JSON."
                )
                self.consent_frame.setVisible(False)
                self.apply_button.setVisible(False)
            bottom.addWidget(guard_frame, 5)
            bottom_widget.setMinimumHeight(248)
            self.bottom_widget = bottom_widget
            self.work_splitter.addWidget(bottom_widget)
            self.work_splitter.setStretchFactor(0, 7)
            self.work_splitter.setStretchFactor(1, 5)
            self.work_splitter.setSizes([430, 245])
            outer.addWidget(self.work_splitter, 1)

            tail = QtGui.QHBoxLayout()
            self.status = QtGui.QLabel("Ready. No automatic writes or saves.")
            self.status.setWordWrap(True)
            self.status.setStyleSheet(
                "color:#004D40;font-size:10px;font-weight:bold;"
            )
            tail.addWidget(self.status, 1)
            self.close_button = QtGui.QPushButton("Close")
            self.close_button.setMinimumWidth(84)
            tail.addWidget(self.close_button)
            outer.addLayout(tail)

            self._connect(self.scan_button.clicked, self.scan)
            self._connect(self.all_button.clicked, lambda: self.toggle_all(True))
            self._connect(self.none_button.clicked, lambda: self.toggle_all(False))
            self._connect(self.focus_button.clicked, self.toggle_workspace_focus)
            self._connect(self.report_button.clicked, self.export_report)
            self._connect(self.apply_button.clicked, self.apply_selection)
            self._connect(self.close_button.clicked, self.close)
            self._connect(self.filter_input.textChanged, self.filter_rows)
            self._connect(self.confirm_copy.toggled, self.refresh_buttons)
            class_changed = lambda item, col: self._safe(
                lambda: self.on_class_item_changed(item, col)
            )
            self.class_table.itemChanged.connect(class_changed)
            self.connections.append((self.class_table.itemChanged, class_changed))
            glyph_changed = lambda item, col: self._safe(
                lambda: self.on_glyph_item_changed(item, col)
            )
            self.glyph_table.itemChanged.connect(glyph_changed)
            self.connections.append((self.glyph_table.itemChanged, glyph_changed))
            current_changed = lambda current, previous: self._safe(
                lambda: self.show_class(current)
            )
            self.class_table.currentItemChanged.connect(current_changed)
            self.connections.append((self.class_table.currentItemChanged, current_changed))
            self.refresh_buttons()
            self._safe(self.scan)

        def _connect(self, signal, callback):
            guarded = lambda *args: self._safe(callback)
            signal.connect(guarded)
            self.connections.append((signal, guarded))

        def _safe(self, callback):
            try:
                callback()
            except Exception as exc:
                details = traceback.format_exc()
                print("NGHIATYPE V2 GUI ERROR:\n" + details)
                self.set_status(type(exc).__name__ + ": " + str(exc), True)
                self.diagnostics.setPlainText(details[-4000:])
                self.apply_button.setEnabled(False)

        def set_status(self, message, error=False):
            self.status.setText(message)
            self.status.setStyleSheet("color:#C84C3D;" if error else "color:#24705B;")

        def toggle_workspace_focus(self):
            """Use all available height for class/glyph selection, if desired."""
            if not self.focus_active:
                try:
                    self._saved_split_sizes = list(qt_value(self.work_splitter, "sizes"))
                except Exception:
                    self._saved_split_sizes = [550, 235]
                self.bottom_widget.setVisible(False)
                self.focus_active = True
                self.focus_button.setText("Show Preview / Apply")
                self.set_status(
                    "Workspace expanded. Preview still updates in the background."
                )
            else:
                self.bottom_widget.setVisible(True)
                self.work_splitter.setSizes(self._saved_split_sizes)
                self.focus_active = False
                self.focus_button.setText("Expand workspace")
                self.set_status("Preview / Apply is visible again.")

        def invalidate_preview(self):
            self.preview = None
            self.apply_result = None
            self.confirm_copy.setChecked(False)
            self.live_indicator.setText("WAITING")
            self.refresh_buttons()

        def selection_changed(self):
            """Fail closed on selection changes, then create a fresh READ-ONLY plan.

            The preview is rendered before Apply can be enabled. User consent
            and exact filename/master confirmation are always reset.
            """
            if self.applied or self.locked_after_failure:
                return
            self.invalidate_preview()
            if self.snap is None:
                return
            if self.chosen_pairs():
                self.preview_selection()
            else:
                self.diagnostics.setPlainText(
                    "READ ONLY / %d available classes / %d memberships\n"
                    "%d conflicts, %d scan issues.\n"
                    "Nothing selected. Choose class/glyph checkboxes above; "
                    "Live Preview will update automatically."
                    % (len(self.snap["safe_all"]), len(self.entries),
                       len(self.snap["blocked"]), len(self.snap["issues"]))
                )
                self.set_status("No glyphs selected. Font unchanged.")

        def scan(self):
            if self.locked_after_failure:
                self.set_status("DO NOT SAVE. Close the test font WITHOUT saving.", True)
                return
            self.snap = None
            self.applied = False
            self.class_table.setEnabled(True)
            self.glyph_table.setEnabled(True)
            self.entries = []
            self.parents = {}
            self.selected_glyphs = set()
            self.active_class = None
            self.glyph_widgets = {}
            self.updating_tree = True
            try:
                self.class_table.clear()
                self.glyph_table.clear()
            finally:
                self.updating_tree = False
            self.invalidate_preview()
            snap = scan_native(fontlab, core)
            self.snap = snap
            self.font_info.setText(
                "Font: " + (ntpath.basename(snap["font_path"]) or "<UNSAVED>")
                + "  |  Master: " + snap["master"]
                + "  |  Masters: " + str(snap["master_count"])
            )
            self.stats["glyphs"].setText(str(len(snap["available"])))
            self.stats["classes"].setText(str(len(snap["groups"])))
            self.stats["candidates"].setText(str(snap["candidate_count"]))
            self.stats["available"].setText(
                str(sum(len(names) for names in snap["safe_all"].values()))
            )
            self.updating_tree = True
            try:
                for key in sorted(snap["safe_all"],
                                  key=lambda name: (name.casefold(), name)):
                    names = snap["safe_all"][key]
                    members, mode = snap["groups"][key]
                    row = QtGui.QTreeWidgetItem(self.class_table)
                    row.setFlags(row.flags() | QtCore.Qt.ItemIsUserCheckable)
                    row.setCheckState(0, QtCore.Qt.Unchecked)
                    row.setText(1, key)
                    row.setText(2, mode)
                    row.setText(3, str(len(members)))
                    row.setText(4, "+" + str(len(names)))
                    self.parents[key] = row
                    for glyph in names:
                        self.entries.append((key, glyph))
            finally:
                self.updating_tree = False
            # PythonQt may expose topLevelItemCount as an int property, not a
            # callable method. Use our own freshly built row map instead.
            first = next(iter(self.parents.values()), None)
            if first is not None:
                self.updating_tree = True
                try:
                    self.class_table.setCurrentItem(first)
                finally:
                    self.updating_tree = False
                self.show_class(first)
            else:
                self.show_class(None)
            message = (
                "READ ONLY / %d available classes / %d memberships\n"
                "%d conflicts, %d scan issues.\n"
                "Nothing selected. Tick a class or glyph to see Live Preview automatically."
                % (len(snap["safe_all"]), len(self.entries), len(snap["blocked"]),
                   len(snap["issues"]))
            )
            if snap["blocked"]:
                message += "\nCONFLICTS: " + repr(snap["blocked"][:8])
            if snap["issues"]:
                message += "\nISSUES: " + "\n".join(snap["issues"][:15])
            if self.major != 8:
                message += "\nNATIVE WRITER LOCKED: FL9 / unknown version is Preview only."
            self.diagnostics.setPlainText(message)
            self.set_status("Scan complete; font unchanged.", bool(snap["issues"] or snap["blocked"]))
            self.filter_rows()
            self.refresh_buttons()

        def chosen_pairs(self):
            return frozenset(self.selected_glyphs)

        def show_class(self, item):
            """Left-row focus controls which candidate glyphs appear on right."""
            if self.updating_tree or self.snap is None:
                return
            key = str(item.text(1)) if item is not None else ""
            self.active_class = key if key in self.snap["safe_all"] else None
            self.render_current_glyphs()

        def render_current_glyphs(self):
            """Render only one class; all check states live in selected_glyphs."""
            self.updating_tree = True
            try:
                self.glyph_table.clear()
                self.glyph_widgets = {}
                key = self.active_class
                if key is None or self.snap is None:
                    self.glyph_title.setText("PROPOSED GLYPHS  /  Select a class")
                    self.glyph_note.setText("Click a class row on the left to inspect its glyphs.")
                    return
                names = self.snap["safe_all"][key]
                selected_count = sum((key, name) in self.selected_glyphs for name in names)
                self.glyph_title.setText(
                    "CLASS %s  /  %d proposed  /  %d selected"
                    % (key, len(names), selected_count)
                )
                self.glyph_note.setText(
                    "Tick glyphs here. Class checkbox selects all."
                )
                for glyph in names:
                    row = QtGui.QTreeWidgetItem(self.glyph_table)
                    row.setFlags(row.flags() | QtCore.Qt.ItemIsUserCheckable)
                    state = (QtCore.Qt.Checked if (key, glyph) in self.selected_glyphs
                             else QtCore.Qt.Unchecked)
                    row.setCheckState(0, state)
                    row.setText(1, glyph)
                    provenance = self.snap["origin"].get(
                        glyph.split(".", 1)[0], (None, "name")
                    )[1]
                    try:
                        row.setToolTip(
                            1, "Detected by Unicode" if provenance == "unicode"
                            else "Name-only candidate (Apply will be blocked)"
                        )
                    except Exception:
                        pass
                    self.glyph_widgets[glyph] = row
            finally:
                self.updating_tree = False

        def sync_class_checks(self):
            self.updating_tree = True
            try:
                for key, row in self.parents.items():
                    names = self.snap["safe_all"][key]
                    chosen = sum((key, glyph) in self.selected_glyphs for glyph in names)
                    state = (QtCore.Qt.Checked if chosen == len(names)
                             else QtCore.Qt.Unchecked if not chosen
                             else QtCore.Qt.PartiallyChecked)
                    row.setCheckState(0, state)
            finally:
                self.updating_tree = False

        def on_class_item_changed(self, item, column):
            if self.updating_tree or column != 0:
                return
            key = str(item.text(1))
            if not self.snap or key not in self.snap["safe_all"]:
                return
            state = item.checkState(0)
            if state == QtCore.Qt.PartiallyChecked:
                return
            group_pairs = {(key, glyph) for glyph in self.snap["safe_all"][key]}
            if state == QtCore.Qt.Checked:
                self.selected_glyphs.update(group_pairs)
            else:
                self.selected_glyphs.difference_update(group_pairs)
            self.sync_class_checks()
            if self.active_class == key:
                self.render_current_glyphs()
            self.selection_changed()

        def on_glyph_item_changed(self, item, column):
            if self.updating_tree or column != 0 or self.active_class is None:
                return
            glyph = str(item.text(1))
            pair = (self.active_class, glyph)
            if self.snap is None or glyph not in self.snap["safe_all"][self.active_class]:
                return
            if item.checkState(0) == QtCore.Qt.Checked:
                self.selected_glyphs.add(pair)
            else:
                self.selected_glyphs.discard(pair)
            self.sync_class_checks()
            names = self.snap["safe_all"][self.active_class]
            chosen = sum((self.active_class, name) in self.selected_glyphs for name in names)
            self.glyph_title.setText(
                "CLASS %s  /  %d proposed  /  %d selected"
                % (self.active_class, len(names), chosen)
            )
            self.selection_changed()

        def toggle_all(self, select):
            self.selected_glyphs = set(self.entries) if select else set()
            self.sync_class_checks()
            self.render_current_glyphs()
            self.selection_changed()

        def filter_rows(self):
            query = qt_text(self.filter_input).strip().casefold()
            first_match = None
            for key, row in self.parents.items():
                visible = (not query or query in key.casefold()
                           or any(query in name.casefold()
                                  for name in self.snap["safe_all"][key]))
                row.setHidden(not visible)
                if visible and first_match is None:
                    first_match = row
            # Focus is independent of checkbox state; switching classes never
            # discards selections made in another class.
            current_row = self.parents.get(self.active_class)
            if current_row is None or current_row.isHidden():
                if first_match is not None:
                    self.class_table.setCurrentItem(first_match)
                else:
                    self.show_class(None)

        def preview_selection(self):
            if self.snap is None:
                raise RuntimeError("Scan first.")
            if self.applied or self.locked_after_failure:
                raise RuntimeError("Scan again after Apply; the previous plan is no longer current.")
            self.preview = None
            self.apply_result = None
            choice = self.chosen_pairs()
            preview = selected_preview(core, self.snap, choice)
            self.preview = preview
            self.live_indicator.setText("READY / %d GLYPHS" % preview["count"])
            blockers = apply_blockers(core, self.snap, preview, self.major, "", "", False)
            # Remove the three user-confirmation blockers from preview diagnostics.
            blockers = [b for b in blockers if not b.startswith((
                "Typed", "Confirm you are working"
            ))]
            detail = [
                "PROPOSED CHANGES / NOT YET APPLIED",
                "",
            ]
            for key, names in sorted(preview["selected"].items()):
                detail.append("%s  |  +%d  |  %s" %
                              (key, len(names), ", ".join(names)))
            if blockers:
                detail.extend(["", "SAFETY CHECK: BLOCKED"] + blockers)
            else:
                detail.extend([
                    "",
                    "SAFETY CHECK: PASS / no conflicts detected",
                    "Plan is fingerprinted and checked again before Apply.",
                    "Font unchanged. Apply requires explicit COPY confirmation.",
                ])
            if preview["name_only"]:
                detail.append("NAME ONLY: " + ", ".join(preview["name_only"]))
            self.diagnostics.setPlainText("\n".join(detail))
            self.set_status(
                "Preview ready / Apply blocked by safeguards." if blockers
                else "Preview ready / review the list and confirm your saved COPY to Apply.",
                bool(blockers),
            )
            self.refresh_buttons()

        def refresh_buttons(self):
            count = len(self.chosen_pairs())
            self.selection_label.setText("%d / %d memberships" % (count, len(self.entries)))
            selectable = not self.applied and not self.locked_after_failure
            self.all_button.setEnabled(bool(self.entries) and selectable)
            self.none_button.setEnabled(bool(self.entries) and selectable)
            self.report_button.setEnabled(self.snap is not None)
            allowed = bool(self.snap and self.preview and not self.applied
                           and not self.locked_after_failure
                           and self.chosen_pairs() == self.preview["pairs"])
            if allowed:
                allowed = not apply_blockers(
                    core, self.snap, self.preview, self.major,
                    ntpath.basename(self.snap["font_path"]), self.snap["master"],
                    qt_checked(self.confirm_copy),
                )
            self.apply_button.setEnabled(allowed)

        def export_report(self):
            if not self.snap:
                raise RuntimeError("Scan first.")
            data = report_data(self.snap, self.preview, self.major, self.apply_result)
            suggestion = "NghiaType_Native_V2_Report.json"
            selected = QtGui.QFileDialog.getSaveFileName(
                self, "Export native preview/readback JSON", suggestion, "JSON (*.json)"
            )
            if isinstance(selected, (tuple, list)):
                selected = selected[0]
            target = str(selected or "").strip()
            if not target:
                return
            if not target.lower().endswith(".json"):
                target += ".json"
            # Exclusive create: never silently overwrite an existing client log.
            with open(target, "x", encoding="utf-8") as output:
                json.dump(data, output, indent=2, ensure_ascii=True, sort_keys=True)
                output.write("\n")
            self.set_status("JSON exported (font unchanged by export).")

        def apply_selection(self):
            if self.snap is None or self.preview is None or self.applied:
                raise RuntimeError("Scan and select glyphs to generate Live Preview first.")
            if self.locked_after_failure:
                raise RuntimeError("DO NOT SAVE. Close test font without saving.")
            if self.chosen_pairs() != self.preview["pairs"]:
                raise RuntimeError("Selection changed; Preview again.")
            # Exact filename/master are bound to the frozen Scan/Plan token.
            # Only the *human* confirmation moved out of the main UI.
            filename_text = ntpath.basename(self.snap["font_path"])
            master_text = self.snap["master"]
            confirmed = qt_checked(self.confirm_copy)
            current_major, _paths = detect_major(fontlab, QtCore)
            blockers = apply_blockers(
                core, self.snap, self.preview, current_major,
                filename_text, master_text, confirmed,
            )
            if blockers:
                self.diagnostics.setPlainText("APPLY BLOCKED:\n" + "\n".join(blockers))
                self.set_status("Apply refused by backend guards.", True)
                self.apply_button.setEnabled(False)
                return
            typed = QtGui.QInputDialog.getText(
                self, "Confirm disposable test COPY",
                "Font: %s\nMaster: %s\n\n"
                "Type COPY to confirm this is a saved, disposable test font:"
                % (filename_text, master_text),
            )
            if isinstance(typed, (tuple, list)):
                if len(typed) > 1 and not bool(typed[1]):
                    self.set_status("Apply cancelled; font unchanged.")
                    return
                typed = typed[0]
            if str(typed or "").strip().upper() != "COPY":
                self.set_status("Apply cancelled: COPY confirmation was not entered.")
                return
            # Re-read native classes, pairs, filename and master *after* the
            # modal input. No mutations occur until this check succeeds.
            live, blockers = fresh_preflight(
                fontlab, core, self.snap, self.preview, current_major,
                filename_text, master_text, confirmed,
            )
            if blockers:
                self.diagnostics.setPlainText("APPLY BLOCKED:\n" + "\n".join(blockers))
                self.set_status("Live state changed; no writes made.", True)
                self.apply_button.setEnabled(False)
                return
            warning = (
                "EXPERIMENTAL NATIVE WRITE - FONTLAB 8 ONLY\n\n"
                "File: %s\nMaster: %s\n"
                "Selected: %d classes / %d glyph memberships\n"
                "Plan lock: ACTIVE (fresh state verified)\n\n"
                "This modifies native classes IN MEMORY. The font is NOT saved.\n"
                "If any step fails, CLOSE TEST COPY WITHOUT SAVING.\n\n"
                "Continue?" % (filename_text, master_text,
                               len(self.preview["selected"]), self.preview["count"])
            )
            answer = QtGui.QMessageBox.question(
                self, "Confirm guarded native Apply", warning,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if answer != QtGui.QMessageBox.Yes:
                self.set_status("Apply cancelled; font unchanged.")
                return
            # A modal dialog can change the active font. Recheck AFTER consent.
            live, blockers = fresh_preflight(
                fontlab, core, self.snap, self.preview, current_major,
                filename_text, master_text, confirmed,
            )
            if blockers:
                self.diagnostics.setPlainText("RECHECK BLOCKED:\n" + "\n".join(blockers))
                self.set_status("Live state changed; no writes made.", True)
                self.apply_button.setEnabled(False)
                return
            self.apply_button.setEnabled(False)
            record = {"write_attempted": False}
            try:
                self.apply_result = stepwise_native_apply(
                    fontlab, core, live, self.preview, record
                )
            except Exception as exc:
                self.apply_result = {
                    "ok": False, "status": "DO_NOT_SAVE_CLOSE_TEST_COPY",
                    "error": "%s: %s" % (type(exc).__name__, exc),
                }
            self.applied = True
            # Keep the verified readback visible until the next deliberate Scan.
            self.class_table.setEnabled(False)
            self.glyph_table.setEnabled(False)
            if self.apply_result["ok"]:
                steps = self.apply_result["steps_passed"]
                summary = [
                    "STEPWISE READBACK  /  PASS",
                    "%d classes  /  %d memberships verified"
                    % (len(steps), self.preview["count"]),
                    "",
                ]
                for step in steps:
                    summary.append(
                        "PASS  %s  +%d  %s"
                        % (step["class"], len(step["added"]), ", ".join(step["added"]))
                    )
                summary.extend([
                    "",
                    "All other native classes and explicit pairs: unchanged.",
                    "IN MEMORY ONLY / NOT SAVED",
                    "Review and save/reopen the disposable COPY only if expected.",
                ])
                self.diagnostics.setPlainText(
                    "\n".join(summary)
                )
                self.set_status("Native Apply readback PASS; NOT SAVED.")
            else:
                self.locked_after_failure = True
                self.diagnostics.setPlainText(
                    "FAILED / POTENTIALLY PARTIAL IN-MEMORY CHANGES\n"
                    "DO NOT SAVE. CLOSE TEST COPY WITHOUT SAVING.\n"
                    + self.apply_result.get("error", "Unknown readback error")
                )
                self.set_status("DO NOT SAVE. Close test COPY WITHOUT saving.", True)
            self.refresh_buttons()

        def closeEvent(self, event):
            for signal, callback in self.connections:
                try:
                    signal.disconnect(callback)
                except Exception:
                    pass
            self.connections = []
            cache = sys.__dict__.setdefault(KEY, {})
            if cache.get("window") is self:
                cache.pop("window", None)
            QtGui.QDialog.closeEvent(self, event)

    cache = sys.__dict__.setdefault(KEY, {})
    previous = cache.pop("window", None)
    if previous is not None:
        try:
            previous.close()
        except Exception:
            pass
    try:
        parent = fontlab.MainWindow()
    except Exception:
        parent = None
    dialog = Window(parent)
    cache["window"] = dialog
    dialog.show()
    dialog.raise_()
    return dialog


def main():
    try:
        import fontlab
        from PythonQt import QtCore, QtGui
        path = native_core_path_hint()
        if not path:
            selected = QtGui.QFileDialog.getOpenFileName(
                None, "Select NghiaType Native Core V2 Alpha.1.4.1",
                "", "Python scripts (*.py)",
            )
            if isinstance(selected, (tuple, list)):
                selected = selected[0]
            path = str(selected or "").strip()
        if not path:
            print("GUI launch cancelled: Native Core V2 file not selected.")
            return None
        core = load_native_core(path)
        return start_gui(fontlab, core, QtCore, QtGui)
    except Exception:
        print("NghiaType Native Kerning V2 GUI startup failure:")
        print(traceback.format_exc())
        return None


if __name__ == "__main__":
    main()
