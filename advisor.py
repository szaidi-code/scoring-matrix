"""Local advice and user-recorded evidence; independent of matrix scoring."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import stat
import tempfile
import time


CHECKS = {
    'graphics': 'Graphics acceleration',
    'wifi': 'Wi-Fi',
    'bluetooth': 'Bluetooth',
    'audio': 'Audio',
    'suspend': 'Suspend and resume',
    'displays': 'External displays',
}
PROFILES = {
    'everyday': ('Everyday desktop', 'Prioritize responsive browsing, sufficient memory, and working audio, Wi-Fi and displays.'),
    'development': ('Development', 'Prioritize memory and storage for your editor, build tools and project files.'),
    'containers': ('Containers', 'Prioritize memory, CPU concurrency and disk capacity; verify your container workload separately.'),
    'gaming-ai': ('Gaming / local AI', 'Check application-specific GPU, driver and VRAM requirements; this inventory does not measure them.'),
}
RESULTS = ('untested', 'pass', 'fail')
BENCHMARK_ITERATIONS = 200000
BENCHMARK_SAMPLES = 3
MAX_STATE_BYTES = 1024 * 1024
MAX_MACHINES = 256
MAX_COMPUTER_LABEL_LENGTH = 256
MAX_ENVIRONMENT_LENGTH = 4096


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def fingerprint(report):
    """Conservatively invalidate checks after kernel, hardware or driver changes."""
    inv = report['Inventory']
    pci = inv.get('PCI')
    if not isinstance(pci, list) or not pci:
        pci = inv.get('Graphics')
    if not isinstance(pci, list):
        pci = []
    network = inv.get('Network')
    if not isinstance(network, list):
        network = []
    usb = inv.get('USB')
    if not isinstance(usb, list):
        usb = []
    hardware = {
        'Computer': report['Computer'], 'System': inv.get('System'),
        'CPU': inv.get('CPU'), 'Kernel': inv.get('Kernel'),
        'RAMGiB': inv.get('RAMGiB'), 'SelectedDisk': inv.get('SelectedDisk'),
        'Firmware': inv.get('Firmware'), 'SecureBoot': inv.get('SecureBoot'),
        'PCI': sorted((str(p.get('Address', '')), str(p.get('Vendor', '')),
                       str(p.get('Device', '')), str(p.get('Driver', '')))
                      for p in pci if isinstance(p, dict)),
        'USB': sorted(str(item) for item in usb),
        'Network': sorted((str(n.get('Name', '')), str(n.get('Vendor', '')),
                           str(n.get('Device', '')), str(n.get('Driver', '')))
                          for n in network if isinstance(n, dict)),
    }
    return hashlib.sha256(json.dumps(hardware, sort_keys=True).encode()).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate field in advisor state.')
        result[key] = value
    return result


def _valid_timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_state(data):
    if (not isinstance(data, dict) or set(data) != {'Version', 'Profile', 'Machines'}
            or data.get('Version') != 2 or not isinstance(data.get('Profile'), str)
            or data['Profile'] not in PROFILES):
        raise ValueError('Invalid advisor state; your saved data was not changed.')
    machines = data.get('Machines')
    if not isinstance(machines, dict) or len(machines) > MAX_MACHINES:
        raise ValueError('Invalid advisor machines; your saved data was not changed.')
    for label, machine in machines.items():
        if (not isinstance(label, str) or not label.strip()
                or len(label) > MAX_COMPUTER_LABEL_LENGTH
                or not isinstance(machine, dict)
                or set(machine) != {'Checks', 'Benchmark'}):
            raise ValueError('Invalid advisor machine; your saved data was not changed.')
        checks = machine.get('Checks')
        if not isinstance(checks, dict) or not set(checks).issubset(CHECKS):
            raise ValueError('Invalid compatibility checks; your saved data was not changed.')
        for entry in checks.values():
            if (not isinstance(entry, dict)
                    or set(entry) != {'Result', 'Captured', 'Context', 'Environment'}
                    or entry.get('Result') not in RESULTS
                    or not _valid_timestamp(entry.get('Captured'))
                    or not isinstance(entry.get('Context'), str)
                    or not re.fullmatch(r'[0-9a-f]{64}', entry['Context'])
                    or not isinstance(entry.get('Environment'), str)
                    or len(entry['Environment']) > MAX_ENVIRONMENT_LENGTH):
                raise ValueError('Invalid compatibility check; your saved data was not changed.')
        bench = machine.get('Benchmark')
        if bench is not None and (not isinstance(bench, dict)
                                  or set(bench) != {'Captured', 'Context', 'MedianSeconds',
                                                    'Iterations', 'Samples', 'Python'}
                                  or not _valid_timestamp(bench.get('Captured'))
                                  or not isinstance(bench.get('Context'), str)
                                  or not re.fullmatch(r'[0-9a-f]{64}', bench['Context'])
                                  or type(bench.get('MedianSeconds')) not in (int, float)
                                  or not 0 < bench['MedianSeconds'] < 86400
                                  or bench.get('Iterations') != BENCHMARK_ITERATIONS
                                  or bench.get('Samples') != BENCHMARK_SAMPLES
                                  or not isinstance(bench.get('Python'), str)
                                  or len(bench['Python']) > 32):
            raise ValueError('Invalid benchmark result; your saved data was not changed.')


def load_state(directory):
    path = Path(directory) / '.advisor.json'
    if path.is_symlink():
        raise OSError('Advisor state must not be a symlink.')
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return {'Version': 2, 'Profile': 'everyday', 'Machines': {}}
    try:
        with os.fdopen(fd, 'rb') as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError('Advisor state must be a regular file.')
            if os.name == 'posix' and metadata.st_mode & 0o077:
                raise PermissionError('Advisor state permissions must be private (0600).')
            if metadata.st_size > MAX_STATE_BYTES:
                raise ValueError('Advisor state exceeds the 1 MiB limit.')
            raw = stream.read(MAX_STATE_BYTES + 1)
            if len(raw) > MAX_STATE_BYTES:
                raise ValueError('Advisor state exceeds the 1 MiB limit.')
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object)
    except UnicodeDecodeError as exc:
        raise ValueError('Advisor state is not valid UTF-8.') from exc
    except RecursionError as exc:
        raise ValueError('Advisor state nesting exceeds the supported limit.') from exc
    _validate_state(data)
    return data


def update_state(directory, update):
    """Serialize and atomically replace local state, including across widget instances."""
    import fcntl
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = directory / '.advisor.lock'
    if lock_path.is_symlink():
        raise OSError('Advisor lock must not be a symlink.')
    lock_fd = os.open(lock_path,
                      os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    os.fchmod(lock_fd, 0o600)
    with os.fdopen(lock_fd, 'r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state(directory)
        update(state)
        _validate_state(state)
        payload = (json.dumps(state, indent=2) + '\n').encode('utf-8')
        if len(payload) > MAX_STATE_BYTES:
            raise ValueError('Advisor state exceeds the 1 MiB limit.')
        staged = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=directory,
                                             prefix='.advisor-', delete=False) as stream:
                staged = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            staged.chmod(0o600)
            os.replace(staged, directory / '.advisor.json')
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)


def set_check(directory, report, key, result):
    if key not in CHECKS or result not in RESULTS:
        raise ValueError('Invalid compatibility check or result.')
    _validate_machine_label(report)
    inv = report['Inventory']
    devices = [d for collection in ('PCI', 'Network')
               for d in (inv.get(collection) if isinstance(inv.get(collection), list) else [])
               if isinstance(d, dict)]
    drivers = sorted({str(d['Driver']) for d in devices if isinstance(d, dict) and d.get('Driver')})
    environment = 'Kernel: ' + str(inv.get('Kernel') or 'unknown') + '; drivers: ' + (', '.join(drivers) or 'unknown')
    environment = environment[:MAX_ENVIRONMENT_LENGTH]
    entry = {'Result': result, 'Captured': timestamp(), 'Context': fingerprint(report),
             'Environment': environment}
    def update(state):
        machine = _machine(state, report['Computer'])
        machine['Checks'][key] = entry
    update_state(directory, update)


def set_profile(directory, profile):
    if profile not in PROFILES:
        raise ValueError('Invalid workload profile.')
    update_state(directory, lambda state: state.__setitem__('Profile', profile))


def _validate_machine_label(report):
    label = report.get('Computer')
    if (not isinstance(label, str) or not label.strip()
            or len(label) > MAX_COMPUTER_LABEL_LENGTH):
        raise ValueError('Computer label is invalid for advisor state.')


def _machine(state, label):
    machine = state['Machines'].get(label)
    if machine is None:
        if len(state['Machines']) >= MAX_MACHINES:
            raise ValueError('Advisor state has reached its machine limit.')
        machine = {'Checks': {}, 'Benchmark': None}
        state['Machines'][label] = machine
    return machine


def run_cpu_benchmark(directory, report):
    """Single-threaded CPU workload; writes no benchmark data to storage."""
    _validate_machine_label(report)
    samples = []
    for _ in range(BENCHMARK_SAMPLES):
        start = time.perf_counter()
        hashlib.pbkdf2_hmac('sha256', b'scoring-matrix', b'local-cpu-test',
                            BENCHMARK_ITERATIONS)
        samples.append(time.perf_counter() - start)
    result = {'Captured': timestamp(), 'Context': fingerprint(report),
              'MedianSeconds': statistics.median(samples),
              'Iterations': BENCHMARK_ITERATIONS, 'Samples': BENCHMARK_SAMPLES,
              'Python': platform.python_version()}
    def update(state):
        machine = _machine(state, report['Computer'])
        machine['Benchmark'] = result
    update_state(directory, update)
    return result


def recommendations(report):
    inv = report['Inventory']
    actions = []
    missing = [part['Category'] for part in report['Breakdown'] if not part['Known']]
    if missing:
        actions.append('Complete missing inventory first: ' + ', '.join(missing) + '.')
    ram = inv.get('RAMGiB')
    if isinstance(ram, (int, float)) and 15 <= ram < 31:
        actions.append('About 32 GiB of RAM would add 5 v1 points; verify upgrade compatibility first.')
    elif isinstance(ram, (int, float)) and ram < 15:
        actions.append('Consider more RAM for multitasking; verify capacity and upgrade compatibility first.')
    disk = inv.get('SelectedDisk')
    if not disk:
        actions.append('Select the intended whole disk and rescan before judging storage.')
    elif isinstance(disk, dict) and disk.get('Media') == 'HDD':
        actions.append('Consider an SSD for responsiveness; verify hardware compatibility first.')
    if inv.get('SecureBoot') is True:
        actions.append('Review Omarchy Secure Boot guidance before installation; no settings were changed.')
    if not actions:
        actions.append('Record hands-on compatibility checks before relying on this inventory.')
    return actions[:3]


def changes(previous, report):
    if previous is None:
        return []
    old, new = previous['Inventory'], report['Inventory']
    fields = [
        ('CPU', lambda i: i.get('CPU')),
        ('OS-visible RAM', lambda i: i.get('RAMGiB')),
        ('Selected disk', lambda i: i.get('SelectedDisk')),
        ('Graphics', lambda i: i.get('Graphics')),
        ('Network', lambda i: [{k: n.get(k) for k in ('Name', 'Vendor', 'Device', 'Driver', 'Wireless')}
                               for n in (i.get('Network') if isinstance(i.get('Network'), list) else [])
                               if isinstance(n, dict)]),
        ('Kernel', lambda i: i.get('Kernel')),
    ]
    result = [name + ' changed' for name, get in fields if get(old) != get(new)]
    for a, b in zip(previous['Breakdown'], report['Breakdown']):
        difference = b['Points'] - a['Points']
        if difference:
            result.append(f"{a['Category']} v1 points: {a['Points']:g} to {b['Points']:g} ({difference:+g})")
    delta = report['Score'] - previous['Score']
    if delta:
        result.insert(0, f'V1 score changed by {delta:+g} points')
    return result or ['No tracked hardware, driver or score changes.']


def summary(report, state, previous=None):
    context = fingerprint(report)
    machine = state['Machines'].get(report['Computer'], {'Checks': {}, 'Benchmark': None})
    checks = []
    for key, label in CHECKS.items():
        entry = machine['Checks'].get(key)
        checks.append({'Key': key, 'Label': label,
                       'Result': entry['Result'] if entry else 'untested',
                       'Captured': entry['Captured'] if entry else None,
                       'Environment': entry['Environment'] if entry else None,
                       'Stale': bool(entry and entry['Result'] != 'untested' and entry['Context'] != context)})
    bench = machine.get('Benchmark')
    if bench:
        bench = dict(bench, Stale=bench['Context'] != context)
        bench.pop('Context')
    profile = state['Profile']
    actions = [f"Retest {item['Label']}; the system context changed." if item['Stale']
               else f"Investigate and retest {item['Label']}; your last check failed."
               for item in checks if item['Stale'] or item['Result'] == 'fail']
    return {'Recommendations': (actions + recommendations(report))[:3], 'Checks': checks,
            'Profile': profile, 'ProfileLabel': PROFILES[profile][0],
            'ProfileGuidance': PROFILES[profile][1], 'Benchmark': bench,
            'PreviousCaptured': previous['Captured'] if previous else None,
            'Changes': changes(previous, report)}


def redacted(report, state):
    """Allowlist only non-identifying summary fields, with no free-form inventory."""
    info = summary(report, state)
    return {
        'Format': 'scoring-matrix-redacted-v1',
        'MatrixVersion': report['MatrixVersion'],
        'Score': report['Score'], 'Resources': report['Resources'],
        'CompatibilityEstimate': report['Compatibility'], 'Coverage': report['Coverage'],
        'Categories': [{'Category': part['Category'], 'Points': part['Points'],
                        'Maximum': part['Maximum'], 'Known': part['Known']}
                       for part in report['Breakdown']],
        'Checks': [{'Check': item['Key'], 'Result': item['Result'], 'Stale': item['Stale']}
                   for item in info['Checks']],
        'Profile': info['Profile'],
        'Disclaimer': 'Inventory estimates and user-recorded checks; not proof of compatibility.',
    }


def export_redacted(directory, report, state):
    folder = Path(directory) / 'exports'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=folder,
                                     prefix='.export-', suffix='.tmp', delete=False) as stream:
        staged = Path(stream.name)
        destination = folder / ('redacted-' + staged.name[len('.export-'):-len('.tmp')] + '.json')
        try:
            json.dump(redacted(report, state), stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
            staged.chmod(0o600)
            os.replace(staged, destination)
        finally:
            staged.unlink(missing_ok=True)
    return destination
