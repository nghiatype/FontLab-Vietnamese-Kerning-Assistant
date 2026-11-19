# -*- coding: utf-8 -*-
"""NghiaType Native Kerning V2 - guarded ONE-membership Apply, FL8 ALPHA.

Not part of V1 Stable. PREVIEW ONLY by default.
For a disposable .vfc/.vfb COPY, never an original/client master file.

PREVIEW: Set TARGET_GROUP_KEY and GLYPH_TO_ADD, run, inspect all checks.
APPLY: Save As a separate font COPY whose filename contains 'copy', then set
       APPLY_CHANGES=True and I_CONFIRM_TEST_COPY=True and run again.
       Inspect the exact readback and pair preservation BEFORE saving the copy.
       On ANY mismatch, CLOSE THE COPY WITHOUT SAVING.
       After success, save/close/reopen the COPY and run PREVIEW again.

This script intentionally does NOT save, export, write backup files, or touch
OpenType kern. Its only possible write is one Native class on an opted-in COPY.
"""

import ntpath

import fontlab


# -------------------------- USER CONFIGURATION --------------------------
TARGET_GROUP_KEY = "A"       # Example: 'A' (choose from Native Preview)
GLYPH_TO_ADD = "aacute"           # Example: 'Agrave' (must be truly missing)

APPLY_CHANGES = False       # Default: NEVER write
I_CONFIRM_TEST_COPY = False
COPY_FILENAME_MARKER = "copy"
# ------------------------------------------------------------------------


def sides(mode):
    """Fail closed if FL reports an unexpected mode."""
    recognized = {
        "KernLeft": frozenset(("L",)),
        "KernRight": frozenset(("R",)),
        "KernBothSide": frozenset(("L", "R")),
        "KernBoth": frozenset(("L", "R")),
    }
    if mode not in recognized:
        raise ValueError("Unrecognized native kerning group mode: " + repr(mode))
    return recognized[mode]


def groups_snapshot(font):
    return {
        key: (tuple(member_names), mode)
        for key, (member_names, mode) in font.kerning.groups.items()
    }


def pairs_snapshot(font):
    """Capture explicit native pairs and exceptions, not expanded kerning."""
    pairs = []
    for pair, amount in font.kerning.items():
        # fgKerningObjectPair left/right carry glyph/group IDs and modes.
        entry = (
            str(pair.left.id), str(pair.left.mode),
            str(pair.right.id), str(pair.right.mode),
            float(amount),
        )
        pairs.append(entry)
    return tuple(sorted(pairs))


def native_target_readback(font, key, expected_members, mode):
    native = dict(font.groups.items()).get(key)
    if native is None:
        print("NATIVE READBACK: group key missing")
        return False
    members = tuple(native[i] for i in range(len(native)))
    print("NATIVE READBACK MEMBERS:", members)
    if members != expected_members:
        return False
    expected_sides = sides(mode)
    return native.isLeft() == ("L" in expected_sides) and native.isRight() == ("R" in expected_sides)


def main():
    print("=== NGHIATYPE NATIVE GUARDED APPLY / COPY / FL8 ALPHA ===")
    print("MODE:", "GUARDED APPLY" if APPLY_CHANGES else "PREVIEW ONLY")
    if not TARGET_GROUP_KEY or not GLYPH_TO_ADD:
        print("STOP: set TARGET_GROUP_KEY and GLYPH_TO_ADD first")
        return

    try:
        font = fontlab.CurrentFont()
        if font is None:
            print("STOP: no active font")
            return
        path = getattr(font, "path", "") or ""
        filename = ntpath.basename(path)
        original_groups = groups_snapshot(font)
        original_pairs = pairs_snapshot(font)
        glyph_names = set(font.keys())
    except Exception as exc:
        print("STOP: cannot capture read-only baseline:", type(exc).__name__, str(exc))
        return

    print("Active filename:", filename or "<UNSAVED>")
    print("Native classes:", len(original_groups))
    print("Explicit native pairs/exceptions:", len(original_pairs))

    if TARGET_GROUP_KEY not in original_groups:
        print("STOP: requested group key not found")
        return
    if GLYPH_TO_ADD not in glyph_names:
        print("STOP: requested glyph not present in font")
        return

    old_members, target_mode = original_groups[TARGET_GROUP_KEY]
    print("Target class:", repr(TARGET_GROUP_KEY))
    print("Target mode:", target_mode)
    print("Original members:", old_members)
    try:
        target_sides = sides(target_mode)
        conflicts = []
        for key, (members, mode) in original_groups.items():
            if key == TARGET_GROUP_KEY:
                continue
            if GLYPH_TO_ADD in members and target_sides.intersection(sides(mode)):
                conflicts.append((key, mode))
    except Exception as exc:
        print("STOP: unable to verify side conflicts:", type(exc).__name__, str(exc))
        return

    if GLYPH_TO_ADD in old_members:
        print("NO CHANGE: glyph already belongs to this class")
        return
    if conflicts:
        print("STOP: glyph already belongs to conflicting native class(es):", conflicts)
        return

    proposed = old_members + (GLYPH_TO_ADD,)
    print("PROPOSED MEMBERS:", proposed)
    print("CONFLICTS: 0")

    if not APPLY_CHANGES:
        print("PREVIEW READY: no changes made")
        print("Apply requires BOTH flags and a saved filename containing 'copy'.")
        return

    if not I_CONFIRM_TEST_COPY:
        print("STOP: I_CONFIRM_TEST_COPY is False")
        return
    if not filename or COPY_FILENAME_MARKER not in filename.lower():
        print("STOP: active font filename does not contain 'copy'")
        return

    print("\n--- GUARDED APPLY: ONE EXISTING CLASS ---")
    try:
        font.kerning.groups[TARGET_GROUP_KEY] = (list(proposed), target_mode)
    except Exception as exc:
        print("APPLY ERROR:", type(exc).__name__, str(exc))
        print("CLOSE COPY WITHOUT SAVING")
        return

    try:
        actual_groups = groups_snapshot(font)
        actual_pairs = pairs_snapshot(font)
        expected_groups = dict(original_groups)
        expected_groups[TARGET_GROUP_KEY] = (proposed, target_mode)
        all_groups_match = actual_groups == expected_groups
        all_pairs_match = actual_pairs == original_pairs
        native_match = native_target_readback(font, TARGET_GROUP_KEY, proposed, target_mode)
        print("ALL NATIVE GROUPS:", "EXACT MATCH" if all_groups_match else "MISMATCH")
        print("EXPLICIT PAIRS/EXCEPTIONS:", "UNCHANGED" if all_pairs_match else "CHANGED")
        print("TARGET fgGroup:", "EXACT MATCH" if native_match else "MISMATCH")
        if all_groups_match and all_pairs_match and native_match:
            print("SUCCESS: GUARDED APPLY + EXACT READBACK (NOT YET SAVED)")
            print("Review kerning behavior, then manually Save/Reopen the COPY.")
        else:
            print("FAIL: CLOSE THE COPY WITHOUT SAVING")
    except Exception as exc:
        print("READBACK ERROR:", type(exc).__name__, str(exc))
        print("CLOSE THE COPY WITHOUT SAVING")


if __name__ == "__main__":
    main()
