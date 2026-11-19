# -*- coding: utf-8 -*-
"""NghiaType V2 - fgGroup default/copy/slice probe for FontLab 8.

EXPERIMENTAL. Save all open documents before running native API experiments.
Works only with a new, detached fgFont and new, unattached fgGroup objects.
Never uses CurrentFont(), never saves, never updates, never writes a file.

Purpose: after the 4-item tuple constructor failed, check whether the
documented default/copy constructors and sequence operations work in FL8.
"""

import sys
import fontgate


KEY = "NT_V2_PROBE_LEFT"
NAMES = ("A", "Aacute")


def safe_repr(value):
    try:
        return repr(value)
    except Exception as exc:
        return "<repr error: {}>".format(exc)


def show_group(group, title):
    print("\n{}".format(title))
    print("type:", type(group).__name__)
    print("repr:", safe_repr(group))
    for field in ("name", "mode", "id"):
        try:
            print("{}: {}".format(field, safe_repr(getattr(group, field))))
        except Exception as exc:
            print("{}: ERROR {}".format(field, exc))
    try:
        print("isLeft:", group.isLeft())
    except Exception as exc:
        print("isLeft: ERROR", str(exc))
    try:
        print("members:", [group[i] for i in range(len(group))])
    except Exception as exc:
        print("members: ERROR", str(exc))


def run():
    print("=== NGHIATYPE fgGroup DEFAULT PROBE / DETACHED / FL8 ===")
    print("Python:", sys.version.split()[0])
    print("No CurrentFont, no Save, no file writes")

    print("\n--- A. NEW DETACHED FONT ---")
    try:
        font = fontgate.fgFont("NT V2 Default Probe In Memory")
        if getattr(font, "path", "") or list(font.groups.items()):
            print("ABORT: test font is not empty and unsaved")
            return
        glyphs = {}
        for name in NAMES:
            glyphs[name] = font.createGlyph(name)
            if glyphs[name] is None or glyphs[name].name != name:
                print("ABORT: synthetic glyph creation failed")
                return
        ids = [glyphs[name].id for name in NAMES]
        print("created glyph IDs:", ids)
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc))
        return

    print("\n--- B. DEFAULT CONSTRUCTOR ---")
    try:
        empty = fontgate.fgGroup()
        show_group(empty, "fgGroup()")
    except Exception as exc:
        print("STOP at fgGroup():", type(exc).__name__, str(exc))
        return

    print("\n--- C. COPY CONSTRUCTOR (ON UNATTACHED EMPTY GROUP) ---")
    try:
        copied = fontgate.fgGroup(empty)
        show_group(copied, "fgGroup(empty)")
        print("copy_is_distinct_object:", copied is not empty)
    except Exception as exc:
        print("Copy constructor error:", type(exc).__name__, str(exc))

    print("\n--- D. INITIALIZE + INSERT MEMBERS ON UNATTACHED GROUP ---")
    candidates = (("glyph_ids", ids), ("glyph_names", list(NAMES)))
    for kind, values in candidates:
        print("\nCandidate:", kind, safe_repr(values))
        try:
            group = fontgate.fgGroup()
        except Exception as exc:
            print("Fresh empty group error:", type(exc).__name__, str(exc))
            continue

        for field, value in (("name", KEY), ("mode", "KernLeftGroupMode")):
            try:
                setattr(group, field, value)  # ONLY on unattached group
                print("set {}: OK; readback {}".format(field, safe_repr(getattr(group, field))))
            except Exception as exc:
                print("set {}: {}: {}".format(field, type(exc).__name__, exc))

        try:
            group[0:0] = values  # ONLY on unattached, newly made group
            print("slice insertion: OK")
        except Exception as exc:
            print("slice insertion:", type(exc).__name__, str(exc))

        show_group(group, "After candidate " + kind)

        # Do not call fromDict unless this group genuinely has two members
        # AND identifies itself as a left kerning group.
        try:
            suitable = len(group) == 2 and group.isLeft()
        except Exception:
            suitable = False
        if not suitable:
            print("fromDict: SKIPPED (not a valid 2-member left group)")
            continue

        print("Trying fromDict on DETACHED font only")
        try:
            font.groups.fromDict({KEY: group})
            records = dict(font.groups.items())
            stored = records.get(KEY)
            if stored is None:
                print("fromDict: NO STORED GROUP")
            else:
                show_group(stored, "Detached font readback")
                print("kerning view:", safe_repr(dict(font.kerning.groups.items()).get(KEY)))
        except Exception as exc:
            print("fromDict error:", type(exc).__name__, str(exc))
        break  # no more constructors after first eligible insertion

    print("\n=== END / DETACHED TEST ONLY ===")


if __name__ == "__main__":
    run()
