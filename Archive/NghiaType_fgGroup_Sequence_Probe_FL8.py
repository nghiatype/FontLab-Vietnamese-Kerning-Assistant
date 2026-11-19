# -*- coding: utf-8 -*-
"""NghiaType V2: fgGroup native sequence probe (FontLab 8 / Python 3.11).

EXPERIMENTAL: Save all open FontLab documents before running.
Only new, orphan fgGroup objects and a new detached fgFont are used.
No CurrentFont, no external files, no font Save/Update, no fromDict.
"""

import fontgate


def describe(label, group):
    print("\n{}".format(label))
    print("type:", type(group).__name__)
    print("repr:", repr(group))
    try:
        print("members:", [group[i] for i in range(len(group))])
    except Exception as exc:
        print("members error:", type(exc).__name__, str(exc))


def orphan_group():
    group = fontgate.fgGroup()
    group.name = "NT_V2_SEQUENCE_TEST"
    group.mode = "KernLeftGroupMode"
    return group


def attempt(label, operation):
    print("\nTRY:", label)
    group = orphan_group()
    try:
        result = operation(group)
        if result is None:
            result = group
        describe("After operation", result)
    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))


def main():
    print("=== NGHIATYPE fgGroup SEQUENCE PROBE / DETACHED / FL8 ===")
    print("No CurrentFont, no files, no Save/Update")

    try:
        font = fontgate.fgFont("NT V2 Sequence Probe")
        if getattr(font, "path", "") or list(font.groups.items()):
            print("ABORT: test font not empty/unsaved")
            return
        glyph_a = font.createGlyph("A")
        glyph_b = font.createGlyph("Aacute")
        ids = [glyph_a.id, glyph_b.id]
        print("Synthetic glyph IDs:", ids)
    except Exception as exc:
        print("ABORT:", type(exc).__name__, str(exc))
        return

    print("\n--- AVAILABLE SEQUENCE METHODS ---")
    group = orphan_group()
    for name in ("__setslice__", "__add__", "__iadd__", "__setitem__", "append", "extend", "insert"):
        method = getattr(group, name, None)
        print("{}: {}".format(name, "YES" if callable(method) else "NO"))

    if callable(getattr(group, "__setslice__", None)):
        attempt("direct __setslice__(0, 0, IDs)", lambda g: g.__setslice__(0, 0, ids))
        attempt("direct __setslice__(0, 0, names)", lambda g: g.__setslice__(0, 0, ["A", "Aacute"]))

    if callable(getattr(group, "__add__", None)):
        attempt("group + list(IDs)", lambda g: g + ids)
        attempt("group + tuple(IDs)", lambda g: g + tuple(ids))
        attempt("group + list(names)", lambda g: g + ["A", "Aacute"])

    if callable(getattr(group, "__iadd__", None)):
        attempt("direct __iadd__(list IDs)", lambda g: g.__iadd__(ids))

    if callable(getattr(group, "append", None)):
        attempt("append ID", lambda g: (g.append(ids[0]), g)[1])

    if callable(getattr(group, "extend", None)):
        attempt("extend list IDs", lambda g: (g.extend(ids), g)[1])

    print("\n=== END / ALL OBJECTS DETACHED ===")


if __name__ == "__main__":
    main()
