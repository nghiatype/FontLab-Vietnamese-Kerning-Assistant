# -*- coding: utf-8 -*-
"""V3 Alpha.0.13: selective, READ-ONLY Native -> OT kern proposal builder.

Consumes the validated V3 Cross-check JSON-shaped report, not FontLab APIs.
One OT class can represent two separate Native kerning sides. A glyph can be
suggested only when EVERY linked Native side contains it and no known side is
missing. Conflicting data becomes a warning rather than an automatic change.

There are no writers, imports of FontLab, file changes or automatic Apply.
"""

from __future__ import print_function

import re
from collections import defaultdict


def _sort_key(value):
    return value.casefold(), value


def extract_kern_feature_text(source):
    """Extract exactly one top-level `feature kern { ... } kern;` safely.

    Supports nested lookup blocks, comments and quoted braces. The caller
    must treat the resulting text as an EXTERNAL HISTORICAL SNAPSHOT, never
    as the active FontLab feature or an authorization to write anything.
    """
    if not isinstance(source, str):
        raise ValueError("FEA snapshot must be text.")
    starts = list(re.finditer(
        r"(?m)^[ \t]*feature[ \t]+kern[ \t]*\{", source
    ))
    if len(starts) != 1:
        raise ValueError(
            "Expected exactly one explicit 'feature kern {' block in FEA."
        )
    start = starts[0]
    depth = 0
    quote = False
    comment = False
    escaped = False
    for index in range(start.end() - 1, len(source)):
        char = source[index]
        if comment:
            if char in "\r\n":
                comment = False
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quote = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                ending = re.match(r"[ \t\r\n]*kern[ \t]*;", source[index + 1:])
                if ending is None:
                    raise ValueError("Feature kern has no matching '} kern;'.")
                return source[start.start():index + 1 + ending.end()]
            if depth < 0:
                raise ValueError("Unexpected closing brace inside feature kern.")
    raise ValueError("Unterminated feature kern block in FEA snapshot.")


def build_ot_sync_preview(crosscheck):
    """Group missing Native members by UNIQUE OT target class, fail closed."""
    if not isinstance(crosscheck, dict) or crosscheck.get("mode") != "READ_ONLY":
        raise ValueError("A verified read-only Cross-check report is required.")
    rows = crosscheck.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Cross-check rows are missing.")

    by_ot = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid Cross-check row.")
        if row.get("ot_class") and row.get("status") in ("MATCH", "DIFFERENT"):
            by_ot[row["ot_class"]].append(row)

    uncovered = {
        item["ot_class"]: item["missing_roles"]
        for item in crosscheck.get("uncovered_ot_sides", [])
    }
    parser_issues = list(crosscheck.get("parse_issues", []))
    groups = []
    for ot_name in sorted(by_ot, key=_sort_key):
        linked = by_ot[ot_name]
        ot_members = list(linked[0]["ot_members"])
        if any(list(row["ot_members"]) != ot_members for row in linked):
            raise ValueError("Inconsistent OT class snapshots: @" + ot_name)
        if len(ot_members) != len(set(ot_members)):
            raise ValueError("Duplicate OT class members: @" + ot_name)
        sources = sorted((row["native_class"] for row in linked), key=_sort_key)
        additions = [set(row["native_only"]) for row in linked]
        union_additions = set().union(*additions)
        safe_common = set.intersection(*additions)
        ot_extra = sorted(set().union(*(
            set(row["ot_only"]) for row in linked
        )), key=_sort_key)
        warnings = []
        if union_additions != safe_common:
            warnings.append("NATIVE_SIDES_DISAGREE")
        if ot_extra:
            warnings.append("OT_HAS_UNMATCHED_MEMBERS")
        if ot_name in uncovered:
            warnings.append("UNVERIFIED_OT_SIDE")
        if parser_issues:
            warnings.append("OT_PARSE_WARNINGS")

        # The candidate intersection is shown, but no unsafe class is
        # available for selection while any of its safety gates is raised.
        proposed = sorted(safe_common, key=_sort_key) if not warnings else []
        blocked = sorted(union_additions - set(proposed), key=_sort_key)
        if not proposed and not blocked and not warnings:
            continue
        groups.append({
            "ot_class": ot_name,
            "native_sources": sources,
            "current_ot_members": ot_members,
            "proposed": proposed,
            "blocked": blocked,
            "ot_only": ot_extra,
            "uncovered_roles": list(uncovered.get(ot_name, ())),
            "warnings": warnings,
            "status": "READY" if proposed else "REVIEW",
        })

    return {
        "mode": "READ_ONLY",
        "stage": "SELECTIVE_OT_SYNC_PREVIEW",
        "source_native_groups": crosscheck.get("native_classes", 0),
        "source_ot_classes": crosscheck.get("ot_classes", 0),
        "candidate_ot_classes": sum(bool(g["proposed"]) for g in groups),
        "candidate_unique_memberships": sum(len(g["proposed"]) for g in groups),
        "blocked_memberships": sum(len(g["blocked"]) for g in groups),
        "groups": groups,
    }


def render_selected_fea_preview(preview, selected):
    """Render complete class declarations as NON-APPLIED FEA preview text.

    selected is an iterable of (ot_class, glyph) pairs. Unknown selections are
    rejected, so no arbitrary feature code is ever inserted into the preview.
    """
    if preview.get("mode") != "READ_ONLY" or preview.get("stage") != "SELECTIVE_OT_SYNC_PREVIEW":
        raise ValueError("Expected a read-only OT sync preview.")
    allowed = {
        (group["ot_class"], glyph)
        for group in preview["groups"] for glyph in group["proposed"]
    }
    choices = set(tuple(choice) for choice in selected)
    if not choices <= allowed:
        raise ValueError("Preview selection contains an unverified addition.")

    lines = [
        "# READ ONLY - PROPOSED OPENTYPE KERN CHANGES / NOT APPLIED",
        "# Preview is not an instruction to save or compile. No font changes.",
        "# Select a glyph in the GUI to include/exclude it here.",
        "",
    ]
    selected_count = 0
    for group in preview["groups"]:
        chosen = [glyph for glyph in group["proposed"]
                  if (group["ot_class"], glyph) in choices]
        if not chosen:
            continue
        selected_count += len(chosen)
        lines.append("# @%s  /  Native: %s  /  +%d" % (
            group["ot_class"], ", ".join(group["native_sources"]), len(chosen)
        ))
        lines.append("# Add: " + ", ".join(chosen))
        # Preserve ORIGINAL OT order; appending is the only proposed change.
        full_members = group["current_ot_members"] + chosen
        lines.append("@%s = [%s];" % (group["ot_class"], " ".join(full_members)))
        lines.append("")
    if selected_count == 0:
        lines.append("# Nothing selected. Font unchanged.")
    lines.append("# FINAL STATUS: PREVIEW ONLY / %d unique additions selected" % selected_count)
    return "\n".join(lines)
