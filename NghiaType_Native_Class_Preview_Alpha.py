# -*- coding: utf-8 -*-
#FLM: NghiaType Native Class Preview (READ ONLY)
"""Native Kerning Classes: independent read-only preview for FontLab 8/9.

Alpha scope: Vietnamese precomposed glyph candidates, using the conservative
Unicode/name rules from the established V1 workflow. Scan the CURRENT master.

This file has NO Apply implementation and DOES NOT edit/save/export the font.
It does not require the V1 core file or any third-party Python package.
Run inside FontLab's Scripting/Macro panel with a font open, then inspect Output.

ASCII-only source avoids the macro-editor source-encoding issue on Windows.
"""

from __future__ import print_function

import json
import re
import sys
import traceback
import unicodedata
from collections import defaultdict


PREVIEW_CLASS_LIMIT = 30
PREVIEW_GLYPH_LIMIT = 24
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


def codepoint_bases():
    result = {0x0110: "D", 0x0111: "d"}
    for letter, shapes in SHAPES.items():
        for base in (letter, letter.upper()):
            for shape in shapes:
                for tone in TONES:
                    if not shape and not tone:
                        continue
                    composed = unicodedata.normalize("NFC", base + shape + tone)
                    if len(composed) == 1 and composed != base:
                        result[ord(composed)] = base
    return result


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
    """Read glyph Unicode assignments; never infer an unencoded font edit."""
    cp_bases = codepoint_bases()
    names = [str(n) for n in font.keys()]
    available = set(names)
    cp_names = defaultdict(set)
    glyph_cps = {}
    issues = []
    for name in names:
        try:
            values = font[name].unicodes or []
            points = [cp for cp in values if isinstance(cp, int)]
            glyph_cps[name] = points
            if "." not in name:
                for cp in points:
                    if cp in cp_bases:
                        cp_names[cp].add(name)
        except Exception as exc:
            issues.append("Glyph Unicode read error: %s (%s)" %
                          (name, type(exc).__name__))

    detected = defaultdict(set)
    origin = {}
    for cp, matched in sorted(cp_names.items()):
        if len(matched) != 1:
            issues.append("Ambiguous U+%04X: %s" %
                          (cp, ", ".join(sorted(matched))))
            continue
        name = next(iter(matched))
        base = cp_bases[cp]
        if name in origin and origin[name][0] != base:
            issues.append("Conflicting Unicode base: " + name)
            continue
        detected[base].add(name)
        origin[name] = (base, "unicode")

    for name in names:
        if name in origin or "." in name:
            continue
        base = base_from_name(name, cp_bases)
        if base is None:
            continue
        points = glyph_cps.get(name, [])
        if points and not all(cp_bases.get(cp) == base for cp in points):
            continue
        detected[base].add(name)
        origin[name] = (base, "name")
    return available, detected, origin, issues


def side_from_mode(mode):
    """Native FL8 returned 'KernLeft'/'KernRight', not the fgGroup mode."""
    mapping = {
        "KernLeft": "LEFT", "KernLeftGroupMode": "LEFT",
        "KernRight": "RIGHT", "KernRightGroupMode": "RIGHT",
        "KernBoth": "BOTH", "KernBothSide": "BOTH",
        "KernBothSideGroupMode": "BOTH",
    }
    return mapping.get(str(mode))


def normalize_groups(group_mapping):
    """Reject unknown native group shapes instead of silently guessing."""
    rows = group_mapping.items() if hasattr(group_mapping, "items") else group_mapping
    parsed, errors = [], []
    for item in rows:
        try:
            name, record = item
            members, mode = record
            side = side_from_mode(mode)
            if side is None or not isinstance(members, (list, tuple)):
                raise ValueError("Unexpected group mode or members")
            if not all(isinstance(value, str) for value in members):
                raise ValueError("Non-string glyph name in group")
            parsed.append({"name": str(name), "side": side,
                           "members": list(members), "mode": str(mode)})
        except Exception as exc:
            errors.append("Group parse error: %s / %s" %
                          (repr(item)[:100], type(exc).__name__))
    return parsed, errors


def class_bases(members):
    bases = set()
    for member in members:
        for base in BASES:
            if member == base:
                bases.add((base, ""))
            elif member.startswith(base + "."):
                bases.add((base, member[len(base):]))
    return bases


def plan_preview(classes, available, candidates, origin):
    """Only propose additions; block overlapping same-side membership."""
    existing_by_side = defaultdict(set)
    proposed_by_side = defaultdict(set)
    proposals = {}

    for row in classes:
        sides = ("LEFT", "RIGHT") if row["side"] == "BOTH" else (row["side"],)
        for glyph in row["members"]:
            for side in sides:
                existing_by_side[(glyph, side)].add(row["name"])

    for row in classes:
        members = set(row["members"])
        planned = set()
        for base, suffix in class_bases(row["members"]):
            for candidate in candidates.get(base, ()):
                name = candidate + suffix
                if name in available and name not in members:
                    planned.add(name)
        if planned:
            proposals[row["name"]] = sorted(planned, key=str.casefold)
            sides = ("LEFT", "RIGHT") if row["side"] == "BOTH" else (row["side"],)
            for name in planned:
                for side in sides:
                    proposed_by_side[(name, side)].add(row["name"])

    safe, blocked = defaultdict(list), defaultdict(list)
    by_name = {r["name"]: r for r in classes}
    for class_name, glyphs in proposals.items():
        row = by_name[class_name]
        sides = ("LEFT", "RIGHT") if row["side"] == "BOTH" else (row["side"],)
        for glyph in glyphs:
            conflicting = set()
            for side in sides:
                conflicting |= existing_by_side[(glyph, side)] - {class_name}
                conflicting |= proposed_by_side[(glyph, side)] - {class_name}
            if conflicting:
                blocked[class_name].append({"glyph": glyph,
                                            "other_classes": sorted(conflicting)})
            else:
                safe[class_name].append(glyph)

    name_only = {glyph for name, glyphs in safe.items() for glyph in glyphs
                 if origin.get(glyph.split(".", 1)[0], (None, None))[1] == "name"}
    return safe, blocked, sorted(name_only)


def build_report(font, package):
    master = str(package.getLayerName())
    native_kerning = package.kerning(master)
    native_groups = native_kerning.groups.asDict()
    classes, class_errors = normalize_groups(native_groups)
    available, candidates, origin, unicode_errors = detect_vietnamese(font)
    safe, blocked, name_only = plan_preview(
        classes, available, candidates, origin)

    classes_by_name = {row["name"]: row for row in classes}
    summaries = []
    for name in sorted(set(safe) | set(blocked), key=str.casefold):
        row = classes_by_name[name]
        summaries.append({
            "class": name,
            "side": row["side"],
            "existing_members": len(row["members"]),
            "safe_count": len(safe.get(name, ())),
            "safe_sample": safe.get(name, ())[:PREVIEW_GLYPH_LIMIT],
            "blocked_count": len(blocked.get(name, ())),
            "blocked_sample": blocked.get(name, ())[:PREVIEW_GLYPH_LIMIT],
        })
    return {
        "tool": "NghiaType Native Class Preview Alpha 0.1 / READ ONLY",
        "master": master,
        "font_glyphs": len(available),
        "native_class_count": len(classes),
        "unrecognized_class_count": len(class_errors),
        "candidate_glyphs": len(origin),
        "classes_with_proposals": len(summaries),
        "safe_proposed_memberships": sum(map(len, safe.values())),
        "blocked_proposed_memberships": sum(map(len, blocked.values())),
        "name_only_safe_candidates": name_only[:PREVIEW_GLYPH_LIMIT],
        "issues": (class_errors + unicode_errors)[:50],
        "preview_class_limit": PREVIEW_CLASS_LIMIT,
        "classes": summaries[:PREVIEW_CLASS_LIMIT],
        "class_rows_truncated": max(0, len(summaries) - PREVIEW_CLASS_LIMIT),
        "font_modified": False,
        "apply_available": False,
    }


def current_package(fontlab, font):
    try:
        pkg = fontlab.flWorkspace.instance().currentPackage
        if pkg is not None:
            return pkg
    except Exception:
        pass
    return fontlab.flPackage(font)


def main():
    print("=== NGHIATYPE NATIVE CLASS PREVIEW / READ ONLY ===")
    try:
        import fontlab
    except ImportError:
        print("ERROR: Run this script inside FontLab.")
        return
    try:
        font = fontlab.CurrentFont()
        if font is None:
            print("ERROR: No open font.")
            return
        report = build_report(font, current_package(fontlab, font))
        print("NATIVE_PREVIEW_JSON_BEGIN")
        print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
        print("NATIVE_PREVIEW_JSON_END")
        print("DONE: PREVIEW ONLY. No font edits, no save, no export.")
    except Exception:
        print("STOP: Native scan failed. No font writes requested.")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
