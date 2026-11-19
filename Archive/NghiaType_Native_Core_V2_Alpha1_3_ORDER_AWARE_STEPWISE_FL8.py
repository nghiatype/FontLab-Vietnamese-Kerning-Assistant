# -*- coding: utf-8 -*-
#FLM: NghiaType Native Core V2 Alpha.1.3 STEPWISE ORDER-AWARE DIAGNOSTIC
"""NghiaType Native Kerning Core V2 - ORDER-AWARE STEPWISE DIAGNOSTIC (FontLab 8).

NARROW TEST PURPOSE: test the observed FontLab insertion-order normalization on a CLEAN,
DISPOSABLE copy of TANVariety Regular with 384 glyphs / 50 classes / 2267 pairs.

PREVIEW BY DEFAULT. Apply requires both opt-in flags and an exact plan token.
On Apply, write A, Q, Q2 one by one. Verify membership integrity,
original member relative order, explicit pairs, and direct readback after EACH write. STOP on first
mismatch and print precise differences. This is not a production writer.

Never Save or Update; script does not create backup, export, or change OpenType.
Native writes are in-memory, may be partial on failure. Save documents before
experiment. If anything fails, close this TEST COPY without saving.

Do not run on client source fonts or other masters. FL9 not tested.
"""

from __future__ import print_function

import hashlib
import json
import ntpath
import re
import unicodedata
from collections import defaultdict

# -------------------------- USER CONFIG -------------------------------
APPLY_CHANGES = False
I_CONFIRM_TEST_COPY = False
EXPECTED_PLAN_TOKEN = ""  # Copy fresh token from THIS script's Preview
# Test is intentionally locked to the previously verified failing baseline.
DIAGNOSTIC_TEST_ORDER = ("A", "Q", "Q2")
EXPECTED_INITIAL_MEMBERS = {"A": 15, "Q": 20, "Q2": 23}
EXPECTED_INITIAL_MODES = {"A": "KernLeft", "Q": "KernLeft", "Q2": "KernRight"}
EXPECTED_PROPOSALS = {"A": 5, "Q": 1, "Q2": 1}
# ----------------------------------------------------------------------

BASES = "AEIOUYaeiouyDd"
SHAPES = {
    "a": ("", "\u0302", "\u0306"),
    "e": ("", "\u0302"),
    "i": ("",),
    "o": ("", "\u0302", "\u031b"),
    "u": ("", "\u031b"),
    "y": ("",),
}
TONES = ("", "\u0300", "\u0301", "\u0309", "\u0303", "\u0323")
NAME_SHAPES = {
    "a": {"", "breve", "circumflex"},
    "e": {"", "circumflex"},
    "i": {""},
    "o": {"", "circumflex", "horn"},
    "u": {"", "horn"},
    "y": {""},
}
VIET_NAME_RE = re.compile(
    r"^([AEIOUYaeiouy])(circumflex|breve|horn)?"
    r"(acute|grave|hoi|tilde|dotbelow)?$"
)
UNICODE_NAME_RE = re.compile(r"^(?:uni|u)([0-9A-Fa-f]{4,6})$")
MODE_SIDES = {
    "KernLeft": frozenset(("L",)),
    "KernRight": frozenset(("R",)),
    "KernBoth": frozenset(("L", "R")),
    "KernBothSide": frozenset(("L", "R")),
}


def codepoint_bases():
    mapping = {0x0110: "D", 0x0111: "d"}
    for letter, shapes in SHAPES.items():
        for base in (letter, letter.upper()):
            for shape in shapes:
                for tone in TONES:
                    if not shape and not tone:
                        continue
                    char = unicodedata.normalize("NFC", base + shape + tone)
                    if len(char) == 1 and char != base:
                        mapping[ord(char)] = base
    return mapping


def base_from_name(name, cp_bases):
    if name in ("Dcroat", "dcroat"):
        return name[0]
    if "." in name:
        return None
    encoded = UNICODE_NAME_RE.fullmatch(name)
    if encoded:
        return cp_bases.get(int(encoded.group(1), 16))
    match = VIET_NAME_RE.fullmatch(name)
    if match is None:
        return None
    base, shape, tone = match.groups()
    if not shape and not tone:
        return None
    if (shape or "") not in NAME_SHAPES[base.lower()]:
        return None
    return base


def detect_vietnamese(font):
    """Return available glyphs and candidate mapping; no changes."""
    cp_bases = codepoint_bases()
    names = [str(name) for name in font.keys()]
    available = set(names)
    cps_by_glyph = {}
    names_by_codepoint = defaultdict(set)
    issues = []

    for name in names:
        try:
            points = [cp for cp in (font[name].unicodes or [])
                      if isinstance(cp, int) and not isinstance(cp, bool)]
            cps_by_glyph[name] = points
            if "." not in name:
                for cp in points:
                    if cp in cp_bases:
                        names_by_codepoint[cp].add(name)
        except Exception as exc:
            issues.append("Unicode read failed for %r: %s" % (name, type(exc).__name__))

    candidates = defaultdict(set)
    origin = {}
    for cp, glyph_names in sorted(names_by_codepoint.items()):
        if len(glyph_names) != 1:
            issues.append("Ambiguous Unicode U+%04X: %r" % (cp, sorted(glyph_names)))
            continue
        name = next(iter(glyph_names))
        base = cp_bases[cp]
        if name in origin and origin[name][0] != base:
            issues.append("Conflicting Unicode base for %r" % name)
            continue
        candidates[base].add(name)
        origin[name] = (base, "unicode")

    for name in names:
        if name in origin or "." in name:
            continue
        base = base_from_name(name, cp_bases)
        if base is None:
            continue
        points = cps_by_glyph.get(name, [])
        if points and not all(cp_bases.get(cp) == base for cp in points):
            continue
        candidates[base].add(name)
        origin[name] = (base, "name")
    return available, candidates, origin, issues


def class_bases(members):
    bases = set()
    for member in members:
        for base in BASES:
            if member == base:
                bases.add((base, ""))
            elif member.startswith(base + "."):
                bases.add((base, member[len(base):]))
    return bases


def snapshot_groups(kerning):
    """Canonical values; reject unfamiliar shapes instead of coercing them."""
    raw = kerning.groups.asDict()
    snapshot = {}
    for key, item in raw.items():
        if not isinstance(key, str) or not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Unexpected group record: %r" % (key,))
        members, mode = item
        if not isinstance(members, (list, tuple)) or not isinstance(mode, str):
            raise ValueError("Unexpected group shape: %r" % (key,))
        if not all(isinstance(g, str) for g in members):
            raise ValueError("Non-string group member: %r" % (key,))
        snapshot[key] = (tuple(members), mode)
    return snapshot


def snapshot_pairs(kerning):
    """Same explicit-pair snapshot shape as tested Guarded Batch Alpha.2.1."""
    rows = []
    for pair, amount in kerning.items():
        rows.append((
            str(pair.left.id), str(pair.left.mode),
            str(pair.right.id), str(pair.right.mode), float(amount),
        ))
    return tuple(sorted(rows))


def make_plan(groups, available, candidates):
    """Return safe additions and issues, including all overlapping-side checks."""
    issues = []
    existing_by_side = defaultdict(set)
    proposed_by_side = defaultdict(set)
    tentative = {}

    for key, (members, mode) in groups.items():
        sides = MODE_SIDES.get(mode)
        if sides is None:
            issues.append("Unknown group mode for %r: %r" % (key, mode))
            continue
        if len(members) != len(set(members)):
            issues.append("Duplicate members in class %r" % key)
        missing_in_font = sorted(set(members) - available)
        if missing_in_font:
            issues.append("Missing glyphs in class %r: %r" % (key, missing_in_font[:12]))
        for glyph in members:
            for side in sides:
                existing_by_side[(glyph, side)].add(key)

    for key, (members, mode) in groups.items():
        sides = MODE_SIDES.get(mode)
        if sides is None:
            continue
        member_set = set(members)
        proposed = set()
        for base, suffix in class_bases(members):
            for candidate in candidates.get(base, ()):
                name = candidate + suffix
                if name in available and name not in member_set:
                    proposed.add(name)
        if proposed:
            tentative[key] = sorted(proposed, key=str.casefold)
            for glyph in proposed:
                for side in sides:
                    proposed_by_side[(glyph, side)].add(key)

    duplicate_owners = sorted((glyph, side, sorted(owners))
                              for (glyph, side), owners in existing_by_side.items()
                              if len(owners) > 1)
    for glyph, side, owners in duplicate_owners[:20]:
        issues.append("Existing same-side overlap: %s %s %r" % (glyph, side, owners))
    if len(duplicate_owners) > 20:
        issues.append("More existing overlaps: %s" % (len(duplicate_owners) - 20))

    safe, blocked = {}, []
    for key in sorted(tentative, key=str.casefold):
        accepted = []
        for glyph in tentative[key]:
            conflicts = set()
            for side in MODE_SIDES[groups[key][1]]:
                conflicts |= existing_by_side[(glyph, side)] - {key}
                conflicts |= proposed_by_side[(glyph, side)] - {key}
            if conflicts:
                blocked.append({"class": key, "glyph": glyph,
                                "other_classes": sorted(conflicts)})
            else:
                accepted.append(glyph)
        if accepted:
            safe[key] = accepted
    return safe, blocked, issues


def current_package(fontlab, font):
    try:
        package = fontlab.flWorkspace.instance().currentPackage
        if package is not None:
            return package
    except Exception:
        pass
    return fontlab.flPackage(font)


def direct_group_matches(kerning, key, expected):
    actual = kerning.groups[key]
    return (isinstance(actual, tuple) and len(actual) == 2
            and (tuple(actual[0]), actual[1]) == expected)


def plan_token(filename, master, groups, pairs, available, safe, blocked, issues):
    """A preflight token tied to this exact in-session state and planned edits."""
    payload = {
        "filename": ntpath.normcase(filename),
        "master": master,
        "groups": [(key, list(members), mode) for key, (members, mode)
                   in sorted(groups.items())],
        "pairs": pairs,
        "glyphs": sorted(available),
        "safe": [(key, list(glyphs)) for key, glyphs in sorted(safe.items())],
        "blocked": blocked,
        "issues": issues,
    }
    data = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("ascii")).hexdigest()[:24].upper()


def main():
    print("=== NGHIATYPE NATIVE CORE V2 / FL8 ALPHA.1.3 / ORDER-AWARE STEPWISE ===")
    print("MODE:", "GUARDED APPLY" if APPLY_CHANGES else "PREVIEW ONLY")
    try:
        import fontlab
        font = fontlab.CurrentFont()
        if font is None:
            print("STOP: no active font")
            return
        path = str(getattr(font, "path", "") or "")
        filename = ntpath.basename(path)
        package = current_package(fontlab, font)
        master = str(package.getLayerName())
        kerning = package.kerning(master)
        before_groups = snapshot_groups(kerning)
        before_pairs = snapshot_pairs(kerning)
        available, candidates, origin, scan_issues = detect_vietnamese(font)
        safe, blocked, plan_issues = make_plan(before_groups, available, candidates)
    except Exception as exc:
        print("STOP: baseline read failed:", type(exc).__name__, str(exc))
        return

    issues = scan_issues + plan_issues
    name_only = sorted(glyph for glyphs in safe.values() for glyph in glyphs
                       if origin.get(glyph.split(".", 1)[0], (None, "name"))[1] == "name")
    token = plan_token(path, master, before_groups, before_pairs, available, safe, blocked, issues)
    pending = sum(len(glyphs) for glyphs in safe.values())

    print("Active filename:", filename or "<UNSAVED>")
    print("Active master:", master)
    print("Glyphs:", len(available))
    print("Native classes:", len(before_groups))
    print("Explicit native pairs/exceptions:", len(before_pairs))
    print("Candidates:", len(origin))
    print("--- GENERAL PLAN ---")
    for key in sorted(safe, key=str.casefold):
        members, mode = before_groups[key]
        print("CLASS", repr(key), "MODE", mode,
              "MEMBERS", len(members), "->", len(members) + len(safe[key]))
        print("  to_add:", safe[key])
    print("PENDING MEMBERSHIPS:", pending)
    print("BLOCKED PROPOSALS:", len(blocked))
    if blocked:
        print("  conflicts:", blocked[:20])
    print("ISSUES:", len(issues))
    if issues:
        print("  details:", issues[:20])
    print("NAME-ONLY CANDIDATES:", name_only)
    print("PLAN_TOKEN:", token)

    if not APPLY_CHANGES:
        print("PREVIEW COMPLETE: no changes made")
        print("For guarded Apply: inspect all results and back up a disposable COPY first")
        return
    # A zero-pending plan can still contain BLOCKED proposals: do not call it
    # "already applied" unless there are no conflicts or integrity issues.
    if blocked or issues or name_only:
        print("STOP: unsafe/ambiguous proposal; no writes performed")
        return
    if not pending:
        print("ALREADY APPLIED / NOTHING TO ADD: no changes made")
        return
    if not I_CONFIRM_TEST_COPY:
        print("STOP: I_CONFIRM_TEST_COPY must be True")
        return
    if not filename or "copy" not in filename.casefold():
        print("STOP: filename must contain 'copy' (saved disposable test font)")
        return
    if not EXPECTED_PLAN_TOKEN or EXPECTED_PLAN_TOKEN != token:
        print("STOP: PLAN_TOKEN mismatch; run Preview again and review current plan")
        return
    if not before_groups:
        print("STOP: no native classes; V2 does not create missing classes")
        return
    if len(available) == 0:
        print("STOP: empty font")
        return

    # This experiment is intentionally NOT generic: check exact reproduction
    # baseline, which protects unrelated fonts from these native API tests.
    if (len(available), len(before_groups), len(before_pairs)) != (384, 50, 2267):
        print("STOP: diagnostic baseline counts differ; no writes")
        return
    if (set(safe) != set(DIAGNOSTIC_TEST_ORDER)
            or any(len(safe[k]) != EXPECTED_PROPOSALS[k]
                   for k in DIAGNOSTIC_TEST_ORDER)):
        print("STOP: diagnostic plan differs; no writes")
        return
    for key in DIAGNOSTIC_TEST_ORDER:
        if key not in before_groups:
            print("STOP: diagnostic class missing:", repr(key))
            return
        members, mode = before_groups[key]
        if (len(members) != EXPECTED_INITIAL_MEMBERS[key]
                or mode != EXPECTED_INITIAL_MODES[key]):
            print("STOP: diagnostic class baseline differs:", repr(key))
            return

    expected_so_far = dict(before_groups)
    print("--- STEPWISE APPLY / A THEN Q THEN Q2 / NO SAVE ---")
    for step, key in enumerate(DIAGNOSTIC_TEST_ORDER, 1):
        print("--- STEP %d / 3 / CLASS %r ---" % (step, key))
        try:
            current_groups = snapshot_groups(kerning)
            current_pairs = snapshot_pairs(kerning)
            if current_groups != expected_so_far or current_pairs != before_pairs:
                drift = [k for k in sorted(set(current_groups) | set(expected_so_far))
                         if current_groups.get(k) != expected_so_far.get(k)]
                print("FAIL: unexpected state before this write")
                print("  DRIFTING CLASSES:", drift[:25])
                print("  PAIRS SNAPSHOT EQUAL:", current_pairs == before_pairs)
                print("STOP: CLOSE TEST COPY WITHOUT SAVING")
                return

            old_members, mode = current_groups[key]
            target_members = old_members + tuple(safe[key])
            print("  ADD:", safe[key])
            print("  MEMBERS:", len(old_members), "->", len(target_members))

            # One write only, then immediate readback before any other write.
            kerning.groups[key] = (list(target_members), mode)
            actual_groups = snapshot_groups(kerning)
            actual_pairs = snapshot_pairs(kerning)
            direct = kerning.groups[key]
            actual_members, actual_mode = actual_groups.get(key, ((), "<MISSING>"))
            changed = [name for name in sorted(set(current_groups) | set(actual_groups))
                       if current_groups.get(name) != actual_groups.get(name)]
            unplanned = [name for name in changed if name != key]
            missing = sorted(set(target_members) - set(actual_members))
            extra = sorted(set(actual_members) - set(target_members))
            order_diff = (set(actual_members) == set(target_members)
                          and tuple(actual_members) != tuple(target_members))
            # FontLab 8 has been observed returning Ograve inserted inside Q,
            # even though the requested list appended it. This diagnostic
            # accepts a changed INSERTION POSITION for the NEW names only.
            # Existing member order, first member, modes, all other group
            # records and all explicit kerning pairs must remain unchanged.
            additions = set(safe[key])
            members_exact = (len(actual_members) == len(target_members)
                             and len(set(actual_members)) == len(actual_members)
                             and set(actual_members) == set(target_members))
            original_order_preserved = (tuple(g for g in actual_members
                                               if g not in additions) == old_members)
            primary_preserved = bool(old_members and actual_members
                                     and actual_members[0] == old_members[0])
            other_groups_exact = (set(actual_groups) == set(expected_so_far)
                                  and all(actual_groups.get(name) == value
                                          for name, value in expected_so_far.items()
                                          if name != key))
            mode_ok = actual_mode == mode
            target_ok = (members_exact and original_order_preserved
                         and primary_preserved and mode_ok)
            # The raw access must match the freshly read canonical snapshot,
            # not the uncanonicalized list we asked FontLab to store.
            direct_ok = (key in actual_groups
                         and direct_group_matches(kerning, key, actual_groups[key]))
            groups_ok = other_groups_exact and target_ok
            pairs_ok = actual_pairs == before_pairs

            print("  ACTUAL MEMBERS:", list(actual_members))
            print("  ACTUAL MODE:", repr(actual_mode))
            print("  MISSING:", missing)
            print("  EXTRA:", extra)
            print("  ORDER DIFFERENCE (INSERT POSITION):", order_diff)
            print("  MEMBERSHIP EXACT / NO DUPLICATES:", members_exact)
            print("  ORIGINAL MEMBER RELATIVE ORDER PRESERVED:", original_order_preserved)
            print("  ORIGINAL FIRST MEMBER PRESERVED:", primary_preserved)
            print("  MODE DIFFERENCE:", actual_mode != mode)
            print("  ALL OTHER GROUPS EXACT:", other_groups_exact)
            print("  CLASSES CHANGED THIS STEP:", changed)
            print("  UNPLANNED CLASSES CHANGED:", unplanned)
            if unplanned:
                for other in unplanned[:5]:
                    print("    OTHER", repr(other),
                          "BEFORE", repr(current_groups.get(other)),
                          "AFTER", repr(actual_groups.get(other)))
            print("  DIRECT RAW READBACK:", repr(direct))
            print("  ALL NATIVE GROUPS:",
                  "VERIFIED (target insertion order may differ)" if groups_ok else "MISMATCH")
            print("  EXPLICIT PAIRS/EXCEPTIONS:", "UNCHANGED" if pairs_ok else "CHANGED")
            print("  DIRECT GROUP READBACK:", "EXACT MATCH" if direct_ok else "MISMATCH")
            if not (groups_ok and pairs_ok and direct_ok):
                print("FAIL AT STEP %d, CLASS %r" % (step, key))
                print("STOP: CLOSE TEST COPY WITHOUT SAVING")
                return
            # Trust the validated on-disk-model readback for the next step,
            # not our preferred order of newly appended glyphs.
            expected_so_far = dict(actual_groups)
            print("  STEP PASS")
        except Exception as exc:
            print("EXCEPTION AT STEP %d CLASS %r: %s %s" %
                  (step, key, type(exc).__name__, str(exc)))
            print("STOP: partial edits possible; CLOSE TEST COPY WITHOUT SAVING")
            return

    print("DIAGNOSTIC PASS: ALL THREE CLASSES VERIFIED IN MEMORY (NOT SAVED)")
    print("NOTE: insertion order of new members may be canonicalized by FontLab")
    print("STOP HERE: share Output. Do not Save before review.")


if __name__ == "__main__":
    main()
