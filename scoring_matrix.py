#!/usr/bin/env python3
"""Scoring Matrix beta. Standard-library-only, offline Linux collector."""
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
import tempfile

VERSION = '0.1.0-beta.2'
MATRIX = '1.0'
GIB = 1024 ** 3
MAX_REPORT_BYTES = 2 * 1024 * 1024
CATEGORIES = [('CPU', 25, 25), ('RAM', 25, 25), ('Storage', 20, 20),
              ('Graphics', 15, 12), ('Network', 10, 8), ('Firmware', 5, 5)]


def tier(value, thresholds, points):
    return next((p for t, p in zip(thresholds, points) if value >= t), 0)


def score(inv, label=None):
    """Provisional matrix v1 weights; detected does not mean tested."""
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


def validate_report(report):
    """Validate the matrix v1 report contract before display or ranking."""
    def number(value, maximum):
        return (type(value) in (int, float) and 0 <= value <= maximum
                and value == int(value))

    if not isinstance(report, dict) or report.get('MatrixVersion') != MATRIX:
        raise ValueError('Incompatible or missing matrix version')
    for field in ('Computer', 'Captured', 'Status'):
        if not isinstance(report.get(field), str) or not report[field].strip():
            raise ValueError(f'Missing or invalid {field}')
    try:
        captured = dt.datetime.fromisoformat(report['Captured'].replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid capture timestamp') from exc
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=dt.timezone.utc)
    parts = report.get('Breakdown')
    if not isinstance(parts, list) or len(parts) != len(CATEGORIES):
        raise ValueError('Expected six score categories')
    for part, (category, maximum, ceiling) in zip(parts, CATEGORIES):
        if (not isinstance(part, dict) or part.get('Category') != category
                or not number(part.get('Maximum'), maximum) or part['Maximum'] != maximum
                or not number(part.get('Points'), ceiling)
                or type(part.get('Known')) is not bool
                or not isinstance(part.get('Reason'), str)):
            raise ValueError(f'Invalid {category} category')
    expected = dict(Score=sum(p['Points'] for p in parts),
                    Resources=sum(p['Points'] for p in parts[:3]),
                    Compatibility=sum(p['Points'] for p in parts[3:]),
                    Coverage=sum(p['Maximum'] for p in parts if p['Known']))
    for field, total in expected.items():
        if not number(report.get(field), 100) or report[field] != total:
            raise ValueError(f'Invalid {field} total')
    if (not isinstance(report.get('Inventory'), dict)
            or not isinstance(report.get('Issues'), list)
            or not all(isinstance(note, str) for note in report['Issues'])):
        raise ValueError('Invalid inventory or notes')
    return captured


def read_report(path):
    # Bound the actual read as well as the UI payload, including growing files.
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError('Report exceeds the 2 MiB limit')
    report = json.loads(raw.decode('utf-8-sig'))
    validate_report(report)
    return report


def assessment(report):
    """Keep uncertainty separate from capacity. No score implies a tested device."""
    inv = report['Inventory']
    system = inv.get('System') or {}
    model = ' '.join(str(system.get(k, '')) for k in ('Manufacturer', 'Model')) if isinstance(system, dict) else ''
    virtual = inv.get('Virtualized') or re.search(r'vmware|virtualbox|virtual machine|qemu|kvm|parallels', model, re.I)
    if virtual or report['Status'].startswith('Virtual environment'):
        return dict(State='virtual', Title='Guest resources only',
                    Detail='Test the physical computer before comparing installation candidates.', Rankable=False)
    cpu = inv.get('CPU')
    architecture = (isinstance(cpu, dict) and cpu.get('Architecture') in ('x86_64', 'amd64')) or (
        isinstance(cpu, list) and bool(cpu) and all(isinstance(c, dict) and c.get('Architecture') == 9 for c in cpu))
    if not architecture or report['Status'].startswith('Not a standard'):
        return dict(State='architecture', Title='Architecture needs review',
                    Detail='A standard x86-64 candidate has not been established.', Rankable=False)
    if report['Coverage'] < 100 or report['Status'].startswith('Incomplete'):
        missing = ', '.join(p['Category'] for p in report['Breakdown'] if not p['Known'])
        return dict(State='incomplete', Title='Evidence missing',
                    Detail='Review ' + (missing or 'required inventory') + ' before ranking this computer.', Rankable=False)
    if report['Status'] != 'Provisional - Linux validation required':
        return dict(State='review', Title='Status needs review', Detail=report['Status'], Rankable=False)
    return dict(State='provisional', Title='Ready for hands-on checks',
                Detail='Inventory is complete. Test graphics, Wi-Fi, audio and suspend under Omarchy.', Rankable=True)


def view_report(report):
    """Small validated payload for the shell; full inventory stays on disk."""
    if report is None:
        return None
    validate_report(report)
    return dict((key, value) for key, value in report.items() if key != 'Inventory') | {
        'Inventory': {'Virtualized': bool(report['Inventory'].get('Virtualized'))},
        'Assessment': assessment(report)}


def latest_report(directory):
    """Read the latest compatible snapshot without scanning or changing files."""
    candidates = []
    for path in Path(directory).glob('*.json'):
        try:
            report = read_report(path)
            captured = validate_report(report)
            candidates.append((captured, path.name, report))
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
            continue
    return max(candidates, key=lambda item: item[:2])[2] if candidates else None


def boot_id():
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip() or None
    except OSError:
        return None


def ensure_boot_report(directory, target_disk=None):
    """Serialize startup checks across bars on multiple monitors."""
    if sys.platform != 'linux':
        return _ensure_boot_report(directory, target_disk)
    import fcntl
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / '.startup.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _ensure_boot_report(directory, target_disk)


def _ensure_boot_report(directory, target_disk=None):
    """Reuse only a validated snapshot for this boot and disk selection."""
    current_boot = boot_id()
    existing = latest_report(directory)
    if (current_boot and existing and existing.get('ScanBootId') == current_boot
            and existing.get('ScanTargetDisk') == (target_disk or '')):
        return existing
    # Without a boot identity, load the saved report instead of repeatedly scanning.
    if not current_boot and existing:
        return existing
    report = score(collect(target_disk))
    report['ScanBootId'] = current_boot
    report['ScanTargetDisk'] = target_disk or ''
    save(report, directory)
    return report


def save(report, directory):
    validate_report(report)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    label = re.sub(r'[^a-zA-Z0-9_.-]', '_', report['Computer']) or 'computer'
    stem = label + '-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    path = directory / (stem + '.json')
    text_path = path.with_suffix('.txt')
    for destination, content in ((text_path, render(report) + '\n\nINVENTORY\n' + json.dumps(report['Inventory'], indent=2)),
                                 (path, json.dumps(report, indent=2))):
        # Readers see either the previous snapshot or a complete new file.
        staged = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                             prefix='.snapshot-', delete=False) as stream:
                staged = Path(stream.name)
                stream.write(content)
            staged.chmod(0o600)
            os.replace(staged, destination)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    return path


def compare(directory):
    newest = {}
    for path in Path(directory).glob('*.json'):
        try:
            r = read_report(path)
        except (ValueError, RecursionError) as exc:
            raise ValueError(f'Invalid report {path.name}: {exc}') from exc
        key = (validate_report(r), path.name)
        if r['Computer'] not in newest or key > newest[r['Computer']][0]:
            newest[r['Computer']] = (key, r)
    reports = [item[1] for item in newest.values()]
    if not reports:
        raise ValueError('No JSON reports found; copy one report per computer into this folder.')
    lines = ['Latest snapshot per computer label. Matrix 1.0 estimates; no measured performance ranking.']
    for rankable, heading in ((True, 'Complete candidates (provisional)'), (False, 'Needs review (unranked)')):
        group = [r for r in reports if assessment(r)['Rankable'] == rankable]
        lines += ['', heading, 'Computer                 Score  Resources  Compat.  Coverage  Status']
        for r in sorted(group, key=lambda r: (-r['Score'] if rankable else 0, r['Computer'])):
            label = ''.join(c for c in r['Computer'] if c.isprintable())[:24]
            lines.append(f"{label:24} {r['Score']:3g}/100   {r['Resources']:2g}/70     {r['Compatibility']:2g}/30    {r['Coverage']:3g}/100  {assessment(r)['Title']}")
        if not group:
            lines.append('(none)')
    return '\n'.join(lines)


def menu():
    while True:
        print('\nSCORING MATRIX | beta\n1  Score this computer\n2  Score a specific disk\n3  Compare computer reports\n4  Open reports folder\n5  View scoring matrix\n0  Exit')
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
    parser.add_argument('--ensure-boot-report', action='store_true',
                        help='Reuse this boot and disk selection snapshot, or scan and save one')
    parser.add_argument('--view-json', action='store_true', help='Return a compact shell payload with readiness evidence')
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()
    try:
        if args.latest_json:
            report = latest_report(args.output)
            print(json.dumps(view_report(report) if args.view_json else report))
        elif args.ensure_boot_report:
            report = ensure_boot_report(args.output, args.target_disk)
            print(json.dumps(view_report(report) if args.view_json else report))
        elif args.launch:
            launch()
        elif args.menu:
            menu()
        elif args.compare:
            print(compare(args.compare))
        else:
            report = score(collect(args.target_disk, args.secure_boot_reported), args.label)
            report['ScanBootId'] = boot_id()
            report['ScanTargetDisk'] = args.target_disk or ''
            path = save(report, args.output)
            print(json.dumps(view_report(report)) if args.view_json else json.dumps(report) if args.json else render(report) + '\n\nSaved: ' + str(path))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        print('Scoring Matrix: ' + str(e), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        return 0


if __name__ == '__main__':
    sys.exit(main())
