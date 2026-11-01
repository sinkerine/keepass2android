#!/usr/bin/env python3
"""Measure large-file ADB transfer reliability on the runner's private emulator.

Run only through the isolated runner:
    kp2a e2e -- python3 tests/e2e/adb_transfer_stress.py [--rounds N] [--size-mb M]

Each attempt records exit code, stderr, received byte count, SHA-256, duration and
device state, so silent truncation (exit 0, short output) is counted as a failure.
Records go to $KP2A_E2E_ARTIFACTS/adb-transfer-stress/attempts.jsonl.

Useful modes (methods: pull, pull-Z, exec-out, verified):
  --phases cold --methods exec-out,pull ...   first reads of the installed APK right
      after handover; with `kp2a e2e --settle-timeout 0` this hits the post-boot burst
      where the link drops
  --phases cold --delay 60 --burn 2           the same transfers under synthetic CPU load
  --phases post-install,settled               repeated rounds over a random blob and the APK
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import adb_transfer

SERIAL = os.environ['ANDROID_SERIAL']
ADB = ['adb', '-s', SERIAL]
ARTIFACTS = Path(os.environ['KP2A_E2E_ARTIFACTS']) / 'adb-transfer-stress'
BLOB = '/data/local/tmp/kp2a-transfer-blob'


def adb(*args, timeout=60):
    return subprocess.run(ADB + list(args), capture_output=True, timeout=timeout)


def state():
    try:
        return adb('get-state', timeout=5).stdout.decode().strip() or 'none'
    except subprocess.TimeoutExpired:
        return 'timeout'


def wait_device(limit=20.0):
    start = time.monotonic()
    while time.monotonic() - start < limit:
        if state() == 'device':
            return round(time.monotonic() - start, 3)
        time.sleep(0.1)
    return None


def guest_sha(path):
    out = adb('shell', 'sha256sum', path, timeout=120)
    return out.stdout.decode().split()[0] if out.returncode == 0 and out.stdout else None


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def attempt(method, source, size, digest, log, phase, index):
    target = ARTIFACTS / 'received.bin'
    target.unlink(missing_ok=True)
    if method == 'verified':
        return verified(source, size, digest, log, phase, index)
    if method == 'exec-out':
        command = ADB + ['exec-out', 'cat', source]
    else:
        command = ADB + ['pull'] + (['-Z'] if method == 'pull-Z' else []) + [source, str(target)]
    start = time.monotonic()
    wall = time.time()
    try:
        if method == 'exec-out':
            with open(target, 'wb') as out:
                result = subprocess.run(command, stdout=out, stderr=subprocess.PIPE, timeout=180)
        else:
            result = subprocess.run(command, capture_output=True, timeout=180)
        rc = result.returncode
        stderr = result.stderr.decode(errors='replace')[-400:]
    except subprocess.TimeoutExpired:
        rc, stderr = 'timeout', ''
    duration = round(time.monotonic() - start, 3)
    after = state()
    received = target.stat().st_size if target.exists() else None
    received_sha = sha(target) if received == size else None
    if digest is None:
        # Cold phase: hash in the guest only after the transfer, so adbd performs the first read.
        digest = guest_sha(source)
    record = dict(phase=phase, index=index, method=method, source=source, wall=wall, rc=rc,
                  duration=duration, received=received, expected=size, stderr=stderr,
                  state_after=after, ok=rc == 0 and received == size and received_sha == digest)
    if after != 'device':
        record['reconnect_seconds'] = wait_device()
    log.write(json.dumps(record) + '\n')
    log.flush()
    print(f"{phase} #{index} {method:8} {source.rsplit('/', 1)[-1]}: rc={rc} bytes={received}/{size} "
          f"{duration}s state={after} {'OK' if record['ok'] else 'FAIL'}", flush=True)
    target.unlink(missing_ok=True)
    return record


def verified(source, size, digest, log, phase, index):
    target = ARTIFACTS / 'received.bin'
    package = os.environ['KP2A_E2E_PACKAGE']
    def paths():
        return sorted(adb('shell', 'pm', 'path', package).stdout.decode().split())
    try:
        record = adb_transfer.pull_verified(source, target, expected_sha256=digest,
                                            check=paths if '/data/app/' in source else None)
    except adb_transfer.TransferError as error:
        record = error.record
    ok = (record['status'] == 'verified' and record.get('guest_size') == size
          and target.exists() and target.stat().st_size == size)
    record.update(phase=phase, index=index, method='verified', ok=ok)
    log.write(json.dumps(record) + '\n')
    log.flush()
    tries = [(a['rc'], a['received']) for a in record['attempts']]
    print(f"{phase} #{index} verified {source.rsplit('/', 1)[-1]}: {record['status']} attempts={tries} "
          f"{'OK' if ok else 'FAIL'}", flush=True)
    target.unlink(missing_ok=True)
    return dict(record, rc=0 if ok else 1, source=source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=10)
    parser.add_argument('--size-mb', type=int, default=280)
    parser.add_argument('--settle', type=int, default=60, help='Seconds to idle before the settled phase')
    parser.add_argument('--methods', default='pull,exec-out,pull-Z')
    parser.add_argument('--phases', default='post-install,settled')
    parser.add_argument('--reinstall-apk', type=Path,
                        help='Host APK reinstalled before each reinstall-<delay> phase round')
    parser.add_argument('--reinstall-delays', default='0,20',
                        help='Seconds between reinstall and transfer, one phase each')
    parser.add_argument('--burn', type=int, default=0,
                        help='Run the cold transfers while N busy loops per guest CPU saturate the guest, then again idle')
    parser.add_argument('--memhog-mb', type=int, default=0,
                        help='Instead of busy loops, grow a guest tmpfs to this size during the loaded transfers')
    parser.add_argument('--delay', type=float, default=0, help='Seconds to wait before the first transfer')
    args = parser.parse_args()
    time.sleep(args.delay)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    methods = args.methods.split(',')
    package = os.environ['KP2A_E2E_PACKAGE']
    apk = adb('shell', 'pm', 'path', package).stdout.decode().strip().removeprefix('package:')
    phases = args.phases.split(',') if args.phases else []
    records = []
    with open(ARTIFACTS / 'attempts.jsonl', 'a') as log:
        if 'cold' in phases:
            size = int(adb('shell', 'stat', '-c', '%s', apk).stdout.decode().strip())
            loaded = 'mem' if args.memhog_mb else 'burn' if args.burn else None
            for label in ([loaded, 'idle'] if loaded else ['cold']):
                if label == 'mem':
                    # Grow guest shared memory in steps so lmkd and reclaim run during the transfers.
                    adb('shell', 'su 0 sh -c "mkdir -p /data/local/tmp/kp2a-mem && '
                                 'mount -t tmpfs -o size=4000M kp2a-mem /data/local/tmp/kp2a-mem"')
                    adb('shell', f'su 0 setsid sh -c "for i in $(seq {args.memhog_mb // 25}); do '
                                 'head -c 25M /dev/zero > /data/local/tmp/kp2a-mem/$i; sleep 0.2; done" '
                                 '</dev/null >/dev/null 2>&1 &')
                    time.sleep(3)
                if label == 'burn':
                    # Saturate every guest vCPU long after boot to test whether load alone drops the link.
                    adb('shell', f'for i in $(seq $(($(nproc)*{args.burn}))); do '
                                 'setsid timeout 300 sh -c "while :; do :; done" </dev/null >/dev/null 2>&1 & done')
                    time.sleep(3)
                for index, method in enumerate(methods):
                    records.append(attempt(method, apk, size, None, log, label, index))
                if label == 'mem':
                    wait_device()
                    adb('shell', 'su 0 sh -c "pkill -f kp2a-mem; umount /data/local/tmp/kp2a-mem"')
                    time.sleep(5)
                if label == 'burn':
                    wait_device()
                    adb('shell', 'pkill -f "while :; do :; done"')
                    time.sleep(5)
            phases.remove('cold')
    if args.reinstall_apk:
        phases += [f'reinstall-{delay}' for delay in args.reinstall_delays.split(',')]
    sources = {}
    if phases:
        # Create the blob in the guest so no transfer happens before measurement.
        made = adb('shell', f'dd if=/dev/urandom of={BLOB} bs=1048576 count={args.size_mb} 2>/dev/null; sync',
                   timeout=300)
        assert made.returncode == 0, made.stderr
    for path in (BLOB, apk) if phases else ():
        size = int(adb('shell', 'stat', '-c', '%s', path).stdout.decode().strip())
        sources[path] = (size, guest_sha(path))
    (ARTIFACTS / 'sources.json').write_text(json.dumps(sources, indent=2))
    with open(ARTIFACTS / 'attempts.jsonl', 'a') as log:
        for phase in phases:
            if phase == 'settled':
                time.sleep(args.settle)
            for index in range(args.rounds):
                if phase.startswith('reinstall-'):
                    # Reproduce the post-install window, then transfer only the unrelated blob.
                    wait_device()
                    installed = adb('install', '--no-incremental', '-r', str(args.reinstall_apk), timeout=180)
                    log.write(json.dumps(dict(phase=phase, index=index, event='reinstall', wall=time.time(),
                                              rc=installed.returncode)) + '\n')
                    time.sleep(int(phase.removeprefix('reinstall-')))
                for method in methods:
                    for path, (size, digest) in sources.items():
                        if phase.startswith('reinstall-') and path != BLOB:
                            continue
                        records.append(attempt(method, path, size, digest, log, phase, index))
    summary = {}
    for record in records:
        key = f"{record['phase']}/{record['method']}/{'apk' if record['source'] == apk else 'blob'}"
        bucket = summary.setdefault(key, {'ok': 0, 'fail': 0, 'silent_truncation': 0})
        bucket['ok' if record['ok'] else 'fail'] += 1
        if record['rc'] == 0 and not record['ok']:
            bucket['silent_truncation'] += 1
    (ARTIFACTS / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    adb('shell', 'rm', '-f', BLOB)


if __name__ == '__main__':
    main()
