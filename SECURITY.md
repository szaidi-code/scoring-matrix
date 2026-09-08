# Security

## Report a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/szaidi-code/scoring-matrix/security/advisories/new). Include the affected commit, reproduction steps and impact. Do not post credentials or hardware reports in public issues.

## Scope and data handling

The widget runs with the user's permissions inside Omarchy's shell. Hardware collection invokes local commands with argument arrays, without shell evaluation. It does not request elevated privileges or send reports over the network. The optional terminal installer writes only its managed application files and desktop entry; removal preserves user reports.

Linux reports are local hardware inventory and can include computer labels, device identifiers, mount paths and boot identity. Review reports before sharing them. JSON and text snapshots are written through private temporary files. Report validation checks consistency; it does not establish authenticity. Windows report permissions follow the chosen output directory's Windows access controls.

## Repository checks

GitHub secret scanning, push protection, dependency alerts and private vulnerability reporting are enabled. CI runs a redacted full-history Gitleaks scan and a Bandit check for medium/high Python findings. Action dependencies are pinned to commit IDs, and the Gitleaks download is verified against a pinned checksum.

The September 7, 2026 audit found no secret matches in the eight reachable commits or working tree at `78687cc`. Bandit reported ten low-severity subprocess/PATH notices, manually reviewed as local argument-array calls; no medium/high findings were reported. These checks do not prove the absence of every vulnerability. Public commit email metadata uses GitHub noreply addresses. QA documentation uses anonymous labels, and the identifying preview has been removed from all reachable history.
