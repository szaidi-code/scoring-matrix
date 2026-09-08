# Scoring Matrix

**Beta 0.1.0-beta.2 · MIT licensed.** A local hardware inventory and provisional **Omarchy Score**, with a native Omarchy bar widget and optional terminal application. No cloud service, telemetry, account registration, scheduled scans, or disk benchmarks. Nothing changes your disks or firmware.

## Install the Omarchy widget

On Omarchy versions with the native shell plugin API:

```bash
omarchy plugin add https://github.com/szaidi-code/scoring-matrix --enable
```

The **Score** bar button opens a native Omarchy popup with an animated total score, six clickable category cards, scoring explanations, and notes. The bar shows the most recently loaded score. Opening the popup reads the latest valid local report without scanning; **Rescan** performs a read-only scan and saves a new report. Arrow keys move between categories, Tab reaches controls, and Escape or clicking outside closes the popup. Plugin id: `szaidi.scoring-matrix`. By default, it starts no scanner until you request a scan. The popup uses the same shell panel components as the built-in network panel and follows the current theme. The separate terminal launcher supports Ghostty, foot, Alacritty, kitty, or xterm. The optional terminal application below works separately. Native plugin add does not run `install.py`; run that separately if you want both.

The evidence summary distinguishes complete inventory, missing evidence, unknown architecture, and guest resources. “Observed” means inventory was collected, not that the hardware passed a functional test. Colors and the bar button follow the active Omarchy theme. Saved snapshots are validated before display; full PCI and peripheral inventory stays in the report file instead of being sent to the shell.

With the panel open, press **R** to rescan or **N** to toggle notes. Arrow keys select a category; **Escape** closes the panel.

The widget follows Omarchy's font family and shared typography scale, including a user `base-size` override in `~/.config/omarchy/shell.toml`. Body text uses the configured base size; headings and score numerals use the shell's proportional type tokens. Panel dimensions, cards, rings and spacing scale with the shell's spacing settings.

Enable **Scan once per boot** in the widget settings, or run `omarchy bar set szaidi.scoring-matrix scanOnStartup true`. This takes effect when the shell next starts. A validated snapshot from the same boot and disk selection is reused across shell restarts. Set it to `false` to return to manual scans. Hardware scans remain local and read-only. If the boot identity is unavailable, an existing valid report is reused.



If root-disk detection is ambiguous, select a whole disk for the next **Rescan** in the widget settings, or use:

```bash
omarchy bar set szaidi.scoring-matrix targetDisk /dev/nvme0n1
# Restore automatic root-disk selection:
omarchy bar set szaidi.scoring-matrix targetDisk ''
```

The saved score continues to describe its original disk until you rescan. An invalid disk selection reports an error and preserves the previous report.

This native plugin targets the shell API documented in September 2026. The popup has been visually tested on Omarchy 4.0.2; it requires the native shell Panel and KeyboardPanel API. On an older Omarchy without this plugin API, use the application-menu installation.

## Optional terminal application

To also install an application-menu entry for the terminal interface:

```bash
git clone https://github.com/szaidi-code/scoring-matrix.git
cd scoring-matrix
python3 install.py
```

Open the application launcher and search **Scoring Matrix**. Its terminal menu lets you:

1. Score this computer and save a report.
2. Choose a specific whole disk to score.
3. Compare reports from your computers.
4. Open the reports folder.
5. Read the scoring matrix.

Requires Python 3.9+, `lscpu` and `lsblk` (util-linux). `lspci` (pciutils) and `lsusb` (usbutils) improve hardware names/peripheral inventory. These are commonly present on Arch-based installations; missing commands are reported without installing packages automatically. A working default terminal is required for the application launcher.

The installer copies the app to `$XDG_DATA_HOME/scoring-matrix` (default `~/.local/share/scoring-matrix`) and writes one `.desktop` entry in the applications directory. No sudo needed. It doesn't change the Omarchy menu source or replace any built-in menu. Installer paths containing `%` or newlines are rejected rather than producing an ambiguous desktop command.

## Linux command line and comparing devices

```bash
python3 scoring_matrix.py
python3 scoring_matrix.py --target-disk /dev/nvme1n1 --label office-pc
python3 scoring_matrix.py --secure-boot-reported enabled
python3 scoring_matrix.py --compare ./fleet
```

Linux reports are saved in `$XDG_STATE_HOME/scoring-matrix/reports` (default `~/.local/state/scoring-matrix/reports`), with local JSON and detailed text files. `--output DIRECTORY` changes the destination. Reports contain hardware IDs and computer labels; review before sharing. No reports or real-device fixtures are committed to this repository.

Copy JSON reports into `fleet` and use `python3 scoring_matrix.py --compare ./fleet`. The Python comparator selects the latest capture per exact computer label, validates categories and totals, and separates incomplete, non-x86-64, and detected virtual-machine reports into an unranked review section. Use a unique label for each computer; two machines sharing a label are treated as one. A newer incomplete snapshot supersedes an older complete one. Invalid reports stop comparison with a filename and reason; saved-panel loading skips them. Files larger than 2 MiB are rejected.

The Linux collector uses matrix **1.0**. RAM is OS-visible MemTotal, which may be lower than physically installed memory because of hardware reservations. Core count and memory are capacity estimates, not benchmarks; virtualization detection is best effort and guest resources should not be ranked as host hardware. Unavailable inventory is explicitly marked, and incomplete results must not be treated as install recommendations.

Scores reserve five points for future functional validation; even a Linux scan does not automatically prove working accelerated graphics or reliable Wi-Fi. The automatic ceiling is 95/100. See [the complete matrix and limitations](MATRIX.md).

Report JSON and text files are written through private temporary files and atomically replaced individually, so readers do not see partial JSON. Schema validation checks consistency, not authenticity: an edited report is not proof of measured hardware or successful tests.

## Update / uninstall

For the application-menu install:

```bash
git pull --ff-only
python3 install.py
# To remove the application-menu install (keeps reports):
python3 install.py --uninstall
```

For the native shell plugin:

```bash
omarchy plugin update szaidi.scoring-matrix
omarchy plugin remove szaidi.scoring-matrix
```

## Beta checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Try menu launch, default/explicit disk selection, saved reports, offline comparisons, Secure Boot provenance, suspend/resume, audio, Bluetooth and external displays. This is a beta: scores describe observed inventory, not tested hardware performance or installation certification.

See [the comparison and design review](docs/plugin-review.md) and [publication preparation](docs/publication.md) for the implementation rationale and remaining release decisions.

## License

[MIT](LICENSE), copyright 2026 szaidi-code.

## References

- [Omarchy shell plugins](https://omarchy.org/manual/shell-plugins/)
- [Omarchy shell manifest and IPC specification](https://github.com/omacom/omarchy/blob/quattro/shell/README.md)
- [XDG desktop entry specification](https://specifications.freedesktop.org/desktop-entry/latest/)
- [Omarchy installation guidance](https://omarchy.org/manual/getting-started/)
