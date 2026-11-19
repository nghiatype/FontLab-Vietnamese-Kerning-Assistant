# -*- coding: utf-8 -*-
#FLM: NghiaType Native Core V2 Alpha.1 (PREVIEW default)
"""NghiaType Native Kerning Core V2 - general-purpose experimental writer.

For FontLab 8 Python 3.11 (FL9 NOT YET TESTED for this version).

PREVIEW ONLY by default. The reader and planner are based on the previously
verified Native Class Preview Alpha 0.1; writing uses the separately tested
package.kerning(master).groups[key] = (glyph_names, mode) API.

The script does NOT modify OpenType `kern`, save, export, update features,
make backups, or create files. A guarded Apply changes only in-memory Native
Kerning Classes of the active master. Make a separate saved TEST COPY first.

To allow Apply on a sacrificial test copy AFTER inspecting Preview:
  1. Copy PLAN_TOKEN from the Preview output to EXPECTED_PLAN_TOKEN below.
  2. Set APPLY_CHANGES and I_CONFIRM_TEST_COPY both True.
  3. Confirm the active file name includes "copy" and the master is correct.
  4. Run. If any error/mismatch: CLOSE TEST COPY WITHOUT SAVING.

Never use Apply on a client source font. FL9 needs independent validation.
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
EXPECTED_PLAN_TOKEN = ""  # Paste the PLAN_TOKEN printed by a reviewed Preview
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
    print("=== NGHIATYPE NATIVE CORE V2 / FL8 ALPHA.1 ===")
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

    # Prepare the *entire* expected result before touching the Native API.
    expected_groups = dict(before_groups)
    try:
        for key, glyphs in safe.items():
            old_members, mode = before_groups[key]
            expected_groups[key] = (old_members + tuple(glyphs), mode)
        print("--- APPLY / CURRENT MASTER / NO SAVE ---")
        for key in sorted(safe, key=str.casefold):
            members, mode = expected_groups[key]
            kerning.groups[key] = (list(members), mode)
        after_groups = snapshot_groups(kerning)
        after_pairs = snapshot_pairs(kerning)
        group_ok = after_groups == expected_groups
        pairs_ok = after_pairs == before_pairs
        direct_ok = all(direct_group_matches(kerning, key, expected_groups[key])
                        for key in safe)
        print("ALL NATIVE GROUPS:", "EXACT MATCH" if group_ok else "MISMATCH")
        print("EXPLICIT PAIRS/EXCEPTIONS:", "UNCHANGED" if pairs_ok else "CHANGED")
        print("DIRECT GROUP READBACK:", "EXACT MATCH" if direct_ok else "MISMATCH")
        if group_ok and pairs_ok and direct_ok:
            print("SUCCESS: generalized guarded apply + exact readback (NOT YET SAVED)")
            print("Inspect kerning manually, then save/reopen this TEST COPY only")
        else:
            print("FAIL: CLOSE TEST COPY WITHOUT SAVING")
    except Exception as exc:
        print("APPLY/READBACK ERROR:", type(exc).__name__, str(exc))
        print("Partial in-memory edits may exist: CLOSE TEST COPY WITHOUT SAVING")


if __name__ == "__main__":
    main()
