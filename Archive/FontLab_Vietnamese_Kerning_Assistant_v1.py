# -*- coding: utf-8 -*-
"""
FontLab Vietnamese Kerning Assistant v1.0
=========================================
Combines two approaches tested by the user on FontLab 8.4.3.8984:
  - Unicode-based glyph identification and left/right class conflict checks.
  - Glyph-name fallback, original FEA backup, proposed FEA, unified DIFF, JSON.

DEFAULT IS PREVIEW ONLY. This script does NOT save the font or edit native
FontLab Classes-panel kerning groups. It edits class declarations already
present in the OpenType "kern" feature.

Before applying:
  1. Save As a disposable COPY of the font, with "copy" in its FILENAME.
  2. Run with APPLY_CHANGES=False and inspect the report.
  3. Set APPLY_CHANGES=True and I_CONFIRM_TEST_COPY=True.
  4. If name-only detection was used, inspect those glyphs and explicitly set
     ALLOW_NAME_ONLY_APPLY=True before applying.
  5. Run on the COPY. Require "APPLY READBACK: EXACT MATCH".
  6. Compile the feature; if an error occurs, CLOSE WITHOUT SAVING.
  7. Save, close, reopen the COPY; run PREVIEW again and expect 0 additions.
  8. Export OTF/TTF and check kerning. Keep the original source safe.

VERIFICATION STATUS:
  VERIFIED on FontLab 8.4.3.8984, Post Grotesk Light (2026-11-14):
    Preview: 878 glyphs, 96 kern classes, 4,302 POS rules, 0 safety issues.
    Apply: 154 memberships added to 17 classes; exact readback.
    Save/Close/Reopen: preview reports 0 remaining memberships.
    Export: OTF and TTF each contain 878 glyphs, with equivalent GPOS
    kerning (2,442 explicit pairs plus 606,698 tested class pair positions).
    Exported kerning matches the two earlier verified component scripts.
  Scope: one FL8 build and font family; other fonts require a new preview.
  FL9: UNVERIFIED. Never assume cross-version compatibility.

Only Python standard-library modules are required.
"""

from __future__ import print_function

import difflib
import hashlib
import json
import ntpath
import os
import re
import sys
import time
import traceback
import unicodedata
import uuid
from collections import defaultdict


# ------------------------------ USER SETTINGS ------------------------------
APPLY_CHANGES = False
I_CONFIRM_TEST_COPY = False
ALLOW_NAME_ONLY_APPLY = False
COPY_FILENAME_MARKER = "copy"
OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "FontLab_Kerning_Assistant")
# ---------------------------------------------------------------------------

CLASS_RE = re.compile(
    r"@(?P<name>[A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*"
    r"\[(?P<body>[^\]]*)\]\s*;",
    re.S,
)
PAIR_RE = re.compile(r"^(?:enum\s+)?pos\s+(\S+)\s+(\S+)", re.I)
VIET_NAME_RE = re.compile(
    r"^([AEIOUYaeiouy])(circumflex|breve|horn)?"
    r"(acute|grave|hoi|tilde|dotbelow)?$"
)
UNICODE_NAME_RE = re.compile(r"^(?:uni|u)([0-9A-Fa-f]{4,6})$")
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
BASES = "AEIOUYaeiouyDd"


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def unicode_to_base():
    """Vietnamese precomposed codepoints, mapped to their base Latin letters."""
    result = {0x0110: "D", 0x0111: "d"}
    for lowercase, shapes in SHAPES.items():
        for base in (lowercase, lowercase.upper()):
            for shape in shapes:
                for tone in TONES:
                    if not shape and not tone:
                        continue
                    composed = unicodedata.normalize("NFC", base + shape + tone)
                    if len(composed) == 1 and composed != base:
                        result[ord(composed)] = base
    return result


def base_from_name(name):
    """Recognize conservative Vietnamese-style, unsuffixed glyph names."""
    if name == "Dcroat":
        return "D"
    if name == "dcroat":
        return "d"
    if "." in name:
        return None
    encoded_name = UNICODE_NAME_RE.fullmatch(name)
    if encoded_name:
        return unicode_to_base().get(int(encoded_name.group(1), 16))
    match = VIET_NAME_RE.fullmatch(name)
    if not match:
        return None
    base, shape, tone = match.groups()
    if not shape and not tone:
        return None
    if (shape or "") not in NAME_SHAPES[base.lower()]:
        return None
    return base


def parse_classes(text):
    """Only simple FEA class declarations are supported; ambiguous text blocks APPLY."""
    classes = []
    issues = []
    seen = set()
    for match in CLASS_RE.finditer(text):
        name = match.group("name")
        body = re.sub(r"#[^\r\n]*", "", match.group("body"))
        members = body.split()
        if name in seen:
            issues.append("Duplicate class declaration @" + name)
        if any(member.startswith(("@", "\\")) for member in members):
            issues.append("Nested/escaped token in @" + name)
        if len(members) != len(set(members)):
            issues.append("Existing duplicate glyph member in @" + name)
        seen.add(name)
        classes.append((name, members))
    return classes, issues


def pair_roles(text):
    """Find left/right roles in simple two-position FEA 'pos' statements."""
    result = defaultdict(set)
    for line in text.splitlines():
        code = line.split("#", 1)[0].strip()
        match = PAIR_RE.match(code)
        if match is None:
            continue
        left, right = match.groups()
        if left.startswith("@"):
            result[left[1:]].add("LEFT")
        if right.startswith("@"):
            result[right[1:]].add("RIGHT")
    return dict(result)


def pos_lines(text):
    return [
        line for line in text.splitlines()
        if re.match(r"^\s*(?:enum\s+)?pos\s", line, re.I)
    ]


def glyph_candidates(font):
    """Resolve by Unicode first; name fallback only for unencoded candidates.

    Returns (all_names, base->set(glyph names), detection_method, issues).
    Ambiguous Unicode mapping is excluded and flagged to block applying.
    """
    codepoint_bases = unicode_to_base()
    names = list(font.keys())
    available = set(names)
    cp_to_names = defaultdict(set)
    glyph_unicodes = {}
    issues = []

    for name in names:
        try:
            values = font[name].unicodes
            if values is None:
                values = []
            points = [cp for cp in values if isinstance(cp, int)]
            glyph_unicodes[name] = points
            if "." not in name:
                for cp in points:
                    if cp in codepoint_bases:
                        cp_to_names[cp].add(name)
        except Exception as exc:
            issues.append(
                "Could not read glyph " + name + ": "
                + type(exc).__name__ + ": " + str(exc)
            )

    detected = defaultdict(set)
    method = {}
    for cp, matching_names in sorted(cp_to_names.items()):
        if len(matching_names) != 1:
            issues.append(
                "Ambiguous U+%04X: %s" % (cp, ", ".join(sorted(matching_names)))
            )
            continue
        name = next(iter(matching_names))
        base = codepoint_bases[cp]
        previously = method.get(name)
        if previously and previously[0] != base:
            issues.append("Different Unicode base mappings for " + name)
            continue
        detected[base].add(name)
        method[name] = (base, "unicode")

    for name in names:
        if name in method or "." in name:
            continue
        base = base_from_name(name)
        if base is None:
            continue
        # A glyph with an unrelated assigned Unicode scalar is NOT a
        # safe name-only Vietnamese candidate.
        points = glyph_unicodes.get(name, [])
        if points and not all(codepoint_bases.get(cp) == base for cp in points):
            continue
        detected[base].add(name)
        method[name] = (base, "name")

    return available, dict(detected), method, issues


def class_anchors(members):
    anchors = set()
    for member in members:
        for base in BASES:
            if member == base:
                anchors.add((base, ""))
            elif member.startswith(base + "."):
                anchors.add((base, member[len(base):]))
    return anchors


def plan_memberships(classes, available, candidates, detection):
    """Add the candidate to every matching *existing* class, never create one."""
    changes = {}
    provenance = {}
    for class_name, members in classes:
        current = set(members)
        planned = set()
        for base, suffix in class_anchors(members):
            for candidate in candidates.get(base, []):
                name = candidate + suffix
                if name in available and name not in current:
                    planned.add(name)
                    if detection.get(candidate, (None, None))[1] == "name":
                        provenance[name] = "name"
                    elif name not in provenance:
                        provenance[name] = "unicode"
        if planned:
            changes[class_name] = sorted(planned, key=str.casefold)
    return changes, provenance


def class_overlap_issues(classes, changes, roles):
    """Reject newly overlapping same-side class memberships.

    Overlap in opposite-side classes is intentional and permitted.
    Existing overlaps unrelated to new proposals are not evaluated.
    """
    existing = defaultdict(set)
    for class_name, members in classes:
        for name in members:
            existing[name].add(class_name)

    planned = defaultdict(set)
    issues = set()
    for class_name, glyphs in changes.items():
        if not roles.get(class_name):
            issues.add("No recognized LEFT/RIGHT role for @" + class_name)
        for name in glyphs:
            planned[name].add(class_name)

    for name, new_classes in planned.items():
        all_classes = existing.get(name, set()) | new_classes
        for new_class in new_classes:
            for other_class in all_classes - {new_class}:
                same_side = roles.get(new_class, set()) & roles.get(other_class, set())
                if same_side:
                    issues.add(
                        "%s: @%s overlaps @%s on %s"
                        % (name, new_class, other_class, "/".join(sorted(same_side)))
                    )
    return sorted(issues)


def explicit_pair_overrides(text, changes):
    """Report newly added glyphs named explicitly in POS rules, without editing."""
    added = {name for glyphs in changes.values() for name in glyphs}
    overrides = defaultdict(int)
    for line in pos_lines(text):
        code = line.split("#", 1)[0]
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_.-]*", code))
        for name in tokens & added:
            overrides[name] += 1
    return dict(overrides)


def render_kern(original, changes):
    matches = list(CLASS_RE.finditer(original))
    found = [match.group("name") for match in matches]
    if len(found) != len(set(found)):
        raise ValueError("Duplicate class declarations: stop")
    if not set(changes).issubset(set(found)):
        raise ValueError("Cannot find every class to modify")

    changed = original
    for match in reversed(matches):
        names = changes.get(match.group("name"))
        if not names:
            continue
        body = match.group("body")
        if "#" in body:
            raise ValueError(
                "Comments inside @" + match.group("name")
                + " require manual editing"
            )
        core = body.rstrip()
        tail = body[len(core):]
        updated = core + (" " if core else "") + " ".join(names) + tail
        changed = (
            changed[:match.start("body")]
            + updated
            + changed[match.end("body"):]
        )
    return changed


def verify_render(original, changed, classes, changes, available):
    """Validate text invariants before allowing any FontLab write."""
    errors = []
    next_classes, parse_errors = parse_classes(changed)
    errors.extend(parse_errors)
    if len(next_classes) != len(classes):
        errors.append("FEA class count changed")
    if pos_lines(original) != pos_lines(changed):
        errors.append("Positioning rules changed")
    if CLASS_RE.sub("", original) != CLASS_RE.sub("", changed):
        errors.append("Text outside class declarations changed")
    if not set(name for items in changes.values() for name in items).issubset(available):
        errors.append("A proposed glyph does not exist in this font")

    original_map = dict(classes)
    next_map = dict(next_classes)
    if set(original_map) != set(next_map):
        errors.append("Class names changed")
    for name, before in classes:
        after = next_map.get(name, [])
        added = changes.get(name, [])
        if len(after) != len(before) + len(added):
            errors.append("Wrong member count in @" + name)
        if after[:len(before)] != before or set(after[len(before):]) != set(added):
            errors.append("Existing members modified in @" + name)
    return errors


def read_kern(layout):
    method = getattr(layout, "get_feature", None)
    if callable(method):
        return method("kern")
    return layout["kern"]


def write_kern(layout, value):
    method = getattr(layout, "set_feature", None)
    if callable(method):
        method("kern", value)
        return "fgOTLayout.set_feature"
    layout["kern"] = value
    return "fgOTLayout.__setitem__"


def save_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def save_report(path, data):
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, default=str)


def write_artifacts(original, proposed, report):
    """Write original backup and diff BEFORE any font mutation."""
    folder = os.path.join(
        OUTPUT_FOLDER,
        time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6],
    )
    os.makedirs(folder)
    backup = os.path.join(folder, "kern_BACKUP_original.fea")
    new_file = os.path.join(folder, "kern_PROPOSED.fea")
    diff_file = os.path.join(folder, "kern_changes.diff")
    report_file = os.path.join(folder, "report.json")
    save_text(backup, original)
    save_text(new_file, proposed)
    lines = difflib.unified_diff(
        original.splitlines(),
        proposed.splitlines(),
        fromfile="kern_BACKUP_original",
        tofile="kern_PROPOSED",
        lineterm="",
        n=2,
    )
    save_text(diff_file, "\n".join(lines) + "\n")
    report["files"] = {
        "original_fea": backup,
        "proposed_fea": new_file,
        "diff": diff_file,
        "report_json": report_file,
    }
    save_report(report_file, report)
    return report_file, folder


def main():
    try:
        import fontlab  # available when run inside the FontLab Macro panel
    except ImportError:
        print("ERROR: Run this script INSIDE FontLab, not system Python.")
        return

    font = fontlab.CurrentFont()
    if font is None:
        print("ERROR: Open a font first.")
        return
    try:
        layout = font.features
        if "kern" not in list(layout.keys()):
            print("STOP: This font does not have a text 'kern' feature.")
            return
        original = read_kern(layout)
        if not isinstance(original, str):
            print("STOP: Could not read kern feature as text.")
            return
        prefix_before = layout.get_prefix()
        available, candidates, method, glyph_issues = glyph_candidates(font)
        classes, class_issues = parse_classes(original)
        roles = pair_roles(original)
        changes, provenance = plan_memberships(
            classes, available, candidates, method
        )
        side_issues = class_overlap_issues(classes, changes, roles)
        proposed = render_kern(original, changes)
        render_issues = verify_render(
            original, proposed, classes, changes, available
        )
    except Exception:
        print("STOP: Failed while inspecting font (no changes made).")
        print(traceback.format_exc())
        return

    name_only = sorted(
        name for name in {n for row in changes.values() for n in row}
        if provenance.get(name) == "name"
    )
    issues = glyph_issues + class_issues + side_issues + render_issues
    font_path = str(getattr(font, "path", "") or "")
    count = sum(len(row) for row in changes.values())
    report = {
        "tool": "FontLab Vietnamese Kerning Assistant v1.0",
        "approaches": ["Unicode + class-side checks", "Name fallback + FEA/DIFF/JSON backup"],
        "verification": (
            "VERIFIED on FL8.4.3.8984 / Post Grotesk Light; "
            "new fonts and FL9 require independent validation"
        ),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version,
        "font_object_type": type(font).__name__,
        "feature_object_type": type(layout).__name__,
        "font_path": font_path,
        "font_glyphs": len(available),
        "kern_source_sha256": sha256_text(original),
        "kern_proposed_sha256": sha256_text(proposed),
        "kern_source_length": len(original),
        "kern_proposed_length": len(proposed),
        "kern_classes": len(classes),
        "kern_pos_rules": len(pos_lines(original)),
        "classes_changed": len(changes),
        "memberships_to_add": count,
        "name_only_glyphs": name_only,
        "additions": changes,
        "explicit_pos_overrides": explicit_pair_overrides(original, changes),
        "issues": issues,
        "status": "PREVIEW_ONLY",
        "apply_requested": bool(APPLY_CHANGES),
    }
    try:
        report_path, output_dir = write_artifacts(original, proposed, report)
    except Exception:
        print("STOP: Could not create feature backup/reports; NO FONT EDIT.")
        print(traceback.format_exc())
        return

    print("=== FONTLAB VIETNAMESE KERNING ASSISTANT v1.0 ===")
    print("MODE:", "APPLY" if APPLY_CHANGES else "PREVIEW / NO FONT WRITES")
    print("GLYPHS:", len(available), "| KERN CLASSES:", len(classes))
    print("POS RULES:", len(pos_lines(original)))
    print("CLASS CHANGES:", len(changes), "| NEW MEMBERSHIPS:", count)
    print("NAME-ONLY CANDIDATES:", len(name_only))
    print("SAFETY ISSUES:", len(issues))
    for name, glyphs in sorted(changes.items()):
        print("  @%s +%s : %s" % (
            name, len(glyphs), " ".join(glyphs[:12])
            + (" ..." if len(glyphs) > 12 else ""),
        ))
    for issue in issues[:25]:
        print("ISSUE:", issue)
    for name in name_only[:20]:
        print("NAME-ONLY:", name)
    if report["explicit_pos_overrides"]:
        print("INFO: Explicit POS rules affect some candidates; see report.json.")
    print("BACKUP + DIFF + REPORT:", output_dir)

    if not APPLY_CHANGES:
        print("DRY RUN FINISHED. NO FONT CHANGES.")
        return

    reasons = []
    if not I_CONFIRM_TEST_COPY:
        reasons.append("I_CONFIRM_TEST_COPY is False")
    if not font_path or COPY_FILENAME_MARKER.lower() not in ntpath.basename(font_path).lower():
        reasons.append("Font FILENAME does not contain '%s'" % COPY_FILENAME_MARKER)
    if name_only and not ALLOW_NAME_ONLY_APPLY:
        reasons.append("Name-only glyphs require ALLOW_NAME_ONLY_APPLY=True")
    if not changes:
        reasons.append("No additional memberships are needed")
    if issues:
        reasons.append("Preflight safety issues were found")
    if reasons:
        for reason in reasons:
            print("APPLY BLOCKED:", reason)
        report["status"] = "APPLY_BLOCKED"
        report["apply_blockers"] = reasons
        try:
            save_report(report_path, report)
        except Exception as exc:
            print("WARNING: Could not update report JSON:", str(exc))
        return

    try:
        if read_kern(layout) != original or set(font.keys()) != available:
            raise RuntimeError("Font changed after the preview was computed")
        if layout.get_prefix() != prefix_before:
            raise RuntimeError("Common FEA prefix changed during this run")
        used_api = write_kern(layout, proposed)
        readback = read_kern(layout)
        prefix_after = layout.get_prefix()
        report["write_api"] = used_api
        report["readback_equals_proposed"] = (readback == proposed)
        report["prefix_unchanged"] = (prefix_before == prefix_after)
        if readback == proposed and prefix_before == prefix_after:
            report["status"] = "READBACK_PASS_NOT_YET_SAVED"
            print("APPLY READBACK: EXACT MATCH")
            print("APPLIED MEMBERSHIPS:", count)
            print("NEXT: Compile. Save/Close/Reopen the COPY, then PREVIEW again.")
        else:
            report["status"] = "READBACK_MISMATCH_DO_NOT_SAVE"
            print("READBACK MISMATCH: DO NOT SAVE THIS COPY.")
            print("Close the font WITHOUT saving; inspect BACKUP.")
    except Exception:
        report["status"] = "APPLY_ERROR_DO_NOT_SAVE"
        report["apply_traceback"] = traceback.format_exc()
        print("APPLY ERROR: DO NOT SAVE THIS COPY.")
        print(report["apply_traceback"])
    finally:
        try:
            save_report(report_path, report)
        except Exception as exc:
            print("WARNING: Could not update report JSON:", str(exc))


if __name__ == "__main__":
    main()
