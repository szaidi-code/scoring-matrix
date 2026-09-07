# Scoring Matrix

**Private beta 0.1.0-beta.1.** A local hardware inventory and provisional **Omarchy Score**, with an Omarchy application-menu entry, optional native bar plugin, and Windows scanner. No cloud service, telemetry, account registration, background scans, or disk benchmarks. Nothing changes your disks or firmware.

## Install on Omarchy

Your GitHub account must have access to this private repository. Use your existing GitHub SSH authentication:

```bash
git clone git@github.com:szaidi-code/scoring-matrix.git
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

## Optional native Omarchy bar plugin

For Omarchy versions that provide `omarchy plugin`, the same repository is also a shell plugin:

```bash
omarchy plugin add git@github.com:szaidi-code/scoring-matrix.git --enable
```

The **Score** bar button opens the same terminal menu. Plugin id: `szaidi.scoring-matrix`. It starts no scanner until you request a scan. The button supports Ghostty, foot, Alacritty, kitty, or xterm. The application-menu installation above works separately and is the primary beta entry point. Native plugin add does not run `install.py`; run that separately if you want both.

This native plugin targets the shell API documented in September 2026. It has not yet been visually tested in an actual Omarchy session; testing that integration is part of the beta. On an older Omarchy without this plugin API, use the application-menu installation.

## Windows devices

Copy `windows/OmarchyScore.ps1` onto a Windows computer and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\OmarchyScore.ps1
```

Windows reports go into `reports` beside the script. Secure Boot is probed directly, then via the Windows Secure Boot registry state if privileges prevent the first query. You can explicitly record a known setting with provenance:

```powershell
.\OmarchyScore.ps1 -SecureBootReported Enabled
```

This records **User reported**, not **Detected**, and changes no setting. With UEFI and Secure Boot enabled, firmware earns 3/5; this is an installation-readiness issue, not a CPU/RAM penalty.

## Linux command line and comparing devices

```bash
python3 scoring_matrix.py
python3 scoring_matrix.py --target-disk /dev/nvme1n1 --label office-pc
python3 scoring_matrix.py --secure-boot-reported enabled
python3 scoring_matrix.py --compare ./fleet
```

Linux reports are saved in `$XDG_STATE_HOME/scoring-matrix/reports` (default `~/.local/state/scoring-matrix/reports`), with local JSON and detailed text files. `--output DIRECTORY` changes the destination. Reports contain hardware IDs and computer labels; review before sharing. No reports or real-device fixtures are committed to this repository.

Copy **one current JSON report per computer** into `fleet`. Both collectors use matrix **1.0**, so Linux and Windows reports can be compared. Collector fields differ by OS, but category weights are shared. Linux RAM is OS-visible MemTotal, which may differ slightly from Windows installed RAM. Core count and memory are capacity estimates, not benchmarks; virtualization is flagged by Linux and guest resources should not be ranked as host hardware. Unavailable inventory is explicitly marked, and incomplete results must not be treated as install recommendations.

Scores reserve five points for future functional validation; even a Linux scan does not automatically prove working accelerated graphics or reliable Wi-Fi. The automatic ceiling is 95/100. See [the complete matrix and limitations](MATRIX.md).

## Update / uninstall

For the application-menu install:

```bash
git pull --ff-only
python3 install.py
# To remove the application-menu install (keeps reports):
python3 install.py --uninstall
```

For the optional native shell plugin:

```bash
omarchy plugin update szaidi.scoring-matrix
omarchy plugin remove szaidi.scoring-matrix
```

## Beta checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Try menu launch, default/explicit disk selection, saved reports, comparisons with Windows, Secure Boot provenance, suspend/resume, audio, Bluetooth and external displays. Keep the repository private until you decide the beta is ready. Public directory submission, public visibility, and an open-source license are separate future decisions.

## References

- [Omarchy shell plugins](https://omarchy.org/manual/shell-plugins/)
- [Omarchy shell manifest and IPC specification](https://github.com/omacom/omarchy/blob/quattro/shell/README.md)
- [XDG desktop entry specification](https://specifications.freedesktop.org/desktop-entry/latest/)
- [Omarchy installation guidance](https://omarchy.org/manual/getting-started/)
