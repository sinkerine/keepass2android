#!/usr/bin/env python3
"""Bounded original AC5/9/10 UI checks; run only in one fresh kp2a e2e child.

Uses the approved installed-byte gate, a loopback-only synthetic WebDAV byte
store, normal settings/storage picker/offline UI and persisted KDBX oracles.
"""
import hashlib
import json
import os
import re
import signal
from contextlib import contextmanager
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
from keeshare_local_acceptance import LocalAcceptance, APPROVED_APK, EXPECTED_APK_BYTES
from offline_mount_data import (LoopbackDav, prepare, custom, group, mounts, add_marker,
                                DESKTOP, IOC_PREFIX, MOUNT_PREFIX)
from pykeepass import PyKeePass

CASES = ('prepare', 'AC10-nonlocal-offline-skip-local-control',
         'AC10-online-automatic-recovery', 'AC9-mount-picker-create-peer-remove')
OFFLINE = 'Work on internal cache only'
ONLINE = 'Synchronize cache copy with source'
HTTP_USER = 'fixture-user'
HTTP_PASSWORD = 'fixture-webdav-pass'


class OfflineMount(LocalAcceptance):
    def __init__(self):
        self.service = None
        self.command_events = []
        self.navigation_deadline = None
        super().__init__()
        self.results = {name: {'status': 'not-run'} for name in CASES}
        self.deadline = time.monotonic() + 14 * 60
        self.offline_start = None

    @staticmethod
    def redact(raw):
        raw = LocalAcceptance.redact(raw)
        raw = raw.replace(HTTP_USER.encode(), b'[synthetic-user-redacted]')
        raw = raw.replace(HTTP_PASSWORD.encode(), b'[synthetic-secret-redacted]')
        return re.sub(rb'(https?://)[^/\s<>"|]*@', rb'\1[credentials-redacted]@', raw)

    def adb_run(self, *args, **kwargs):
        if self.navigation_deadline is not None:
            remaining = self.navigation_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Navigation step deadline exceeded before command')
            kwargs['timeout'] = min(kwargs.get('timeout', 40), remaining)
        event = {'sequence': len(self.command_events), 'phase': getattr(self, 'current', 'provenance'),
                 'command': self.redact((' '.join(args)).encode()).decode(),
                 'started_wall': time.time(), 'started_monotonic': time.monotonic(), 'status': 'running'}
        self.command_events.append(event)
        def persist():
            if hasattr(self, 'art'):
                with (self.art / 'offline-mount-commands.json').open('w') as output:
                    json.dump(self.command_events, output, indent=2)
                    output.flush()
                    os.fsync(output.fileno())
        persist()
        try:
            result = super().adb_run(*args, **kwargs)
            event.update(status='finished', returncode=result.returncode)
            return result
        except BaseException as error:
            event.update(status='failed', error=type(error).__name__, message=str(error))
            raise
        finally:
            event.update(finished_wall=time.time(), finished_monotonic=time.monotonic())
            persist()

    @contextmanager
    def navigation(self, label, seconds=60):
        previous = self.navigation_deadline
        self.navigation_deadline = min(previous or float('inf'), time.monotonic() + seconds)
        self.observations['navigation'] = {'step': label, 'status': 'running', 'started': time.time()}
        self.record()
        try:
            yield
            self.observations['navigation']['status'] = 'finished'
        except BaseException as error:
            self.observations['navigation'].update(status='failed', error=str(error))
            raise
        finally:
            self.navigation_deadline = previous
            self.record()

    def scroll_text(self, value, down=True):
        # Source uses a preference RecyclerView or an explicit KeeShare ListView.
        # Stop at an unchanged viewport; never sweep both directions blindly.
        with self.navigation('find visible text: ' + value, 40):
            previous = None
            for _ in range(5):
                nodes = self.nodes()
                found = next((n for n in nodes if n.get('text') == value), None)
                if found is not None:
                    return found
                viewport = [(n.get('resource-id'), n.get('text'), n.get('bounds')) for n in nodes]
                if viewport == previous:
                    break
                previous = viewport
                scroll = next((n for n in nodes if n.get('scrollable') == 'true' and
                    n.get('resource-id', '').rsplit('/', 1)[-1] in ('recycler_view', 'keeshare_list', 'list', 'gridview')), None)
                assert scroll is not None, 'No supported scroll container for ' + value
                x1, y1, x2, y2 = map(int, re.findall(r'\d+', scroll.get('bounds')))
                self.snap('navigation-before-scroll')
                self.shell('input', 'swipe', str((x1+x2)//2), str(y2-80 if down else y1+80),
                           str((x1+x2)//2), str(y1+80 if down else y2-80), '300')
            raise AssertionError('Text unavailable after bounded source-backed scrolling: ' + value)

    def config(self):
        with self.navigation('Settings > Database settings > KeeShare groups', 65):
            self.overflow('Settings')
            self.tap(self.text('Database settings', seconds=10))
            self.snap('database-preferences')
            self.tap(self.scroll_text('KeeShare groups'))
            self.by_id('keeshare_list', seconds=10)
            self.snap('configuration-entered')

    def record(self):
        (self.art / 'offline-mount-results.json').write_bytes(self.redact(json.dumps({
            'apk': self.apk, 'package': self.package, 'started': self.started,
            'serial': os.environ['ANDROID_SERIAL'], 'private_adb': os.environ['ADB_SERVER_SOCKET'],
            'cases': self.results, 'observations': self.observations,
            'installed_provenance': self.provenance,
            'scope': 'Original AC5/9 mount UI and AC10 offline/online, synthetic WebDAV only; live SMB waived',
        }, indent=2).encode()) + b'\n')

    def open_path(self, path, filename=None, already_open=False):
        if filename is not None:
            self.filename = filename
        assert '://' not in path, 'File-open intent fallback is local-only'
        self.shell('am', 'start', '-a', 'kp2a.action.SelectCurrentDbActivity',
                   '-p', self.package, '--es', 'fileName', path)
        nodes = self.wait_nodes(lambda nodes: (
            any(n.get('resource-id') == self.package + ':id/pass_ok' and n.get('text') == 'Unlock' for n in nodes)
            and any(n.get('resource-id') == self.package + ':id/filename' and n.get('text') == path for n in nodes))
            or any(n.get('resource-id') == self.package + ':id/group_text' and n.get('text') == 'Personal'
                   for n in nodes), 'exact filename with Unlock or already-open root', seconds=60)
        if any(n.get('resource-id') == self.package + ':id/pass_ok' for n in nodes):
            assert not already_open, 'Unexpected unlock would invalidate actual offline control'
            self.unlock()
        self.wait_operations_idle('open-' + (filename or 'remote'), titles=('Personal',))

    def choose_http(self, path):
        with self.navigation('normal HTTP picker with synthetic login', 60):
            self.tap(self.scroll_text('HTTP (WebDav)'))
            self.fill('http_url', self.service.base + path)
            self.fill('http_user', HTTP_USER)
            # Password has importantForAccessibility=no in httpcredentials.axml.
            # TAB from the focused username is the normal next-field action.
            self.key(61)
            self.shell('input', 'text', HTTP_PASSWORD)
            self.key(4)
            self.snap('normal-http-login')
            self.tap(self.text('OK', seconds=10))

    def open_remote(self):
        with self.navigation('normal Open file HTTP parent', 110):
            self.root()
            self.overflow('Open another database…')
            nodes = self.wait_nodes(lambda nodes: any(n.get('resource-id') == self.package + ':id/gridview'
                or n.get('resource-id') == self.package + ':id/start_open_file' for n in nodes),
                'database selector or file selection', seconds=15)
            if any(n.get('resource-id') == self.package + ':id/gridview' for n in nodes):
                self.tap(self.text('Open file...', seconds=10))
            self.tap(self.by_id('start_open_file', seconds=15))
            self.choose_http('/remote-parent.kdbx')
            self.by_id('pass_ok', seconds=15)
            self.unlock()
            self.wait_operations_idle('normal-http-parent-opened', titles=('Personal',))
            ledger = self.service.snapshot()
            assert any(r['method'] == 'GET' and r['path'] == '/remote-parent.kdbx' for r in ledger), \
                'Normal HTTP parent opening reached no actual server request'
            self.observations['normal_http_parent_opened'] = {'positive_requests': ledger,
                'picker_login_supplied': True, 'raw_remote_intent_used': False}

    def switch_open(self, filename):
        with self.navigation('normal selector switch: ' + filename, 45):
            self.root()
            self.tap(self.wait(lambda n: n.get('content-desc') == 'Navigate up', 'root database selector', seconds=10))
            self.by_id('gridview', seconds=10)
            node = self.wait(lambda n: n.get('class') == 'android.widget.Button' and
                filename in n.get('text', ''), 'already-open database: ' + filename, seconds=10)
            self.snap('already-open-selector')
            self.tap(node)
            nodes = self.wait_nodes(lambda nodes: any(n.get('resource-id') == self.package + ':id/group_text'
                and n.get('text') == 'Personal' for n in nodes) or
                any(n.get('resource-id') == self.package + ':id/pass_ok' for n in nodes), 'already-open root', seconds=10)
            assert not any(n.get('resource-id') == self.package + ':id/pass_ok' for n in nodes), \
                'Unexpected Unlock invalidates offline control'
            self.wait_operations_idle('already-open-' + filename, titles=('Personal',))

    def root(self):
        self.back_to_root()
        self.wait_operations_idle('root', titles=('Personal',))

    def menu_state(self, expected, absent):
        self.tap(self.wait(lambda n: n.get('content-desc') == 'More options', 'More options'))
        nodes = self.nodes({'text': expected})
        assert not any(n.get('text') == absent for n in nodes), 'Conflicting offline menu state'
        self.snap('menu-' + ('offline' if expected == ONLINE else 'online'))
        self.key(4)

    def assert_offline_ledger(self, label):
        ledger = self.service.snapshot()
        assert ledger == self.offline_start, 'Actual server request occurred while offline: ' + label
        self.observations.setdefault('offline_ledger_samples', []).append({
            'label': label, 'time': time.time(), 'requests': len(ledger)})
        self.record()

    def save_local(self, filename, predicate, label):
        return self.eventually_file(filename, predicate, label + '.kdbx')

    def mount_case(self):
        self.open_path(self.canonical_files + '/mount-parent.kdbx', 'mount-parent.kdbx')
        self.config()
        self.wait_status('Team Sync', lambda value: value == 'Location not set on this device', 'peer initially unset')
        self.snap('peer-no-mapping')
        self.row_button('Team Import', 'keeshare_row_edit')
        assert self.by_id('keeshare_path').get('text') == DESKTOP + '/team.kdbx'
        self.tap(self.scroll_to_id('keeshare_pick_device_file'))
        self.choose_http('/shares/team.kdbx')
        checkbox = self.scroll_to_id('keeshare_remember_mount')
        assert checkbox.get('checked') == 'true', 'Derived mount checkbox not checked'
        assert DESKTOP in checkbox.get('text', '') and '/shares' in checkbox.get('text', ''), \
            'Unexpected derived prefix/folder'
        self.snap('derived-checkbox')
        self.tap(self.scroll_to_id('keeshare_save'))
        self.by_id('keeshare_list')
        def mapped(path):
            db = PyKeePass(path, password='main-pass')
            return any(rows for rows in mounts(db).values())
        saved = self.save_local('mount-parent.kdbx', mapped, 'mount-created')
        db = PyKeePass(saved, password='main-pass')
        values = mounts(db)
        assert len(values) == 1, 'Expected one current-device mount key'
        key, rows = next(iter(values.items()))
        assert len(rows) == 1 and rows[0][0] == DESKTOP, 'Wrong desktop mapping'
        assert ('10.0.2.2:' + str(self.service.server.server_port) + '/shares') in rows[0][1], 'Wrong serialized mapped folder'
        assert HTTP_USER in rows[0][1] and HTTP_PASSWORD in rows[0][1], 'Provider folder IOC lost supplied synthetic credentials'
        picked = custom(group(db, 'Team Import'))
        iocs = [k for k in picked if k.startswith(IOC_PREFIX)]
        assert iocs == [IOC_PREFIX + key.removeprefix(MOUNT_PREFIX)], 'Mount and pick differ in device owner'
        assert not any(k.startswith(IOC_PREFIX) for k in custom(group(db, 'Team Sync'))), 'Peer has a device override'
        self.by_id('keeshare_mount_prefix')
        self.text(DESKTOP)
        self.snap('visible-persisted-mount')
        baseline = len(self.service.snapshot())
        self.row_button('Team Sync', 'keeshare_row_sync')
        self.wait_status('Team Sync', lambda value: value == 'Imported changes from KeeShare', 'unpicked mapped peer import')
        self.root()
        self.tap(self.text('Team Sync'))
        self.text('Mapped Peer Marker')
        self.snap('unpicked-peer-visible')
        saved = self.save_local('mount-parent.kdbx', lambda path:
            PyKeePass(path, password='main-pass').find_entries(title='Mapped Peer Marker', first=True) is not None,
            'mount-peer-imported')
        db = PyKeePass(saved, password='main-pass')
        assert not any(k.startswith(IOC_PREFIX) for k in custom(group(db, 'Team Sync'))), 'Peer acquired an IOC'
        ledger = self.service.snapshot()[baseline:]
        assert any(row['method'] == 'GET' and row['path'] == '/shares/peer.kdbx' for row in ledger), 'No actual peer fetch'
        self.root()
        self.config()
        self.tap(self.by_id('keeshare_mount_remove'))
        removed = self.save_local('mount-parent.kdbx', lambda path:
            not any(mounts(PyKeePass(path, password='main-pass')).values()), 'mount-removed')
        self.by_id('keeshare_list')
        assert not any(n.get('resource-id') == self.package + ':id/keeshare_mount_prefix' for n in self.nodes()), \
            'Removed mount remains visible'
        self.snap('mount-removed-ui')
        self.row_button('Team Sync', 'keeshare_row_sync')
        self.wait_status('Team Sync', lambda value: value == 'Location not set on this device', 'peer unavailable after remove')
        self.root()
        self.observations['mount'] = {'device_key': key, 'created_map': values,
            'removed_map': mounts(PyKeePass(removed, password='main-pass')),
            'peer_no_ioc': True, 'peer_marker': 'Mapped Peer Marker',
            'picker': 'normal HTTP (WebDav) picker; filename dialog, real derive checkbox',
            'peer_requests': ledger,
            'downloads_limit': 'SAF content display has no filename segments after scheme root; GetFilePath unsupported; no SAF mapping pass claimed'}

    def offline_case(self):
        self.open_remote()
        self.tap(self.text('Team Import'))
        self.text('Network Initial Marker')
        self.snap('initial-network-import')
        self.root()
        self.menu_state(OFFLINE, ONLINE)
        changed = add_marker(self.service.read('/remote-share.kdbx'), self.files / 'changed-remote-share.kdbx',
                             'Online Recovery Marker')
        self.service.replace('/remote-share.kdbx', changed)
        self.overflow(OFFLINE)
        self.menu_state(ONLINE, OFFLINE)
        self.wait_operations_idle('offline-start-drained', titles=('Personal',))
        self.offline_start = self.service.snapshot()
        self.observations['offline_start'] = {'time': time.time(), 'ledger_requests': len(self.offline_start),
            'changed_remote_sha256': hashlib.sha256(changed).hexdigest()}
        self.config()
        self.row_button('Team Import', 'keeshare_row_sync')
        self.wait_status('Team Import', lambda value: value == 'KeeShare is unavailable in offline mode', 'actual offline skip')
        self.snap('nonlocal-offline-result')
        self.root()
        self.tap(self.text('Team Import'))
        nodes = self.nodes({'text': 'Network Initial Marker'})
        assert not any(n.get('text') == 'Online Recovery Marker' for n in nodes), 'Offline phase imported remote update'
        self.snap('offline-content-unchanged')
        self.root()
        self.menu_state(ONLINE, OFFLINE)
        self.assert_offline_ledger('remote-skip')
        # Keep process/global OfflineMode alive. This second parent is local and
        # uses an ordinary relative reference; no seeded device IOC or mount.
        self.push(self.files / 'local-share-updated.kdbx', 'local-share.kdbx')
        self.filename = 'local-control.kdbx'
        self.switch_open('local-control.kdbx')
        self.config()
        self.row_button('Team Import', 'keeshare_row_sync')
        self.wait_status('Team Import', lambda value: value == 'Imported changes from KeeShare', 'local positive offline sync')
        self.root()
        self.tap(self.text('Team Import'))
        self.text('Offline Local Control Marker')
        self.snap('local-positive-import-visible')
        persisted = self.save_local('local-control.kdbx', lambda path:
            PyKeePass(path, password='main-pass').find_entries(title='Offline Local Control Marker', first=True) is not None,
            'offline-local-control-imported')
        assert not any(mounts(PyKeePass(persisted, password='main-pass')).values())
        self.assert_offline_ledger('local-positive-import')
        self.root()
        self.switch_open('remote-parent.kdbx')
        self.menu_state(ONLINE, OFFLINE)
        self.config()
        self.wait_status('Team Import', lambda value: value == 'KeeShare is unavailable in offline mode', 'offline remains enabled')
        self.snap('offline-still-visible-after-local-control')
        self.root()
        self.assert_offline_ledger('after-local-control-return')
        (self.art / 'offline-ledger-window.json').write_text(json.dumps({
            'start': self.offline_start, 'end': self.service.snapshot(), 'new_requests': []}, indent=2) + '\n')

    def recovery_case(self):
        assert self.offline_start is not None, 'Offline setup did not complete'
        self.assert_offline_ledger('before-online-tap')
        self.overflow(ONLINE)
        self.wait_operations_idle('online-auto-sync', titles=('Personal',))
        self.menu_state(OFFLINE, ONLINE)
        self.tap(self.text('Team Import'))
        self.text('Online Recovery Marker', seconds=60)
        self.snap('automatic-online-import-visible')
        self.root()
        self.config()
        self.wait_status('Team Import', lambda value: value == 'Imported changes from KeeShare', 'online automatic import result')
        self.snap('online-result')
        self.root()
        dbpath = self.art / 'online-recovered-remote-parent.kdbx'
        dbpath.write_bytes(self.service.read('/remote-parent.kdbx'))
        db = PyKeePass(dbpath, password='main-pass')
        marker = db.find_entries(title='Online Recovery Marker', first=True)
        assert marker is not None and marker.parentgroup.name == 'Team Import', 'Recovery not persisted in actual server parent'
        ledger = self.service.snapshot()[len(self.offline_start):]
        assert any(r['method'] == 'GET' and r['path'] == '/remote-share.kdbx' for r in ledger), 'No online share request'
        assert any(r['method'] in ('PUT', 'MOVE') for r in ledger), 'No parent persistence request'
        self.observations['online_recovery'] = {'marker': marker.title,
            'automatic_trigger': 'visible Synchronize cache copy with source; no KeeShare Sync now',
            'requests_after_online': ledger, 'parent_sha256': hashlib.sha256(dbpath.read_bytes()).hexdigest()}

    def run(self):
        with LoopbackDav(self.art / 'webdav-request-ledger.json') as service:
            self.service = service
            with self.case('prepare'), self.navigation('prepare visible preferences and local control', 240):
                service.files.update(prepare(self.files))
                self.shell('run-as', self.package, 'mkdir', '-p', 'files')
                for name in ('mount-parent.kdbx', 'local-control.kdbx', 'local-share.kdbx'):
                    self.push(self.files / name)
                self.launch()
                self.by_id('start_open_file', 60)
                self.open_path(self.canonical_files + '/local-control.kdbx', 'local-control.kdbx')
                self.set_app_checkbox('File handling', 'Allow clear-text network traffic in WebDav', True)
                self.set_app_checkbox('File handling', 'Database caching', True)
                self.set_app_checkbox('File handling', 'Synchronize in background', False)
                self.root()
                self.observations['service'] = {'binding': '127.0.0.1', 'port': service.server.server_port,
                    'emulator_url': service.base, 'scope': 'owned byte-store child; synthetic picker credentials; server accepts without auth'}
            for name, action in (
                    ('AC10-nonlocal-offline-skip-local-control', self.offline_case),
                    ('AC10-online-automatic-recovery', self.recovery_case),
                    ('AC9-mount-picker-create-peer-remove', self.mount_case)):
                if time.monotonic() >= self.deadline:
                    self.observations['deadline_reached'] = True
                    break
                if name == 'AC10-online-automatic-recovery' and self.results['AC10-nonlocal-offline-skip-local-control']['status'] != 'passed':
                    continue
                try:
                    with self.case(name):
                        with self.navigation(name, 390 if name == 'AC10-nonlocal-offline-skip-local-control' else 250):
                            action()
                except Exception:
                    if self.transport_failed:
                        break
                    if name.startswith('AC10'):
                        # Keep the independent local mount route available only if
                        # actual online state can be recovered through visible UI.
                        try:
                            self.root()
                            self.overflow(ONLINE)
                            self.wait_operations_idle('failure-online-recovery', titles=('Personal',))
                        except Exception as recovery_error:
                            self.observations['failed_route_recovery'] = {'error': str(recovery_error),
                                'next': 'independent local mount fixture; normal local unlock restores online state'}
                            self.record()
                            continue
        self.observations['server_cleanup'] = {'thread_stopped': not service.thread.is_alive(), 'socket_closed': service.server.fileno() == -1}
        self.record()


def main():
    def terminate(_signum, _frame):
        raise TimeoutError('Enforced child timeout sent SIGTERM')
    signal.signal(signal.SIGTERM, terminate)
    journey = None
    try:
        journey = OfflineMount()
        journey.run()
        return 0 if all(r['status'] == 'passed' for r in journey.results.values()) else 1
    except Exception as error:
        traceback.print_exc()
        if journey is None and os.environ.get('KP2A_E2E_ARTIFACTS'):
            art = Path(os.environ['KP2A_E2E_ARTIFACTS']) / 'keeshare'
            art.mkdir(exist_ok=True)
            (art / 'offline-mount-results.json').write_text(json.dumps({
                'target_apk_sha256': APPROVED_APK, 'expected_apk_bytes': EXPECTED_APK_BYTES,
                'startup': {'status': 'failed', 'error': str(error)},
                'cases': {name: {'status': 'not-run', 'reason': 'Startup provenance gate failed'} for name in CASES}}, indent=2) + '\n')
        return 1
    finally:
        if journey is not None:
            if journey.service is not None:
                journey.observations['server_cleanup'] = {
                    'thread_stopped': not journey.service.thread.is_alive(),
                    'socket_closed': journey.service.server.fileno() == -1}
            journey.record()
            if not journey.transport_failed:
                (journey.art / 'offline-mount-logcat.txt').write_bytes(journey.redact(journey.adb_run('logcat', '-d').stdout))


if __name__ == '__main__':
    raise SystemExit(main())
