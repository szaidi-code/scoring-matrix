# Changelog

## 0.1.0 - 2026-11-25

- Add local workload guidance, manual compatibility checks, snapshot comparisons, an optional CPU test, and redacted exports without changing matrix 1.0.
- Keep compatibility evidence per computer, mark results stale when hardware, memory, firmware, drivers or kernel change, and preserve the score if advisor state is unreadable.
- Validate and bound local advisor state, serialize private atomic writes, bound shell payloads, and make redacted exports atomic.
- Publish the first stable release following beta.3.

## 0.1.0-beta.3

- Modernize widget motion for Omarchy 4.5: route all QML animations through `Style.duration(...)` and `Style.easeOut` under 300ms so `omarchy toggle animations` disables transitions cleanly.
- Harden UI text safety: set `textFormat: Text.PlainText` explicitly on `ScoreRing.qml` labels, neutralize markup/control characters and bound lengths before passing dynamic text to `WidgetButton`, and validate report fields strictly on load.
- Add live localization and locale support: ship `i18n/en.json` via `Commons.Translations`, format displayed numerals with `Commons.I18n.formatNumber`, format saved timestamps with `Qt.locale(Commons.I18n.formatLocale)`, and mirror Left/Right category navigation via `Commons.Util.readingKey`.
- Add QML safety, motion, translation, and version-parity regression tests (`tests/test_qml_contract.py`).

## 0.1.0-beta.2

- Native Omarchy bar widget with six score categories, explanations and local report loading.
- Evidence summaries distinguish complete, incomplete, unknown-architecture and virtual-machine snapshots.
- Validated offline comparisons select the latest snapshot for each computer label.
- Honor the shell font family, base size and spacing; close the popup using the bar button, Escape or an outside click.
- Optional scan once per boot, disabled by default, with caching and locking across multiple displays.
- MIT license; terminal application installation and removal preserve saved reports.

Matrix 1.0 remains a provisional capacity and compatibility estimate with an automatic ceiling of 95. Hardware collection requires Linux.
