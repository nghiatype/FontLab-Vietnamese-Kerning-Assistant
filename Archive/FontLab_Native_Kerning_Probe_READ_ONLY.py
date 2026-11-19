# -*- coding: utf-8 -*-
#FLM: Native Kerning Classes - READ ONLY Probe
"""FontLab 8/9 native kerning-class API probe (READ ONLY).

Run this file in FontLab's Macro/Scripting panel with a font open.
It prints a compact JSON summary into the Output panel. Copy that output
to your developer; check that no client-sensitive names are shared.

No methods that change font data are called. This script does NOT:
  - modify native classes, pair values, the Features panel, or glyphs;
  - save or export a font;
  - create reports on disk;
  - import the existing Vietnamese Kerning Assistant core.

The script intentionally uses only ASCII source text to avoid the UTF-8
mojibake observed when FontLab executes a macro as <string> on Windows.
"""

from __future__ import print_function

import json
import sys
import traceback


MAX_GROUP_PREVIEW = 8
MAX_MEMBER_PREVIEW = 12
MAX_RAW_PREVIEW_CHARS = 220


def _typename(value):
    return type(value).__name__


def _brief(value):
    """Never dump an unlimited native-object representation to Output."""
    try:
        value = repr(value)
    except Exception as exc:
        return "<repr error: %s>" % _typename(exc)
    if len(value) > MAX_RAW_PREVIEW_CHARS:
        value = value[:MAX_RAW_PREVIEW_CHARS] + "..."
    return value


def _read_items(container):
    """Use documented read accessors; return (rows, accessor, error)."""
    failures = []
    for method_name in ("items", "asDict"):
        try:
            method = getattr(container, method_name, None)
            if not callable(method):
                continue
            data = method()
            if isinstance(data, dict):
                return list(data.items()), method_name, None
            if isinstance(data, (list, tuple)):
                return list(data), method_name, None
            if not isinstance(data, (str, bytes)) and hasattr(data, "__iter__"):
                return list(data), method_name, None
            failures.append("%s returned %s" % (method_name, _typename(data)))
        except Exception as exc:
            failures.append("%s: %s: %s" %
                            (method_name, _typename(exc), str(exc)[:120]))
    return [], None, "; ".join(failures) or "No supported read accessor"


def _member_list(record):
    """Recognize only unambiguous membership data; no silent guessing."""
    if isinstance(record, dict):
        for key in ("glyphs", "members", "names"):
            value = record.get(key)
            if isinstance(value, (list, tuple)):
                return [str(v) for v in value]
    if isinstance(record, (list, tuple)):
        # Observed formats may be (members, mode, keyGlyph) or similar.
        for value in record:
            if isinstance(value, (list, tuple)) and all(
                    isinstance(v, str) for v in value):
                return list(value)
        # Do not treat a tuple of metadata strings as class members.
    return None


def _mode_hint(record):
    """Display mode only if exposed clearly by the runtime."""
    try:
        if isinstance(record, dict) and "mode" in record:
            return str(record["mode"])
        mode = getattr(record, "mode", None)
        if mode is not None and not callable(mode):
            return str(mode)
        if isinstance(record, (list, tuple)):
            for value in record:
                if isinstance(value, str) and (
                        "GroupMode" in value or value in ("left", "right", "both")):
                    return value
    except Exception:
        pass
    return None


def _preview_rows(rows):
    preview = []
    for entry in rows[:MAX_GROUP_PREVIEW]:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            name, record = entry
            item = {"name": str(name), "record_type": _typename(record)}
            members = _member_list(record)
            if members is not None:
                item["member_count"] = len(members)
                item["members_sample"] = members[:MAX_MEMBER_PREVIEW]
            mode = _mode_hint(record)
            if mode is not None:
                item["mode_hint"] = mode
            item["raw_sample"] = _brief(record)
        else:
            item = {"entry_type": _typename(entry), "raw_sample": _brief(entry)}
        preview.append(item)
    return preview


def _scan_container(label, container):
    result = {"label": label, "container_type": _typename(container)}
    rows, accessor, error = _read_items(container)
    if error:
        result["read_error"] = error
    else:
        result["accessor"] = accessor
        result["entry_count"] = len(rows)
        result["sample"] = _preview_rows(rows)
    return result


def build_snapshot(font):
    """Detached report. Reading only; no FontLab mutation calls."""
    snapshot = {
        "probe": "FontLab Native Kerning Probe 0.1 (READ ONLY)",
        "python": sys.version.split()[0],
        "font_type": _typename(font),
        "containers": [],
    }

    # fgFont.kerning and fgKerning.groups are documented native attributes.
    try:
        kerning = getattr(font, "kerning")
        snapshot["kerning_object_type"] = _typename(kerning)
        native_groups = getattr(kerning, "groups")
        snapshot["containers"].append(
            _scan_container("font.kerning.groups", native_groups))
    except Exception as exc:
        snapshot["kerning_error"] = "%s: %s" % (_typename(exc), str(exc)[:200])

    # fgFont.groups holds general glyph classes. Compare with native kerning.
    try:
        groups = getattr(font, "groups")
        snapshot["containers"].append(_scan_container("font.groups", groups))
    except Exception as exc:
        snapshot["groups_error"] = "%s: %s" % (_typename(exc), str(exc)[:200])

    # Do not infer class ownership or pair values until FL8/FL9 output is seen.
    snapshot["font_modified"] = False
    return snapshot


def main():
    print("=== NATIVE KERNING PROBE / READ ONLY ===")
    try:
        import fontlab
    except ImportError:
        print("ERROR: Run inside FontLab, not standalone Python.")
        return
    try:
        font = fontlab.CurrentFont()
        if font is None:
            print("ERROR: Open a font before running the probe.")
            return
        report = build_snapshot(font)
        print("NATIVE_PROBE_JSON_BEGIN")
        print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
        print("NATIVE_PROBE_JSON_END")
        print("DONE: No font edits, no file writes, no automatic save.")
    except Exception:
        print("ERROR: Probe failed; no font edits were requested.")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
