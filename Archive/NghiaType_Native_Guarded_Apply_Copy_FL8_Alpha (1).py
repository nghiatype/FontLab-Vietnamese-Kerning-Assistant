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

V0.2: access package.kerning(current_master), matching the verified Native
Class Preview. fgFont.kerning may be empty even when the master has 50 classes.
"""

import ntpath

import fontlab


# -------------------------- USER CONFIGURATION --------------------------
TARGET_GROUP_KEY = "A"
GLYPH_TO_ADD = "aacute"

# Fingerprint of the verified Native Preview output on the test font.
EXPECTED_MASTER = "Regular"
EXPECTED_GLYPH_COUNT = 384
EXPECTED_CLASS_COUNT = 50
EXPECTED_TARGET_MEMBERS = 15

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


def current_package(font):
    """Use the same owner/master resolution as Native Class Preview Alpha."""
    try:
        package = fontlab.flWorkspace.instance().currentPackage
        if package is not None:
            return package
    except Exception:
        pass
    return fontlab.flPackage(font)


def groups_snapshot(kerning):
    return {
        key: (tuple(member_names), mode)
        for key, (member_names, mode) in kerning.groups.asDict().items()
    }


def pairs_snapshot(kerning):
    """Capture explicit native pairs and exceptions, not expanded kerning."""
    pairs = []
    for pair, amount in kerning.items():
        # fgKerningObjectPair left/right carry glyph/group IDs and modes.
        entry = (
            str(pair.left.id), str(pair.left.mode),
            str(pair.right.id), str(pair.right.mode),
            float(amount),
        )
        pairs.append(entry)
    return tuple(sorted(pairs))


def native_target_readback(kerning, key, expected_members, mode):
    """Independent direct key lookup in the SAME current-master object."""
    try:
        value = kerning.groups[key]
        print("DIRECT MASTER GROUP READBACK:", repr(value))
        return (
            isinstance(value, tuple)
            and len(value) == 2
            and tuple(value[0]) == expected_members
            and value[1] == mode
        )
    except Exception as exc:
        print("DIRECT MASTER GROUP READBACK ERROR:", type(exc).__name__, str(exc))
        return False


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
        package = current_package(font)
        master = str(package.getLayerName())
        master_kerning = package.kerning(master)
        original_groups = groups_snapshot(master_kerning)
        original_pairs = pairs_snapshot(master_kerning)
        glyph_names = set(font.keys())
    except Exception as exc:
        print("STOP: cannot capture read-only baseline:", type(exc).__name__, str(exc))
        return

    print("Active filename:", filename or "<UNSAVED>")
    print("Active master:", master)
    print("Font glyphs:", len(glyph_names))
    print("Native classes:", len(original_groups))
    print("Explicit native pairs/exceptions:", len(original_pairs))

    if (master != EXPECTED_MASTER
            or len(glyph_names) != EXPECTED_GLYPH_COUNT
            or len(original_groups) != EXPECTED_CLASS_COUNT):
        print("STOP: font/master fingerprint differs from verified Native Preview")
        return

    if TARGET_GROUP_KEY not in original_groups:
        print("STOP: requested group key not found")
        return
    if GLYPH_TO_ADD not in glyph_names:
        print("STOP: requested glyph not present in font")
        return

    old_members, target_mode = original_groups[TARGET_GROUP_KEY]
    if len(old_members) != EXPECTED_TARGET_MEMBERS:
        print("STOP: target class size differs from verified Native Preview")
        return
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
        master_kerning.groups[TARGET_GROUP_KEY] = (list(proposed), target_mode)
    except Exception as exc:
        print("APPLY ERROR:", type(exc).__name__, str(exc))
        print("CLOSE COPY WITHOUT SAVING")
        return

    try:
        actual_groups = groups_snapshot(master_kerning)
        actual_pairs = pairs_snapshot(master_kerning)
        expected_groups = dict(original_groups)
        expected_groups[TARGET_GROUP_KEY] = (proposed, target_mode)
        all_groups_match = actual_groups == expected_groups
        all_pairs_match = actual_pairs == original_pairs
        native_match = native_target_readback(master_kerning, TARGET_GROUP_KEY, proposed, target_mode)
        print("ALL NATIVE GROUPS:", "EXACT MATCH" if all_groups_match else "MISMATCH")
        print("EXPLICIT PAIRS/EXCEPTIONS:", "UNCHANGED" if all_pairs_match else "CHANGED")
        print("DIRECT MASTER GROUP:", "EXACT MATCH" if native_match else "MISMATCH")
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
