# Candidate QA — September 7, 2026

The implementation is based on Scoring Matrix commit `278d2dbb0ca598756c8f14c82980c7e0b6a87334`. Matrix version remains 1.0; this is a beta candidate, not a published release.

## Results

| Check | Result |
|---|---|
| Python unit suite on Windows | 21 tests passed |
| Same suite on Omarchy 4.0.2, x86-64 | 21 tests passed |
| Omarchy plugin manifest validation | Passed on staged and installed candidate |
| Python syntax and Git whitespace | Passed |
| Existing local reports | Loaded and validated without rescanning on open |
| R shortcut / read-only rescan | Saved a fresh snapshot; score stayed 48/100, evidence 100/100 |
| Category navigation | Right arrow selected Memory and changed the explanation |
| N shortcut | Notes opened and wrapped within the scrollable panel |
| Escape and shell hide/summon | Exercised successfully |
| Shell restart and plugin rescan | Plugin loaded; shell remained responsive |
| Invalid explicit whole disk | Clear error, nonzero exit, no report directory created |
| Live visual inspection | Panel, evidence summary, category cards, reasons, notes and footer inspected on a 2560×1600 display at 1.25 scale; observed under two active theme palettes |
| Plugin runtime errors | No matching Widget.qml, TypeError, ReferenceError or binding-loop errors in the inspected current shell log |

The standalone `qmllint -I "$OMARCHY_PATH/shell"` invocation exited zero but warned that `qs.Ui` and `qs.Commons` could not be resolved. This is not a clean lint result. The candidate was then loaded and exercised in the real shell, which resolves those imports. The generic `shell call ... refresh` route returned `unknown` for this bar widget; rescan was verified through the actual R shortcut instead.

## Preservation and limits

The installed QA plugin already had uncommitted changes. Its Widget.qml and collector matched the current upstream versions; a complete copy of the plugin and shell configuration was made before replacement. The remote backup is under `~/.local/state/scoring-matrix/qa-backup-20260907-154652/`. The candidate remains installed for further testing; existing reports were preserved.

Before a public release, still exercise disable/re-enable/removal, multiple monitors, a vertical bar, smaller display scales, and real Windows hardware collection. Synthetic Windows-shaped reports are covered by automated tests; this pass did not collect hardware on Windows. No performance benchmark or functional hardware certification was performed. The deadline failure path was not tested by waiting out a deliberately stalled process.

Visual verification used actual running panels. QA screenshots are not included in the public repository.

## Font-setting follow-up

Replaced fixed text sizes with `Style.font` tokens, applied the shared font family to the ring numerals, and scaled geometry with `Style.space`. Verified the running panel with `base-size = 9` on QA laptop A (2560×1600 at 1.6 scale) and QA laptop B (1920×1080 internal display at 1.0 scale, with an additional display connected). Both plugin manifests validated and both shells responded after reload. Screenshots were inspected for wrapping, clipping and footer visibility. No widget or ring runtime errors appeared in the inspected startup logs; QA laptop B logged an unrelated duplicate clock IPC handler warning.

Before build unification, QA laptop B ran a locally customized older plugin with startup scanning. Applied the typography changes and close-button removal to its existing QML while retaining its collector and startup behavior. That deployment was not a byte-identical checkout of this repository. Original QML files were backed up under `~/.local/state/scoring-matrix/font-backup-*` on each device.

## Unified startup option

The shared widget now exposes `scanOnStartup` (default false), backed by a validated boot-id and disk-selection cache. Focused tests cover restart reuse, new boots, changed disks, corrupt reports, scanner failure, and missing boot identity. Manual rescans still create a fresh snapshot. QA deployments use Git checkouts of the same main commit; QA laptop B enables startup scanning and QA laptop A retains manual scanning.

## Marketplace preparation

The unified runtime at `17cd4ce804c0cbadf0c51bf759184803b0685533` passed all 26 tests on both QA laptop A and QA laptop B. Both installed checkouts were clean and their widget, ring, collector and manifest hashes matched. Screenshots on both internal displays confirmed the shared layout and font-size behavior. QA laptop B enables startup scanning; QA laptop A retains manual scans. Multi-monitor startup requests are serialized with a file lock.

The submission-preparation changes add licensing and release documentation, include LICENSE in the optional installer, and align its version marker with the manifest. Local Windows validation passed 25 tests with the Linux locking test skipped. A fresh staging check could not connect to either QA machine over SSH; the prior 26-test Linux/runtime results above apply to the unified build before these packaging changes.

The marketplace baseline analysis was run locally against the candidate files using marketplace commit `d5ac6f9b` on September 7, 2026. It returned `review-required`, `blocksApproval: false`, and no unsafe-execution findings. Capability flags concern the optional installer, documented repository installation, and package installation inside GitHub CI (including broad keyword matches in documentation). This is a local precheck, not official marketplace approval or a complete security audit.
