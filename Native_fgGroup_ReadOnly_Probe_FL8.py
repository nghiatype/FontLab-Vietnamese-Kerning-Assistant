# -*- coding: utf-8 -*-
"""NghiaType Native Kerning V2 - fgGroup READ-ONLY probe (18 Nov 2026).

Run inside FontLab 8 > Scripting with a font containing native kerning classes.
This diagnostic does not call constructors, setters, save, update, or addGroup.
It does not write files. It inspects at most two entries per collection.
"""

import sys

import fontlab


MAX_GROUPS_PER_SOURCE = 2
MAX_SEQUENCE_MEMBERS = 5
MAX_REPR_LENGTH = 240


def short_repr(value):
    try:
        result = repr(value)
    except Exception as exc:
        return "<repr failed: {}>".format(exc)
    return result[:MAX_REPR_LENGTH] + ("..." if len(result) > MAX_REPR_LENGTH else "")


def describe(value, label, depth=0):
    """Inspect one object; all access operations are read-only."""
    prefix = "  " * depth
    print("{}{}".format(prefix, label))
    print("{}  type: {}.{}".format(prefix, type(value).__module__, type(value).__name__))
    print("{}  repr: {}".format(prefix, short_repr(value)))

    if value is None:
        return

    if type(value).__name__ == "fgGroup":
        # These are documented read-only observations of an existing fgGroup.
        for name in ("id", "name", "mode"):
            try:
                print("{}  {}: {}".format(prefix, name, short_repr(getattr(value, name))))
            except Exception as exc:
                print("{}  {}: ERROR {}".format(prefix, name, exc))

        for name in ("isLeft", "isRight", "isBoth", "isFeaGroup"):
            try:
                print("{}  {}(): {}".format(prefix, name, short_repr(getattr(value, name)())))
            except Exception as exc:
                print("{}  {}(): ERROR {}".format(prefix, name, exc))

        try:
            print("{}  public_names: {}".format(
                prefix, [n for n in dir(value) if not n.startswith("_")]
            ))
        except Exception as exc:
            print("{}  dir: ERROR {}".format(prefix, exc))

        try:
            length = len(value)
            print("{}  len: {}".format(prefix, length))
            for i in range(min(length, MAX_SEQUENCE_MEMBERS)):
                try:
                    member = value[i]
                    print("{}  [{}]: {} ({})".format(
                        prefix, i, short_repr(member), type(member).__name__
                    ))
                except Exception as exc:
                    print("{}  [{}]: ERROR {}".format(prefix, i, exc))
        except Exception as exc:
            print("{}  len: ERROR {}".format(prefix, exc))

    elif depth < 2 and isinstance(value, (tuple, list)):
        for i, member in enumerate(value[:2]):
            describe(member, "element[{}]".format(i), depth + 1)


def inspect_collection(font, label, collection):
    print("\n=== {} ===".format(label))
    if collection is None:
        print("Not available on this FontLab object")
        return

    print("collection type: {}.{}".format(
        type(collection).__module__, type(collection).__name__
    ))

    # items() is a documented read method for both fgGroups and fgKerningGroups.
    try:
        items = collection.items()
        iterator = iter(items)
    except Exception as exc:
        print("items() unavailable: {}: {}".format(type(exc).__name__, exc))
        print("available public names: {}".format(
            [name for name in dir(collection) if not name.startswith("_")]
        ))
        return

    count = 0
    for item in iterator:
        if count >= MAX_GROUPS_PER_SOURCE:
            break
        describe(item, "item[{}]".format(count))
        count += 1
    print("sampled entries: {}".format(count))


def main():
    print("=== NGHIATYPE fgGroup READ-ONLY PROBE / FL8 ===")
    print("Python: {}".format(sys.version.split()[0]))
    print("No constructors, mutators, file writes, save or update are used.")

    try:
        font = fontlab.CurrentFont()
    except Exception as exc:
        print("Cannot get current font: {}: {}".format(type(exc).__name__, exc))
        return

    if font is None:
        print("Please open and activate a test font containing native classes.")
        return

    print("CurrentFont type: {}.{}".format(
        type(font).__module__, type(font).__name__
    ))

    try:
        font_groups = font.groups
    except Exception as exc:
        print("font.groups access error: {}: {}".format(type(exc).__name__, exc))
        font_groups = None

    try:
        kerning_groups = font.kerning.groups
    except Exception as exc:
        print("font.kerning.groups access error: {}: {}".format(
            type(exc).__name__, exc
        ))
        kerning_groups = None

    inspect_collection(font, "font.groups (fgGroups)", font_groups)
    inspect_collection(font, "font.kerning.groups (fgKerningGroups)", kerning_groups)
    print("\n=== FINISHED / READ ONLY ===")
    print("If this output contains client names, redact them before sharing.")


if __name__ == "__main__":
    main()
