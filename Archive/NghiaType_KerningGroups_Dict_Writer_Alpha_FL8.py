# -*- coding: utf-8 -*-
"""NghiaType V2 - detached fgKerningGroups dictionary writer (FL8 alpha).

EXPERIMENTAL. Save open documents before running native API tests.
Creates ONLY a new unsaved fgFont and synthetic glyphs in memory.
No CurrentFont(), no access to client fonts, no Save/Update, no file writes.

Probe inspired by FL's documented fgKerningGroups.__setitem__ and observed
fgKerningGroups.items() form: (group_key, (glyph_name_list, mode)).
"""

import fontgate


KEY = "NT_V2_TEST_LEFT"
ALL_NAMES = ("A", "Aacute", "Agrave")


def inspect_views(font, expected):
    expected = list(expected)
    try:
        kerning_data = dict(font.kerning.groups.items())
        value = kerning_data.get(KEY)
        print("fgKerningGroups value:", repr(value))
        kerning_ok = (
            isinstance(value, tuple)
            and len(value) == 2
            and list(value[0]) == expected
            and value[1] == "KernLeft"
        )
    except Exception as exc:
        print("fgKerningGroups read error:", type(exc).__name__, str(exc))
        kerning_ok = False

    try:
        native_data = dict(font.groups.items())
        group = native_data.get(KEY)
        if group is None:
            print("fgGroups: NO GROUP FOUND")
            native_ok = False
        else:
            members = [group[i] for i in range(len(group))]
            print("fgGroup:", repr(group))
            print("fgGroup members:", members)
            print("fgGroup mode:", group.mode)
            native_ok = members == expected and group.isLeft()
    except Exception as exc:
        print("fgGroups read error:", type(exc).__name__, str(exc))
        native_ok = False

    print("KERNING VIEW:", "EXACT MATCH" if kerning_ok else "MISMATCH")
    print("NATIVE VIEW:", "EXACT MATCH" if native_ok else "MISMATCH")
    return kerning_ok and native_ok


def main():
    print("=== NGHIATYPE fgKerningGroups DICT WRITER / DETACHED ALPHA / FL8 ===")
    print("No CurrentFont; no Save/Update; no file writes")

    try:
        font = fontgate.fgFont("NT V2 Detached Dictionary Test")
        if getattr(font, "path", ""):
            print("ABORT: test font unexpectedly has a path")
            return
        if list(font.groups.items()) or list(font.kerning.groups.items()):
            print("ABORT: test font is not empty")
            return
        for name in ALL_NAMES:
            glyph = font.createGlyph(name)
            if glyph is None or glyph.name != name:
                print("ABORT: synthetic glyph creation failed for", name)
                return
    except Exception as exc:
        print("ABORT:", type(exc).__name__, str(exc))
        return

    print("Detached font:", repr(font))
    groups = font.kerning.groups
    setter = getattr(groups, "__setitem__", None)
    print("fgKerningGroups.__setitem__ available:", callable(setter))
    if not callable(setter):
        print("STOP: no dictionary writer available")
        return

    print("\n--- 1. CREATE 2-MEMBER LEFT GROUP ---")
    try:
        groups[KEY] = (["A", "Aacute"], "KernLeft")
    except Exception as exc:
        print("SETITEM ERROR:", type(exc).__name__, str(exc))
        print("STOP: no alternate argument guesses in this probe")
        return
    if not inspect_views(font, ALL_NAMES[:2]):
        print("STOP: initial readback failed; replacement skipped")
        return

    print("\n--- 2. REPLACE WITH 3 MEMBERS ---")
    try:
        groups[KEY] = (["A", "Aacute", "Agrave"], "KernLeft")
    except Exception as exc:
        print("SETITEM UPDATE ERROR:", type(exc).__name__, str(exc))
        return
    if not inspect_views(font, ALL_NAMES):
        print("STOP: update readback failed")
        return

    print("\nSUCCESS: DETACHED CREATE + UPDATE + EXACT DUAL READBACK")
    print("This does NOT verify Apply to open font or Save/Reopen.")


if __name__ == "__main__":
    main()
