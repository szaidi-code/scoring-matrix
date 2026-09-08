# Plugin review — September 7, 2026

Scoring Matrix should focus on explainable hardware readiness and local comparisons. A capacity estimate, a measured performance benchmark, and a live utilization monitor answer different questions. Combining all three into one score would make the result harder to interpret.

| Aspect | Scoring Matrix | OmaRank | Hardware Monitor |
|---|---|---|---|
| Primary question | What hardware is present, and what still needs checking? | What enthusiast tier does this configuration resemble? | What is using resources now? |
| Engine | Standard-library Python; separate Windows collector | Rust engine with model/driver-based scoring rules | QML/JavaScript reads from procfs/sysfs, discovery helper, NVIDIA subprocess |
| Presentation | Six category cards, score rings, evidence and reasons | Tier titles, component summaries, world-rank display | Live dials, temperatures, history and configurable bar readouts |
| Comparison | Local reports with explicit matrix version | Rank derived from score against a fixed population in inspected source | No installation-readiness ranking |
| Useful pattern | Transparent rules and saved evidence | Concise component summaries and an engaging overview | Native shell integration and explicit unavailable-sensor states |

Inspected repositories: Scoring Matrix at `278d2dbb0ca598756c8f14c82980c7e0b6a87334`, OmaRank at `9bf1542b8f00ea8ecb88b2e3d4dd19d6d50c3492`, and Hardware Monitor at `f1373fba766fc1702e96eef0c9fe844ffeaafddb`. No source or image assets were copied from the comparison plugins. OmaRank's inspected HEAD is newer than its marketplace-listed commit `6cca69e816555ff2046619f89d3787e315f2b150`.

## Findings and implemented changes

1. Saved-report loading previously accepted six arbitrary categories as long as the sum matched. A shared validator now checks ordered category names, v1 maxima and automatic ceilings, numeric types, coverage, subtotal consistency, timestamps, notes and inventory shape. This protects display consistency; it does not authenticate the report.
2. Comparison previously sorted every file by score. It now selects the newest snapshot per exact label and keeps incomplete, unknown-architecture and detected-VM results out of the candidate ranking. The matrix weights remain unchanged for existing Linux/Windows reports.
3. The shell previously received the complete hardware inventory and duplicated a basic mouse/text bar button. It now receives a compact view and uses Omarchy's native button, including theme, tooltip and orientation-aware sizing. The panel shows evidence status even when coverage is complete.
4. A missing observation now has a visible “Partial evidence” card state. Unknown is not presented as confirmed failure or success. The selected-disk setting reaches the scanner through an argument array and applies only on explicit rescan.
5. Snapshot files are staged privately and renamed individually. Saved report reads have a size limit, shell processes have deadlines, and tests exercise malformed data, Windows report shapes, deduplication and interrupted saves.

## What the comparison source actually does

[OmaRank](https://github.com/ozdil/omarchy-omarank) calls its result a benchmark in the README, but the inspected `src/score.rs` computes category estimates from inventory and model heuristics. Its `calculate_global_rank` uses a score-to-percentile formula and `total_machines = 12480`. That world-rank number should not be treated as a measured live population statistic. Scoring Matrix should show only local comparisons unless a real, documented dataset exists.

[Hardware Monitor](https://github.com/meviusisback/omarchy-hw-monitor) offers useful live resource views. Its `Service.qml` uses direct virtual-file reads after discovery and a separate NVIDIA path. That is a good complement to Scoring Matrix; duplicating its background telemetry would add work without improving installation evidence.

The marketplace listing and a baseline scan are not guarantees of runtime correctness. Review source, validate the exact candidate, and test in the running Omarchy shell.

## Next product step

A future matrix version could add dated, user-recorded functional checks for acceleration, Wi-Fi, Bluetooth, audio, suspend and external displays. Those checks should retain kernel/driver context and expire when relevant hardware changes. Measured performance should be a separate opt-in benchmark suite with repeatability rules. Neither should silently inflate matrix 1.0 or retroactively make old reports comparable.
