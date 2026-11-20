# NghiaType

**Keep your Native and OpenType kerning classes in sync.**

NghiaType is a PythonQt utility for **FontLab 8**. Its Kerning Studio provides a guided workflow for finding missing glyphs in Native kerning groups, comparing them with OpenType `kern` classes, and carefully updating eligible classes.

**Current version:** `1.9.5` · **Released:** 20 November 2026  
**Status:** Kerning Studio workflow completed and tested on FontLab 8; FontLab 9 compatibility remains experimental.

> [!CAUTION]
> Use a **saved test COPY** of your font, and keep a separate backup of the original. The guarded writers are designed for FontLab 8 test copies. They do not automatically save or compile the font. If verification fails, **close the test copy without saving**.

## Kerning Studio

| Step | Module | What it does |
| --- | --- | --- |
| 01 | **Native classes** | Scan existing Native kerning classes, preview missing glyphs, select them, perform safety checks, and add the approved members. |
| 02 | **Cross-check** | Read-only comparison of Native groups against text-based OpenType `kern` classes, with clear **In sync**, **Differs**, and **Needs review** statuses. |
| 03 | **OpenType sync** | Select eligible missing OpenType glyphs, run preflight, back up the current `kern` feature as `.fea`, apply additions, and verify the result. |

The interface preserves selections while switching classes. A selection is locked after safety checks; choose **Edit selection** to change it and check again. After a successful round, use **Scan again** to start a fresh scan.

### Safety-first OpenType backup flow

1. Review the glyph count and affected OpenType classes.
2. Read and acknowledge the confirmation dialog.
3. Choose **where to save a new `.fea` backup** of the original OpenType `kern` feature.
4. NghiaType repeats its safety checks, creates the backup, applies eligible class additions, and verifies them.
5. Save the **test font copy manually** in FontLab only after a successful verified result.

The `.fea` file is a backup of the **OpenType `kern` feature text**, **not** a saved copy of the font. Canceling either dialog stops the operation before glyphs are added.

### Shared classes and manual review

One OpenType class can be referenced on both kerning sides. If an update could affect multiple Native groups, NghiaType marks the class as requiring review and explains why. Such classes are **not automatically unlocked or force-synced**. Review them in OpenType Studio before changing them manually.

## Requirements

- FontLab **8** with its bundled Python / PythonQt environment.
- A **saved test copy** of the active font; the guarded writers require the filename to indicate a copy.
- A backup of the original font. Native and OpenType writes require their respective safety checks and user confirmation.
- The companion NghiaType scripts listed below.

### Companion scripts

The main `NghiaType_1.9.5.py` GUI is a **shell**, not a standalone implementation of every scanner and writer. It loads these exact-named modules:

```text
NghiaType_1.9.5.py
NghiaType_Native_Kerning_V2_GUI_Alpha1.py
FontLab_Vietnamese_Kerning_Assistant_v1.py
NghiaType_Kerning_Crosscheck_V3_Alpha0_11.py
NghiaType_OT_Sync_Preview_V3_Alpha0_12.py
NghiaType_OT_Guarded_Preflight_V3_Alpha0_14.py
NghiaType_OT_Guarded_Writer_V3_Alpha0_16.py
```

Place the available companion scripts beside the main file. If a required module cannot be found there, NghiaType asks you to locate the **exact matching filename**. Keep these engine files at their tested versions; do not substitute a similarly named script.

## Run in FontLab 8

1. **Back up your original font**, then open a separately saved **COPY** in FontLab 8.
2. Open FontLab's **Macro** panel and run `NghiaType_1.9.5.py`.
3. In **Native classes**, select **Scan Native classes**. Review the proposed members before using **Check selection** and confirming additions.
4. In **Cross-check**, compare the Native and OpenType classes. Read the separate warnings for ambiguous or shared classes.
5. In **OpenType sync**, choose the eligible glyphs, run the safety check, confirm the plan, select a new `.fea` backup destination, and let NghiaType verify the result.
6. **Save the test font manually** only when the result explicitly reports a successful verification.

You can inspect additional read-only information through the **Report**, **Details**, and **FEA details** controls. Native preview information can also be exported as JSON.

## Important limitations

- **FontLab 9:** experimental compatibility only; guarded write support is not established for FL9.
- **OpenType scope:** Cross-check uses a text `kern` reader with a deliberately limited understanding of class declarations and pair-position rules. It does **not** audit every possible OpenType syntax or compiled GPOS behavior.
- **No silent writes:** scanning, Cross-check, previewing an older `.fea`, and exporting reports do not themselves add glyphs.
- **No automatic Save/Compile:** successfully updating in-memory font data is not the same as saving a font file to disk.
- **Verification failures:** treat the test copy as unsafe to save. Close it without saving, inspect the technical report, and begin again from a clean copy.

## Release history

See [DEVLOG.md](DEVLOG.md) for the 1.9.5 release notes, interface decisions, safety boundaries, and development milestones.

---

*NghiaType · FontLab workflow tools · Version 1.9.5*
