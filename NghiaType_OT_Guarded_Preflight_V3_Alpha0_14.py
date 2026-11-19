# -*- coding: utf-8 -*-
"""NghiaType V3 Alpha.0.16: pure, read-only OT class membership preflight.

This module NEVER calls FontLab writers, writes files, compiles or saves.
The V1 engine is injected solely for its tested parsers and FEA renderer.
Historical FEA comparisons are useful for inspecting diffs but can NEVER
pass the live-Apply gate.
"""

from __future__ import print_function

import difflib
import hashlib
import ntpath


REQUIRED_V1_FUNCTIONS = (
    "parse_classes", "pair_roles", "class_overlap_issues", "render_kern",
    "verify_render", "explicit_pair_overrides",
)


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _members(snapshot):
    """Copy group data to ordinary values for a stable equality comparison."""
    if not isinstance(snapshot, dict):
        return None
    return {
        name: (tuple(data[0]), str(data[1]))
        for name, data in snapshot.items()
    }


def prepare_ot_preflight(
    preview, selected, source_kern, live_kern, v1,
    original_native_groups, live_native_groups, original_glyphs, live_glyphs,
    original_prefix, live_prefix, original_font_path, live_font_path,
    original_master, live_master, fontlab_major,
    original_native_pairs=None, live_native_pairs=None,
    original_native_issues=(), live_native_issues=(),
    original_master_count=None, live_master_count=None,
    saved_copy_exists=True,
):
    """Build exact FEA diff and detect any reason a FUTURE Apply must stop.

    Even a successful report here is NOT authorization to write. A separate
    guarded writer and real FL8 readback test are mandatory before enabling
    a production Apply button.
    """
    if not isinstance(preview, dict) or preview.get("mode") != "READ_ONLY":
        raise ValueError("A read-only selective preview is required.")
    if preview.get("stage") != "SELECTIVE_OT_SYNC_PREVIEW":
        raise ValueError("Unknown OT preview stage.")
    if not isinstance(source_kern, str) or not isinstance(live_kern, str):
        raise ValueError("Both source and current kern must be text.")
    for name in REQUIRED_V1_FUNCTIONS:
        if not callable(getattr(v1, name, None)):
            raise ValueError("Missing validated V1 FEA function: " + name)

    blockers = []
    source_mode = preview.get("source_mode")
    if source_mode != "LIVE_CROSSCHECK_SNAPSHOT":
        blockers.append("EXTERNAL_SNAPSHOT_NOT_LIVE")
    if fontlab_major != 8:
        blockers.append("FONTLAB_8_ONLY")
    if not original_font_path or not live_font_path:
        blockers.append("SAVED_TEST_COPY_REQUIRED")
    elif "copy" not in ntpath.basename(live_font_path).lower():
        blockers.append("COPY_FILENAME_MARKER_MISSING")
    if not saved_copy_exists:
        blockers.append("COPY_FILE_NOT_FOUND_ON_DISK")
    if original_font_path != live_font_path:
        blockers.append("ACTIVE_FONT_CHANGED")
    if not original_master or original_master != live_master:
        blockers.append("MASTER_CHANGED")
    if (original_master_count != 1 or live_master_count != 1):
        blockers.append("SINGLE_MASTER_ONLY")
    if source_kern != live_kern:
        blockers.append(
            "EXTERNAL_FEA_DIFFERS_FROM_LIVE" if source_mode == "EXTERNAL_FEA_SNAPSHOT"
            else "LIVE_KERN_CHANGED_SINCE_PREVIEW"
        )
    if original_prefix != live_prefix:
        blockers.append("FEA_PREFIX_CHANGED_SINCE_PREVIEW")
    if _members(original_native_groups) != _members(live_native_groups):
        blockers.append("NATIVE_GROUPS_CHANGED_SINCE_PREVIEW")
    if original_native_pairs != live_native_pairs:
        blockers.append("NATIVE_KERN_PAIRS_CHANGED_SINCE_PREVIEW")
    if original_native_issues or live_native_issues:
        blockers.append("NATIVE_SCAN_ISSUES_REVIEW_REQUIRED")

    original_glyphs = set(original_glyphs or ())
    live_glyphs = set(live_glyphs or ())
    if original_glyphs != live_glyphs:
        blockers.append("FONT_GLYPH_SET_CHANGED_SINCE_PREVIEW")

    # Never accept arbitrary names sent by the GUI (or a stale checkbox).
    groups = preview.get("groups", ())
    allowed = {(group["ot_class"], glyph)
               for group in groups for glyph in group["proposed"]}
    try:
        choices = {tuple(item) for item in selected}
    except (TypeError, ValueError):
        choices = set()
        blockers.append("INVALID_SELECTION")
    if not choices.issubset(allowed):
        blockers.append("SELECTION_NOT_IN_VERIFIED_PLAN")
    if not choices:
        blockers.append("NO_SELECTED_ADDITIONS")

    changes = {}
    for group in groups:
        name = group["ot_class"]
        chosen = [glyph for glyph in group["proposed"]
                  if (name, glyph) in choices]
        if chosen:
            if group["status"] != "READY" or group["warnings"]:
                blockers.append("BLOCKED_TARGET_CLASS_" + name)
            changes[name] = chosen

    current_classes, parse_issues = v1.parse_classes(source_kern)
    if parse_issues:
        blockers.append("KERN_CLASS_PARSE_ISSUES")
    existing = dict(current_classes)
    if len(existing) != len(current_classes):
        blockers.append("DUPLICATE_KERN_CLASSES")
    for group in groups:
        if group["ot_class"] in changes and (
            existing.get(group["ot_class"]) != group["current_ot_members"]
        ):
            blockers.append("CLASS_MEMBERSHIP_CHANGED_" + group["ot_class"])

    missing_glyphs = sorted({glyph for values in changes.values()
                             for glyph in values} - live_glyphs)
    if missing_glyphs:
        blockers.append("SELECTED_GLYPH_MISSING_IN_FONT")
    roles = v1.pair_roles(source_kern)
    overlap_issues = v1.class_overlap_issues(current_classes, changes, roles)
    if overlap_issues:
        blockers.append("SAME_SIDE_OT_CLASS_CONFLICT")
    # V1 reports existing glyph-specific POS references for human context.
    # They are NOT class-membership conflicts by themselves. Keep every POS
    # statement byte-for-byte unchanged and verify that invariant below.
    overrides = v1.explicit_pair_overrides(source_kern, changes)

    proposed = source_kern
    render_issues = []
    try:
        proposed = v1.render_kern(source_kern, changes)
        render_issues = v1.verify_render(
            source_kern, proposed, current_classes, changes, live_glyphs
        )
        if render_issues:
            blockers.append("V1_FEA_RENDER_VERIFICATION_FAILED")
    except Exception as exc:
        render_issues.append(type(exc).__name__ + ": " + str(exc))
        blockers.append("V1_FEA_RENDER_REJECTED")

    diff = "\n".join(difflib.unified_diff(
        source_kern.splitlines(), proposed.splitlines(),
        fromfile="kern_ORIGINAL", tofile="kern_PROPOSED",
        lineterm="", n=2,
    ))
    if proposed == source_kern:
        blockers.append("NO_FEA_TEXT_CHANGE")

    return {
        "mode": "READ_ONLY",
        "stage": "OT_GUARDED_PREFLIGHT",
        "font_changed": False,
        "ready_for_writer_integration_test": not blockers,
        "apply_available": False,
        "source_mode": source_mode,
        "fontlab_major": fontlab_major,
        "selected_memberships": sum(len(values) for values in changes.values()),
        "changed_classes": len(changes),
        "blockers": list(dict.fromkeys(blockers)),
        "overlap_issues": overlap_issues,
        "render_issues": render_issues,
        "explicit_pair_overrides": overrides,
        "pos_references_severity": "INFO" if overrides else "NONE",
        "missing_glyphs": missing_glyphs,
        "original_sha256": _hash(source_kern),
        "proposed_sha256": _hash(proposed),
        "original_prefix_sha256": _hash(str(original_prefix or "")),
        "proposed_kern": proposed,
        "diff": diff,
    }


def render_preflight_report(report):
    lines = [
        "PREFLIGHT / %s / READ ONLY - NO WRITE OR SAVE" % (
            "PASS" if report["ready_for_writer_integration_test"] else "BLOCKED"
        ),
        "Selected: %d additions in %d OpenType classes" % (
            report["selected_memberships"], report["changed_classes"]
        ),
        ("FL8 COPY test writer: confirmation required; no automatic write."
         if report["ready_for_writer_integration_test"]
         else "Writer BLOCKED until preflight passes."),
        "Preflight did not modify the font. No compile, no backup file, no Save.",
        "",
        "Safety checks: " + (
            "PASS (eligible for a future guarded writer test)"
            if not report["blockers"] else "BLOCKED"
        ),
    ]
    if report["blockers"]:
        lines.extend("  - " + reason for reason in report["blockers"])
    for label, entries in (("Class collisions", report["overlap_issues"]),
                           ("FEA verification", report["render_issues"])):
        if entries:
            lines.append(label + ":")
            lines.extend("  - " + reason for reason in entries[:10])
    if report["missing_glyphs"]:
        lines.append("Missing glyphs: " + ", ".join(report["missing_glyphs"]))
    if report["explicit_pair_overrides"]:
        details = ", ".join(
            "%s (%s rules)" % (name, report["explicit_pair_overrides"][name])
            for name in sorted(report["explicit_pair_overrides"])
        )
        lines.append("INFO / existing glyph-specific POS references: " + details)
        lines.append("All POS rules are preserved; their presence alone is not a blocker.")
    lines.extend([
        "", "SOURCE SHA256: " + report["original_sha256"],
        "PROPOSED SHA256: " + report["proposed_sha256"],
        "", "FEA DIFF / SIMULATION ONLY:",
        report["diff"] or "(No FEA changes)",
    ])
    return "\n".join(lines)
