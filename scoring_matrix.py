#!/usr/bin/env python3
"""Scoring Matrix private beta. Standard-library-only, offline Linux collector."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

VERSION = '0.1.0-beta.1'
MATRIX = '1.0'
GIB = 1024 ** 3


def tier(value, thresholds, points):
    return next((p for t, p in zip(thresholds, points) if value >= t), 0)


def score(inv, label=None):
    """Same provisional weights as Windows v1; detected does not mean tested."""
    parts, notes = [], list(inv.get('Errors', []))

    def add(name, points, maximum, known, reason):
        parts.append(dict(Category=name, Points=points, Maximum=maximum,
                          Known=bool(known), Reason=reason))

    cpu = inv.get('CPU') or {}
    cores, threads = cpu.get('Cores', 0), cpu.get('Threads', 0)
    add('CPU', tier(cores, [16, 12, 8, 6, 4, 2, 1], [20, 18, 16, 13, 10, 5, 2]) +
        tier(threads, [24, 16, 8, 4], [5, 4, 3, 1]), 25, cores and threads,
        f'{cores} physical cores / {threads} threads; capacity proxy, not speed benchmark')
    ram = inv.get('RAMGiB')
    add('RAM', tier(ram or 0, [63, 31, 15, 7, 3], [25, 23, 18, 10, 3]),
        25, ram is not None, f'{ram} GiB OS-visible memory')
    disk = inv.get('SelectedDisk') or {}
    media = disk.get('Media', 'Unknown')
    add('Storage', {'NVMe': 12, 'SSD': 9, 'HDD': 2}.get(media, 0) +
        tier(disk.get('Size', 0) / GIB, [950, 475, 237, 119, 60], [8, 7, 5, 3, 1]),
        20, disk and media != 'Unknown',
        f"Selected {disk.get('Path', 'unknown')}: {disk.get('Model', '')}, {media}; repurposed capacity")
    gpus = inv.get('Graphics', [])
    vendors = [g.get('Vendor', '').lower() for g in gpus]
    if '0x10de' in vendors:
        graphics = 8
        notes.append('NVIDIA/hybrid: test driver support, displays, and suspend under Omarchy.')
    elif any(v in ('0x8086', '0x1002') for v in vendors):
        graphics = 12
    else:
        graphics = 3 if gpus else 0
    add('Graphics', graphics, 15, gpus, '; '.join(g.get('Name', '') for g in gpus))
    network = inv.get('Network', [])
    wifi = [n for n in network if n.get('Wireless')]
    ethernet = [n for n in network if not n.get('Wireless') and n.get('Ethernet')]
    wireless_points = 4 if any(n.get('Vendor') == '0x8086' for n in wifi) else 2 if wifi else 0
    add('Network', wireless_points + (4 if ethernet else 0), 10, network,
        f'{len(wifi)} wireless / {len(ethernet)} Ethernet interfaces; chipset estimate only')
    firmware, secure = inv.get('Firmware'), inv.get('SecureBoot')
    add('Firmware', (3 + (2 if secure is False else 0)) if firmware == 'Uefi' else 0,
        5, firmware is not None and secure is not None,
        f'Firmware={firmware}; Secure Boot={secure} ({inv.get("SecureBootSource", "Unknown")})')
    if secure is True:
        notes.append('Secure Boot is enabled; review Omarchy installation guidance. No settings changed.')
    if secure is None:
        notes.append('Secure Boot could not be read; no off-state points awarded.')
    notes.append('Five points remain reserved: graphics 3 and Wi-Fi 2. No automatic Linux functional validation is claimed.')
    notes.append('Audio, Bluetooth, camera, battery runtime, suspend, graphics acceleration and Wi-Fi reliability need hands-on tests.')
    status = 'Provisional - Linux validation required'
    if cpu.get('Architecture') not in ('x86_64', 'amd64'):
        status = 'Not a standard x86-64 installation candidate'
    if not cores or ram is None or not disk:
        status = 'Incomplete inventory - do not rank yet'
    if inv.get('Virtualized'):
        notes.append('Virtual environment detected: this describes guest-visible resources, not host suitability.')
        status = 'Virtual environment - do not rank as physical hardware'
    total = sum(p['Points'] for p in parts)
    resources = sum(p['Points'] for p in parts[:3])
    return dict(MatrixVersion=MATRIX, AppVersion=VERSION, Computer=label or platform.node(),
                Captured=dt.datetime.now(dt.timezone.utc).isoformat(), Score=total,
                Resources=resources, Compatibility=total-resources,
                Coverage=sum(p['Maximum'] for p in parts if p['Known']), Status=status,
                SecureBootSource=inv.get('SecureBootSource', 'Unknown'), Breakdown=parts,
                Issues=notes, Inventory=inv)


def collect(target=None, secure_reported='unknown'):
    if platform.system() != 'Linux':
        raise RuntimeError('Use windows/OmarchyScore.ps1 on Windows. Hardware collection requires Linux.')
    errors = []

    def read(path, default=None):
        try:
            return Path(path).read_text().strip()
        except (OSError, UnicodeError):
            return default

    def command(args):
        try:
            return subprocess.run(args, capture_output=True, text=True, check=True,
                                  timeout=20, env=dict(os.environ, LC_ALL='C')).stdout
        except (OSError, subprocess.SubprocessError) as e:
            errors.append(f'{args[0]} unavailable or failed ({type(e).__name__})')
            return ''

    topology = command(['lscpu', '-p=SOCKET,CORE'])
    rows = [r.split(',') for r in topology.splitlines() if r and not r.startswith('#')]
    valid = [r for r in rows if len(r) == 2 and all(c.isdigit() for c in r)]
    cpu_text = read('/proc/cpuinfo', '')
    name = next((x.split(':', 1)[1].strip() for x in cpu_text.splitlines() if x.startswith('model name')), platform.processor())
    cpu = dict(Name=name, Cores=len(set(tuple(r) for r in valid)), Threads=len(valid), Architecture=platform.machine().lower())
    mem = {}
    for line in read('/proc/meminfo', '').splitlines():
        key, value = line.split(':', 1)
        mem[key] = int(value.strip().split()[0])

    block_text = command(['lsblk', '--json', '--bytes', '--output', 'NAME,PATH,TYPE,SIZE,ROTA,TRAN,MODEL,MOUNTPOINTS,FSTYPE,FSAVAIL'])
    try:
        roots = json.loads(block_text).get('blockdevices', [])
    except (ValueError, TypeError):
        roots = []
        errors.append('Disk inventory unavailable')

    def contains_root(node):
        return '/' in (node.get('mountpoints') or []) or any(contains_root(n) for n in node.get('children', []))

    disks = []
    for node in roots:
        if node.get('type') != 'disk' or node.get('name', '').startswith('zram'):
            continue
        tran = node.get('tran') or ''
        rota = node.get('rota')
        media = 'NVMe' if tran == 'nvme' else 'HDD' if rota in (True, 1, '1') else 'SSD' if rota in (False, 0, '0') else 'Unknown'
        disks.append(dict(Path=node['path'], Model=(node.get('model') or '').strip(),
                          Size=int(node.get('size') or 0), Media=media, Bus=tran,
                          ContainsRoot=contains_root(node), Layout=node))
    if target:
        selected = next((d for d in disks if d['Path'] == target), None)
        if selected is None:
            raise ValueError(f'Target {target} is not a detected whole disk; no report saved.')
    else:
        candidates = [d for d in disks if d['ContainsRoot']]
        selected = candidates[0] if len(candidates) == 1 else None
        if selected is None:
            errors.append('Root disk is ambiguous/unavailable (live USB, RAID or pooled root); choose --target-disk explicitly.')
    if selected and selected['Bus'] in ('usb', 'iscsi'):
        errors.append('Selected disk is external/remote; review suitability manually.')

    pci_names = {}
    for line in command(['lspci', '-D', '-nn']).splitlines():
        address, _, desc = line.partition(' ')
        pci_names[address] = desc
    pci, graphics = [], []
    for device in Path('/sys/bus/pci/devices').glob('*'):
        driver = device / 'driver'
        item = dict(Address=device.name, Vendor=read(device/'vendor', ''),
                    Device=read(device/'device', ''), Class=read(device/'class', ''),
                    Name=pci_names.get(device.name, device.name),
                    Driver=driver.resolve().name if driver.exists() else None)
        pci.append(item)
        if item['Class'].startswith('0x03'):
            graphics.append(item)
    network = []
    for interface in Path('/sys/class/net').glob('*'):
        device = interface / 'device'
        if not device.exists():
            continue
        wireless = (interface/'wireless').exists() or (interface/'phy80211').exists()
        vendor = read(device/'vendor') or read(device/'../idVendor', '')
        driver = device/'driver'
        usb_product = read(device/'../product', '')
        internal = vendor.lower() == '05ac' and usb_product == 'Apple T2 Controller'
        if internal:
            errors.append(f'{interface.name}: internal Apple T2 link; excluded from Ethernet points.')
        network.append(dict(Name=interface.name, Wireless=wireless,
                            Ethernet=not wireless and not internal and read(interface/'type') == '1',
                            Internal=internal, Product=usb_product,
                            Vendor=vendor, Device=read(device/'device', ''),
                            Driver=driver.resolve().name if driver.exists() else None,
                            State=read(interface/'operstate'),
                            LinkMbps=read(interface/'speed')))
    firmware = 'Uefi' if Path('/sys/firmware/efi').exists() else 'Legacy'
    secure, source = None, 'Unknown'
    if secure_reported != 'unknown':
        secure, source = secure_reported == 'enabled', 'User reported'
    else:
        secure_path = Path('/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c')
        try:
            data = secure_path.read_bytes()
            if len(data) >= 5 and data[4] in (0, 1):
                secure, source = bool(data[4]), 'Detected EFI variable'
        except OSError:
            pass
    batteries = []
    for battery in Path('/sys/class/power_supply').glob('*'):
        if read(battery/'type') == 'Battery':
            batteries.append({k: read(battery/k) for k in ('manufacturer', 'model_name', 'status', 'capacity', 'energy_full', 'energy_full_design', 'cycle_count')})
    # A nonzero result means bare metal, not a failed inventory query.
    virtualized = 'microsoft' in platform.release().lower()
    if shutil.which('systemd-detect-virt'):
        try:
            virtualized = virtualized or subprocess.run(['systemd-detect-virt', '--quiet'], timeout=5).returncode == 0
        except (OSError, subprocess.SubprocessError):
            pass
    return dict(CPU=cpu, RAMGiB=round(mem['MemTotal']/1024**2, 1) if 'MemTotal' in mem else None,
                CurrentlyFreeRAMGiB=round(mem['MemAvailable']/1024**2, 1) if 'MemAvailable' in mem else None,
                System=dict(Manufacturer=read('/sys/class/dmi/id/sys_vendor'), Model=read('/sys/class/dmi/id/product_name')),
                Disks=disks, SelectedDisk=selected, RootFilesystemFreeGiB=round(shutil.disk_usage('/').free/GIB, 1),
                Graphics=graphics, Network=network, PCI=pci, USB=command(['lsusb']).splitlines(),
                Audio=read('/proc/asound/cards'), Batteries=batteries,
                BluetoothControllers=[p.name for p in Path('/sys/class/bluetooth').glob('hci*')],
                Cameras=[read(p/'name') for p in Path('/sys/class/video4linux').glob('*')],
                Firmware=firmware, SecureBoot=secure, SecureBootSource=source,
                Kernel=platform.release(), Virtualized=virtualized, Errors=errors)


def render(report):
    lines = [f"OMARCHY SCORE: {report['Score']}/100", f"Computer: {report['Computer']}",
             f"Resources {report['Resources']}/70 | Compatibility estimate {report['Compatibility']}/30",
             f"Coverage {report['Coverage']}/100 | {report['Status']}", '']
    for row in report['Breakdown']:
        lines.append(f"{row['Category']:12} {row['Points']:2}/{row['Maximum']:<2}  {row['Reason']}")
    lines += ['', 'NOTES'] + report['Issues']
    return '\n'.join(lines)


def report_dir():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state'))) / 'scoring-matrix/reports'


def latest_report(directory):
    """Read the latest compatible snapshot without scanning or changing files."""
    candidates = []
    for path in Path(directory).glob('*.json'):
        try:
            report = json.loads(path.read_text(encoding='utf-8-sig'))
            parts = report.get('Breakdown', [])
            if (report.get('MatrixVersion') != MATRIX or len(parts) != 6
                    or report.get('Score') != sum(p['Points'] for p in parts)
                    or not isinstance(report.get('Inventory'), dict)):
                continue
            captured = dt.datetime.fromisoformat(report['Captured'].replace('Z', '+00:00'))
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=dt.timezone.utc)
            candidates.append((captured, path.name, report))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
    return max(candidates, key=lambda item: item[:2])[2] if candidates else None


def save(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    label = re.sub(r'[^a-zA-Z0-9_.-]', '_', report['Computer']) or 'computer'
    stem = label + '-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    path = directory / (stem + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    path.chmod(0o600)
    text_path = path.with_suffix('.txt')
    text_path.write_text(render(report) + '\n\nINVENTORY\n' + json.dumps(report['Inventory'], indent=2), encoding='utf-8')
    text_path.chmod(0o600)
    return path


def compare(directory):
    reports = []
    for path in Path(directory).glob('*.json'):
        r = json.loads(path.read_text(encoding='utf-8-sig'))
        if r.get('MatrixVersion') != MATRIX:
            raise ValueError(f'Incompatible matrix in {path.name}')
        if r.get('Score') != sum(p['Points'] for p in r.get('Breakdown', [])):
            raise ValueError(f'Invalid score total in {path.name}')
        reports.append(r)
    if not reports:
        raise ValueError('No JSON reports found; copy one report per computer into this folder.')
    lines = ['Computer                 Score  Resources  Compat.  Coverage  Status']
    for r in sorted(reports, key=lambda r: r['Score'], reverse=True):
        lines.append(f"{r['Computer'][:24]:24} {r['Score']:3}/100   {r['Resources']:2}/70     {r['Compatibility']:2}/30    {r['Coverage']:3}/100  {r['Status']}")
    return '\n'.join(lines)


def menu():
    while True:
        print('\nSCORING MATRIX | private beta\n1  Score this computer\n2  Score a specific disk\n3  Compare computer reports\n4  Open reports folder\n5  View scoring matrix\n0  Exit')
        choice = input('Choose: ').strip()
        try:
            if choice == '0':
                return
            if choice in ('1', '2'):
                target = input('Whole disk path (example /dev/nvme0n1): ').strip() if choice == '2' else None
                if choice == '2' and not target:
                    continue
                report = score(collect(target))
                path = save(report, report_dir())
                print('\n' + render(report) + '\n\nSaved: ' + str(path))
            elif choice == '3':
                folder = input('Folder with one JSON report per computer: ').strip()
                print(compare(Path(folder).expanduser()))
            elif choice == '4':
                report_dir().mkdir(parents=True, exist_ok=True, mode=0o700)
                subprocess.Popen(['xdg-open', str(report_dir())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif choice == '5':
                print(Path(__file__).with_name('MATRIX.md').read_text(encoding='utf-8'))
        except (OSError, ValueError, RuntimeError, KeyError) as e:
            print('Could not complete: ' + str(e))


def launch():
    script = str(Path(__file__).resolve())
    for binary, args in [('ghostty', ['-e']), ('foot', ['-e']), ('alacritty', ['-e']), ('kitty', []), ('xterm', ['-e'])]:
        if shutil.which(binary):
            subprocess.Popen([binary, *args, 'python3', script, '--menu'], start_new_session=True)
            return
    raise RuntimeError('No supported terminal found. Run python3 scoring_matrix.py --menu in your terminal.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--menu', action='store_true')
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--target-disk')
    parser.add_argument('--label')
    parser.add_argument('--secure-boot-reported', choices=['unknown', 'enabled', 'disabled'], default='unknown')
    parser.add_argument('--output', type=Path, default=report_dir())
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--latest-json', action='store_true',
                        help='Read the latest valid saved report as JSON; does not scan')
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()
    try:
        if args.latest_json:
            print(json.dumps(latest_report(args.output)))
        elif args.launch:
            launch()
        elif args.menu:
            menu()
        elif args.compare:
            print(compare(args.compare))
        else:
            report = score(collect(args.target_disk, args.secure_boot_reported), args.label)
            path = save(report, args.output)
            print(json.dumps(report) if args.json else render(report) + '\n\nSaved: ' + str(path))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        print('Scoring Matrix: ' + str(e), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        return 0


if __name__ == '__main__':
    sys.exit(main())
