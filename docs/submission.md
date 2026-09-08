### Repository URL

https://github.com/szaidi-code/scoring-matrix

### Category

Hardware

### Tags

bar, quickshell, system

### Suggest a missing tag

_No response_

### Maintainer notes

Scoring Matrix 0.1.0-beta.2 is a native Omarchy bar widget for local hardware inventory and provisional capacity and compatibility scores. It provides six category cards, evidence summaries, explanations, saved snapshots and offline comparisons. It follows the shell's font and theme settings.

Requires the native Omarchy shell plugin API (tested on Omarchy 4.0.2), Python 3.9+ and util-linux. Optional pciutils and usbutils improve inventory names. No telemetry, network calls from the collector, sudo, disk benchmarks, or firmware changes. Optional scan once per boot is disabled by default and serialized across multiple displays. Reports stay under the user's XDG state directory and are preserved on removal.

MIT licensed. No preview asset is included. The optional terminal application installer is separate from plugin installation. Matrix 1.0 is an inventory estimate, not a performance benchmark or certification.

### Submission checklist

- [x] The repository is public and contains installation and removal instructions.
- [x] I have documented the plugin license and any external dependencies.
- [x] I confirm that I own or have permission to submit this plugin and its preview assets.
- [x] The plugin does not overwrite user configuration without explicit consent.
- [x] I understand that approval is for listing and is not a security review.
