# -*- coding: utf-8 -*-
#FLM: NghiaType Native Detached Writer Test (ALPHA)
"""Test native fgKerning.addGroup on a brand-new, UNSAVED font in memory.

IMPORTANT: Save ALL open FontLab documents before running this experimental
native-API test. An undocumented native binding could raise an exception or
in the worst case destabilize the FontLab process.

This script DOES mutate the newly constructed *detached* fgFont object.
It NEVER requests CurrentFont(), currentPackage, or a live flPackage; it does
not edit an open font and never writes any file. It does not test Native Apply.
"""

from __future__ import print_function

import json
import sys
import traceback


GLYPHS = ("A", "Aacute")
TEST_CASES = (
    ("name_members_kernleft", "KernLeft"),
    ("name_members_fullmode", "KernLeftGroupMode"),
    ("name_members_shortmode", "L"),
)


def _new_detached_font(fontgate):
    font = fontgate.fgFont("NghiaType_Detached_API_Test_UNSAVED")
    if type(font).__name__ != "fgFont":
        raise TypeError("Unexpected detached font type")
    for name in GLYPHS:
        font.addGlyph(fontgate.fgGlyph(name))
    names = set(font.keys())
    if not all(name in names for name in GLYPHS):
        raise RuntimeError("Temporary glyph initialization failed")
    groups_before = font.kerning.groups.asDict()
    if not isinstance(groups_before, dict) or groups_before:
        raise RuntimeError("Detached font must start with zero kerning groups")
    return font


def _clean_group_record(record):
    if not isinstance(record, (tuple, list)) or len(record) != 2:
        return {"shape": type(record).__name__}
    members, mode = record
    return {
        "members": [str(item) for item in members],
        "mode": str(mode),
    }


def _test_one(fontgate, index, label, mode):
    report = {"case": label, "mode_argument": mode}
    temp_font = _new_detached_font(fontgate)
    name = "NghiaTypeTmpLeft{}".format(index)
    try:
        result = temp_font.kerning.addGroup(name, list(GLYPHS), mode)
        report["call_return_type"] = type(result).__name__
        if isinstance(result, (str, int, float, bool, type(None))):
            report["call_return"] = result
        after = temp_font.kerning.groups.asDict()
        report["group_count_after"] = len(after)
        report["group_found"] = name in after
        if name in after:
            report["readback"] = _clean_group_record(after[name])
            record = report["readback"]
            report["exact_glyphs_readback"] = (
                set(record.get("members", ())) == set(GLYPHS)
            )
        else:
            report["exact_glyphs_readback"] = False
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error_message"] = str(exc)[:900]
        report["exact_glyphs_readback"] = False
    return report


def main():
    print("=== NGHIATYPE NATIVE DETACHED WRITER TEST / ALPHA ===")
    print("WARNING: Save open documents before any experimental native call.")
    try:
        import fontgate

        results = []
        for index, (label, mode) in enumerate(TEST_CASES, 1):
            result = _test_one(fontgate, index, label, mode)
            results.append(result)
            if result.get("exact_glyphs_readback"):
                break

        report = {
            "tool": "NghiaType Native Detached Writer Test 0.1 / ALPHA",
            "python": sys.version.split()[0],
            "detached_object_type": "fgFont",
            "temp_glyphs": list(GLYPHS),
            "cases": results,
            "native_call_on_temporary_font": True,
            "current_font_accessed": False,
            "files_written": False,
            "apply_available": False,
            "writer_signature_supported": any(
                row.get("exact_glyphs_readback") for row in results
            ),
        }
        print("NATIVE_DETACHED_TEST_JSON_BEGIN")
        print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
        print("NATIVE_DETACHED_TEST_JSON_END")
        print("DONE: Temporary font object discarded; no files saved.")
    except Exception:
        print("STOP: Detached test could not be completed.")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
