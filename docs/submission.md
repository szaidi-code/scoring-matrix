### Repository URL

https://github.com/szaidi-code/scoring-matrix

### Category

Hardware

### Tags

bar, quickshell, system

### Suggest a missing tag

_No response_

### Maintainer notes

Omarchy Hardware Score 0.1.0 is a native Omarchy bar widget for local hardware inventory and provisional capacity and compatibility estimates. It provides six category cards, evidence summaries, explanations, saved snapshots, offline comparisons, workload guidance, user-recorded compatibility checks, an optional CPU microbenchmark and redacted export. It follows the shell's font, theme, reduced-motion, and language/locale settings.

Requires the native Omarchy shell plugin API (beta baseline tested on Omarchy 4.5.0-3), Python 3.9+ and util-linux. Optional pciutils and usbutils improve inventory names. No telemetry, network calls from the collector, sudo, disk benchmarks, or firmware changes. Optional scan once per boot is disabled by default and serialized across multiple displays. Reports stay under the user's XDG state directory and are preserved on removal. Complete target-hardware compatibility checks before relying on an installation recommendation.

MIT licensed. The root preview shows the actual widget with an anonymous computer label. The optional terminal application installer is separate from plugin installation. Matrix 1.0 is an inventory estimate, not a performance benchmark or certification.

### Submission checklist

- [x] The repository is public and contains installation and removal instructions.
- [x] I have documented the plugin license and any external dependencies.
- [x] I confirm that I own or have permission to submit this plugin and its preview assets.
- [x] The plugin does not overwrite user configuration without explicit consent.
- [x] I understand that approval is for listing and is not a security review.
