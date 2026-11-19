NghiaType 1.9.3 Beta
Released: 19.11.2026
Primary target: FontLab 8 / PythonQt

UPDATE: CROSS-CHECK WORKSPACE + CONTINUOUS NATIVE -> OPENTYPE FLOW
- HOTFIX: corrected a FontLab PythonQt property/method mismatch in the
  Cross-check glyph-list height calculation. This previously raised
  TypeError: 'int' object is not callable while selecting a class.
- Rebuilt the Cross-check tab around the reference layout: a compact
  READ ONLY summary, the Native/OT comparison on the left (7:5 split),
  and an inspector for differing glyphs on the right.
- Final layout polish: the status badge stays at the right edge of the
  inspector header without squeezing the class title into extra lines;
  the pink explanation has clearance below the glyph table.
- MATCH/DIFFERENT colors, a class-by-class comparison and a short
  Vietnamese explanation make the results easier to understand.
- The right inspector keeps its pink explanation directly below the
  relevant glyph rows; longer difference lists remain scrollable.
- The Cross-check tab cannot write to Native or OpenType. Its button
  only navigates to the separate OT Sync & Apply step.
- After a successful, verified Native write, users may Cross-check
  and continue to guarded OT review in the SAME FontLab session.
  No intermediate Save, close or reopen is imposed by this workflow.
- OT preflight still re-reads the current Native groups/pairs and live
  kern feature and checks the exact selection before any OT write.
- No change to the Native or OT writer implementation. Explicit COPY
  confirmation, OT backup, preflight, and writer readback stay required.
- No automatic Compile or Save; the user saves the test COPY manually.

IMPORTANT TEST NOTE
Offline regression tests: 92 PASS (including simulated PythonQt property
and PyQt method-style glyph counts). The new layout and same-session
Native -> OT flow have NOT been tested in a real FontLab 8 host yet.
Please use a DISPOSABLE, already-saved COPY with a separate backup.
If any write/readback fails, close the test font WITHOUT saving;
partial in-memory changes may have occurred.

HOW TO TEST THE WORKFLOW
1. Extract ALL included files to a new clean folder. Do not mix with
   historical scripts that have similar names.
2. Open a disposable saved .vfc COPY in FontLab 8 and run
   NghiaType_1.9.3_Beta.py.
3. On Native Classes, Scan, select glyphs, Check selection and confirm
   Add to Native. Wait for the verified-readback result.
4. WITHOUT closing or saving yet, use Cross-check. Check the short
   summary and the right-side glyph comparison; no edits occur here.
5. Continue to OT Sync & Apply. Review selected additions and run
   Check changes. Only apply if the guard reports a pass, and confirm
   the requested new .fea backup.
6. After verified OT readback, manually Save your test COPY. If anything
   differs from expectation or verification fails, DO NOT Save.

OpenType feature exploration outside kerning and FL9 write support
remain future work.
