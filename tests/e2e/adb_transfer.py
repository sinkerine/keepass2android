"""Verified file transfer from the runner's private emulator.

The emulator's ADB transport can drop mid-transfer while the guest CPU is
saturated (reliably for about 20 seconds after boot) and reconnects within a
second, often only to drop again until the guest calms down. `adb pull` then
fails, while `adb exec-out cat` can exit 0 with truncated output, so neither
exit status nor a host-side input hash proves what was received.

pull_verified() accepts a file only when the received bytes match the guest's
size and SHA-256, measured independently before and after the transfer, and an
optional caller check (such as stable `pm path` output) still holds. A failed
attempt's partial file is deleted, never resumed or concatenated. Only transport
failures (nonzero exit, short or missing output) are retried, a bounded number
of times after the device reconnects and the guest is idle again; a full-size
hash mismatch or a changed source is refused immediately.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


class TransferError(RuntimeError):
    def __init__(self, message, record):
        super().__init__(message)
        self.record = record


def _adb():
    return ['adb', '-s', os.environ['ANDROID_SERIAL']]


def _run(args, timeout):
    return subprocess.run(_adb() + args, capture_output=True, timeout=timeout)


def wait_for_device(limit):
    """Return seconds until `get-state` reports device, or None after limit."""
    start = time.monotonic()
    while time.monotonic() - start < limit:
        try:
            if _run(['get-state'], 5).stdout.decode().strip() == 'device':
                return round(time.monotonic() - start, 3)
        except subprocess.TimeoutExpired:
            pass
        time.sleep(0.2)
    return None


def wait_until_idle(adb, limit, env=None, idle=0.5, calm=3):
    """Wait until guest CPU idle is at least `idle` for `calm` one-second samples.

    Returns (settled, seconds, idle samples); a timed-out or failed shell counts as busy.
    """
    start = time.monotonic()
    previous, samples = None, []
    while time.monotonic() - start < limit:
        try:
            result = subprocess.run(adb + ['shell', 'head', '-1', '/proc/stat'], env=env,
                                    capture_output=True, text=True, timeout=10)
            fields = result.stdout.split() if result.returncode == 0 else []
        except subprocess.TimeoutExpired:
            fields = []
        current = list(map(int, fields[1:5])) if fields[:1] == ['cpu'] else None
        if current and previous:
            delta = [now - before for now, before in zip(current, previous)]
            samples.append(round(delta[3] / max(sum(delta), 1), 2))
            if len(samples) >= calm and min(samples[-calm:]) >= idle:
                return True, round(time.monotonic() - start, 1), samples
        previous = current
        time.sleep(1)
    return False, round(time.monotonic() - start, 1), samples


def guest_identity(remote, timeout=120):
    """Size and SHA-256 computed in the guest, independent of any transfer."""
    size = _run(['shell', 'stat', '-c', '%s', remote], timeout)
    digest = _run(['shell', 'sha256sum', remote], timeout)
    fields = digest.stdout.decode().split()
    if size.returncode or digest.returncode or not fields or not size.stdout.strip().isdigit():
        raise RuntimeError(f'Cannot identify guest file {remote}: {size.stderr!r} {digest.stderr!r}')
    return int(size.stdout), fields[0]


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def pull_verified(remote, local, *, expected_sha256=None, check=None, attempts=3,
                  reconnect_limit=20.0, idle_limit=90.0, timeout=180, record_path=None):
    """Pull remote to local and return a provenance record, or raise TransferError.

    check, if given, is called before and after transfer and must return equal,
    truthy values (for example sorted `pm path` output).
    """
    local = Path(local)
    partial = local.with_name(local.name + '.partial')
    record = {'remote': remote, 'artifact': str(local), 'attempts': [], 'status': 'failed'}

    def finish(status, message=None):
        record['status'] = status
        if message:
            record['error'] = message
        if record_path:
            Path(record_path).write_text(json.dumps(record, indent=2))
        if message:
            raise TransferError(message, record)
        return record

    local.unlink(missing_ok=True)
    partial.unlink(missing_ok=True)
    before = check() if check else None
    if check and not before:
        return finish('refused', 'Source check returned nothing before transfer')
    size, guest_sha = guest_identity(remote)
    record.update(check_before=before, guest_size=size, guest_sha256=guest_sha)
    if expected_sha256 and guest_sha != expected_sha256:
        return finish('refused', 'Guest file differs from expected SHA-256')
    for number in range(1, attempts + 1):
        partial.unlink(missing_ok=True)
        entry = {'attempt': number, 'started': time.time()}
        record['attempts'].append(entry)
        start = time.monotonic()
        try:
            result = _run(['pull', remote, str(partial)], timeout)
            entry.update(rc=result.returncode, stderr=result.stderr.decode(errors='replace')[-500:])
        except subprocess.TimeoutExpired:
            entry.update(rc='timeout', stderr='')
        entry['seconds'] = round(time.monotonic() - start, 3)
        received = partial.stat().st_size if partial.exists() else None
        entry['received'] = received
        if entry['rc'] == 0 and received == size:
            entry['sha256'] = _sha256(partial)
            if entry['sha256'] != guest_sha:
                partial.unlink()
                return finish('refused', 'Received full-size file with a different SHA-256')
            after = check() if check else None
            if after != before:
                partial.unlink()
                record['check_after'] = after
                return finish('refused', 'Source check changed during transfer')
            if guest_identity(remote) != (size, guest_sha):
                partial.unlink()
                return finish('refused', 'Guest file changed during transfer')
            partial.replace(local)
            record.update(check_after=after, received_bytes=received, received_sha256=entry['sha256'])
            return finish('verified')
        # Transport failure: discard partial bytes, wait for reconnect and an idle
        # guest (the link keeps dropping while it is busy), then retry the whole file.
        partial.unlink(missing_ok=True)
        entry['partial_removed'] = True
        entry['reconnect_seconds'] = wait_for_device(reconnect_limit)
        if entry['reconnect_seconds'] is None:
            return finish('failed', 'Device did not reconnect after failed transfer')
        if number < attempts:
            settled, entry['idle_wait_seconds'], entry['idle_samples'] = wait_until_idle(_adb(), idle_limit)
            if not settled:
                return finish('failed', 'Guest stayed busy after failed transfer')
            if wait_for_device(reconnect_limit) is None:
                return finish('failed', 'Device did not reconnect after failed transfer')
        if guest_identity(remote) != (size, guest_sha):
            return finish('refused', 'Guest file changed after failed transfer')
    return finish('failed', f'Transfer failed after {attempts} attempts')
