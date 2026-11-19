# -*- coding: utf-8 -*-
#FLM: NghiaType Native Writer Source Probe (READ ONLY)
"""Inspect locally installed TypeRig wrappers without calling writer methods.

WHY: FontLab's native fgKerning.addGroup has no documented argument signature.
TypeRig's Python wrapper may reveal which native calls and arguments it uses.

SAFETY: Only imports modules, reads function source, and reads font/group counts.
No addGroup, deleteGroup, renameGroup, class edits, saves, or exports are called.
The current font and Kerning Assistant v1 are left untouched.
"""

from __future__ import print_function

import importlib
import inspect
import json
import sys
import traceback


METHODS = (
    ("typerig.proxy.objects.kern", "pKerning", "addGroup"),
    ("typerig.proxy.objects.kern", "pKerning", "groupsFromDict"),
    ("typerig.proxy.objects.kern", "pKerning", "storeExternalGroupData"),
    ("typerig.proxy.objects.font", "pFont", "add_kerning_group"),
    ("typerig.proxy.fl.objects.kern", "pKerning", "addGroup"),
    ("typerig.proxy.fl.objects.font", "pFont", "add_kerning_group"),
)


def _safe_method_source(module_name, class_name, method_name, modules):
    result = {
        "module": module_name,
        "class": class_name,
        "method": method_name,
    }
    if module_name not in modules:
        try:
            modules[module_name] = importlib.import_module(module_name)
        except Exception as exc:
            modules[module_name] = None
            result["status"] = "module_unavailable"
            result["reason"] = type(exc).__name__
            return result

    module = modules[module_name]
    if module is None:
        result["status"] = "module_unavailable"
        return result

    cls = getattr(module, class_name, None)
    method = getattr(cls, method_name, None) if cls is not None else None
    if not callable(method):
        result["status"] = "method_unavailable"
        return result

    result["status"] = "method_found"
    try:
        result["signature"] = str(inspect.signature(method))
    except Exception as exc:
        result["signature_error"] = type(exc).__name__
    try:
        source = inspect.getsource(method)
        # A source excerpt is sufficient to identify the native call route.
        result["source"] = source[:8500]
        result["source_truncated"] = len(source) > 8500
    except Exception as exc:
        result["source_error"] = type(exc).__name__
    return result


def _font_summary():
    """Counts only: no names or user font paths in the report."""
    try:
        import fontlab
        font = fontlab.CurrentFont()
        if font is None:
            return {"status": "no_font_open"}
        package = fontlab.flWorkspace.instance().currentPackage
        master = str(package.getLayerName())
        native_groups = package.kerning(master).groups.asDict()
        return {
            "status": "ok",
            "font_glyph_count": len(list(font.keys())),
            "package_glyph_count": len(list(package.fgPackage.keys())),
            "native_group_count": len(native_groups),
        }
    except Exception as exc:
        return {"status": "read_failed", "reason": type(exc).__name__}


def main():
    print("=== NGHIATYPE NATIVE WRITER SOURCE PROBE / READ ONLY ===")
    try:
        modules = {}
        report = {
            "tool": "NghiaType Native Writer Source Probe 0.1 / READ ONLY",
            "python": sys.version.split()[0],
            "font": _font_summary(),
            "wrappers": [
                _safe_method_source(module, cls, method, modules)
                for module, cls, method in METHODS
            ],
            "writer_methods_invoked": False,
            "font_modified": False,
            "apply_available": False,
        }
        print("NATIVE_WRITER_SOURCE_JSON_BEGIN")
        print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
        print("NATIVE_WRITER_SOURCE_JSON_END")
        print("DONE: No writer methods called; no font edits or saves.")
    except Exception:
        print("STOP: Inspection failed. No writer method was called.")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
