# -*- coding: utf-8 -*-
#FLM: NghiaType Native Group Dictionary Test (ALPHA)
"""Try the documented fgGroup + fgGroups.fromDict route on a detached font.

SAVE ALL OPEN DOCUMENTS FIRST: this uses native APIs inside FontLab.

This script changes only a NEW, UNSAVED fgFont object created in memory.
It never calls CurrentFont(), currentPackage, or any live document method.
Nothing is written to disk. This is NOT Native Apply for an open font.

FontLab documented API:
  fgFont('name') -> new, empty font
  fgGlyph('name') -> new glyph
  fgGroup((name, list(glyph_ids), group_mode, main_glyph_name))
  fgGroups.fromDict(dict(name=fgGroup))
"""

from __future__ import print_function

import json
import sys
import traceback


def _build_report():
    import fontgate

    result = {
        "tool": "NghiaType Native Group Dictionary Test 0.1 / ALPHA",
        "python": sys.version.split()[0],
        "font_is_new_detached_object": True,
        "live_font_accessed": False,
        "files_written": False,
        "apply_available": False,
    }
    temp_font = fontgate.fgFont("NghiaType_Unsaved_GroupDict_Test")
    if type(temp_font).__name__ != "fgFont":
        raise TypeError("Not a detached fgFont object")

    for name in ("A", "Aacute"):
        temp_font.addGlyph(fontgate.fgGlyph(name))
    if set(temp_font.keys()) != {"A", "Aacute"}:
        raise RuntimeError("Detached font should contain exactly two test glyphs")

    font_group_dict = temp_font.groups.asDict()
    kerning_group_dict = temp_font.kerning.groups.asDict()
    if not isinstance(font_group_dict, dict) or font_group_dict:
        raise RuntimeError("Detached font groups must be initially empty")
    if not isinstance(kerning_group_dict, dict) or kerning_group_dict:
        raise RuntimeError("Detached kerning groups must be initially empty")

    glyph_ids = [int(temp_font[name].id) for name in ("A", "Aacute")]
    result["temporary_glyph_ids"] = glyph_ids
    result["glyph_names"] = ["A", "Aacute"]
    result["mode"] = "KernLeftGroupMode"
    result["class_name"] = "NghiaTypeTestLeft"

    try:
        group = fontgate.fgGroup((
            "NghiaTypeTestLeft",
            glyph_ids,
            "KernLeftGroupMode",
            "A",
        ))
        result["group_constructor"] = "ok"
        result["group_mode_readback"] = str(group.mode)
        result["group_is_left"] = bool(group.isLeft())
    except Exception as exc:
        result["group_constructor"] = "failed"
        result["constructor_error_type"] = type(exc).__name__
        result["constructor_error"] = str(exc)[:700]
        return result

    try:
        write_result = temp_font.groups.fromDict({"NghiaTypeTestLeft": group})
        result["from_dict_call"] = "returned"
        result["from_dict_return_type"] = type(write_result).__name__
        if isinstance(write_result, (bool, int, float, str, type(None))):
            result["from_dict_return"] = write_result
    except Exception as exc:
        result["from_dict_call"] = "failed"
        result["from_dict_error_type"] = type(exc).__name__
        result["from_dict_error"] = str(exc)[:700]
        return result

    after_font_groups = temp_font.groups.asDict()
    after_kern_groups = temp_font.kerning.groups.asDict()
    class_name = "NghiaTypeTestLeft"
    result["font_groups_after"] = len(after_font_groups)
    result["kerning_groups_after"] = len(after_kern_groups)
    result["in_font_groups"] = class_name in after_font_groups
    result["in_native_kerning_groups"] = class_name in after_kern_groups
    if class_name in after_kern_groups:
        record = after_kern_groups[class_name]
        if isinstance(record, (tuple, list)) and len(record) == 2:
            members, mode = record
            result["native_members"] = list(members)
            result["native_mode"] = str(mode)
            result["exact_membership_readback"] = (
                set(members) == {"A", "Aacute"}
                and str(mode) in ("KernLeft", "KernLeftGroupMode")
            )
        else:
            result["unexpected_kerning_record_type"] = type(record).__name__
    return result


def main():
    print("=== NGHIATYPE NATIVE GROUP DICT TEST / ALPHA ===")
    print("WARNING: Save all open documents before running native experiments.")
    try:
        report = _build_report()
        print("NATIVE_GROUP_DICT_JSON_BEGIN")
        print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
        print("NATIVE_GROUP_DICT_JSON_END")
        print("DONE: Detached temporary font only; no file writes or saves.")
    except Exception:
        print("STOP: No live document access or file writes were attempted.")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
