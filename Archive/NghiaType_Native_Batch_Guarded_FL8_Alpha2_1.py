# -*- coding: utf-8 -*-
#FLM: NghiaType Native Batch Guarded (COPY / PREVIEW default)
"""NghiaType Native Kerning V2 - guarded BATCH ALPHA.2.1 for FontLab 8.

Diagnostic update: print current class state BEFORE the baseline guard.
No baseline protections have been relaxed.

Starting point: verified TANVariety-Regular Copy.vfc, after the one-glyph
A + aacute Apply and a successful manual Save/Close/Reopen.

PREVIEW ONLY by default. NEVER use on the original/client source file.
For APPLY, make ANOTHER disposable file named with BOTH 'copy' and 'batch',
then review a Preview run before enabling both flags below.

This script uses the verified package.kerning(current_master).groups API.
It modifies only the current master's native kerning groups, never OpenType
features. It does not Save, Update, export, create backups, or write files.

If ANY apply/readback failure occurs, CLOSE THE BATCH COPY WITHOUT SAVING.
"""

import ntpath
import fontlab

# ------------------------ CONFIG ------------------------
APPLY_CHANGES = False
I_CONFIRM_BATCH_COPY = False

EXPECTED_MASTER = "Regular"
EXPECTED_GLYPH_COUNT = 384
EXPECTED_CLASS_COUNT = 50
EXPECTED_EXPLICIT_PAIR_COUNT = 2267

# Remaining six memberships after the verified A + aacute save/reopen.
TARGETS = {
    "A": ("abreve", "acircumflex", "agrave", "atilde"),
    "Q": ("Ograve",),
    "Q2": ("Ograve",),
}
EXPECTED_MODES = {"A": "KernLeft", "Q": "KernLeft", "Q2": "KernRight"}
BASE_MEMBERS_COUNTS = {"A": 16, "Q": 20, "Q2": 23}

# Independently verified original class A membership list AFTER A+aacute.
BASE_A = (
    "A", "Aacute", "Abreve", "Acircumflex", "Adieresis", "Agrave",
    "Amacron", "Aogonek", "Aring", "Atilde", "E_A", "H_A",
    "L_A", "L_A.001", "a", "aacute",
)
# --------------------------------------------------------


def sides(mode):
    mapping = {
        "KernLeft": frozenset(("L",)),
        "KernRight": frozenset(("R",)),
        "KernBoth": frozenset(("L", "R")),
        "KernBothSide": frozenset(("L", "R")),
    }
    if mode not in mapping:
        raise ValueError("Unknown native mode: " + repr(mode))
    return mapping[mode]


def current_package(font):
    try:
        p = fontlab.flWorkspace.instance().currentPackage
        if p is not None:
            return p
    except Exception:
        pass
    return fontlab.flPackage(font)


def groups_snapshot(kerning):
    return {
        key: (tuple(names), mode)
        for key, (names, mode) in kerning.groups.asDict().items()
    }


def pairs_snapshot(kerning):
    rows = []
    for pair, amount in kerning.items():
        rows.append((
            str(pair.left.id), str(pair.left.mode),
            str(pair.right.id), str(pair.right.mode), float(amount),
        ))
    return tuple(sorted(rows))


def direct_group_matches(kerning, key, expected):
    value = kerning.groups[key]
    return (isinstance(value, tuple) and len(value) == 2
            and (tuple(value[0]), value[1]) == expected)


def main():
    print("=== NGHIATYPE NATIVE BATCH / FL8 ALPHA.2.1 ===")
    print("MODE:", "GUARDED BATCH APPLY" if APPLY_CHANGES else "PREVIEW ONLY")
    try:
        font = fontlab.CurrentFont()
        if font is None:
            print("STOP: no active font")
            return
        filename = ntpath.basename(getattr(font, "path", "") or "")
        package = current_package(font)
        master = str(package.getLayerName())
        kerning = package.kerning(master)
        before_groups = groups_snapshot(kerning)
        before_pairs = pairs_snapshot(kerning)
        font_glyphs = set(font.keys())
    except Exception as exc:
        print("STOP: failed to read baseline:", type(exc).__name__, str(exc))
        return

    print("Active filename:", filename or "<UNSAVED>")
    print("Active master:", master)
    print("Glyphs:", len(font_glyphs))
    print("Native classes:", len(before_groups))
    print("Explicit native pairs/exceptions:", len(before_pairs))

    if (master != EXPECTED_MASTER
            or len(font_glyphs) != EXPECTED_GLYPH_COUNT
            or len(before_groups) != EXPECTED_CLASS_COUNT
            or len(before_pairs) != EXPECTED_EXPLICIT_PAIR_COUNT):
        print("STOP: master/font/kerning fingerprint differs from verified copy")
        return

    # Validate entire snapshot before any change; the writer never creates a class.
    for key, (members, mode) in before_groups.items():
        try:
            sides(mode)
        except Exception as exc:
            print("STOP: cannot validate mode for", repr(key), str(exc))
            return
        if len(members) != len(set(members)):
            print("STOP: duplicate memberships in", repr(key))
            return

    print("--- READ-ONLY BASELINE DIAGNOSTICS ---")
    for check_key in ("A", "Q", "Q2"):
        if check_key not in before_groups:
            print("CHECK", repr(check_key), "MISSING")
            continue
        check_members, check_mode = before_groups[check_key]
        check_present = [g for g in TARGETS[check_key] if g in check_members]
        check_missing = [g for g in TARGETS[check_key] if g not in check_members]
        print("CHECK", repr(check_key), "MODE", repr(check_mode),
              "MEMBER COUNT", len(check_members),
              "EXPECTED AT THIS STAGE", BASE_MEMBERS_COUNTS[check_key] + len(check_present))
        print("  already_present_targets:", check_present)
        print("  missing_targets:", check_missing)
        if check_key == "A":
            print("  has_aacute:", "aacute" in check_members)
            print("  missing_from_verified_baseline:", sorted(set(BASE_A) - set(check_members)))
            print("  extra_beyond_baseline_and_targets:",
                  sorted(set(check_members) - set(BASE_A) - set(TARGETS[check_key])))
            print("  actual_members:", list(check_members))
    print("--- END DIAGNOSTICS / NO CHANGES ---")

    expected_groups = dict(before_groups)
    pending = []
    for key in ("A", "Q", "Q2"):
        if key not in before_groups:
            print("STOP: missing group", repr(key))
            return
        old_members, mode = before_groups[key]
        if mode != EXPECTED_MODES[key]:
            print("STOP: unexpected group mode", repr(key), repr(mode))
            return
        present = [g for g in TARGETS[key] if g in old_members]
        missing = [g for g in TARGETS[key] if g not in old_members]
        if len(old_members) != BASE_MEMBERS_COUNTS[key] + len(present):
            print("STOP: unexpected member count for", repr(key),
                  "actual", len(old_members),
                  "expected", BASE_MEMBERS_COUNTS[key] + len(present))
            return
        if key == "A":
            known = set(BASE_A)
            if set(old_members) != known | set(present):
                print("STOP: class A members differ from verified baseline")
                return
        for glyph in TARGETS[key]:
            if glyph not in font_glyphs:
                print("STOP: glyph absent:", repr(glyph))
                return
            competing = []
            for other, (others, other_mode) in before_groups.items():
                if other != key and glyph in others and sides(mode) & sides(other_mode):
                    competing.append(other)
            if competing:
                print("STOP: same-side conflict:", key, glyph, competing)
                return
        planned = old_members + tuple(missing)
        expected_groups[key] = (planned, mode)
        pending.extend((key, glyph) for glyph in missing)
        print("CLASS", repr(key), "MODE", mode,
              "MEMBERS", len(old_members), "->", len(planned))
        print("  already_present:", present)
        print("  to_add:", missing)

    print("PENDING MEMBERSHIPS:", len(pending))
    print("CONFLICTS: 0")
    if not pending:
        print("ALREADY APPLIED: all six target memberships exist; no changes made")
        return
    if not APPLY_CHANGES:
        print("PREVIEW READY: no changes made")
        print("For apply: make a new saved BATCH COPY, review Output, then enable both flags")
        return

    if not I_CONFIRM_BATCH_COPY:
        print("STOP: I_CONFIRM_BATCH_COPY=False")
        return
    if not filename or "copy" not in filename.lower() or "batch" not in filename.lower():
        print("STOP: filename must contain BOTH 'copy' and 'batch'")
        return

    print("--- APPLY / NATIVE MASTER ONLY / NO SAVE ---")
    try:
        for key in ("A", "Q", "Q2"):
            if expected_groups[key] == before_groups[key]:
                continue
            members, mode = expected_groups[key]
            kerning.groups[key] = (list(members), mode)
        after_groups = groups_snapshot(kerning)
        after_pairs = pairs_snapshot(kerning)
        all_groups_match = after_groups == expected_groups
        all_pairs_match = after_pairs == before_pairs
        all_direct_match = all(
            direct_group_matches(kerning, key, expected_groups[key])
            for key in ("A", "Q", "Q2")
        )
        print("ALL NATIVE GROUPS:", "EXACT MATCH" if all_groups_match else "MISMATCH")
        print("EXPLICIT PAIRS/EXCEPTIONS:", "UNCHANGED" if all_pairs_match else "CHANGED")
        print("DIRECT GROUP READBACK:", "EXACT MATCH" if all_direct_match else "MISMATCH")
        if all_groups_match and all_pairs_match and all_direct_match:
            print("SUCCESS: guarded batch apply + exact readback (NOT YET SAVED)")
            print("Inspect class/pair behavior manually; then SAVE/CLOSE/REOPEN the BATCH COPY")
        else:
            print("FAIL: CLOSE BATCH COPY WITHOUT SAVING")
    except Exception as exc:
        print("APPLY/READBACK ERROR:", type(exc).__name__, str(exc))
        print("Partial in-memory changes are possible. CLOSE BATCH COPY WITHOUT SAVING")


if __name__ == "__main__":
    main()
