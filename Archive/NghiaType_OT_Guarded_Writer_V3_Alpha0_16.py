# -*- coding: utf-8 -*-
"""FL8 test-COPY-only OT kern membership writer with immediate readback.

No FontLab import or GUI dependency. The V1 feature reader/writer is injected.
This module never compiles a feature or saves the font. A separate original
FEA backup is created exclusively and verified BEFORE any in-memory write.
Alpha.0.17 adds exact class/glyph and readback-audit details to the receipt.
"""

from __future__ import print_function

import hashlib
import ntpath
import os


class WriteBlocked(RuntimeError):
    """A pre-write safety gate stopped the operation without modifying FEA."""


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _feature_changes(v1, original, proposed, report):
    """Independently establish an append-only, class-only FEA diff."""
    before, errors = v1.parse_classes(original)
    after, after_errors = v1.parse_classes(proposed)
    if errors or after_errors or len(before) != len(after):
        raise WriteBlocked("FEA_CLASS_PARSE_OR_COUNT_CHANGED")
    first = dict(before)
    second = dict(after)
    if len(first) != len(before) or len(second) != len(after):
        raise WriteBlocked("DUPLICATE_OT_CLASSES")
    if set(first) != set(second):
        raise WriteBlocked("OT_CLASS_NAMES_CHANGED")

    changes = {}
    for name, members in before:
        target = second[name]
        if target[:len(members)] != members:
            raise WriteBlocked("EXISTING_OT_MEMBERS_CHANGED_" + name)
        additions = target[len(members):]
        if additions:
            if len(additions) != len(set(additions)) or set(additions) & set(members):
                raise WriteBlocked("DUPLICATE_OT_MEMBERS_" + name)
            changes[name] = additions
    if not changes:
        raise WriteBlocked("NO_OT_CLASS_ADDITIONS")
    if sum(len(items) for items in changes.values()) != report["selected_memberships"]:
        raise WriteBlocked("SELECTED_MEMBERSHIP_COUNT_CHANGED")
    if len(changes) != report["changed_classes"]:
        raise WriteBlocked("CHANGED_CLASS_COUNT_MISMATCH")
    if v1.render_kern(original, changes) != proposed:
        raise WriteBlocked("FEA_IS_NOT_EXACT_CLASS_ONLY_RENDER")
    return changes


def guarded_write_to_copy(
    *, layout, v1, preflight, backup_path, fontlab_major,
    active_font_path, expected_font_path, active_master, expected_master,
    master_count, live_glyph_names, get_prefix, verify_after,
    confirmed_by_user,
):
    """Write only when ALL conditions pass; read back before allowing Save.

    A failed post-write check attempts to restore original kern text in memory.
    On any failure the caller must instruct the user NOT to save the font.
    """
    if not confirmed_by_user:
        raise WriteBlocked("EXPLICIT_USER_CONFIRMATION_REQUIRED")
    if fontlab_major != 8:
        raise WriteBlocked("FONTLAB_8_ONLY")
    if not isinstance(preflight, dict) or (
        preflight.get("mode") != "READ_ONLY"
        or preflight.get("stage") != "OT_GUARDED_PREFLIGHT"
        or not preflight.get("ready_for_writer_integration_test")
        or preflight.get("blockers")
        or preflight.get("source_mode") != "LIVE_CROSSCHECK_SNAPSHOT"
        or preflight.get("fontlab_major") != 8
    ):
        raise WriteBlocked("PREFLIGHT_NOT_APPROVED_FOR_TEST_COPY")

    if (not active_font_path or active_font_path != expected_font_path
            or "copy" not in ntpath.basename(active_font_path).lower()
            or not os.path.isfile(active_font_path)):
        raise WriteBlocked("ACTIVE_SAVED_TEST_COPY_REQUIRED")
    if (not active_master or active_master != expected_master
            or master_count != 1):
        raise WriteBlocked("SINGLE_ORIGINAL_MASTER_REQUIRED")
    if not callable(get_prefix) or not callable(verify_after):
        raise WriteBlocked("READBACK_VERIFIERS_REQUIRED")
    if not all(callable(getattr(v1, name, None)) for name in (
        "read_kern", "write_kern", "parse_classes", "render_kern",
        "verify_render", "pos_lines",
    )):
        raise WriteBlocked("VALIDATED_V1_READER_WRITER_REQUIRED")

    original = v1.read_kern(layout)
    proposed = preflight.get("proposed_kern")
    if not isinstance(original, str) or not isinstance(proposed, str):
        raise WriteBlocked("FEA_MUST_BE_TEXT")
    if (_sha(original) != preflight.get("original_sha256")
            or _sha(proposed) != preflight.get("proposed_sha256")):
        raise WriteBlocked("KERN_SOURCE_OR_PROPOSAL_CHANGED")

    changes = _feature_changes(v1, original, proposed, preflight)
    if live_glyph_names is None:
        raise WriteBlocked("LIVE_FONT_GLYPH_SET_REQUIRED")
    available = set(live_glyph_names)
    if not {name for items in changes.values() for name in items}.issubset(available):
        raise WriteBlocked("SELECTED_GLYPH_MISSING_IN_LIVE_FONT")
    issues = v1.verify_render(original, proposed, v1.parse_classes(original)[0],
                              changes, available)
    if issues or v1.pos_lines(original) != v1.pos_lines(proposed):
        raise WriteBlocked("CLASS_ONLY_FEA_VERIFICATION_FAILED")

    prefix_before = get_prefix()
    if not isinstance(prefix_before, str) or (
        _sha(prefix_before) != preflight.get("original_prefix_sha256")
    ):
        raise WriteBlocked("FEA_PREFIX_CHANGED_SINCE_PREFLIGHT")

    backup = os.path.abspath(str(backup_path or ""))
    if (not backup_path or not backup.lower().endswith(".fea")
            or os.path.normcase(backup) == os.path.normcase(
                os.path.abspath(active_font_path))):
        raise WriteBlocked("ORIGINAL_FEA_BACKUP_PATH_REQUIRED")
    if os.path.lexists(backup):
        raise WriteBlocked("BACKUP_PATH_ALREADY_EXISTS")

    # The backup can never silently overwrite an existing user's file.
    # No FontLab write occurs if this or the byte-for-byte readback fails.
    with open(backup, "x", encoding="utf-8", newline="") as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    with open(backup, "r", encoding="utf-8", newline="") as stream:
        if stream.read() != original:
            raise WriteBlocked("ORIGINAL_FEA_BACKUP_VERIFICATION_FAILED")

    result = {
        "status": "BACKUP_VERIFIED_NO_FONT_WRITE",
        "backup_path": backup,
        "backup_sha256": _sha(original),
        "source_sha256": _sha(original),
        "proposed_sha256": _sha(proposed),
        "memberships": sum(len(items) for items in changes.values()),
        "classes": sorted(changes),
        "additions": {name: list(changes[name]) for name in sorted(changes)},
        "original_pos_rules": len(v1.pos_lines(original)),
        "proposed_pos_unchanged": True,
        "other_font_state_readback": "NOT_VERIFIED",
        "readback_exact": False,
        "rollback_exact": None,  # Only kern text + FEA prefix, NOT full font.
        "font_saved": False,
        "feature_compiled": False,
        "write_api": "",
        "failure": "",
    }

    # Detect any change during the backup file dialog/work before mutation.
    if v1.read_kern(layout) != original or get_prefix() != prefix_before:
        raise WriteBlocked("KERN_CHANGED_WHILE_BACKING_UP")

    try:
        result["write_api"] = v1.write_kern(layout, proposed)
        readback = v1.read_kern(layout)
        if readback != proposed:
            raise RuntimeError("FEA_READBACK_NOT_EXACT")
        if get_prefix() != prefix_before:
            raise RuntimeError("FEA_PREFIX_CHANGED_AFTER_WRITE")
        after_issues = verify_after()
        if not isinstance(after_issues, (tuple, list)):
            raise RuntimeError("POST_WRITE_READBACK_AUDIT_UNAVAILABLE")
        if after_issues:
            raise RuntimeError("FONT_STATE_CHANGED_AFTER_WRITE: " +
                               ", ".join(str(item) for item in after_issues))
        result["other_font_state_readback"] = "PASS"
        result["readback_exact"] = True
        result["status"] = "READBACK_PASS_NOT_SAVED_OR_COMPILED"
    except Exception as exc:
        result["failure"] = type(exc).__name__ + ": " + str(exc)
        try:
            v1.write_kern(layout, original)
            result["rollback_exact"] = (
                v1.read_kern(layout) == original and get_prefix() == prefix_before
            )
        except Exception as rollback_exc:
            result["failure"] += (" / rollback: " + type(rollback_exc).__name__
                                  + ": " + str(rollback_exc))
            result["rollback_exact"] = False
        result["status"] = (
            "KERN_ROLLBACK_EXACT_DO_NOT_SAVE" if result["rollback_exact"]
            else "ROLLBACK_UNVERIFIED_DO_NOT_SAVE"
        )
    return result


def render_writer_result(result):
    lines = [
        "OT GUARDED WRITE / " + result["status"],
        "FONT NOT SAVED / NO COMPILE",
        "Original kern backup: " + result["backup_path"],
        "Backup SHA256: " + result["backup_sha256"],
        "Changes: %d glyph memberships / %s OT classes" % (
            result["memberships"], len(result["classes"])
        ),
        "Exact class/glyph additions:",
    ]
    for name, glyphs in sorted(result["additions"].items()):
        lines.append("  @%s / +%d: %s" % (name, len(glyphs), ", ".join(glyphs)))
    lines.extend([
        "Existing POS rules preserved in proposal: %s (%d rules)" % (
            "YES" if result["proposed_pos_unchanged"] else "NO",
            result["original_pos_rules"]
        ),
        "Writer API: " + str(result["write_api"]),
        "FEA readback exact: " + str(result["readback_exact"]),
        "Other font state readback: " + result["other_font_state_readback"],
        "Proposed SHA256: " + result["proposed_sha256"],
    ])
    if result["failure"]:
        lines.append("Write/readback issue: " + result["failure"])
        lines.append("Rollback exact: " + str(result["rollback_exact"]))
    if result["status"] == "READBACK_PASS_NOT_SAVED_OR_COMPILED":
        lines.append("NEXT: Save the disposable COPY manually, close and reopen it.")
        lines.append("Do NOT click Play/Create kern before reopen verification.")
        lines.append("After reopening, Cross-check Native/OT; 0 DIFFERENT is required.")
    else:
        lines.append("DO NOT SAVE this font; close WITHOUT saving and inspect backup.")
    return "\n".join(lines)
