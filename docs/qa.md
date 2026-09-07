# Candidate QA — September 7, 2026

The implementation is based on Scoring Matrix commit `ff874bd09400543468176c618de93e77aec279c6`. Matrix version remains 1.0; this is a private beta candidate, not a published release.

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

The preview is a direct capture from the running QA panel. It is not a generated mockup. Full-desktop QA captures remain outside the plugin repository and should not be published.
