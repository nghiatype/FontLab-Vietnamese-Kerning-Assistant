# NghiaType Development Log

This log records the Kerning Studio milestones, release-level changes, and safety constraints. It is intended to accompany [README.md](README.md).

## 1.9.5 — 20 November 2026

**Status: Kerning Studio workflow finalized.**

### Added and refined

- Completed the three-step **Native classes → Cross-check → OpenType sync** workflow.
- Simplified workspace lists: glyph names remain prominent, Native side (`Left` / `Right`) and `+N` counts use compact capsules, and individual rows have subtle dividers.
- Gave Cross-check results clear priority: **In sync** uses a green capsule with white text; differences and manual-review states use separate, readable warning colors.
- Moved explanations for shared OpenType classes into **separate warning cards**, instead of burying critical advice in a long paragraph.
- Improved selection lock feedback with a system lock icon and genuinely disabled/visually muted workspace controls. Locked list backgrounds stay white, avoiding a rectangular pink overlay inside rounded panels.
- Removed redundant table headings, repeated status text, distracting bottom notes, and the old **NATIVE + OPENTYPE** title chip.
- Set a stable product subtitle: **“Keep your Native and OpenType kerning classes in sync.”**
- Kept technical reports accessible through contextual **Report / Details / FEA details** actions.

### OpenType confirmation and backup UX

- **Changed the order:** show the human-readable confirmation dialog **before** opening the file-location picker.
- Explicitly describe the backup as a separate **OpenType `kern` `.fea` file**, not a font save operation.
- After confirmation, users choose a **new backup destination**; only then can the guarded OpenType update proceed.
- Canceling confirmation or the file picker stops the operation without adding glyphs.
- Retained required user acknowledgment, fresh preflight checks, exact-result verification, and a manual font Save.

### Reliability fixes carried into 1.9.5

- Kept the **Scan again** action in the main workflow guidance instead of allowing a duplicate button to float into the page header after a completed round.
- Preserved the completed OpenType state until the user intentionally starts a new Native scan.
- Prevented verified readback rows from becoming editable selections again.
- Corrected **Close** button callbacks in secondary dialogs to avoid passing PythonQt's `clicked(False)` argument to a no-argument `accept()` method.
- Removed Qt's unused `?` window-help hint from secondary and confirmation dialogs.
- Fixed duplicate/overlapping status capsules by using one rendered badge per result cell.
- Avoided graphics-opacity effects that previously left stale table content painted over another workflow tab.

### Safety boundaries retained

- **Native V2:** continues using the established scanner/planner and guarded writer; selected memberships must pass a fresh live safety check before applying.
- **Cross-check:** remains read-only and does not authorize any writer operation by itself.
- **OpenType sync:** still requires an eligible, reviewed selection; matching preflight data; a new `.fea` backup path; a guarded FontLab 8 test-copy writer; and post-write readback verification.
- **No automatic Save or Compile** in either writer. An unverified or potentially partial write results in a **DO NOT SAVE** state.
- Shared/ambiguous classes remain blocked from automatic synchronization.

### Verification

- Nine offline regression suites passed in the development workspace, including selection locking, cancellation of both confirmation stages, Native re-scan, row and capsule rendering logic, round-completion state, and the backup-dialog sequence.
- The FontLab/PythonQt rendering and full end-to-end font-writing flow must still be exercised on a **disposable FontLab 8 test copy** when moving the release to a different environment.

## 1.9.4 Beta — 18–20 November 2026

**Focus: UI/UX refinement and consolidated Kerning Studio shell.**

- Consolidated Native classes, Cross-check, and OpenType sync under one desktop workflow.
- Introduced contextual guidance cards, manual action states, separate reports, and clearer read-only summaries.
- Iteratively simplified colors, class labels, selection checkboxes, table layout, window sizing, and result feedback using the Material 3 light theme.
- Added explicit **Check → Lock → Confirm** behavior for Native selection and retained independent OpenType preflight safeguards.
- Tested completion and re-scan behavior to avoid leaving stale **Add glyphs** actions visible after OpenType sync.

## Earlier development milestones — November 2026

- Developed and tested **Native Kerning V2** read/plan/write operations for existing FontLab Native classes.
- Built read-only **Native ↔ OpenType `kern` class** Cross-check with side-aware mapping.
- Added selective OpenType preview, guarded preflight, backup creation, and exact readback for FontLab 8 copies.
- Separated the GUI shell from its companion V1/V2/V3 engines so that UI changes do not silently replace safety-sensitive core logic.
- Investigated FontLab 9 compatibility; Native/OT guarded writing remains **unverified/experimental** there.

## Known limits / next review

- Support and test coverage for **FontLab 9 writing** remain open work.
- Complex text `.fea` constructs and compiled GPOS lookups are outside the guaranteed Cross-check scope.
- Re-test against a fresh disposable copy after changing FontLab builds, companion engines, or native-feature regeneration behavior.

---

**Release principle:** Never let a prettier interface weaken a writer's permission checks, backups, manual confirmation, or readback requirements.
