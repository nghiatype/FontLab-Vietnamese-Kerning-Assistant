# -*- coding: utf-8 -*-
#FLM: NghiaType Native Writer API Check (READ ONLY)
"""Inspect FontLab native kerning write bindings WITHOUT invoking them.

This is a diagnostic step before developing Native Class Apply. It calls
ONLY read methods and Python introspection. It does not modify or save fonts.
No TypeRig or other third-party packages are needed.

Run within FontLab 8, with a font open and initialized (Font Info > Apply if
needed for this installation). Output contains no font paths or glyph names.
"""

from __future__ import print_function

import inspect
import json
import sys
import traceback


def _name(value):
    return type(value).__name__


def _method_info(owner, name):
    """Inspect a Python attribute without invoking the target method."""
    result = {"name": name, "owner_type": _name(owner)}
    try:
        method = getattr(owner, name)
    except Exception as exc:
        result["access_error"] = type(exc).__name__
        return result
    result["available"] = True
    result["callable"] = callable(method)
    result["binding_type"] = _name(method)
    if not callable(method):
        return result
    try:
        result["signature"] = str(inspect.signature(method))[:600]
    except Exception as exc:
        result["signature_error"] = type(exc).__name__
    try:
        doc = getattr(method, "__doc__", None)
        if doc:
            result["doc"] = str(doc).strip()[:1500]
        else:
            result["doc"] = "<no docstring>"
    except Exception as exc:
        result["doc_error"] = type(exc).__name__
    return result


def _current_package(fontlab, font):
    try:
        package = fontlab.flWorkspace.instance().currentPackage
        if package is not None:
            return package, "flWorkspace.instance().currentPackage"
    except Exception:
        pass
    return fontlab.flPackage(font), "flPackage(CurrentFont())"


def _count_glyphs(font):
    try:
        return len(list(font.keys()))
    except Exception:
        return None


def build_report(font, fontlab):
    package, source = _current_package(fontlab, font)
    master = str(package.getLayerName())
    kerning = package.kerning(master)
    groups = kerning.groups
    data = groups.asDict()
    if not isinstance(data, dict):
        raise TypeError("Expected dict from native kerning.groups.asDict()")
    modes = {}
    for record in data.values():
        if not isinstance(record, (tuple, list)) or len(record) != 2:
            mode = "<unknown>"
        else:
            mode = str(record[1])
        modes[mode] = modes.get(mode, 0) + 1

    report = {
        "tool": "NghiaType Native Writer API Check 0.1 / READ ONLY",
        "python": sys.version.split()[0],
        "font_type": _name(font),
        "package_type": _name(package),
        "package_source": source,
        "current_font_glyph_count": _count_glyphs(font),
        "package_font_glyph_count": _count_glyphs(package.fgPackage),
        "master": master,
        "native_kerning_groups": len(data),
        "native_group_modes": modes,
        "methods": [
            _method_info(kerning, "addGroup"),
            _method_info(kerning, "deleteGroup"),
            _method_info(kerning, "renameGroup"),
            _method_info(groups, "remove"),
            _method_info(groups, "rename"),
            _method_info(package, "getAllGroups"),
        ],
        "read_only": True,
        "apply_available": False,
    }
    return report


def main():
    print("=== NGHIATYPE NATIVE WRITER API CHECK / READ ONLY ===")
    try:
        import fontlab
        font = fontlab.CurrentFont()
        if font is None:
            print("STOP: Open a font first.")
            return
        report = build_report(font, fontlab)
        print("NATIVE_WRITER_CHECK_JSON_BEGIN")
        print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
        print("NATIVE_WRITER_CHECK_JSON_END")
        print("DONE: Did not invoke any native writer; no font edits or saves.")
    except Exception:
        print("STOP: Inspection failed; no write operation was invoked.")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
