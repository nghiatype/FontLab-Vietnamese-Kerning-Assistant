# -*- coding: utf-8 -*-
"""NghiaType V3 Alpha.0.11: read-only Native / text kern comparison.

Native V2 exposes LEFT and RIGHT as separate class-group records. OpenType
feature text may reuse ONE @class in both pair positions. Compare each Native
SIDE against the corresponding role of that OT class: never require an
unnecessarily one-to-one Native-to-OT class mapping.

Inputs come from the verified V1/V2 readers. No FontLab imports, writer,
feature edits, file writes or implicit synchronization exist in this module.
"""

from __future__ import print_function

from collections import Counter, defaultdict


MODE_ROLES = {
    "KernLeft": frozenset(("LEFT",)),
    "KernRight": frozenset(("RIGHT",)),
    "KernBoth": frozenset(("LEFT", "RIGHT")),
    "KernBothSide": frozenset(("LEFT", "RIGHT")),
}


REASON_TEXT = {
    "IN_SYNC": "Native and linked OT glyph members are identical.",
    "MEMBERSHIP_DIFFERENT": "These linked classes differ in their glyph members.",
    "NO_REPRESENTATIVE_MATCH":
        "No parsed OT class contains the first Native member. The OT "
        "class may be named differently or outside V1's text scan.",
    "NAME_HINT_ONLY":
        "An OT class has a similar name, but does not contain the first "
        "Native glyph. Similar names alone cannot establish a link.",
    "OT_ROLE_NOT_DETECTED":
        "OT class contains the representative, but V1 did not detect a "
        "simple pos rule establishing its kerning side.",
    "SIDE_MISMATCH":
        "OT class contains the representative, but its detected pair role "
        "does not include the Native class side.",
    "MULTIPLE_OT_CANDIDATES":
        "Multiple OT classes contain this representative on the required "
        "side. No automatic choice was made.",
    "SHARED_OT_SIDE":
        "Multiple Native classes claim the same OT class on the same side. "
        "No automatic choice was made.",
    "UNKNOWN_NATIVE_MODE": "The Native kerning mode is not recognized.",
    "EMPTY_NATIVE_CLASS": "This Native class has no representative glyph.",
}


def _names(values, context):
    if not isinstance(values, (tuple, list)) or any(
        not isinstance(value, str) for value in values
    ):
        raise ValueError("Invalid member list: " + context)
    if len(values) != len(set(values)):
        raise ValueError("Duplicate member: " + context)
    return tuple(values)


def _sort_key(value):
    return value.casefold(), value


def _name_hint(native_name, ot_name):
    """A label for investigation, not evidence of equivalent classes."""
    return ot_name.lstrip("_") == native_name


def compare_kerning(native_groups, ot_classes, ot_roles, parse_issues=()):
    """Compare a Native group with a unique OT representative AND side.

    Separate KernLeft and KernRight groups may legitimately link to one OT
    class when that OT class is used as both LEFT and RIGHT in kern text.
    Two Native groups cannot claim overlapping sides of one OT class.
    Every result is advisory/read-only; no mapping authorizes applying data.
    """
    if not isinstance(native_groups, dict) or not isinstance(ot_roles, dict):
        raise ValueError("Invalid Native/OT reader results")

    ot = {}
    for name, members in ot_classes:
        if not isinstance(name, str) or name in ot:
            raise ValueError("Duplicate/invalid OpenType class: %r" % (name,))
        ot[name] = _names(members, "OT @" + name)

    roles = {}
    for name, values in ot_roles.items():
        if not isinstance(name, str) or not isinstance(
            values, (tuple, list, set, frozenset)
        ) or any(value not in ("LEFT", "RIGHT") for value in values):
            raise ValueError("Invalid OpenType role entry: %r" % (name,))
        roles[name] = frozenset(values)

    rows = []
    tentative = defaultdict(list)
    for native_name in sorted(native_groups, key=_sort_key):
        record = native_groups[native_name]
        if not isinstance(native_name, str) or not isinstance(
            record, (list, tuple)
        ) or len(record) != 2:
            raise ValueError("Invalid Native class: %r" % (native_name,))
        members = _names(record[0], "Native " + native_name)
        mode = record[1]
        if not isinstance(mode, str):
            raise ValueError("Invalid Native class mode: " + native_name)
        expected = MODE_ROLES.get(mode, frozenset())
        representative = members[0] if members else None

        row = {
            "native_class": native_name,
            "mode": mode,
            "expected_roles": sorted(expected),
            "representative": representative,
            "native_count": len(members),
            "native_members": list(members),
            "ot_class": None,
            "ot_count": None,
            "ot_members": [],
            "ot_roles": [],
            "native_only": [],
            "ot_only": [],
            "candidates": [],
            "inspected_candidates": [],
            "status": "UNMAPPED",
            "reason": "NO_REPRESENTATIVE_MATCH",
            "mapping": None,
        }

        # Include name-only clues as diagnostic hints, NEVER as mappings.
        for ot_name in sorted(ot, key=_sort_key):
            glyphs = ot[ot_name]
            contains = representative is not None and representative in glyphs
            same_name = _name_hint(native_name, ot_name)
            if not (contains or same_name):
                continue
            ot_sides = roles.get(ot_name, frozenset())
            row["inspected_candidates"].append({
                "ot_class": ot_name,
                "representative_present": contains,
                "name_hint": same_name,
                "ot_roles": sorted(ot_sides),
                "side_matches": bool(expected and expected <= ot_sides),
                "ot_count": len(glyphs),
            })

        if mode not in MODE_ROLES:
            row["status"] = "UNKNOWN_NATIVE_MODE"
            row["reason"] = "UNKNOWN_NATIVE_MODE"
        elif not members:
            row["status"] = "EMPTY_NATIVE_CLASS"
            row["reason"] = "EMPTY_NATIVE_CLASS"
        else:
            matched = [candidate for candidate in row["inspected_candidates"]
                       if candidate["representative_present"]
                       and candidate["side_matches"]]
            row["candidates"] = [candidate["ot_class"] for candidate in matched]
            if len(matched) > 1:
                row["status"] = "AMBIGUOUS"
                row["reason"] = "MULTIPLE_OT_CANDIDATES"
            elif len(matched) == 1:
                ot_name = matched[0]["ot_class"]
                row["status"] = "PENDING"
                row["ot_class"] = ot_name
                for side in expected:
                    tentative[(ot_name, side)].append(row)
            else:
                anchored = [candidate for candidate in row["inspected_candidates"]
                            if candidate["representative_present"]]
                if anchored:
                    row["reason"] = (
                        "SIDE_MISMATCH" if any(candidate["ot_roles"]
                                               for candidate in anchored)
                        else "OT_ROLE_NOT_DETECTED"
                    )
                elif any(candidate["name_hint"] for candidate in
                         row["inspected_candidates"]):
                    row["reason"] = "NAME_HINT_ONLY"
        rows.append(row)

    # Reject overlapping Native claims on any one OT side. Distinct LEFT and
    # RIGHT claimants of a dual-role OT class are intentional and valid.
    conflicting = set()
    for claims in tentative.values():
        if len(claims) > 1:
            conflicting.update(id(row) for row in claims)

    claimed_ot_sides = defaultdict(set)
    for row in rows:
        if row["status"] != "PENDING":
            continue
        if id(row) in conflicting:
            row["status"] = "AMBIGUOUS"
            row["reason"] = "SHARED_OT_SIDE"
            row["ot_class"] = None
            continue
        ot_name = row["ot_class"]
        native_set = set(row["native_members"])
        ot_set = set(ot[ot_name])
        row["ot_count"] = len(ot[ot_name])
        row["ot_members"] = list(ot[ot_name])
        row["ot_roles"] = sorted(roles.get(ot_name, frozenset()))
        row["native_only"] = sorted(native_set - ot_set, key=_sort_key)
        row["ot_only"] = sorted(ot_set - native_set, key=_sort_key)
        row["mapping"] = (
            "SHARED_BOTH_SIDES" if len(roles.get(ot_name, ())) > 1
            else "SINGLE_SIDE"
        )
        row["status"] = (
            "DIFFERENT" if row["native_only"] or row["ot_only"] else "MATCH"
        )
        row["reason"] = (
            "MEMBERSHIP_DIFFERENT" if row["status"] == "DIFFERENT"
            else "IN_SYNC"
        )
        claimed_ot_sides[ot_name].update(row["expected_roles"])

    counts = Counter(row["status"] for row in rows)
    reasons = Counter(row["reason"] for row in rows)
    unmatched_ot = set(ot) - set(claimed_ot_sides)
    uncovered_ot_sides = [
        {"ot_class": name, "missing_roles": sorted(ot_sides - claimed_ot_sides[name])}
        for name, ot_sides in sorted(roles.items(), key=lambda pair: _sort_key(pair[0]))
        if name in ot and ot_sides - claimed_ot_sides[name]
    ]
    return {
        "mode": "READ_ONLY",
        "scope": "Simple class declarations and pos rules in text feature kern only",
        "native_classes": len(rows),
        "ot_classes": len(ot),
        "matched_classes": counts["MATCH"] + counts["DIFFERENT"],
        "linked_ot_classes": len(claimed_ot_sides),
        "dual_side_ot_classes": sum(
            1 for name in ot if roles.get(name) == frozenset(("LEFT", "RIGHT"))
        ),
        "dual_side_native_links": sum(
            1 for row in rows if row["mapping"] == "SHARED_BOTH_SIDES"
        ),
        "native_only_memberships": sum(len(row["native_only"]) for row in rows),
        "ot_only_memberships": sum(len(row["ot_only"]) for row in rows),
        "statuses": dict(sorted(counts.items())),
        "reasons": dict(sorted(reasons.items())),
        "unmatched_ot_classes": sorted(unmatched_ot, key=_sort_key),
        "uncovered_ot_sides": uncovered_ot_sides,
        "parse_issues": list(parse_issues),
        "rows": rows,
    }
