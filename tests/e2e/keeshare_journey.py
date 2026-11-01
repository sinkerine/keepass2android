#!/usr/bin/env python3
"""Exercise KeeShare through the Android UI on a fresh `kp2a e2e` emulator.

Run: nix run . -- -c 'kp2a build && kp2a e2e -- python3 tests/e2e/keeshare_journey.py'
All inputs are synthetic. results.json distinguishes passed, failed and unrun cases.
No activity internals or host replicas of the Android engine are used.
Use --extended for nested fixtures, or --resume-regressions ARTIFACT_DIR for
remaining checks in a new emulator seeded only with prior synthetic files.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from zipfile import ZipFile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).with_name('keeshare')))
from make_fixtures import make_fixtures
from verify_share import verify_share
from journey_data import enrich, load_share, save_zip, group_state, custom, assert_sanitized
from lxml import etree
from pykeepass import PyKeePass

# Review cases requiring additional controlled lifecycle/provider infrastructure are
# explicit omissions, never passing placeholders. See the adjacent coverage file.
CASES = [
    '01-prepare', '02-open', '03-relative-import', '04-readonly',
    '05-zip-import', '06-save-export', '07-configuration', '08-create-share',
    '09-device-file-failure', '10-log-secrets',
    'engine-add-change-delete', 'wrong-key-atomic', 'recursive-export-metadata',
    'repeat-sync-stability', 'nested-local-config-merge', 'local-move-recycle',
    'import-disabled-safe-skip', 'direct-duplicate-uuid-readonly',
    'picker-no-presave-write', 'editor-recreation', 'changed-parent-reload',
    'offline-recovery',
]


class Journey:
    def __init__(self, extended=False, resume_regressions=None, remaining_only=False):
        self.extended = extended
        self.resume_regressions = resume_regressions
        self.remaining_only = remaining_only
        required = ('ANDROID_SERIAL', 'ADB_SERVER_SOCKET', 'KP2A_E2E_PACKAGE', 'KP2A_E2E_ARTIFACTS')
        if not all(os.environ.get(k) for k in required):
            raise RuntimeError('Run only as a child of kp2a e2e (private ADB required)')
        self.package = os.environ['KP2A_E2E_PACKAGE']
        self.art = Path(os.environ['KP2A_E2E_ARTIFACTS']) / 'keeshare'
        self.art.mkdir(parents=True)
        self.adb = ['adb', '-s', os.environ['ANDROID_SERIAL']]
        self.results = {case: {'status': 'not-run'} for case in CASES}
        self.current = 'setup'
        self.last_xml = b''
        self.files = self.art / 'fixtures'
        self.started = time.time()
        self.apk = self.installed_apk()

    def installed_apk(self):
        # The runner may use --apk outside the build tree. Identify the installed
        # package through this run's private ADB, never a host APK's mtime.
        def package_paths():
            output = self.shell('pm', 'path', self.package)
            lines = output.splitlines()
            if not lines or any(not re.fullmatch(r'package:/[^\r\n]+\.apk', line) for line in lines):
                raise RuntimeError('Cannot identify installed APK paths: ' + output)
            paths = [line.removeprefix('package:') for line in lines]
            if len(set(paths)) != len(paths):
                raise RuntimeError('Ambiguous installed APK paths: ' + output)
            return paths

        paths = package_paths()
        bases = [path for path in paths if Path(path).name == 'base.apk']
        if len(bases) != 1:
            raise RuntimeError('Expected exactly one installed base APK: ' + repr(paths))
        apk = self.art / 'installed-base.apk'
        self.adb_run('pull', bases[0], str(apk))
        if set(package_paths()) != set(paths):
            raise RuntimeError('Installed APK paths changed while collecting provenance')
        data = apk.read_bytes()
        if not data:
            raise RuntimeError('Pulled installed base APK is empty')
        return {'path': bases[0], 'artifact': str(apk.resolve()),
                'source': 'installed-package-base', 'package_paths': paths,
                'sha256': hashlib.sha256(data).hexdigest()}

    def adb_run(self, *args, check=True, **kwargs):
        return subprocess.run(self.adb + list(args), check=check, capture_output=True,
                              timeout=kwargs.pop('timeout', 40), **kwargs)

    def shell(self, *args):
        return self.adb_run('shell', *args).stdout.decode().strip()

    @staticmethod
    def redact(raw):
        for secret in (b'main-pass', b'share-pass', b'exp-pass'):
            raw = raw.replace(secret, b'[synthetic-secret-redacted]')
        return raw

    def dump(self):
        # Clear both cached evidence and the remote file before every attempt so
        # failed uiautomator invocations can never supply a preceding hierarchy.
        self.last_xml = b''
        (self.art / 'latest.xml').unlink(missing_ok=True)
        remote = '/data/local/tmp/keeshare-window.xml'
        evidence = bytearray()
        try:
            for args in (('shell', 'rm', '-f', remote),
                         ('shell', 'uiautomator', 'dump', remote),
                         ('exec-out', 'cat', remote)):
                result = self.adb_run(*args, check=False)
                evidence.extend(('command: ' + ' '.join(args) + '\nreturncode: '
                                 + str(result.returncode) + '\nstdout:\n').encode())
                evidence.extend(result.stdout + b'\nstderr:\n' + result.stderr + b'\n')
                if result.returncode:
                    raise RuntimeError('UI dump command failed')
            raw = result.stdout
            root = ET.fromstring(raw)
            if root.tag != 'hierarchy' or root.find('node') is None:
                raise ET.ParseError('not a populated hierarchy')
        except (RuntimeError, ET.ParseError, subprocess.TimeoutExpired) as error:
            if isinstance(error, subprocess.TimeoutExpired):
                evidence.extend((error.stdout or b'') + b'\n' + (error.stderr or b''))
            evidence.extend(('\n' + str(error) + '\n').encode())
            with (self.art / 'dump-error.txt').open('ab') as output:
                output.write(self.redact(bytes(evidence)))
            return None
        # Persist masked evidence even while checking the revealed input value.
        self.last_xml = self.redact(raw)
        (self.art / 'latest.xml').write_bytes(self.last_xml)
        return root

    def nodes(self, *anchors):
        root = self.dump()
        if root is None:
            raise AssertionError('Cannot capture fresh UI hierarchy; see dump-error.txt')
        nodes = list(root.iter('node'))
        for anchor in anchors:
            assert any(all(node.get(key) == value for key, value in anchor.items())
                       for node in nodes), 'Missing expected-screen anchor: ' + repr(anchor)
        return nodes

    def wait_nodes(self, predicate, description, seconds=35):
        # Only explicit, bounded polling may retry a failed capture. An absent
        # hierarchy must never be passed to a predicate as an empty observation.
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            root = self.dump()
            if root is not None:
                nodes = list(root.iter('node'))
                if predicate(nodes):
                    return nodes
            time.sleep(.4)
        raise AssertionError('Missing UI: ' + description)

    def wait(self, predicate, description, seconds=35):
        nodes = self.wait_nodes(lambda nodes: any(predicate(node) for node in nodes),
                                description, seconds)
        return next(node for node in nodes if predicate(node))

    def by_id(self, name, seconds=35):
        return self.wait(lambda n: n.get('resource-id') == self.package + ':id/' + name, name, seconds)

    def scroll_to_id(self, name):
        for _ in range(8):
            root = self.dump()
            if root is None:
                time.sleep(.4)
                continue
            node = next((n for n in root.iter('node') if n.get('resource-id') == self.package + ':id/' + name), None)
            if node is not None:
                return node
            # Collapse the unlock header / scroll the editor, using visible UI.
            self.shell('input', 'swipe', '540', '815', '540', '280', '350')
        return self.by_id(name, 3)

    def text(self, value, seconds=35):
        return self.wait(lambda n: n.get('text') == value, value, seconds)

    def scroll_text(self, value, down=True):
        for direction in (down, not down):
            for _ in range(9):
                root = self.dump()
                if root is None:
                    time.sleep(.4)
                    continue
                nodes = list(root.iter('node'))
                node = next((n for n in nodes if n.get('text') == value), None)
                if node is not None:
                    return node
                scrollable = next((n for n in nodes if n.get('resource-id', '').endswith('keeshare_list')), None)
                if scrollable is None:
                    scrollable = next((n for n in nodes if n.get('scrollable') == 'true'), None)
                bounds = list(map(int, re.findall(r'\d+', scrollable.get('bounds')))) if scrollable is not None else [0, 250, 1080, 1800]
                x = str((bounds[0] + bounds[2]) // 2)
                top, bottom = bounds[1] + 100, bounds[3] - 100
                self.shell('input', 'swipe', x, str(bottom if direction else top),
                           x, str(top if direction else bottom), '350')
        raise AssertionError('Missing scrollable UI: ' + value)

    def tap(self, node, long=False):
        x1, y1, x2, y2 = map(int, re.findall(r'\d+', node.get('bounds', '')))
        x, y = str((x1 + x2) // 2), str((y1 + y2) // 2)
        if long:
            self.shell('input', 'swipe', x, y, x, y, '900')
        else:
            self.shell('input', 'tap', x, y)

    def key(self, code):
        self.shell('input', 'keyevent', str(code))

    def fill(self, name, value, masked=False):
        self.tap(self.by_id(name))
        self.shell('input', 'keycombination', '113', '29')  # CTRL+A on the focused field
        self.key(67)
        if value:
            self.shell('input', 'text', value.replace(' ', '%s'))
        node = self.by_id(name)
        assert node.get('focused') == 'true', 'Input field lost focus: ' + name
        if not masked:
            assert node.get('text') == value, 'Entered text differs: ' + name
        else:
            assert node.get('text'), 'Password field remained empty'

    def snap(self, label):
        if self.dump() is None:
            raise AssertionError('Cannot capture fresh UI hierarchy; see dump-error.txt')
        stem = self.art / (self.current + '-' + label)
        stem.with_suffix('.xml').write_bytes(self.last_xml)
        stem.with_suffix('.png').write_bytes(self.adb_run('exec-out', 'screencap', '-p').stdout)

    def record(self):
        (self.art / 'results.json').write_text(json.dumps({
            'package': self.package, 'serial': os.environ['ANDROID_SERIAL'],
            'private_adb': os.environ['ADB_SERVER_SOCKET'], 'started': self.started,
            'apk': self.apk, 'phase': 'extended' if self.extended else 'core', 'cases': self.results,
            'unverified': [name for name, result in self.results.items() if result['status'] == 'not-run'],
            'coverage_notes': 'tests/e2e/keeshare/coverage.md',
        }, indent=2) + '\n')

    @contextmanager
    def case(self, name):
        self.current = name
        self.results[name] = {'status': 'running'}
        self.record()
        print('RUN:', name, flush=True)
        try:
            yield
            self.snap('passed')
            self.results[name]['status'] = 'passed'
            self.results[name]['artifacts'] = [name + '-passed.xml', name + '-passed.png']
            print('PASS:', name, flush=True)
        except Exception as error:
            self.results[name] = {'status': 'failed', 'error': str(error), 'type': type(error).__name__}
            failure = traceback.format_exc()
            try:
                self.snap('failed')
            except Exception as snapshot_error:
                self.results[name]['snapshot_error'] = str(snapshot_error)
            (self.art / (name + '-traceback.txt')).write_bytes(self.redact(failure.encode()))
            raise
        finally:
            self.record()

    def push(self, path, name=None):
        name = name or path.name
        assert re.fullmatch(r'[a-zA-Z0-9_.-]+', name)
        self.adb_run('push', str(path), '/data/local/tmp/' + name)
        self.shell('run-as', self.package, 'cp', '/data/local/tmp/' + name, 'files/' + name)

    def pull(self, name, label=None, required=True):
        result = self.adb_run('exec-out', 'run-as', self.package, 'cat', 'files/' + name, check=False)
        if result.returncode:
            if required:
                raise AssertionError('App file missing: ' + name)
            return None
        path = self.art / (label or name)
        path.write_bytes(result.stdout)
        return path

    def eventually_file(self, name, predicate, label=None, seconds=45):
        end = time.monotonic() + seconds
        last = None
        while time.monotonic() < end:
            path = self.pull(name, label, required=False)
            if path:
                try:
                    if predicate(path):
                        return path
                except Exception as error:
                    last = type(error).__name__
            time.sleep(1)
        raise AssertionError('File assertion timed out: ' + name + ' (' + str(last) + ')')

    def launch(self):
        self.adb_run('shell', 'monkey', '-p', self.package, '-c', 'android.intent.category.LAUNCHER', '1')

    def choose_document(self, filename):
        self.tap(self.text('System file picker'))
        self.wait(lambda n: n.get('package') == 'com.google.android.documentsui', 'Android document picker')
        self.snap('document-picker')
        # Downloads provides a real local DocumentsProvider with persisted grants.
        self.tap(self.wait(lambda n: n.get('content-desc') == 'Show roots', 'document roots'))
        self.tap(self.text('Downloads'))
        self.tap(self.text(filename))

    def unlock(self):
        self.scroll_to_id('password_edit')
        self.fill('password_edit', 'main-pass', masked=True)
        # Reveal and assert the actual entered password before clicking Unlock.
        toggle = self.wait(lambda n: n.get('content-desc') == 'Show password', 'Show password')
        self.tap(toggle)
        assert self.by_id('password_edit').get('text') == 'main-pass', 'Actual password not entered'
        self.tap(self.by_id('toggle_password'))
        self.snap('password-entered-masked')
        self.key(4)  # hide IME, then resolve a fresh button node
        self.tap(self.by_id('pass_ok'))
        self.text('Team Import', 35)
        self.text('Team Sync')
        self.snap('unlocked-groups')

    def back_to_root(self):
        for _ in range(8):
            root = self.dump()
            if root is None:
                time.sleep(.4)
                continue
            if any(n.get('text') == 'Personal' and n.get('resource-id', '').endswith('group_text') for n in root.iter('node')):
                return
            self.key(4)
        raise AssertionError('Root groups not restored after Back')

    def app_setting(self, category, title):
        self.back_to_root()
        self.overflow('Settings')
        self.tap(self.text('App settings'))
        self.tap(self.scroll_text(category))
        self.tap(self.scroll_text(title))

    def set_app_checkbox(self, category, title, checked):
        self.back_to_root()
        self.overflow('Settings')
        self.tap(self.text('App settings'))
        self.tap(self.scroll_text(category))
        self.scroll_text(title)

        def checkbox():
            root = self.dump()
            assert root is not None, 'Cannot capture fresh preference hierarchy'
            for row in reversed(list(root.iter('node'))):
                if any(n.get('text') == title for n in row.iter('node')):
                    boxes = [n for n in row.iter('node') if n.get('checkable') == 'true']
                    if len(boxes) == 1:
                        return boxes[0]
            raise AssertionError('Missing preference checkbox: ' + title)

        if checkbox().get('checked') != str(checked).lower():
            self.tap(self.text(title))
        assert checkbox().get('checked') == str(checked).lower(), 'Preference not set: ' + title
        self.snap('preference-' + re.sub('[^a-z]+', '-', title.lower()).strip('-'))

    def overflow(self, text):
        nodes = self.nodes()
        direct = next((n for n in nodes if n.get('text') == text or n.get('content-desc') == text), None)
        if direct is not None:
            self.tap(direct)
            return
        self.tap(self.wait(lambda n: n.get('content-desc') == 'More options', 'More options'))
        self.tap(self.text(text))

    def config(self):
        # Exercise the settings entry point, rather than launching its exported intent.
        self.overflow('Settings')
        self.tap(self.text('Database settings'))
        self.tap(self.scroll_text('KeeShare groups'))
        self.by_id('keeshare_list')

    def status(self, group):
        row = self.config_row(group)
        return next(n.get('text', '') for n in row.iter('node')
                    if n.get('resource-id') == self.package + ':id/keeshare_row_status')

    def wait_status(self, group, predicate, description):
        end = time.monotonic() + 40
        while time.monotonic() < end:
            if predicate(self.status(group)):
                return
            time.sleep(1)
        raise AssertionError('Missing share result: ' + description)

    def config_row(self, group):
        self.scroll_text(group)
        for _ in range(5):
            root = self.dump()
            if root is None:
                time.sleep(.4)
                continue
            # Innermost matching row wins: an ancestor list may expose only one
            # header while still containing a clipped preceding row's status.
            for parent in reversed(list(root.iter('node'))):
                names = [n for n in parent.iter('node') if n.get('resource-id') == self.package + ':id/keeshare_row_name']
                if len(names) == 1 and names[0].get('text') == group:
                    if any(n.get('resource-id') == self.package + ':id/keeshare_row_sync' for n in parent.iter('node')):
                        return parent
            # Keep the row header visible while bringing its buttons into view.
            header = self.scroll_text(group, down=False)
            _, y1, _, y2 = map(int, re.findall(r'\d+', header.get('bounds')))
            distance = max(80, min(550, y1 - 280))
            self.shell('input', 'swipe', '540', str(min(1100, y2 + 50)),
                       '540', str(max(300, min(1100, y2 + 50) - distance)), '300')
        raise AssertionError('Configuration row missing: ' + group)

    def row_button(self, group, name):
        row = self.config_row(group)
        self.tap(next(n for n in row.iter('node') if n.get('resource-id') == self.package + ':id/' + name))

    def sync_now(self):
        self.row_button('Personal' if self.extended else 'Team Import', 'keeshare_row_sync')
        time.sleep(3)

    def main_db(self, label):
        return PyKeePass(self.pull('main.kdbx', label + '.kdbx'), password='main-pass')

    def readonly_case(self):
        with self.case('04-readonly'):
            anchors = ({'resource-id': self.package + ':id/keeshare_readonly_info'},
                       {'resource-id': self.package + ':id/entry_text', 'text': 'Imported Entry'})
            nodes = self.nodes(*anchors, {'text': 'Team Import'})
            assert not any(n.get('resource-id', '').endswith(
                (':id/fabAddNew', ':id/fabAddNewEntry', ':id/fabAddNewGroup')) for n in nodes), 'Read-only group offers Add'
            self.tap(self.text('Imported Entry'), long=True)
            self.snap('selection')
            nodes = self.nodes(*anchors,
                               {'resource-id': self.package + ':id/check_mark', 'content-desc': 'Selected'},
                               {'resource-id': self.package + ':id/action_mode_close_button'})
            forbidden = {'Delete', 'Move', 'Copy', 'Edit'}
            assert not any(n.get('text') in forbidden or n.get('content-desc') in forbidden or
                           n.get('resource-id', '').endswith((':id/menu_delete', ':id/menu_move',
                                                             ':id/menu_copy', ':id/menu_edit'))
                           for n in nodes), 'Read-only selection offers modification'
            self.key(4)
            self.key(4)

    def decline_templates(self):
        # First creation may show a template offer. Require an observed offer or
        # the actual editor before deciding it can be skipped.
        nodes = self.wait_nodes(lambda nodes: any(n.get('text') == 'Add templates?' or
                                n.get('resource-id') == self.package + ':id/entry_title' for n in nodes),
                                'template offer or entry editor')
        if any(n.get('text') == 'Add templates?' for n in nodes):
            decline = next((n for n in nodes if n.get('text') == 'No'), None)
            assert decline is not None, 'Template offer has no No button'
            self.tap(decline)
        self.by_id('entry_title')

    def run(self):
        if self.resume_regressions:
            self.resume_remaining()
            return
        with self.case('01-prepare'):
            make_fixtures(self.files)
            if self.extended:
                enrich(self.files)
            self.shell('run-as', self.package, 'mkdir', '-p', 'files')
            for name in ('main.kdbx', 'team-import.kdbx', 'team-sync.kdbx.share'):
                self.push(self.files / name)
            # Java's canonical path may use the legacy /data/data alias while
            # shell readlink uses /data/user/0 (different mount namespaces).
            self.canonical_files = '/data/data/' + self.package + '/files'
            assert self.shell('run-as', self.package, 'test', '-f', self.canonical_files + '/main.kdbx') == ''
            (self.art / 'canonical-files-path.txt').write_text(self.canonical_files + '\n')
            listing = self.shell('run-as', self.package, 'ls', 'files')
            (self.art / 'app-files.txt').write_text(listing)
            assert all(name in listing for name in ('main.kdbx', 'team-import.kdbx', 'team-sync.kdbx.share'))
        with self.case('02-open'):
            self.launch()
            self.by_id('start_open_file', 60)
            # Approved opening-only deviation: modern Android hides the local
            # browser. The normal exported open intent retains BuiltInFileStorage.
            self.shell('am', 'start', '-a', 'kp2a.action.SelectCurrentDbActivity',
                       '-p', self.package, '--es', 'fileName',
                       self.canonical_files + '/main.kdbx')
            self.unlock()
        with self.case('03-relative-import'):
            self.tap(self.text('Team Import'))
            self.text('Imported Entry', 60)
            self.by_id('keeshare_readonly_info')
        self.readonly_case()
        with self.case('05-zip-import'):
            self.tap(self.text('Team Sync'))
            self.text('Remote Sync Entry')
            self.by_id('fabAddNew')
            self.snap('editable-share')
        with self.case('06-save-export'):
            self.tap(self.by_id('fabAddNew'))
            self.tap(self.by_id('fabAddNewEntry'))
            self.decline_templates()
            self.fill('entry_title', 'Local Sync Entry')
            self.overflow('Save')
            self.text('Local Sync Entry')
            def exported(path):
                verify_share(path, 'share-pass', ['Remote Sync Entry', 'Local Sync Entry'])
                with ZipFile(path) as z:
                    assert z.namelist() == ['container.share.kdbx']
                return True
            self.eventually_file('team-sync.kdbx.share', exported, '06-export.kdbx.share')
            self.key(4)
        with self.case('07-configuration'):
            self.config()
            for group, kind in [('Team Import', 'Imported from'), ('Team Sync', 'Synchronized with')]:
                row = self.config_row(group)
                texts = [n.get('text', '') for n in row.iter('node')]
                assert any(kind in t for t in texts), texts
                assert any('next to database' in t.lower() for t in texts), texts
                assert any(n.get('resource-id') == self.package + ':id/keeshare_row_status' and
                           n.get('text', '').strip() for n in row.iter('node')), 'Missing observed sync status'
                assert not any('failed' in t.lower() for t in texts), texts
            self.back_to_root()
        with self.case('08-create-share'):
            self.tap(self.text('Personal'), long=True)
            self.overflow('KeeShare…')
            self.tap(self.by_id('keeshare_type_spinner'))
            self.tap(self.text('Export'))
            self.fill('keeshare_path', 'personal-export.kdbx')
            self.fill('keeshare_password', 'exp-pass', masked=True)
            self.key(4)
            keep = self.by_id('keeshare_keep_groups')
            if keep.get('checked') != 'true':
                self.tap(keep)
            self.tap(self.scroll_to_id('keeshare_save'))
            def personal(path):
                verify_share(path, 'exp-pass', ['Personal Entry'], no_reference=True)
                return True
            self.eventually_file('personal-export.kdbx', personal, '08-personal-export.kdbx')
        if not self.extended:
            with self.case('09-device-file-failure'):
                bad = self.files / 'bad.kdbx'
                bad.write_bytes(b'Synthetic invalid KeeShare container\\n')
                self.adb_run('push', str(bad), '/sdcard/Download/bad.kdbx')
                self.config()
                self.row_button('Team Import', 'keeshare_row_edit')
                self.tap(self.scroll_to_id('keeshare_pick_device_file'))
                self.choose_document('bad.kdbx')
                label = self.by_id('keeshare_device_file_label').get('text', '')
                assert 'bad.kdbx' in label, 'Picked file not reflected in editor'
                self.tap(self.scroll_to_id('keeshare_save'))
                self.by_id('keeshare_list')
                def location_saved(path):
                    db = PyKeePass(path, password='main-pass')
                    data = custom(db.find_groups(name='Team Import', first=True))
                    return any(key.startswith('KP2A/KeeShare/Ioc/') and 'bad.kdbx' in value
                               for key, value in data.items())
                self.eventually_file('main.kdbx', location_saved, '09-location-saved.kdbx')
                before = etree.tostring(self.main_db('09-before-sync').tree)
                self.sync_now()
                self.wait_status('Team Import', lambda value: bool(value) and
                                 ('signature' in value.lower() or 'corrupt' in value.lower() or 'fail' in value.lower()),
                                 'bad container failure')
                db = self.main_db('09-failure-main')
                assert etree.tostring(db.tree) == before, 'Failed import modified the database'
                assert db.find_entries(title='Imported Entry', first=True) is not None
                self.snap('failed-status-unchanged')
                self.row_button('Team Import', 'keeshare_row_edit')
                self.tap(self.scroll_to_id('keeshare_clear_device_file'))
                self.tap(self.scroll_to_id('keeshare_save'))
            self.engine_cases()
        else:
            self.config()
            self.export_regressions()
            self.picker_regressions()
            self.trigger_regressions()
            self.recreation_case()
        self.audit_logs()

    def resume_remaining(self):
        # Reuse only synthetic app-written evidence as input to a NEW emulator.
        # No emulator state or scheduler cache survives between these phases.
        self.files.mkdir()
        prior = self.resume_regressions
        inputs = {'nested-export-source.kdbx': 'main.kdbx',
                  'nested-export.kdbx.share': 'team-sync.kdbx.share',
                  'recursive-zip.kdbx.share': 'personal-export.kdbx.share',
                  'fixtures/team-import.kdbx': 'team-import.kdbx'}
        self.shell('run-as', self.package, 'mkdir', '-p', 'files')
        for source, destination in inputs.items():
            local = self.files / destination
            local.write_bytes((prior / source).read_bytes())
            if self.remaining_only and destination == 'main.kdbx':
                seed = PyKeePass(local, password='main-pass')
                for group in seed.groups:
                    if group.name == 'Z Configured Nested':
                        for item in group._element.findall('CustomData/Item'):
                            if item.findtext('Key') == 'KeeShare/Reference':
                                item.getparent().remove(item)
                seed.save()
            self.push(local)
        self.canonical_files = '/data/data/' + self.package + '/files'
        self.launch()
        self.by_id('start_open_file', 60)
        self.shell('am', 'start', '-a', 'kp2a.action.SelectCurrentDbActivity',
                   '-p', self.package, '--es', 'fileName', self.canonical_files + '/main.kdbx')
        self.unlock()
        self.config()
        if not self.remaining_only:
            self.stability_case()
            self.picker_regressions()
        self.recreation_case()
        self.trigger_regressions()
        self.audit_logs()

    def audit_logs(self):
        with self.case('10-log-secrets'):
            logs = self.adb_run('logcat', '-d').stdout.decode(errors='replace')
            (self.art / 'journey-logcat.txt').write_text(logs)
            assert logs.strip(), 'Cannot audit empty logcat'
            assert all(secret not in logs for secret in ('main-pass', 'share-pass', 'exp-pass'))
            assert not any('KeeShare:' in line and ('/data/user/0/' in line or '/data/data/' in line) for line in logs.splitlines())

    def engine_cases(self):
        with self.case('engine-add-change-delete'):
            remote = PyKeePass(self.files / 'team-import.kdbx', password='share-pass')
            old = remote.find_entries(title='Imported Entry', first=True)
            old.title = 'Changed Imported Entry'
            old.touch(modify=True)
            remote.add_entry(remote.root_group, 'Added Imported Entry', 'synthetic', 'synthetic')
            remote.save()
            self.push(self.files / 'team-import.kdbx')
            self.sync_now()
            def changed(path):
                db = PyKeePass(path, password='main-pass')
                return bool(db.find_entries(title='Changed Imported Entry', first=True) and db.find_entries(title='Added Imported Entry', first=True))
            self.eventually_file('main.kdbx', changed, 'engine-changed-main.kdbx')
            deleted = etree.SubElement(remote.tree.find('Root/DeletedObjects'), 'DeletedObject')
            etree.SubElement(deleted, 'UUID').text = base64.b64encode(old.uuid.bytes).decode()
            etree.SubElement(deleted, 'DeletionTime').text = remote._encode_time(datetime.now(timezone.utc))
            remote.delete_entry(old)
            remote.save()
            self.push(self.files / 'team-import.kdbx')
            self.sync_now()
            def removed(path):
                db = PyKeePass(path, password='main-pass')
                return db.find_entries(title='Changed Imported Entry', first=True) is None and db.find_entries(title='Added Imported Entry', first=True) is not None
            self.eventually_file('main.kdbx', removed, 'engine-deleted-main.kdbx')
        with self.case('wrong-key-atomic'):
            before = self.main_db('wrong-key-before')
            before_xml = etree.tostring(before.tree)
            remote.password = 'wrong-key-synthetic'
            remote.save()
            self.push(self.files / 'team-import.kdbx')
            self.sync_now()
            self.wait(lambda n: 'password' in n.get('text', '').lower() and n.get('resource-id', '').endswith('keeshare_row_status'), 'wrong password result')
            after = self.main_db('wrong-key-after')
            assert etree.tostring(after.tree) == before_xml, 'Failed import modified the database'
            remote.password = 'share-pass'
            remote.save()
            self.push(self.files / 'team-import.kdbx')
            self.sync_now()

    def export_regressions(self):
        with self.case('recursive-export-metadata'):
            source = self.main_db('recursive-source')
            group = source.find_groups(name='Personal', first=True)
            before = group_state(group)
            plain = PyKeePass(self.pull('personal-export.kdbx', 'recursive-plain.kdbx'), password='exp-pass')
            assert_sanitized(group, plain)
            self.row_button('Personal', 'keeshare_row_edit')
            self.fill('keeshare_path', 'personal-export.kdbx.share')
            self.key(4)
            self.tap(self.scroll_to_id('keeshare_save'))
            def zip_export(path):
                with ZipFile(path) as z:
                    exported = PyKeePass(BytesIO(z.read('container.share.kdbx')), password='exp-pass')
                current = self.main_db('recursive-zip-source').find_groups(name='Personal', first=True)
                assert_sanitized(current, exported)
                return True
            self.eventually_file('personal-export.kdbx.share', zip_export, 'recursive-zip.kdbx.share')
            # Editing the reference may touch the root; export must not touch children.
            after = group_state(self.main_db('recursive-after').find_groups(name='Personal', first=True))
            for uuid in before:
                if uuid != str(group.uuid):
                    assert before[uuid] == after[uuid], 'Export changed source descendant'
        with self.case('nested-local-config-merge'):
            baseline = self.main_db('nested-before')
            local = baseline.find_groups(name='Z Configured Nested', first=True)
            metadata = custom(local)
            remote = load_share(self.pull('team-sync.kdbx.share', 'nested-remote-before.kdbx.share'))
            entry = remote.find_entries(title='Nested Remote Entry', first=True)
            assert entry is not None
            entry.title = 'Nested Changed Entry'
            entry.touch(modify=True)
            save_zip(remote, self.files / 'team-sync.kdbx.share')
            self.push(self.files / 'team-sync.kdbx.share')
            self.sync_now()
            def merged(path):
                db = PyKeePass(path, password='main-pass')
                return db.find_entries(title='Nested Changed Entry', first=True) is not None
            self.eventually_file('main.kdbx', merged, 'nested-merged-main.kdbx')
            after = self.main_db('nested-after').find_groups(name='Z Configured Nested', first=True)
            assert custom(after) == metadata, 'Genuine merge lost local nested configuration'
            exported = load_share(self.pull('team-sync.kdbx.share', 'nested-export.kdbx.share'))
            assert_sanitized(self.main_db('nested-export-source').find_groups(name='Team Sync', first=True), exported)
        self.stability_case()

    def stability_case(self):
        with self.case('repeat-sync-stability'):
            baseline = self.main_db('stable-before')
            states = {name: group_state(baseline.find_groups(name=name, first=True))
                      for name in ('Personal', 'Team Sync')}
            for cycle in range(3):
                self.sync_now()
                actual = self.main_db('stable-cycle-' + str(cycle))
                for name, expected in states.items():
                    assert group_state(actual.find_groups(name=name, first=True)) == expected, 'Repeated sync changed ' + name
            self.results[self.current]['note'] = 'Three warm-cache sync cycles; cold reopen remains unverified'

    def picker_regressions(self):
        with self.case('picker-no-presave-write'):
            sentinel = self.files / 'sentinel.kdbx'
            sentinel.write_bytes(b'Synthetic sentinel: picker must not write before Save.\\n')
            self.adb_run('push', str(sentinel), '/sdcard/Download/sentinel.kdbx')
            def observed():
                data = self.adb_run('exec-out', 'cat', '/sdcard/Download/sentinel.kdbx').stdout
                stat = self.shell('stat', '-c', '%s:%Y', '/sdcard/Download/sentinel.kdbx')
                return data, stat
            baseline = observed()
            db_before = self.pull('main.kdbx', 'picker-before-main.kdbx').read_bytes()
            self.row_button('Personal', 'keeshare_row_edit')
            self.tap(self.scroll_to_id('keeshare_pick_device_file'))
            self.choose_document('sentinel.kdbx')
            assert 'sentinel.kdbx' in self.by_id('keeshare_device_file_label').get('text', '')
            self.snap('picked-unsaved')
            assert observed() == baseline, 'Picker mutated destination before editor Save'
            self.key(4)
            self.by_id('keeshare_list')
            assert observed() == baseline, 'Editor cancel mutated destination'
            assert self.pull('main.kdbx', 'picker-after-main.kdbx').read_bytes() == db_before, 'Editor cancel saved configuration'
            self.results[self.current]['note'] = 'Existing writable Downloads document select and editor cancel; new plain paths, rejected grants/providers remain unverified'

    def recreation_case(self):
        with self.case('editor-recreation'):
            self.back_to_root()
            self.config()
            self.row_button('Personal', 'keeshare_row_edit')
            self.fill('keeshare_path', 'unsaved-recreated.kdbx')
            self.key(4)
            db_before = self.pull('main.kdbx', 'recreation-before-main.kdbx').read_bytes()
            # Font scale changes are not in this activity's ConfigurationChanges.
            # Unlike rotation this forces an actual destroy/create with saved state.
            self.shell('settings', 'put', 'system', 'font_scale', '1.10')
            time.sleep(2)
            self.by_id('keeshare_path')
            self.wait(lambda n: n.get('resource-id', '').endswith('keeshare_path') and
                      n.get('text') == 'unsaved-recreated.kdbx', 'restored path draft')
            nodes = self.nodes({'resource-id': self.package + ':id/keeshare_path',
                                'text': 'unsaved-recreated.kdbx'},
                               {'resource-id': self.package + ':id/keeshare_password'})
            password = next(n for n in nodes if n.get('resource-id') == self.package + ':id/keeshare_password')
            assert password.get('text') is not None, 'Password field has no observed value'
            assert password.get('text') not in ('exp-pass', '••••••••'), 'Stored password restored after recreation'
            self.tap(self.scroll_to_id('keeshare_save'))
            self.wait(lambda n: 'Re-enter the share password' in n.get('text', ''), 'masked password confirmation')
            self.snap('password-reentry-dialog')
            self.tap(self.text('Cancel'))
            self.key(4)
            # The confirmation's EditText opens the IME; the first Back can
            # consume only that keyboard. Resolve the current screen first.
            nodes = self.wait_nodes(lambda nodes: any(n.get('resource-id') in (
                self.package + ':id/keeshare_path', self.package + ':id/keeshare_list')
                for n in nodes), 'editor or configuration after confirmation cancel')
            if any(n.get('resource-id') == self.package + ':id/keeshare_path' for n in nodes):
                self.key(4)
            self.by_id('keeshare_list')
            assert self.pull('main.kdbx', 'recreation-after-main.kdbx').read_bytes() == db_before, 'Canceled recreated editor saved draft'
            # A failed cat cannot distinguish absence from a provider/ADB error.
            # Require successful app-private directory and nonexistence checks.
            self.shell('run-as', self.package, 'test', '-d', 'files')
            self.shell('run-as', self.package, 'test', '!', '-e', 'files/unsaved-recreated.kdbx')
            self.results[self.current]['note'] = 'Actual font-scale recreation, path draft, password confirmation and cancel; re-entry save, empty key and process death remain unverified'
            self.shell('settings', 'put', 'system', 'font_scale', '1.0')

    def trigger_regressions(self):
        with self.case('import-disabled-safe-skip'):
            self.pull('team-sync.kdbx.share', 'disabled-before.kdbx.share')
            self.app_setting('File handling', 'KeeShare import')
            self.back_to_root()
            self.config()
            remote = load_share(self.art / 'disabled-before.kdbx.share')
            remote.add_entry(remote.root_group, 'Import Disabled Remote Entry', 'synthetic', 'synthetic')
            save_zip(remote, self.files / 'team-sync.kdbx.share')
            self.push(self.files / 'team-sync.kdbx.share')
            remote_bytes = (self.files / 'team-sync.kdbx.share').read_bytes()
            self.sync_now()
            self.wait_status('Team Sync', lambda value: 'Enable KeeShare import' in value, 'import disabled safe skip')
            assert self.pull('team-sync.kdbx.share', 'disabled-after.kdbx.share').read_bytes() == remote_bytes, 'Disabled import exported stale content'
            assert self.main_db('disabled-main').find_entries(title='Import Disabled Remote Entry', first=True) is None
            self.app_setting('File handling', 'KeeShare import')
            self.back_to_root()
            self.config()
            self.sync_now()
            def recovered(path):
                return PyKeePass(path, password='main-pass').find_entries(title='Import Disabled Remote Entry', first=True) is not None
            self.eventually_file('main.kdbx', recovered, 'disabled-recovered.kdbx')
        with self.case('changed-parent-reload'):
            self.back_to_root()
            live = self.main_db('reload-before')
            personal = live.find_entries(title='Personal Entry', first=True)
            personal.title = 'Reloaded Personal Entry'
            personal.touch(modify=True)
            live.save(self.files / 'main.kdbx')
            # Local parents hide the manual Sync command. Use the supported
            # periodic-sync preference, which calls the same noncached check.
            self.set_app_checkbox('File handling', 'Periodic background synchronization', True)
            self.tap(self.scroll_text('Periodic background synchronization time interval'))
            field = self.wait(lambda n: n.get('class') == 'android.widget.EditText', 'sync interval input')
            self.tap(field)
            self.shell('input', 'keycombination', '113', '29')
            self.key(67)
            self.shell('input', 'text', '0')
            assert self.wait(lambda n: n.get('class') == 'android.widget.EditText', 'sync interval input').get('text') == '0'
            self.tap(self.text('OK'))
            self.snap('periodic-sync-configured')
            self.back_to_root()
            before = self.pull('personal-export.kdbx.share', 'reload-export-before.kdbx.share').read_bytes()
            self.push(self.files / 'main.kdbx')
            prompt = 'The file which is currently open was changed by another program. Do you want to reload it?'
            for choice in ('No', 'dismiss', 'Yes'):
                self.text(prompt)
                self.snap('reload-' + choice)
                assert self.pull('personal-export.kdbx.share', 'reload-prompt-' + choice + '-export.kdbx.share').read_bytes() == before, 'Export before reload decision'
                if choice == 'dismiss':
                    self.key(4)
                else:
                    button = 'android:id/button1' if choice == 'Yes' else 'android:id/button2'
                    self.tap(self.wait(lambda n: n.get('resource-id') == button, 'reload ' + choice))
                if choice != 'Yes':
                    time.sleep(2)
                    assert self.pull('personal-export.kdbx.share', 'reload-declined-' + choice + '-export.kdbx.share').read_bytes() == before, 'Export after declining reload'
            self.text('Team Import', 50)
            def reloaded(path):
                with ZipFile(path) as z:
                    db = PyKeePass(BytesIO(z.read('container.share.kdbx')), password='exp-pass')
                return db.find_entries(title='Reloaded Personal Entry', first=True) is not None
            self.eventually_file('personal-export.kdbx.share', reloaded, 'reload-accepted-export.kdbx.share')
            self.results[self.current]['note'] = 'Noncached local parent via UI-enabled periodic sync (zero-minute interval); accept/decline/dismiss; canceled reopen, switching and cached replacement remain unverified'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extended', action='store_true', help='add nested fixtures and review regression cases (separate fresh session)')
    parser.add_argument('--resume-regressions', type=Path, help='seed a fresh emulator from a prior synthetic extended artifact directory')
    parser.add_argument('--remaining-only', action='store_true', help='resume only preference/reload/recreation checks with three configured rows')
    args = parser.parse_args()
    if args.remaining_only and not args.resume_regressions:
        parser.error('--remaining-only requires --resume-regressions')
    journey = Journey(extended=args.extended or bool(args.resume_regressions), resume_regressions=args.resume_regressions, remaining_only=args.remaining_only)
    try:
        journey.run()
    except Exception:
        traceback.print_exc()
        print('FAIL:', journey.current, 'Evidence:', journey.art, flush=True)
        return 1
    finally:
        journey.record()
    print('PASS: implemented cases; see results.json and coverage.md for unrun review cases', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
