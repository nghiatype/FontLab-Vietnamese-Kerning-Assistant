# -*- coding: utf-8 -*-
#FLM: NghiaType FL9 TypeRig Detached Writer Probe (Experimental)
"""FL9 research: one isolated, documented TypeRig pKerning.addGroup call.

STRICT SCOPE:
  * Creates a BRAND-NEW, UNSAVED fgFont with synthetic glyphs in memory.
  * Never calls CurrentFont, opens files, saves, updates, exports, or writes.
  * Does not access flWorkspace, a font package, or any live font document.
  * Calls a group writer ONLY on that fresh detached font, and ONLY if TypeRig
    can be imported. Does not guess native fgKerning.addGroup argument formats.
  * Does not delete, rename, replace, or edit existing kerning groups.

The TypeRig proxy is an external dependency. Its internal implementation has
not been verified on this exact FL9 build. Close important font documents and
save unrelated work before running; experimental native APIs may still crash.

This is NOT a production Native Writer. Report the complete output.
"""

import sys

TEST_KEY = "NT_FL9_DETACHED_LEFT"
TEST_FONT_NAME = "NT FL9 Detached TypeRig Probe"
TEST_GLYPHS = ("A", "Aacute", "Agrave")
INITIAL_MEMBERS = ("A", "Aacute")


def load_type_rig_proxy():
    """Use known proxy paths only; no installation or package mutation."""
    attempts = (
        "typerig.proxy.fl.objects.kern",
        "typerig.proxy.objects.kern",
    )
    for module_name in attempts:
        try:
            from importlib import import_module
            module = import_module(module_name)
            proxy = getattr(module, "pKerning", None)
            if proxy is not None:
                print("TypeRig proxy found:", module_name)
                return proxy
            print("TypeRig module has no pKerning:", module_name)
        except Exception as exc:
            print("TypeRig path unavailable:", module_name,
                  type(exc).__name__, str(exc))
    return None


def readback(font):
    """Verify both native representations and unchanged explicit-pair count."""
    all_kern_groups = dict(font.kerning.groups.items())
    all_native_groups = dict(font.groups.items())
    print("Kerning group keys:", sorted(all_kern_groups))
    print("Native group keys:", sorted(all_native_groups))
    print("Explicit pair count:", len(list(font.kerning.items())))

    value = all_kern_groups.get(TEST_KEY)
    print("Kerning raw group:", repr(value))
    kern_ok = (
        isinstance(value, (tuple, list)) and len(value) == 2
        and list(value[0]) == list(INITIAL_MEMBERS)
        and value[1] == "KernLeft"
    )

    group = all_native_groups.get(TEST_KEY)
    if group is None:
        print("Native raw group: MISSING")
        native_ok = False
    else:
        members = [str(group[i]) for i in range(len(group))]
        print("Native group type:", type(group).__name__)
        print("Native group mode:", str(group.mode))
        print("Native group members:", members)
        native_ok = members == list(INITIAL_MEMBERS) and bool(group.isLeft())

    only_one = (set(all_kern_groups) == {TEST_KEY}
                and set(all_native_groups) == {TEST_KEY})
    pairs_empty = len(list(font.kerning.items())) == 0
    print("KERNING READBACK:", "PASS" if kern_ok else "FAIL")
    print("NATIVE READBACK:", "PASS" if native_ok else "FAIL")
    print("NO EXTRA GROUPS:", only_one)
    print("NO EXPLICIT PAIRS:", pairs_empty)
    return kern_ok and native_ok and only_one and pairs_empty


def main():
    print("=== NGHIATYPE FL9 / TYPERIG DETACHED WRITER / ALPHA ===")
    print("Python:", sys.version.split()[0])
    print("SCOPE: DETACHED FONT ONLY; NO CurrentFont / Save / file writes")

    # Import TypeRig before doing any mutations. If unavailable, stop cleanly.
    proxy_class = load_type_rig_proxy()
    if proxy_class is None:
        print("STOP: TypeRig pKerning unavailable; NO MUTATIONS ATTEMPTED")
        return

    try:
        import fontgate
        font = fontgate.fgFont(TEST_FONT_NAME)
        if getattr(font, "path", ""):
            print("STOP: detached font unexpectedly has a path")
            return
        if list(font.groups.items()) or list(font.kerning.groups.items()):
            print("STOP: detached font is not empty")
            return

        for name in TEST_GLYPHS:
            glyph = font.createGlyph(name)
            if glyph is None or str(glyph.name) != name:
                print("STOP: synthetic glyph creation failed:", name)
                return
        print("Detached synthetic glyphs:", list(TEST_GLYPHS))
        print("Detached font path empty:", not bool(getattr(font, "path", "")))
    except Exception as exc:
        print("STOP: synthetic font setup:", type(exc).__name__, str(exc))
        return

    # A documented TypeRig wrapper call, NOT a guessed native API signature.
    # We pass the detached font's fgKerning object explicitly. Because the
    # external TypeRig implementation is unverified here, this is an
    # experimental safety boundary, not a guarantee about library internals.
    print("--- ONE TYPERIG addGroup CALL / DETACHED ONLY ---")
    print("Proposed:", TEST_KEY, list(INITIAL_MEMBERS), "L")
    try:
        proxy = proxy_class(font.kerning)
        proxy.addGroup(TEST_KEY, list(INITIAL_MEMBERS), "L")
    except Exception as exc:
        print("WRITER ERROR:", type(exc).__name__, str(exc))
        print("STOP: no alternate guesses and no live-font Apply")
        return

    try:
        if readback(font):
            print("DETACHED CREATE PASS: native + kerning exact dual readback")
        else:
            print("DETACHED CREATE NOT VERIFIED: do not proceed to Apply")
    except Exception as exc:
        print("READBACK ERROR:", type(exc).__name__, str(exc))

    print("=== END / NO SAVE / NO LIVE FONT MODIFICATION ===")


if __name__ == "__main__":
    main()
