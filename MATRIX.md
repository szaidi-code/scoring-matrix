# Omarchy Score matrix v1.0

Scoring Matrix is a read-only, offline hardware inventory and provisional suitability score for an Omarchy desktop used for coding, browsers, containers and everyday work. These weights are this project's decision rubric, not an official Omarchy benchmark or minimum requirements. The collector does not run performance benchmarks or award functional-test points automatically.

## Use on Omarchy

Open the **Score** bar widget and select **Rescan**, or run the Linux collector from the repository:

```bash
python3 scoring_matrix.py
# Select a whole disk explicitly:
python3 scoring_matrix.py --target-disk /dev/nvme0n1
# Compare saved reports from several computers:
python3 scoring_matrix.py --compare ./fleet
```

See [README.md](README.md) for plugin installation, the optional terminal application, dependencies and report storage. Scanning makes no hardware, partition, firmware or network changes and uploads nothing. Reports contain computer labels and hardware inventory; review them before sharing.

The comparator uses the latest valid snapshot per computer label. Incomplete, unknown-architecture and detected virtual-machine reports are separated from complete candidates. Scores remain estimates, not measured performance rankings.

## Scoring matrix (100 possible points)

| Category | Maximum | Rules |
|---|---:|---|
| CPU capacity | 25 | Physical cores 1/2/4/6/8/12/16+ earn 2/5/10/13/16/18/20; threads 4/8/16/24+ add 1/3/4/5. |
| OS-visible RAM | 25 | Approximately 4/8/16/32/64+ GB classes earn 3/10/18/23/25. Actual GiB thresholds are 3/7/15/31/63 to tolerate hardware reservations. |
| Selected disk | 20 | NVMe 12, other SSD 9, HDD 2, unknown 0; capacity >=60/119/237/475/950 GiB adds 1/3/5/7/8. |
| Graphics suitability estimate | 15 | Intel/AMD without NVIDIA 12; any NVIDIA/hybrid 8; other detected graphics 3; missing 0. This is a setup-risk estimate, not GPU performance. |
| Network suitability estimate | 10 | Physical Ethernet present 4; Wi-Fi present 2, or Intel PCI vendor 8086 Wi-Fi 4. No double counting multiple adapters. |
| Firmware readiness | 5 | UEFI detected 3; confirmed Secure Boot off adds 2. Unknown receives no corresponding points. |

Resources = CPU + RAM + storage, out of 70. Compatibility estimate = graphics + networking + firmware, out of 30. Omarchy Score = their sum. The collector reserves 3 graphics points and 2 Wi-Fi points for future functional validation. Running it on Linux does not award these points automatically, so its maximum is 95/100. Do not manually add them to JSON reports used for v1 comparisons.

Coverage counts category weights whose required inventory fields were observed. It is not a probability of successful installation. A failed query produces an explicit note and earns no points for unavailable facts; an incomplete inventory should be rerun with the needed access.

Suggested interpretation for complete x86-64 inventories: 85+ strong candidate, 70-84 good candidate with tradeoffs, 50-69 modest candidate, below 50 limited capacity or substantial uncertainty. Every result remains provisional until hands-on functional testing. Thresholds and weights are subjective and versioned.

## What the score does and does not measure

CPU core/thread counts measure available concurrency only. They do not account for generation, performance versus efficiency cores, single-thread speed, cooling, or power limits. Two similarly scored machines need comparable CPU benchmarks to distinguish actual speed. The 64 GB and 1 TB ceilings intentionally favor a practical desktop over unlimited server capacity. This rubric is not a gaming or local-AI ranking; an RTX 4090's compute value needs a separate workload score.

Storage points use one selected whole disk, not the sum of unrelated disks. Linux reports use kernel-reported disk size, media, bus type and mount layout. Capacity assumes the selected disk could be repurposed; filesystem free space is not unallocated installation space. NVMe identification does not measure endurance or disk speed. Live environments, RAID and pooled roots may require an explicit target disk.

RAM uses OS-visible memory from `/proc/meminfo`, allowing for hardware reservations. Currently free RAM varies with applications and does not affect the score. Network link speed is a current local observation, not an Internet speed test. Ethernet and GPU/Wi-Fi vendor points do not establish that every required function works.

Peripheral inventory provides context without awarding points for device count. The collector cannot verify audio quality, camera operation, touchpad gestures, fingerprint readers, battery runtime, suspend/resume, graphics acceleration or external monitor routing. Missing observations are reported as unavailable evidence.

## Linux validation before choosing the winner

Boot a recent Linux live environment to identify devices and test Wi-Fi/Bluetooth, audio, camera, input devices, and suspend/resume. A successful test on another distribution is supporting evidence, not proof for Omarchy. Verify the intended Omarchy/Hyprland stack on a spare disk or test installation for accelerated graphics, external displays, scaling, and suspend. Record exact PCI/USB IDs and kernel/driver versions when investigating failures. Prefer the highest-resource machine whose required functions actually pass.

Future v2: measured CPU/storage benchmarks and recorded pass/fail compatibility tests. Recalibrate weights and version the matrix before comparing those results to this v1 preflight. Any future scoring changes must use a new matrix version before their reports are compared.

## Sources checked September 7, 2026

- [Omarchy installation manual](https://omarchy.org/manual/getting-started/): installation options and Secure Boot guidance. Full-disk installation erases the selected drive; free-space installation needs unallocated space. This scanner performs neither.
- [Hyprland NVIDIA documentation](https://wiki.hypr.land/Nvidia/): driver setup and graphics caveats informing the provisional NVIDIA score.
- [Linux Intel wireless documentation](https://wireless.docs.kernel.org/en/latest/en/users/drivers/iwlwifi.html): chipset/firmware support reference; vendor identity alone does not prove support.
- [Omarchy troubleshooting](https://omarchy.org/manual/troubleshooting/): display scaling and peripheral troubleshooting.

The point values above are design choices, not claims made by those sources.
