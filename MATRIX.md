# Omarchy Score matrix v1.0

Scoring Matrix now includes Linux and Windows collectors; see [README.md](README.md) for the application-menu installer and Linux commands. The Windows examples below apply to `windows/OmarchyScore.ps1`. Both collectors use the same provisional point rules. Linux reads OS-visible memory and kernel-reported storage/media; neither collector runs performance benchmarks or awards functional-test points automatically.

A read-only, offline Windows hardware inventory and provisional suitability score for an Omarchy desktop used for coding, browsers, containers, and everyday work. These weights are our decision rubric, not an official Omarchy benchmark or published minimum requirements. Requires Windows PowerShell 5.1 or later on Windows. No Python, downloads, installation, or administrator rights normally required; some firmware/storage queries may need an elevated PowerShell.

## Run on each Windows PC

Copy `OmarchyScore.ps1` to each computer, open PowerShell in that folder, and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\OmarchyScore.ps1
```

The execution-policy override applies only to that process. The script reads hardware and writes timestamped JSON and text files to `reports` beside the script. It makes no hardware, partition, firmware, or network changes and uploads nothing. Reports include your chosen computer label, device models and hardware IDs, but deliberately omit serial-number fields, IP addresses, MAC addresses, and Wi-Fi credentials.

By default the Windows boot disk is the candidate installation disk. Select another disk explicitly, using its Number in the report:

```powershell
.\OmarchyScore.ps1 -Label Office-PC -TargetDiskNumber 1
```

Copy one current JSON report per computer into a folder named `fleet`, then rank:

```powershell
.\OmarchyScore.ps1 -CompareDirectory .\fleet
```

Comparison rejects other matrix versions. Multiple snapshots of a computer appear as separate rows, so keep only the desired snapshot in `fleet`. Check Status and Coverage before trusting the numerical order; incomplete or non-x86-64 inventories are not install recommendations.

## Scoring matrix (100 possible points)

| Category | Maximum | Rules |
|---|---:|---|
| CPU capacity | 25 | Physical cores 1/2/4/6/8/12/16+ earn 2/5/10/13/16/18/20; threads 4/8/16/24+ add 1/3/4/5. |
| Installed RAM | 25 | Approximately 4/8/16/32/64+ GB classes earn 3/10/18/23/25. Actual GiB thresholds are 3/7/15/31/63 to tolerate hardware reservations. |
| Selected disk | 20 | NVMe 12, other SSD 9, HDD 2, unknown 0; capacity >=60/119/237/475/950 GiB adds 1/3/5/7/8. |
| Graphics suitability estimate | 15 | Intel/AMD without NVIDIA 12; any NVIDIA/hybrid 8; other detected graphics 3; missing 0. This is a setup-risk estimate, not GPU performance. |
| Network suitability estimate | 10 | Physical Ethernet present 4; Wi-Fi present 2, or Intel name/PCI vendor 8086 Wi-Fi 4. No double counting multiple adapters. |
| Firmware readiness | 5 | UEFI detected 3; confirmed Secure Boot off adds 2. Unknown receives no corresponding points. |

Resources = CPU + RAM + storage, out of 70. Compatibility estimate = graphics + networking + firmware, out of 30. Omarchy Score = their sum. The Windows-only scanner deliberately leaves 3 graphics points and 2 Wi-Fi points unawarded: those require a future Linux validation stage. Its maximum is therefore 95/100. Do not manually add them to JSON reports used for v1 comparisons.

Coverage counts category weights whose required inventory fields were observed. It is not a probability of successful installation. A failed query produces an explicit note and earns no points for unavailable facts; an incomplete inventory should be rerun with the needed access.

Suggested interpretation for complete x86-64 inventories: 85+ strong candidate, 70-84 good candidate with tradeoffs, 50-69 modest candidate, below 50 limited capacity or substantial uncertainty. Every result remains provisional until Linux testing. Thresholds and weights are subjective and versioned.

## What the score does and does not measure

CPU core/thread counts measure available concurrency only. They do not account for generation, performance versus efficiency cores, single-thread speed, cooling, or power limits. Two similarly scored machines need comparable CPU benchmarks to distinguish actual speed. The 64 GB and 1 TB ceilings intentionally favor a practical desktop over unlimited server capacity. This rubric is not a gaming or local-AI ranking; an RTX 4090's compute value needs a separate workload score.

Storage points use one selected disk, not the sum of unrelated or external disks. The report inventories all visible disks, media, bus types, health, allocated bytes and mounted drive free space. Capacity scoring assumes that the selected drive could be repurposed. Free space within C: is not unallocated space available to an installer, and a second drive is not necessarily empty. Neither basic Windows health status nor NVMe identification measures endurance or real disk speed. RAID and ambiguous media may need manual review.

Installed RAM is scored because currently free RAM depends on running applications; the latter is reported separately. Network LinkSpeed is the current Windows link, not maximum wireless capability or an Internet speed test. Ethernet points indicate availability, not confirmed Linux driver support. GPU and Wi-Fi vendor estimates cannot establish support for every chipset or generation.

Peripherals include Bluetooth, audio, cameras, monitors, HID devices, and available battery data, without inflating the score merely for device count. Battery capacity may be unavailable. The script cannot test sleep, speakers, microphone, touchpad gestures, fingerprint reader, battery runtime, graphics acceleration, or external monitor routing under Linux. Standard Windows hardware queries can also miss disabled devices.

## Linux validation before choosing the winner

Boot a recent Linux live environment to identify devices and test Wi-Fi/Bluetooth, audio, camera, input devices, and suspend/resume. A successful test on another distribution is supporting evidence, not proof for Omarchy. Verify the intended Omarchy/Hyprland stack on a spare disk or test installation for accelerated graphics, external displays, scaling, and suspend. Record exact PCI/USB IDs and kernel/driver versions when investigating failures. Prefer the highest-resource machine whose required functions actually pass.

Future v2: measured CPU/storage benchmarks and recorded pass/fail compatibility tests. Recalibrate weights and version the matrix before comparing those results to this v1 preflight. The beta Linux collector uses the same v1 category weights and report summary fields; detailed inventory fields vary by OS.

## Sources checked September 7, 2026

- [Omarchy installation manual](https://omarchy.org/manual/getting-started/): installation options and Secure Boot guidance. Full-disk installation erases the selected drive; free-space installation needs unallocated space. This scanner performs neither.
- [Hyprland NVIDIA documentation](https://wiki.hypr.land/Nvidia/): driver setup and graphics caveats informing the provisional NVIDIA score.
- [Linux Intel wireless documentation](https://wireless.docs.kernel.org/en/latest/en/users/drivers/iwlwifi.html): chipset/firmware support reference; vendor identity alone does not prove support.
- [Omarchy troubleshooting](https://omarchy.org/manual/troubleshooting/): display scaling and peripheral troubleshooting.

The point values above are design choices, not claims made by those sources.
