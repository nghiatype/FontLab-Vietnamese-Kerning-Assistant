# -*- coding: utf-8 -*-
#FLM: NghiaType Tools V3 - Sidebar Navigation Alpha 0.9
"""NghiaType Tools V3: desktop sidebar with native read-only workflow.

PythonQt / FontLab 8+9. This new file does not modify either stable core.
The Native tab calls the existing V2 scanner/planner, but has NO APPLY writer.
OpenType and Reports are separate modules with no writers.

Keep source ASCII-only for FontLab's Macro panel compatibility.
"""

from __future__ import print_function

import importlib.util
import json
import ntpath
import os
import re
import sys
import traceback
import unicodedata


SHELL_VERSION = "V3 Alpha.0.9 / Sidebar Navigation"
NATIVE_GUI_FILENAME = "NghiaType_Native_Kerning_V2_GUI_Alpha1.py"
WINDOW_CACHE_KEY = "_nghiatype_tools_v3_shell"

# Light scheme from the user's Material Theme Builder export (2026-11-18).
# Keep the GUI self-contained: FontLab's Macro panel must not need the JSON.
# Dark/contrast schemes in the export are reserved for a later theme switch.
M3_LIGHT = {
    "primary": "#784F82",
    "surfaceTint": "#784F82",
    "onPrimary": "#FFFFFF",
    "primaryContainer": "#FBD7FF",
    "onPrimaryContainer": "#5F3869",
    "secondary": "#6A596C",
    "onSecondary": "#FFFFFF",
    "secondaryContainer": "#F2DBF3",
    "onSecondaryContainer": "#514154",
    "tertiary": "#82524D",
    "onTertiary": "#FFFFFF",
    "tertiaryContainer": "#FFDAD6",
    "onTertiaryContainer": "#673B37",
    "error": "#BA1A1A",
    "onError": "#FFFFFF",
    "errorContainer": "#FFDAD6",
    "onErrorContainer": "#93000A",
    "background": "#FFF7FB",
    "onBackground": "#1F1A1F",
    "surface": "#FFF7FB",
    "onSurface": "#1F1A1F",
    "surfaceVariant": "#ECDFE9",
    "onSurfaceVariant": "#4C444C",
    "outline": "#7E747D",
    "outlineVariant": "#CFC3CD",
    "primaryFixedDim": "#E7B6F0",
    "secondaryFixedDim": "#D6C0D6",
    "tertiaryFixedDim": "#F5B7B1",
    "surfaceContainerLowest": "#FFFFFF",
    "surfaceContainerLow": "#FBF1F8",
    "surfaceContainer": "#F5EBF2",
    "surfaceContainerHigh": "#F0E5EC",
    "surfaceContainerHighest": "#EAE0E7",
}

UI_FONT_FAMILIES = (
    "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI",
    "Arial", "Helvetica", "Sans Serif",
)

COMBINING_MARK_LABELS = {
    0x0300: "grave", 0x0301: "acute", 0x0302: "circumflex",
    0x0303: "tilde", 0x0306: "breve", 0x0309: "hook above",
    0x031B: "horn", 0x0323: "dot below",
}


def read_glyph_codepoints(font, names):
    """Read each FontLab glyph's actual Unicode values, without mutations."""
    result = {}
    for name in set(names):
        try:
            points = read_qt_value(font[name], "unicodes", ()) or ()
            result[name] = tuple(sorted({
                cp for cp in points
                if isinstance(cp, int) and not isinstance(cp, bool)
                and 0 <= cp <= 0x10FFFF
            }))
        except Exception:
            result[name] = ()
    return result


def format_unicode_values(codepoints):
    """Show exact encoded values; never infer a codepoint from glyph names."""
    return (
        ", ".join("U+%04X" % cp for cp in codepoints)
        if codepoints else "\u2014"
    )


def describe_unicode_components(codepoints):
    """Describe canonical accents only when there is a unique encoded glyph."""
    if len(codepoints) != 1:
        return "\u2014"
    pieces = unicodedata.normalize("NFD", chr(codepoints[0]))
    if len(pieces) < 2:
        return "\u2014"
    marks = []
    for mark in pieces[1:]:
        cp = ord(mark)
        if not unicodedata.combining(mark):
            return "\u2014"
        marks.append(COMBINING_MARK_LABELS.get(
            cp, unicodedata.name(mark, "mark").replace("COMBINING ", "").lower()
        ))
    return pieces[0] + " + " + " + ".join(marks)


def choose_ui_font_family(qtgui, platform=None):
    """Use macOS's native system font; prefer Segoe UI Variable elsewhere."""
    platform = sys.platform if platform is None else platform
    if platform == "darwin":
        # Qt resolves the actual San Francisco system family on macOS.
        # Avoid hardcoding SF Pro, whose public family name may vary.
        try:
            database = qtgui.QFontDatabase
            system_font = database.systemFont(database.GeneralFont)
            family = str(read_qt_value(system_font, "family", "") or "")
            if family:
                return family
        except Exception:
            pass
        try:
            family = str(read_qt_value(qtgui.QFont(), "family", "") or "")
            if family:
                return family
        except Exception:
            pass
        return "Helvetica Neue"
    try:
        database = qtgui.QFontDatabase()
        available = read_qt_value(database, "families", [])
        families = {str(name).casefold(): str(name) for name in available}
        for preferred in UI_FONT_FAMILIES:
            if preferred.casefold() in families:
                return families[preferred.casefold()]
    except Exception:
        pass
    # If font enumeration is unavailable in PythonQt, Qt substitutes a font.
    return "Segoe UI Variable"


def read_qt_value(obj, name, default=None):
    """Handle Qt/PythonQt getters exported as either methods or properties."""
    try:
        value = getattr(obj, name, default)
        return value() if callable(value) else value
    except Exception:
        return default


def detect_fontlab_major(fontlab, qtcore=None):
    """Display-only detection. Actual writer authorization stays in V2."""
    paths = [str(read_qt_value(fontlab, "ApplicationPath", "") or "")]
    if qtcore is not None:
        application = getattr(qtcore, "QCoreApplication", None)
        paths.append(str(read_qt_value(application, "applicationFilePath", "") or ""))
    found = set()
    for path in paths:
        found.update(int(n) for n in re.findall(
            r"(?i)fontlab[ _-]*([89])(?=\W|$)", path
        ))
    return next(iter(found)) if len(found) == 1 else None


def current_font_context(fontlab):
    """Read active font context only. No class/feature writes."""
    try:
        font = fontlab.CurrentFont()
    except Exception:
        font = None
    if font is None:
        return {"font": "No font open", "master": "--", "masters": "--"}
    font_name = ntpath.basename(str(getattr(font, "path", "") or ""))
    if not font_name:
        font_name = "<UNSAVED FONT>"
    master, masters = "--", "--"
    try:
        workspace = fontlab.flWorkspace.instance()
        package = read_qt_value(workspace, "currentPackage")
        if package is not None:
            master = str(read_qt_value(package, "getLayerName", "--") or "--")
            masters = str(read_qt_value(package, "mastersCount", "--") or "--")
    except Exception:
        pass
    return {"font": font_name, "master": master, "masters": masters}


def native_gui_hint():
    """Find the existing V2 script only when placed beside this shell."""
    folder = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
    target = os.path.join(folder, NATIVE_GUI_FILENAME) if folder else ""
    return target if target and os.path.isfile(target) else ""


def load_existing_native_gui(path):
    """Load exactly the known V2 GUI; never alter its writer or checks."""
    path = os.path.abspath(str(path or ""))
    if ntpath.basename(path) != NATIVE_GUI_FILENAME or not os.path.isfile(path):
        raise RuntimeError("Select the existing NghiaType Native Kerning V2 GUI .py file.")
    spec = importlib.util.spec_from_file_location("_nghiatype_v2_gui_from_v3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the existing V2 GUI.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "main", None)):
        raise RuntimeError("The chosen V2 GUI has no main() function.")
    return module


def start_gui(fontlab, QtCore, QtGui):
    class ToolsShell(QtGui.QDialog):
        def __init__(self, parent=None):
            QtGui.QDialog.__init__(self, parent)
            self.setWindowTitle("NghiaType Tools | " + SHELL_VERSION)
            self.setMinimumSize(1180, 650)
            window_width, window_height = 1420, 820
            try:
                desktop = read_qt_value(QtGui.QApplication, "desktop")
                geometry = read_qt_value(desktop, "availableGeometry")
                screen_width = int(read_qt_value(geometry, "width", 0))
                screen_height = int(read_qt_value(geometry, "height", 0))
                if screen_width > 0:
                    window_width = max(1180, min(window_width, screen_width - 36))
                if screen_height > 0:
                    window_height = max(650, min(window_height, screen_height - 36))
            except Exception:
                pass
            self.resize(window_width, window_height)
            try:
                self.setWindowFlags(
                    self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception:
                pass
            self.native_backend = None
            self.native_core = None
            self.native_snapshot = None
            self.native_preview = None
            self.native_rows = {}
            self.native_selected = set()
            self.native_entries = []
            self.native_unicode_map = {}
            self.native_active_class = None
            self.native_updating = False
            self.connections = []
            self.ui_font_family = choose_ui_font_family(QtGui)
            self.setFont(QtGui.QFont(self.ui_font_family, 11))
            palette = dict(M3_LIGHT)
            palette["uiFont"] = self.ui_font_family
            self.setStyleSheet("""
                QDialog { background:%(background)s; color:%(onBackground)s;
                    font-family:'%(uiFont)s'; font-size:12px; }
                QLabel { color:%(onSurface)s; }
                QTabWidget::pane { border:1px solid %(outlineVariant)s;
                    border-radius:14px; background:%(surfaceContainerLowest)s; }
                QTabBar::tab { background:%(surfaceContainer)s;
                    color:%(onSurfaceVariant)s;
                    border:0; border-radius:11px; margin-right:8px;
                    padding:10px 17px; font-weight:bold; min-width:118px; }
                QTabBar::tab:selected { background:%(primary)s;
                    color:%(onPrimary)s; }
                QTabBar::tab:hover:!selected { background:%(primaryContainer)s; }
                QTreeWidget, QPlainTextEdit, QLineEdit {
                    background:%(surfaceContainerLowest)s;
                    color:%(onSurface)s;border:1px solid %(outlineVariant)s;
                    border-radius:11px;
                    selection-background-color:%(primaryContainer)s; }
                QTreeWidget { outline:none;
                    alternate-background-color:%(surfaceContainerLow)s; }
                QTreeWidget::item { padding:7px 5px; }
                QTreeWidget::item:selected {
                    background:%(primaryContainer)s;
                    color:%(onPrimaryContainer)s; }
                QHeaderView::section { background:%(surfaceContainerHigh)s;
                    color:%(onSurfaceVariant)s;
                    border:0;border-bottom:1px solid %(outlineVariant)s;
                    padding:9px 6px;font-weight:bold; }
                QHeaderView::section:first { border-top-left-radius:9px; }
                QHeaderView::section:last { border-top-right-radius:9px; }
                QPlainTextEdit { padding:10px;
                    font-family:Consolas,'Courier New',monospace;font-size:11px; }
                QLineEdit { padding:9px 12px; }
                QPushButton { border:0; border-radius:11px;
                    background:%(secondaryContainer)s;
                    color:%(onSecondaryContainer)s;
                    padding:10px 16px; font-weight:bold; }
                QPushButton:hover { background:%(primaryContainer)s;
                    color:%(onPrimaryContainer)s; }
                QPushButton#nativeScan { background:%(primary)s;
                    color:%(onPrimary)s; font-size:13px; border-radius:15px; }
                QPushButton#nativeScan:hover { background:%(onPrimaryContainer)s; }
                QFrame#sideRail { background:%(surfaceContainerLow)s;
                    border:0; border-right:1px solid %(outlineVariant)s; }
                QFrame#sidebarBrand { background:%(surfaceContainerLowest)s;
                    border:0; border-bottom:1px solid %(outlineVariant)s; }
                QFrame#sidebarContext { background:%(surfaceContainerLow)s;
                    border:0; border-bottom:1px solid %(outlineVariant)s; }
                QFrame#sidebarRuntime { background:%(surfaceContainerLowest)s;
                    border:0; border-top:1px solid %(outlineVariant)s; }
                QFrame#sidebarNav { background:transparent; border:0; }
                QFrame#nativeTopBand {
                    background:%(surfaceContainerLowest)s; border:0;
                    border-bottom:1px solid %(outlineVariant)s; }
                QFrame#footerBand {
                    background:%(surfaceContainerLowest)s; border:0;
                    border-top:1px solid %(outlineVariant)s; }
                QFrame#nativeMetricBand {
                    background:%(surfaceContainerLow)s; border:0;
                    border-bottom:1px solid %(outlineVariant)s; }
                QWidget#nativeWorkArea { background:%(background)s; }
                QFrame#nativeClassHead, QFrame#nativeGlyphHead,
                QFrame#nativePreviewHead, QFrame#nativeApplyHead {
                    background:%(surfaceContainerLow)s; border:0;
                    border-bottom:1px solid %(outlineVariant)s;
                    border-top-left-radius:14px; border-top-right-radius:14px; }
                QPushButton#sideNav { padding:0; border-radius:11px;
                    color:%(onSurfaceVariant)s;
                    border:1px solid transparent;
                    background:transparent; font-weight:normal; }
                QPushButton#sideNav:checked {
                    background:%(surfaceContainerLowest)s;
                    color:%(primary)s;
                    border:1px solid %(outlineVariant)s; }
                QPushButton#sideNav:hover:!checked {
                    background:%(surfaceContainerHigh)s; }
                QPushButton#refreshFontInfo { background:%(surfaceContainerLowest)s;
                    border:1px solid %(outlineVariant)s; border-radius:8px;
                    color:%(onSurface)s; padding:7px 9px; }
                QPushButton:disabled, QPushButton#nativeApply:disabled {
                    background:%(surfaceContainerHighest)s;
                    color:%(outline)s; }
            """ % palette)
            # The sidebar is fixed-width; only the desktop workspace grows.
            outer = QtGui.QHBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)

            sidebar = QtGui.QFrame()
            sidebar.setObjectName("sideRail")
            sidebar.setFixedWidth(236)
            rail = QtGui.QVBoxLayout(sidebar)
            rail.setContentsMargins(0, 0, 0, 0)
            rail.setSpacing(0)

            brand = QtGui.QFrame()
            brand.setObjectName("sidebarBrand")
            brand_col = QtGui.QVBoxLayout(brand)
            brand_col.setContentsMargins(15, 12, 15, 11)
            brand_col.setSpacing(3)
            brand_col.addWidget(self.heading("NghiaType", 15))
            brand_col.addWidget(self.paragraph("FontLab Tools  /  V3 Alpha.0.9"))
            rail.addWidget(brand)
            self.sidebar_brand = brand

            context = QtGui.QFrame()
            context.setObjectName("sidebarContext")
            context_col = QtGui.QVBoxLayout(context)
            context_col.setContentsMargins(15, 11, 15, 12)
            context_col.setSpacing(4)
            context_col.addWidget(self.paragraph("ACTIVE FONT FILE"))
            self.context_label = QtGui.QLabel("No font open")
            self.context_label.setWordWrap(True)
            self.context_label.setStyleSheet(
                "color:%s;background:transparent;border:0;font-weight:bold;" %
                M3_LIGHT["onSurface"]
            )
            context_col.addWidget(self.context_label)
            self.context_detail = self.paragraph("Master: --  /  Masters: --")
            context_col.addWidget(self.context_detail)
            rail.addWidget(context)
            self.sidebar_context = context

            nav = QtGui.QFrame()
            nav.setObjectName("sidebarNav")
            nav_col = QtGui.QVBoxLayout(nav)
            nav_col.setContentsMargins(9, 12, 9, 10)
            nav_col.setSpacing(5)
            nav_caption = self.paragraph("WORKFLOW MODULES")
            nav_caption.setContentsMargins(6, 0, 0, 5)
            nav_col.addWidget(nav_caption)
            self.nav_buttons = []
            self.nav_badges = []
            self.nav_titles = []
            self.nav_dots = []
            for index, (name, subtitle) in enumerate((
                ("Native Kerning", "Selective scan & preview"),
                ("OpenType Studio", "Features & lookups"),
                ("Glyph Matrix", "Unicode audit & sets"),
                ("Reports & Logs", "Readback validations"),
            )):
                button = QtGui.QPushButton("")
                button.setObjectName("sideNav")
                button.setCheckable(True)
                button.setFixedHeight(54)
                button.setToolTip(name + " - " + subtitle)
                nav_row = QtGui.QHBoxLayout(button)
                nav_row.setContentsMargins(9, 5, 8, 5)
                nav_row.setSpacing(9)

                number = QtGui.QLabel("%02d" % (index + 1))
                number.setAlignment(QtCore.Qt.AlignCenter)
                number.setFixedSize(27, 27)
                nav_row.addWidget(number)

                words = QtGui.QVBoxLayout()
                words.setContentsMargins(0, 0, 0, 0)
                words.setSpacing(1)
                title = QtGui.QLabel(name)
                title.setFont(QtGui.QFont(self.ui_font_family, 10,
                                         QtGui.QFont.Bold))
                description = QtGui.QLabel(subtitle)
                description.setStyleSheet(
                    "color:%s;background:transparent;border:0;font-size:10px;" %
                    M3_LIGHT["onSurfaceVariant"]
                )
                words.addWidget(title)
                words.addWidget(description)
                nav_row.addLayout(words, 1)

                dot = QtGui.QLabel(u"\u2022")
                dot.setFixedWidth(9)
                dot.setAlignment(QtCore.Qt.AlignCenter)
                dot.setStyleSheet(
                    "color:%s;background:transparent;border:0;" %
                    M3_LIGHT["primary"]
                )
                nav_row.addWidget(dot)
                # Labels are visual only; clicks anywhere on a nav card must
                # reach its checkable button, including the number chip.
                for label in (number, title, description, dot):
                    label.setAttribute(
                        QtCore.Qt.WA_TransparentForMouseEvents, True
                    )
                callback = lambda *args, target=index: self.navigate_to(target)
                button.clicked.connect(callback)
                self.connections.append((button.clicked, callback))
                self.nav_buttons.append(button)
                self.nav_badges.append(number)
                self.nav_titles.append(title)
                self.nav_dots.append(dot)
                nav_col.addWidget(button)
            rail.addWidget(nav)
            rail.addStretch(1)

            runtime = QtGui.QFrame()
            runtime.setObjectName("sidebarRuntime")
            runtime_col = QtGui.QVBoxLayout(runtime)
            runtime_col.setContentsMargins(14, 11, 14, 13)
            runtime_col.setSpacing(5)
            for heading_text, value_text in (
                ("Engine:", "Python %d.%d.%d" % sys.version_info[:3]),
                ("FL Host:", "FontLab %s" %
                 (detect_fontlab_major(fontlab, QtCore) or "unknown")),
            ):
                info_row = QtGui.QHBoxLayout()
                info_row.addWidget(self.paragraph(heading_text))
                info_row.addStretch(1)
                info_row.addWidget(self.paragraph(value_text))
                runtime_col.addLayout(info_row)
            refresh = QtGui.QPushButton("Refresh font info")
            refresh.setObjectName("refreshFontInfo")
            refresh.setToolTip("Refresh the active filename and master only.")
            refresh.clicked.connect(self.refresh_context)
            runtime_col.addWidget(refresh)
            rail.addWidget(runtime)
            outer.addWidget(sidebar)

            right = QtGui.QWidget()
            right_layout = QtGui.QVBoxLayout(right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(0)

            self.pages = QtGui.QStackedWidget()
            self.pages.addWidget(self.native_page())
            self.pages.addWidget(self.opentype_page())
            self.pages.addWidget(self.glyph_matrix_page())
            self.pages.addWidget(self.reports_page())
            right_layout.addWidget(self.pages, 1)

            footer_band = QtGui.QFrame()
            footer_band.setObjectName("footerBand")
            footer = QtGui.QHBoxLayout(footer_band)
            footer.setContentsMargins(16, 6, 16, 6)
            self.status_label = QtGui.QLabel(
                "V3 PREVIEW ONLY / No automatic font writes or saves."
            )
            self.status_label.setStyleSheet(
                "color:%s;font-size:10px;" % M3_LIGHT["primary"]
            )
            footer.addWidget(self.status_label, 1)
            close = QtGui.QPushButton("Close")
            close.clicked.connect(self.close)
            footer.addWidget(close)
            right_layout.addWidget(footer_band)
            outer.addWidget(right, 1)
            self.navigate_to(0)
            self.refresh_context()

        def navigate_to(self, index):
            """Sidebar navigation only; never starts a scan or applies data."""
            if index < 0 or index >= len(self.nav_buttons):
                return
            self.pages.setCurrentIndex(index)
            for current, button in enumerate(self.nav_buttons):
                active = current == index
                button.setChecked(active)
                self.nav_badges[current].setStyleSheet(
                    "background:%s;color:%s;border:0;border-radius:7px;"
                    "font-weight:bold;font-size:10px;" % (
                        M3_LIGHT["primaryContainer"] if active else
                        M3_LIGHT["surfaceContainer"],
                        M3_LIGHT["onPrimaryContainer"] if active else
                        M3_LIGHT["onSurfaceVariant"]
                    )
                )
                self.nav_titles[current].setStyleSheet(
                    "background:transparent;border:0;color:%s;" % (
                        M3_LIGHT["primary"] if active else
                        M3_LIGHT["onSurfaceVariant"]
                    )
                )
                self.nav_dots[current].setVisible(active)

        def align_native_bands(self):
            """Match the two sidebar separators to their Native page bands."""
            for side, main, minimum in (
                (self.sidebar_brand, self.native_top_band, 70),
                (self.sidebar_context, self.native_metrics_band, 91),
            ):
                heights = [minimum]
                for frame in (side, main):
                    layout = read_qt_value(frame, "layout")
                    hint = read_qt_value(layout, "sizeHint")
                    heights.append(int(read_qt_value(hint, "height", 0)))
                # A little breathing room prevents text clipping when the
                # system font or FontLab display scaling differs.
                height = max(heights) + 7
                side.setFixedHeight(height)
                main.setFixedHeight(height)

        def toggle_native_workspace(self):
            """Give class/glyph tables more height without changing font state."""
            expanded = not getattr(self, "native_workspace_expanded", False)
            self.native_workspace_expanded = expanded
            self.native_lower_container.setVisible(not expanded)
            self.native_expand_button.setText(
                "Show Preview / Apply" if expanded else "Expand workspace"
            )

        def toggle_native_report(self):
            """Keep detailed readback accessible without occupying default space."""
            self.native_report_expanded = not self.native_report_expanded
            self.native_diagnostics.setVisible(self.native_report_expanded)
            self.native_report_button.setText(
                "Hide report" if self.native_report_expanded else "Show report"
            )

        def set_native_latest(self, message):
            """Always display the latest preview event, even when collapsed."""
            self.native_latest_line.setText("Latest: " + message)
            self.native_latest_line.setToolTip(message)

        def make_card(self, name, background, border, radius):
            frame = QtGui.QFrame()
            frame.setObjectName(name)
            frame.setStyleSheet(
                "QFrame#%s{background:%s;border:1px solid %s;"
                "border-radius:%dpx;}" % (name, background, border, radius)
            )
            return frame

        def heading(self, text, size=16, color=None):
            label = QtGui.QLabel(text)
            label.setFont(QtGui.QFont(self.ui_font_family, size, QtGui.QFont.Bold))
            label.setStyleSheet(
                "color:%s;background:transparent;border:0;" %
                (color or M3_LIGHT["primary"])
            )
            return label

        def paragraph(self, text):
            label = QtGui.QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(
                "color:%s;background:transparent;border:0;" %
                M3_LIGHT["onSurfaceVariant"]
            )
            return label

        def configure_tree_columns(self, table, fixed_widths, stretch_columns):
            """Share spare panel width without hiding glyph data offscreen.

            FontLab 8/9 ship different Qt header bindings; a missing resize
            method falls back to readable default column widths.
            """
            for index, width in enumerate(fixed_widths):
                table.setColumnWidth(index, width)
            header = read_qt_value(table, "header")
            if header is None:
                return
            try:
                header.setStretchLastSection(False)
                resize = getattr(header, "setSectionResizeMode", None)
                if resize is None:
                    resize = getattr(header, "setResizeMode", None)
                stretch = getattr(QtGui.QHeaderView, "Stretch", None)
                fixed = getattr(QtGui.QHeaderView, "Fixed", None)
                if not callable(resize) or stretch is None or fixed is None:
                    return
                for index in range(len(fixed_widths)):
                    resize(index, stretch if index in stretch_columns else fixed)
            except Exception:
                # Column resizing is visual only; never block Scan/Preview.
                pass

        def native_page(self):
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            header_band = QtGui.QFrame()
            header_band.setObjectName("nativeTopBand")
            self.native_top_band = header_band
            header_layout = QtGui.QVBoxLayout(header_band)
            header_layout.setContentsMargins(18, 11, 18, 11)

            title_row = QtGui.QHBoxLayout()
            header_text = QtGui.QVBoxLayout()
            header_text.setSpacing(3)
            title_line = QtGui.QHBoxLayout()
            title_line.addWidget(self.heading("Native Kerning Pipeline", 15))
            core_chip = QtGui.QLabel("V2 CORE  /  SELECTIVE SCAN")
            core_chip.setStyleSheet(
                "background:%s;color:%s;border-radius:8px;"
                "padding:6px 9px;font-weight:bold;font-size:10px;" %
                (M3_LIGHT["primaryContainer"], M3_LIGHT["onPrimaryContainer"])
            )
            title_line.addWidget(core_chip)
            title_line.addStretch(1)
            header_text.addLayout(title_line)
            header_text.addWidget(self.paragraph(
                "Scan native classes and review proposals before any guarded Apply."
            ))
            title_row.addLayout(header_text, 1)
            self.native_scan_button = QtGui.QPushButton("Scan Native Classes")
            self.native_scan_button.setObjectName("nativeScan")
            self.native_scan_button.setMinimumHeight(43)
            title_row.addWidget(self.native_scan_button)
            header_layout.addLayout(title_row)
            layout.addWidget(header_band)

            metrics_band = QtGui.QFrame()
            metrics_band.setObjectName("nativeMetricBand")
            self.native_metrics_band = metrics_band
            metrics = QtGui.QHBoxLayout(metrics_band)
            metrics.setContentsMargins(18, 10, 18, 10)
            metrics.setSpacing(9)
            self.native_metrics = {}
            for key, label, color, border, ink in (
                ("glyphs", "GLYPHS", M3_LIGHT["surfaceContainerLowest"],
                 M3_LIGHT["outlineVariant"], M3_LIGHT["onSurface"]),
                ("classes", "NATIVE CLASSES", M3_LIGHT["surfaceContainerLowest"],
                 M3_LIGHT["outlineVariant"], M3_LIGHT["primary"]),
                ("candidates", "VIET CANDIDATES", M3_LIGHT["surfaceContainerLowest"],
                 M3_LIGHT["outlineVariant"], M3_LIGHT["tertiary"]),
                ("available", "AVAILABLE ADDS", M3_LIGHT["primaryContainer"],
                 M3_LIGHT["primaryFixedDim"], M3_LIGHT["onPrimaryContainer"]),
            ):
                card = self.make_card("nativeMetric_" + key, color, border, 12)
                column = QtGui.QVBoxLayout(card)
                column.setContentsMargins(12, 5, 10, 5)
                column.setSpacing(1)
                caption = QtGui.QLabel(label)
                caption.setStyleSheet(
                    "color:%s;background:transparent;border:0;"
                    "font-size:9px;font-weight:bold;" % ink
                )
                number = QtGui.QLabel("\u2014")
                number.setFont(
                    QtGui.QFont(self.ui_font_family, 19, QtGui.QFont.Bold)
                )
                number.setStyleSheet(
                    "color:%s;background:transparent;border:0;" % ink
                )
                column.addWidget(caption)
                column.addWidget(number)
                self.native_metrics[key] = number
                metrics.addWidget(card, 1)
            layout.addWidget(metrics_band)

            work_area = QtGui.QWidget()
            work_area.setObjectName("nativeWorkArea")
            work_layout = QtGui.QVBoxLayout(work_area)
            work_layout.setContentsMargins(18, 15, 18, 12)
            work_layout.setSpacing(13)

            self.native_all_button = QtGui.QPushButton("Select all")
            self.native_all_button.setText("All")
            self.native_all_button.setToolTip("Select all proposed glyphs")
            self.native_clear_button = QtGui.QPushButton("Clear")
            self.native_selection_label = QtGui.QLabel("0 / 0 memberships")
            self.native_selection_label.setStyleSheet(
                "background:%s;color:%s;border-radius:8px;"
                "padding:8px;font-weight:bold;" %
                (M3_LIGHT["primaryContainer"], M3_LIGHT["onPrimaryContainer"])
            )
            self.native_filter = QtGui.QLineEdit()
            self.native_filter.setPlaceholderText("Search classes or glyphs...")
            self.native_filter.setMinimumWidth(145)
            self.native_expand_button = QtGui.QPushButton("Expand workspace")

            tables = QtGui.QHBoxLayout()
            tables.setSpacing(11)
            class_panel = self.make_card(
                "nativeClassPanel", M3_LIGHT["surfaceContainerLowest"],
                M3_LIGHT["outlineVariant"], 15
            )
            class_col = QtGui.QVBoxLayout(class_panel)
            class_col.setContentsMargins(1, 1, 1, 1)
            class_col.setSpacing(0)
            class_head = QtGui.QFrame()
            class_head.setObjectName("nativeClassHead")
            class_head_layout = QtGui.QVBoxLayout(class_head)
            class_head_layout.setContentsMargins(13, 10, 13, 10)
            class_head_layout.setSpacing(5)
            class_actions = QtGui.QHBoxLayout()
            class_actions.addWidget(self.heading("02  Browse Classes", 11))
            class_actions.addStretch(1)
            class_actions.addWidget(self.native_all_button)
            class_actions.addWidget(self.native_clear_button)
            class_actions.addWidget(self.native_selection_label)
            class_head_layout.addLayout(class_actions)
            class_head_layout.addWidget(self.paragraph(
                "Click a row to inspect; tick the class to select its glyphs."
            ))
            class_head_layout.addWidget(self.native_filter)
            class_col.addWidget(class_head)
            class_body = QtGui.QWidget()
            class_body_layout = QtGui.QVBoxLayout(class_body)
            class_body_layout.setContentsMargins(8, 7, 8, 8)
            class_body_layout.setSpacing(0)
            self.native_class_table = QtGui.QTreeWidget()
            self.native_class_table.setColumnCount(5)
            self.native_class_table.setHeaderLabels(
                ["Tick", "Class", "Mode", "Members", "+ Adds"]
            )
            self.native_class_table.setRootIsDecorated(False)
            self.native_class_table.setAlternatingRowColors(True)
            self.native_class_table.setSelectionMode(
                QtGui.QAbstractItemView.SingleSelection
            )
            self.native_class_table.setMinimumHeight(170)
            self.native_class_table.setStyleSheet(
                "QTreeWidget{background:#FFFFFF;border:0;border-radius:0;}"
            )
            self.configure_tree_columns(
                self.native_class_table, (38, 94, 91, 69, 65), (1, 2)
            )
            class_body_layout.addWidget(self.native_class_table, 1)
            class_col.addWidget(class_body, 1)
            tables.addWidget(class_panel, 1)

            glyph_panel = self.make_card(
                "nativeGlyphPanel", M3_LIGHT["surfaceContainerLowest"],
                M3_LIGHT["outlineVariant"], 15
            )
            glyph_col = QtGui.QVBoxLayout(glyph_panel)
            glyph_col.setContentsMargins(1, 1, 1, 1)
            glyph_col.setSpacing(0)
            glyph_head = QtGui.QFrame()
            glyph_head.setObjectName("nativeGlyphHead")
            glyph_head_layout = QtGui.QVBoxLayout(glyph_head)
            glyph_head_layout.setContentsMargins(13, 10, 13, 10)
            glyph_head_layout.setSpacing(5)
            self.native_glyph_title = self.heading(
                "PROPOSED GLYPHS  /  Select a class", 11
            )
            glyph_header = QtGui.QHBoxLayout()
            glyph_header.addWidget(self.native_glyph_title)
            glyph_header.addStretch(1)
            glyph_header.addWidget(self.native_expand_button)
            glyph_head_layout.addLayout(glyph_header)
            glyph_head_layout.addWidget(self.paragraph(
                "Tick individual glyphs; switching classes preserves selections."
            ))
            glyph_col.addWidget(glyph_head)
            glyph_body = QtGui.QWidget()
            glyph_body_layout = QtGui.QVBoxLayout(glyph_body)
            glyph_body_layout.setContentsMargins(8, 7, 8, 8)
            glyph_body_layout.setSpacing(0)
            self.native_glyph_table = QtGui.QTreeWidget()
            self.native_glyph_table.setColumnCount(4)
            self.native_glyph_table.setHeaderLabels([
                "Tick", "Proposed glyph", "Base & accents", "Unicode"
            ])
            self.native_glyph_table.setRootIsDecorated(False)
            self.native_glyph_table.setAlternatingRowColors(True)
            self.native_glyph_table.setSelectionMode(
                QtGui.QAbstractItemView.NoSelection
            )
            self.native_glyph_table.setMinimumHeight(170)
            self.native_glyph_table.setStyleSheet(
                "QTreeWidget{background:#FFFFFF;border:0;border-radius:0;}"
            )
            self.configure_tree_columns(
                self.native_glyph_table, (38, 140, 140, 78), (1, 2)
            )
            glyph_body_layout.addWidget(self.native_glyph_table, 1)
            glyph_col.addWidget(glyph_body, 1)
            tables.addWidget(glyph_panel, 1)
            work_layout.addLayout(tables, 1)

            self.native_lower_container = QtGui.QWidget()
            lower = QtGui.QHBoxLayout(self.native_lower_container)
            lower.setContentsMargins(0, 0, 0, 0)
            lower.setSpacing(11)
            preview_panel = self.make_card(
                "nativePreviewPanel", M3_LIGHT["surfaceContainerLowest"],
                M3_LIGHT["outlineVariant"], 15
            )
            preview_col = QtGui.QVBoxLayout(preview_panel)
            preview_col.setContentsMargins(1, 1, 1, 1)
            preview_col.setSpacing(0)
            preview_head_frame = QtGui.QFrame()
            preview_head_frame.setObjectName("nativePreviewHead")
            preview_head = QtGui.QHBoxLayout(preview_head_frame)
            preview_head.setContentsMargins(11, 8, 11, 8)
            preview_head.addWidget(self.heading("03  Preview / Readback", 11))
            preview_head.addStretch()
            self.native_live_badge = QtGui.QLabel("WAITING FOR SCAN")
            self.native_live_badge.setStyleSheet(
                "background:%s;color:%s;border-radius:9px;"
                "padding:6px 9px;font-weight:bold;font-size:9px;" %
                (M3_LIGHT["primaryContainer"], M3_LIGHT["onPrimaryContainer"])
            )
            preview_head.addWidget(self.native_live_badge)
            self.native_report_button = QtGui.QPushButton("Show report")
            self.native_report_button.setToolTip(
                "Expand the read-only plan and diagnostic details."
            )
            preview_head.addWidget(self.native_report_button)
            self.native_export_button = QtGui.QPushButton("Export JSON")
            self.native_export_button.setEnabled(False)
            preview_head.addWidget(self.native_export_button)
            preview_col.addWidget(preview_head_frame)
            preview_body = QtGui.QWidget()
            preview_body_layout = QtGui.QVBoxLayout(preview_body)
            preview_body_layout.setContentsMargins(12, 9, 12, 9)
            preview_body_layout.setSpacing(5)
            self.native_latest_line = self.paragraph(
                "Latest: Waiting for native class scan. Font unchanged."
            )
            preview_body_layout.addWidget(self.native_latest_line)
            self.native_diagnostics = QtGui.QPlainTextEdit()
            self.native_diagnostics.setReadOnly(True)
            self.native_diagnostics.setMinimumHeight(105)
            self.native_diagnostics.setMaximumHeight(175)
            self.native_diagnostics.setPlainText(
                "Scan native classes to inspect proposals. Font unchanged."
            )
            self.native_report_expanded = False
            self.native_diagnostics.setVisible(False)
            preview_body_layout.addWidget(self.native_diagnostics)
            preview_col.addWidget(preview_body, 1)
            lower.addWidget(preview_panel, 7)

            apply_panel = self.make_card(
                "nativeApplyPanel", M3_LIGHT["surfaceContainerLowest"],
                M3_LIGHT["outlineVariant"], 15
            )
            apply_col = QtGui.QVBoxLayout(apply_panel)
            apply_col.setContentsMargins(1, 1, 1, 1)
            apply_col.setSpacing(0)
            apply_head_frame = QtGui.QFrame()
            apply_head_frame.setObjectName("nativeApplyHead")
            apply_head = QtGui.QHBoxLayout(apply_head_frame)
            apply_head.setContentsMargins(11, 8, 11, 8)
            apply_head.addWidget(self.heading("04  Guarded Apply / FL8", 11))
            apply_head.addStretch(1)
            lock_badge = QtGui.QLabel("LOCKED")
            lock_badge.setStyleSheet(
                "background:%s;color:%s;border-radius:9px;"
                "padding:6px 9px;font-weight:bold;" %
                (M3_LIGHT["errorContainer"], M3_LIGHT["onErrorContainer"])
            )
            apply_head.addWidget(lock_badge)
            apply_col.addWidget(apply_head_frame)
            apply_body = QtGui.QWidget()
            apply_body_layout = QtGui.QVBoxLayout(apply_body)
            apply_body_layout.setContentsMargins(12, 9, 12, 9)
            apply_body_layout.setSpacing(5)
            apply_body_layout.addWidget(self.paragraph(
                "Writer disabled until V3 passes the FL8 apply/readback gate."
            ))
            self.native_apply_button = QtGui.QPushButton(
                "Apply locked in V3 Alpha.0.9"
            )
            self.native_apply_button.setObjectName("nativeApply")
            self.native_apply_button.setEnabled(False)
            self.native_apply_button.setMinimumHeight(32)
            apply_body_layout.addWidget(self.native_apply_button)
            apply_col.addWidget(apply_body, 1)
            lower.addWidget(apply_panel, 5)
            work_layout.addWidget(self.native_lower_container, 0)
            layout.addWidget(work_area, 1)

            self.native_all_button.setEnabled(False)
            self.native_clear_button.setEnabled(False)
            self.native_scan_button.clicked.connect(
                lambda *args: self.safe_native(self.scan_native_tab)
            )
            self.native_all_button.clicked.connect(
                lambda *args: self.safe_native(lambda: self.select_all_native(True))
            )
            self.native_clear_button.clicked.connect(
                lambda *args: self.safe_native(lambda: self.select_all_native(False))
            )
            self.native_expand_button.clicked.connect(
                lambda *args: self.toggle_native_workspace()
            )
            self.native_export_button.clicked.connect(
                lambda *args: self.safe_native(self.export_native_report)
            )
            self.native_report_button.clicked.connect(
                lambda *args: self.toggle_native_report()
            )
            self.native_filter.textChanged.connect(
                lambda *args: self.safe_native(self.filter_native_classes)
            )
            class_toggled = lambda item, col: self.safe_native(
                lambda: self.on_native_class_toggled(item, col)
            )
            glyph_toggled = lambda item, col: self.safe_native(
                lambda: self.on_native_glyph_toggled(item, col)
            )
            class_focus = lambda item, old: self.safe_native(
                lambda: self.show_native_class(item)
            )
            self.native_class_table.itemChanged.connect(class_toggled)
            self.native_glyph_table.itemChanged.connect(glyph_toggled)
            self.native_class_table.currentItemChanged.connect(class_focus)
            self.connections.extend([
                (self.native_class_table.itemChanged, class_toggled),
                (self.native_glyph_table.itemChanged, glyph_toggled),
                (self.native_class_table.currentItemChanged, class_focus),
            ])
            return page

        def empty_ot_table(self, labels, widths):
            table = QtGui.QTreeWidget()
            table.setColumnCount(len(labels))
            table.setHeaderLabels(labels)
            table.setRootIsDecorated(False)
            table.setAlternatingRowColors(True)
            for i, width in enumerate(widths):
                table.setColumnWidth(i, width)
            table.setEnabled(False)
            return table

        def opentype_classes_page(self):
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(14, 13, 14, 13)
            layout.setSpacing(9)
            heading_row = QtGui.QHBoxLayout()
            heading_row.addWidget(self.heading("OpenType Classes", 12))
            heading_row.addStretch()
            search = QtGui.QLineEdit()
            search.setPlaceholderText("Search OT classes or glyphs...")
            search.setEnabled(False)
            heading_row.addWidget(search)
            scan = QtGui.QPushButton("Scan OT classes")
            scan.setEnabled(False)
            scan.setToolTip("Enabled after verifying the OpenType reader API.")
            heading_row.addWidget(scan)
            layout.addLayout(heading_row)

            tables = QtGui.QHBoxLayout()
            tables.setSpacing(10)
            left = self.make_card(
                "otClassList", M3_LIGHT["surfaceContainerLow"],
                M3_LIGHT["outlineVariant"], 16
            )
            left_layout = QtGui.QVBoxLayout(left)
            left_layout.setContentsMargins(10, 10, 10, 10)
            left_layout.addWidget(self.heading("CLASS DIRECTORY", 10))
            left_layout.addWidget(self.paragraph(
                "Name, side, membership count, and linked features."
            ))
            left_layout.addWidget(self.empty_ot_table(
                ["Class", "Type / Side", "Members", "Features"],
                [150, 110, 75, 120]
            ), 1)
            tables.addWidget(left, 7)
            right = self.make_card(
                "otClassInspect", M3_LIGHT["surfaceContainerLow"],
                M3_LIGHT["outlineVariant"], 16
            )
            right_layout = QtGui.QVBoxLayout(right)
            right_layout.setContentsMargins(10, 10, 10, 10)
            right_layout.addWidget(self.heading("CLASS MEMBERS", 10))
            right_layout.addWidget(self.paragraph(
                "Choose a class to inspect its glyphs and references."
            ))
            right_layout.addWidget(self.empty_ot_table(
                ["Glyph name", "Unicode / Source"], [210, 130]
            ), 1)
            tables.addWidget(right, 5)
            layout.addLayout(tables, 1)
            layout.addWidget(self.paragraph(
                "READER NOT CONNECTED / No OpenType class data shown yet."
            ))
            return page

        def opentype_features_page(self):
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(14, 13, 14, 13)
            layout.setSpacing(9)
            layout.addWidget(self.heading("Feature Explorer", 12))
            layout.addWidget(self.paragraph(
                "Planned coverage: kern, liga, locl, smcp, c2sc, aalt, "
                "ss01-ss20, and additional OpenType features."
            ))
            columns = QtGui.QHBoxLayout()
            columns.setSpacing(10)
            feature_list = self.make_card(
                "otFeatureList", M3_LIGHT["surfaceContainerLow"],
                M3_LIGHT["outlineVariant"], 16
            )
            list_layout = QtGui.QVBoxLayout(feature_list)
            list_layout.addWidget(self.heading("FEATURES", 10))
            list_layout.addWidget(self.empty_ot_table(
                ["Tag", "Status", "Lookups"], [110, 120, 100]
            ), 1)
            columns.addWidget(feature_list, 5)
            feature_detail = self.make_card(
                "otFeatureDetail", M3_LIGHT["surfaceContainerLow"],
                M3_LIGHT["outlineVariant"], 16
            )
            detail_layout = QtGui.QVBoxLayout(feature_detail)
            detail_layout.addWidget(self.heading("FEATURE DETAILS", 10))
            details = QtGui.QPlainTextEdit()
            details.setReadOnly(True)
            details.setPlainText(
                "OpenType feature code and class references will appear here "
                "after the read-only feature scanner is verified."
            )
            detail_layout.addWidget(details, 1)
            columns.addWidget(feature_detail, 7)
            layout.addLayout(columns, 1)
            return page

        def opentype_validation_page(self):
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(14, 13, 14, 13)
            layout.addWidget(self.heading("OpenType Validation", 12))
            layout.addWidget(self.paragraph(
                "Future checks: missing glyphs, duplicate memberships, "
                "broken class references, unsupported lookups, and feature dependencies."
            ))
            results = QtGui.QPlainTextEdit()
            results.setReadOnly(True)
            results.setPlainText(
                "VALIDATION NOT STARTED\n\n"
                "No OpenType reader or writer is connected in Alpha.0.9."
            )
            layout.addWidget(results, 1)
            return page

        def opentype_page(self):
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(11)
            layout.addWidget(self.heading("OpenType Studio"))
            layout.addWidget(self.paragraph(
                "A separate module for OpenType Classes, GSUB/GPOS Features "
                "and validation. It will not reuse the Native writer."
            ))
            sections = QtGui.QTabWidget()
            sections.addTab(self.opentype_classes_page(), "Classes")
            sections.addTab(self.opentype_features_page(), "Features")
            sections.addTab(self.opentype_validation_page(), "Validation")
            layout.addWidget(sections, 1)
            return page

        def glyph_matrix_page(self):
            """Show the future module honestly, without querying or editing font data."""
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(9)
            layout.addWidget(self.heading("Glyph Matrix / Planned"))
            layout.addWidget(self.paragraph(
                "A future read-only workspace for Unicode coverage, glyph sets "
                "and consistency checks across Native and OpenType modules."
            ))
            placeholder = QtGui.QPlainTextEdit()
            placeholder.setReadOnly(True)
            placeholder.setPlainText(
                "NOT CONNECTED / no glyph scans are running here yet.\n\n"
                "The active Native Kerning scanner remains available in module 01."
            )
            layout.addWidget(placeholder, 1)
            return page

        def reports_page(self):
            page = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(page)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.addWidget(self.heading("Reports & Readback"))
            layout.addWidget(self.paragraph(
                "A future shared home for Native and OpenType scan results, "
                "conflicts, and JSON exports. Native V2's existing Export JSON "
                "button remains functional in its own verified GUI."
            ))
            layout.addStretch(1)
            return page

        def refresh_context(self):
            snap = current_font_context(fontlab)
            self.context_label.setText(snap["font"])
            self.context_label.setToolTip(snap["font"])
            self.context_detail.setText(
                "Master: %s   /   Masters: %s" %
                (snap["master"], snap["masters"])
            )
            self.align_native_bands()

        def safe_native(self, callback):
            try:
                callback()
            except Exception as exc:
                print("NGHIATYPE V3 NATIVE PREVIEW ERROR:\n" + traceback.format_exc())
                self.native_diagnostics.setPlainText(traceback.format_exc()[-4000:])
                self.native_live_badge.setText("ERROR / READ ONLY")
                self.status_label.setText(type(exc).__name__ + ": " + str(exc))
                self.set_native_latest("ERROR / " + type(exc).__name__ + ": " + str(exc))

        def get_native_backend(self):
            """Load the V2 reader/planner and companion Core, but NOT its GUI."""
            if self.native_backend is not None and self.native_core is not None:
                return self.native_backend, self.native_core
            path = native_gui_hint()
            if not path:
                selected = QtGui.QFileDialog.getOpenFileName(
                    self, "Select the verified Native Kerning V2 GUI",
                    "", "Python scripts (*.py)"
                )
                if isinstance(selected, (tuple, list)):
                    selected = selected[0]
                path = str(selected or "").strip()
            if not path:
                return None, None
            backend = load_existing_native_gui(path)
            core_path = backend.native_core_path_hint()
            if not core_path:
                selected = QtGui.QFileDialog.getOpenFileName(
                    self, "Select the Native Core V2 Alpha.1.4.1",
                    "", "Python scripts (*.py)"
                )
                if isinstance(selected, (tuple, list)):
                    selected = selected[0]
                core_path = str(selected or "").strip()
            if not core_path:
                return None, None
            core = backend.load_native_core(core_path)
            self.native_backend = backend
            self.native_core = core
            return backend, core

        def scan_native_tab(self):
            """Run the real Native V2 READ-ONLY discovery in the embedded tab."""
            backend, core = self.get_native_backend()
            if backend is None or core is None:
                self.status_label.setText("Native scan cancelled; font unchanged.")
                self.set_native_latest("Scan cancelled; no font changes.")
                return
            self.native_snapshot = None
            self.native_preview = None
            self.native_selected = set()
            self.native_entries = []
            self.native_rows = {}
            self.native_unicode_map = {}
            self.native_active_class = None
            self.native_updating = True
            try:
                self.native_class_table.clear()
                self.native_glyph_table.clear()
            finally:
                self.native_updating = False
            self.native_all_button.setEnabled(False)
            self.native_clear_button.setEnabled(False)
            self.native_export_button.setEnabled(False)
            self.native_live_badge.setText("SCANNING")
            self.set_native_latest("Scanning native classes / read only...")
            snap = backend.scan_native(fontlab, core)
            self.native_snapshot = snap
            try:
                scanned_font = fontlab.CurrentFont()
            except Exception:
                scanned_font = None
            self.native_unicode_map = read_glyph_codepoints(
                scanned_font,
                (name for names in snap["safe_all"].values() for name in names)
            )
            self.native_metrics["glyphs"].setText(str(len(snap["available"])))
            self.native_metrics["classes"].setText(str(len(snap["groups"])))
            self.native_metrics["candidates"].setText(str(snap["candidate_count"]))
            self.native_metrics["available"].setText(
                str(sum(len(x) for x in snap["safe_all"].values()))
            )
            self.native_updating = True
            try:
                for key in sorted(snap["safe_all"],
                                  key=lambda text: (text.casefold(), text)):
                    names = snap["safe_all"][key]
                    members, mode = snap["groups"][key]
                    row = QtGui.QTreeWidgetItem(self.native_class_table)
                    row.setFlags(row.flags() | QtCore.Qt.ItemIsUserCheckable)
                    row.setCheckState(0, QtCore.Qt.Unchecked)
                    row.setText(1, key)
                    row.setText(2, mode)
                    row.setText(3, str(len(members)))
                    row.setText(4, "+" + str(len(names)))
                    self.native_rows[key] = row
                    self.native_entries.extend((key, glyph) for glyph in names)
                first = next(iter(self.native_rows.values()), None)
                if first is not None:
                    self.native_class_table.setCurrentItem(first)
            finally:
                self.native_updating = False
            self.show_native_class(first)
            self.native_all_button.setEnabled(bool(self.native_entries))
            self.native_clear_button.setEnabled(bool(self.native_entries))
            self.native_export_button.setEnabled(True)
            self.native_diagnostics.setPlainText(
                "READ ONLY / %d available classes / %d memberships\n"
                "%d conflicts, %d scan issues.\n"
                "Select a class or glyph. Preview updates automatically.\n"
                "V3 APPLY LOCKED / font unchanged."
                % (len(snap["safe_all"]), len(self.native_entries),
                   len(snap["blocked"]), len(snap["issues"]))
            )
            self.native_live_badge.setText("SCAN COMPLETE")
            self.status_label.setText("Native scan complete; font unchanged.")
            self.set_native_latest(
                "Scan complete / %d classes, %d proposed adds. Font unchanged." %
                (len(snap["safe_all"]), len(self.native_entries))
            )
            self.refresh_native_selection_count()
            self.filter_native_classes()
            self.refresh_context()

        def show_native_class(self, item):
            if self.native_updating or self.native_snapshot is None:
                return
            key = str(item.text(1)) if item is not None else ""
            if key not in self.native_snapshot["safe_all"]:
                key = None
            self.native_active_class = key
            self.render_native_glyphs()

        def render_native_glyphs(self):
            self.native_updating = True
            try:
                self.native_glyph_table.clear()
                key = self.native_active_class
                if key is None or self.native_snapshot is None:
                    self.native_glyph_title.setText(
                        "PROPOSED GLYPHS  /  Select a class"
                    )
                    return
                names = self.native_snapshot["safe_all"][key]
                checked = sum((key, name) in self.native_selected for name in names)
                self.native_glyph_title.setText(
                    "CLASS %s / %d proposed / %d selected" %
                    (key, len(names), checked)
                )
                for glyph in names:
                    row = QtGui.QTreeWidgetItem(self.native_glyph_table)
                    row.setFlags(row.flags() | QtCore.Qt.ItemIsUserCheckable)
                    row.setCheckState(
                        0, QtCore.Qt.Checked if (key, glyph) in self.native_selected
                        else QtCore.Qt.Unchecked
                    )
                    row.setText(1, glyph)
                    codepoints = self.native_unicode_map.get(glyph, ())
                    row.setText(2, describe_unicode_components(codepoints))
                    row.setText(3, format_unicode_values(codepoints))
                    origin = self.native_snapshot["origin"].get(
                        glyph.split(".", 1)[0], (None, "name")
                    )[1]
                    try:
                        row.setToolTip(
                            1, "Unicode-backed proposal" if origin == "unicode"
                            else "Name-only proposal / not authorized for Apply"
                        )
                    except Exception:
                        pass
            finally:
                self.native_updating = False

        def sync_native_class_checks(self):
            if self.native_snapshot is None:
                return
            self.native_updating = True
            try:
                for key, row in self.native_rows.items():
                    names = self.native_snapshot["safe_all"][key]
                    chosen = sum((key, name) in self.native_selected for name in names)
                    state = (QtCore.Qt.Checked if chosen == len(names)
                             else QtCore.Qt.Unchecked if not chosen
                             else QtCore.Qt.PartiallyChecked)
                    row.setCheckState(0, state)
            finally:
                self.native_updating = False

        def on_native_class_toggled(self, item, column):
            if self.native_updating or column != 0 or self.native_snapshot is None:
                return
            key = str(item.text(1))
            if key not in self.native_snapshot["safe_all"]:
                return
            state = item.checkState(0)
            if state == QtCore.Qt.PartiallyChecked:
                return
            pairs = {(key, glyph) for glyph in self.native_snapshot["safe_all"][key]}
            if state == QtCore.Qt.Checked:
                self.native_selected.update(pairs)
            else:
                self.native_selected.difference_update(pairs)
            self.sync_native_class_checks()
            self.render_native_glyphs()
            self.refresh_native_preview()
            self.set_native_latest(
                "Class %s / %s %d proposed glyphs. Font unchanged." %
                (key, "selected" if state == QtCore.Qt.Checked else "cleared",
                 len(pairs))
            )

        def on_native_glyph_toggled(self, item, column):
            if (self.native_updating or column != 0 or
                    self.native_active_class is None or self.native_snapshot is None):
                return
            key = self.native_active_class
            glyph = str(item.text(1))
            if glyph not in self.native_snapshot["safe_all"][key]:
                return
            if item.checkState(0) == QtCore.Qt.Checked:
                self.native_selected.add((key, glyph))
            else:
                self.native_selected.discard((key, glyph))
            self.sync_native_class_checks()
            self.render_native_glyphs()
            self.refresh_native_preview()
            self.set_native_latest(
                "%s / %s / class %s. Font unchanged." %
                (glyph, "selected" if (key, glyph) in self.native_selected
                 else "deselected", key)
            )

        def select_all_native(self, select):
            if self.native_snapshot is None:
                return
            self.native_selected = set(self.native_entries) if select else set()
            self.sync_native_class_checks()
            self.render_native_glyphs()
            self.refresh_native_preview()
            self.set_native_latest(
                "%s / %d memberships selected. Font unchanged." %
                ("Select all" if select else "Clear all", len(self.native_selected))
            )

        def filter_native_classes(self):
            if self.native_snapshot is None:
                return
            query = str(read_qt_value(self.native_filter, "text", "")).strip().casefold()
            first = None
            for key, row in self.native_rows.items():
                visible = (not query or query in key.casefold()
                           or any(query in glyph.casefold()
                                  for glyph in self.native_snapshot["safe_all"][key]))
                row.setHidden(not visible)
                if visible and first is None:
                    first = row
            current = self.native_rows.get(self.native_active_class)
            if current is None or current.isHidden():
                if first is not None:
                    self.native_class_table.setCurrentItem(first)
                else:
                    self.show_native_class(None)

        def refresh_native_selection_count(self):
            self.native_selection_label.setText(
                "%d / %d memberships" %
                (len(self.native_selected), len(self.native_entries))
            )

        def refresh_native_preview(self):
            self.native_preview = None
            self.refresh_native_selection_count()
            snap = self.native_snapshot
            if snap is None:
                return
            if not self.native_selected:
                self.native_live_badge.setText("NO SELECTION")
                self.native_diagnostics.setPlainText(
                    "READ ONLY / no proposed glyphs selected.\n"
                    "Tick a class or individual glyph. V3 font unchanged."
                )
                self.set_native_latest("No glyphs selected. Font unchanged.")
                return
            preview = self.native_backend.selected_preview(
                self.native_core, snap, frozenset(self.native_selected)
            )
            self.native_preview = preview
            lines = [
                "PROPOSED CHANGES / NOT YET APPLIED",
                "Selected: %d classes / %d memberships" %
                (len(preview["selected"]), preview["count"]), "",
            ]
            for key, names in sorted(preview["selected"].items()):
                lines.append("%s  |  +%d  |  %s" %
                             (key, len(names), ", ".join(names)))
            if snap["blocked"] or preview["issues"] or preview["name_only"]:
                lines.append("")
                lines.append("REVIEW: conflicts / scan issues / name-only proposals")
                if snap["blocked"]:
                    lines.append("Conflicts: %d" % len(snap["blocked"]))
                if preview["issues"]:
                    lines.extend(preview["issues"][:8])
                if preview["name_only"]:
                    lines.append("Name-only: " + ", ".join(preview["name_only"]))
            lines.extend(["", "V3 INTEGRATION GATE: APPLY LOCKED.",
                          "Font unchanged. No automatic writes or saves."])
            self.native_diagnostics.setPlainText("\n".join(lines))
            self.native_live_badge.setText("READY / %d GLYPHS" % preview["count"])
            self.status_label.setText("Read-only native plan ready; V3 Apply locked.")
            self.set_native_latest(
                "Preview / %d classes, %d memberships. Font unchanged." %
                (len(preview["selected"]), preview["count"])
            )

        def export_native_report(self):
            if self.native_snapshot is None or self.native_backend is None:
                raise RuntimeError("Scan native classes first.")
            data = self.native_backend.report_data(
                self.native_snapshot, self.native_preview,
                detect_fontlab_major(fontlab, QtCore), None
            )
            selected = QtGui.QFileDialog.getSaveFileName(
                self, "Export V3 native preview JSON",
                "NghiaType_V3_Native_Preview.json", "JSON (*.json)"
            )
            if isinstance(selected, (tuple, list)):
                selected = selected[0]
            path = str(selected or "").strip()
            if not path:
                return
            if not path.lower().endswith(".json"):
                path += ".json"
            with open(path, "x", encoding="utf-8") as output:
                json.dump(data, output, indent=2, sort_keys=True, ensure_ascii=True)
                output.write("\n")
            self.status_label.setText("Preview JSON exported; font unchanged.")
            self.set_native_latest("Preview JSON exported. Font unchanged.")

        def closeEvent(self, event):
            cache = sys.__dict__.setdefault(WINDOW_CACHE_KEY, {})
            if cache.get("window") is self:
                cache.pop("window", None)
            QtGui.QDialog.closeEvent(self, event)

    cache = sys.__dict__.setdefault(WINDOW_CACHE_KEY, {})
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
    window = ToolsShell(parent)
    cache["window"] = window
    window.show()
    window.raise_()
    return window


def main():
    try:
        import fontlab
        from PythonQt import QtCore, QtGui
        return start_gui(fontlab, QtCore, QtGui)
    except Exception:
        print("NghiaType Tools V3 shell startup failure:")
        print(traceback.format_exc())
        return None


if __name__ == "__main__":
    main()
