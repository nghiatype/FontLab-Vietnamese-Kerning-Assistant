# -*- coding: utf-8 -*-
"""NghiaType Native Kerning V2 - detached writer alpha, 18 Nov 2026.

EXPERIMENTAL. Run inside FontLab 8's Scripting panel only.
Save any open documents BEFORE running experiments with native APIs.

This script creates a NEW fgFont in memory; it never calls CurrentFont(),
never accesses an open font, and never saves or writes files. It tests:
  1) Creating three synthetic glyphs on the detached font.
  2) Constructing an fgGroup from glyph IDs (then names if needed).
  3) Writing that one group with fgGroups.fromDict().
  4) Reading the group back and replacing it with a 3-member version.

`fromDict` and `fgGroup` are DOCUMENTED, but this workflow is NOT YET TESTED
on FontLab 8. Native API bugs could still make FontLab unstable.
"""

import sys

import fontgate


TEST_FONT_NAME = "NghiaType V2 Detached Memory Test"
TEST_GROUP_KEY = "NT_V2_TEST_LEFT"
GLYPH_NAMES = ("A", "Aacute", "Agrave")
MODE = "KernLeftGroupMode"


def announce(text):
    print("\n--- {} ---".format(text))


def group_members(group):
    return [group[i] for i in range(len(group))]


def exact_readback(detached_font, expected):
    records = dict(detached_font.groups.items())
    print("Group keys:", sorted(records))
    if list(records) != [TEST_GROUP_KEY]:
        print("READBACK MISMATCH: unexpected group dictionary")
        return False

    group = records[TEST_GROUP_KEY]
    print("Group object:", repr(group))
    print("Group mode:", group.mode)
    print("Group isLeft():", group.isLeft())
    actual = group_members(group)
    print("Group members:", actual)
    native_good = (actual == list(expected) and group.isLeft())

    try:
        kern_records = dict(detached_font.kerning.groups.items())
        kern_value = kern_records.get(TEST_GROUP_KEY)
        print("Kerning groups view:", repr(kern_value))
        kerning_good = bool(
            isinstance(kern_value, tuple)
            and len(kern_value) == 2
            and list(kern_value[0]) == list(expected)
            and kern_value[1] == "KernLeft"
        )
    except Exception as exc:
        print("Kerning groups view error:", type(exc).__name__, str(exc))
        kerning_good = False

    print("Native fgGroups:", "EXACT MATCH" if native_good else "MISMATCH")
    print("Kerning groups:", "EXACT MATCH" if kerning_good else "MISMATCH")
    return native_good and kerning_good


def make_group(detached_glyphs, names, preferred_kind=None):
    """Try only two evidence-based constructor shapes, on detached data."""
    constructors = []

    ids = [getattr(detached_glyphs[name], "id", None) for name in names]
    if len(set(ids)) == len(ids) and all(type(value) is int and value >= 0 for value in ids):
        constructors.append(("glyph_ids", ids))
    else:
        print("Glyph IDs unavailable or invalid:", ids)

    constructors.append(("glyph_names", list(names)))
    if preferred_kind:
        constructors.sort(key=lambda entry: entry[0] != preferred_kind)

    for kind, values in constructors:
        print("Constructor attempt:", kind, repr(values))
        try:
            group = fontgate.fgGroup((TEST_GROUP_KEY, values, MODE, names[0]))
            print("Constructor result:", repr(group))
            print("Constructed group members:", group_members(group))
            return group, kind
        except Exception as exc:
            print("Constructor error:", type(exc).__name__, str(exc))

    return None, None


def main():
    print("=== NGHIATYPE NATIVE WRITER / DETACHED ALPHA / FL8 ===")
    print("Python:", sys.version.split()[0])
    print("EXP: fgGroup constructor + fgGroups.fromDict")
    print("SAFETY: never calls CurrentFont; no Save/Update/file writes")

    announce("1. CREATE BRAND-NEW DETACHED FONT")
    try:
        font = fontgate.fgFont(TEST_FONT_NAME)
        print("Font:", repr(font))
        print("Font type:", type(font).__name__)
        path = getattr(font, "path", "")
        print("Font path is empty:", not bool(path))
        if path or list(font.groups.items()):
            print("ABORT: test object is not an empty, unsaved font")
            return
    except Exception as exc:
        print("ABORT at font creation:", type(exc).__name__, str(exc))
        return

    announce("2. CREATE SYNTHETIC GLYPHS")
    glyphs = {}
    try:
        for name in GLYPH_NAMES:
            glyph = font.createGlyph(name)
            if glyph is None or glyph.name != name:
                print("ABORT: glyph creation returned unexpected value for", name)
                return
            glyphs[name] = glyph
            print("Glyph:", glyph.name, "id:", getattr(glyph, "id", None))
    except Exception as exc:
        print("ABORT at glyph creation:", type(exc).__name__, str(exc))
        return

    announce("3. CONSTRUCT INITIAL 2-MEMBER GROUP")
    initial_group, successful_kind = make_group(glyphs, GLYPH_NAMES[:2])
    if initial_group is None:
        print("STOP: no working fgGroup constructor found")
        return

    announce("4. WRITE INITIAL GROUP TO DETACHED FONT")
    try:
        font.groups.fromDict({TEST_GROUP_KEY: initial_group})
    except Exception as exc:
        print("STOP: fromDict error:", type(exc).__name__, str(exc))
        return
    if not exact_readback(font, GLYPH_NAMES[:2]):
        print("STOP: initial readback not verified")
        return

    announce("5. REPLACE GROUP WITH 3 MEMBERS (DETACHED ONLY)")
    expanded_group, _ = make_group(glyphs, GLYPH_NAMES, successful_kind)
    if expanded_group is None:
        print("STOP: unable to construct replacement group")
        return

    try:
        font.groups.fromDict({TEST_GROUP_KEY: expanded_group})
    except Exception as exc:
        print("STOP: replacement fromDict error:", type(exc).__name__, str(exc))
        return
    if not exact_readback(font, GLYPH_NAMES):
        print("STOP: replacement readback not verified")
        return

    announce("SUCCESS: DETACHED WRITE + UPDATE + EXACT READBACK")
    print("This is NOT proof of safe Apply to an open font, or Save/Reopen.")


if __name__ == "__main__":
    main()
