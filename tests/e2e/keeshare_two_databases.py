#!/usr/bin/env python3
"""Bounded normal-UI SyncUtil reload and duplicate-UUID ownership checks.

Run only under a fresh `kp2a e2e --apk ... -- python3 ...` session. The exported
selector intent is used only for opening synthetic local files with real password
UI. Search, current-DB selection, sync, entry edit and delete use visible UI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
from keeshare_journey import Journey
from keeshare_reload import PROMPT, export_has_title

APPROVED_APK = '98149d7c99a16222d02208a009e27ceaad9d1b2a851a2f609db7671577255216'
from two_databases_data import (prepare, database, entry_by_uuid, assert_entry,
                                tombstoned, TITLE_A, TITLE_B, EDITED_B, RELOADED_A)

CASES = ('prepare', 'open-two-local-databases', 'select-current-and-combined-search',
         'owner-baseline', 'owner-open-edit', 'owner-delete-cancel',
         'owner-delete-recycle', 'owner-delete-permanent', 'reload-phase-reset',
         'sync-baseline', 'reload-reset-decline', 'reload-reset-dismiss',
         'sync-reload-decline', 'sync-reload-dismiss',
         'sync-reload-accept-automatic-export')


class TwoDatabases(Journey):
    def __init__(self, advanced_search=False):
        self.commands = []
        self.transport_failed = False
        self.advanced_search = advanced_search
        self.provenance = {'status': 'collecting', 'commands': [], 'recovery': {'status': 'not-needed'},
                           'transport_root_cause': 'unknown'}
        super().__init__()
        self.results = {name: {'status': 'not-run'} for name in CASES}
        self.observations = {}
        assert self.apk['sha256'] == APPROVED_APK, 'Installed APK differs from approved build'

    def installed_apk(self):
        # Only this startup gate may observe automatic reconnection. It owns one
        # ordinary pull and at most one explicitly recorded uncompressed pull.
        evidence = self.art / 'two-db-installed-provenance.json'
        identity = (os.environ['ANDROID_SERIAL'], os.environ['ADB_SERVER_SOCKET'])
        apk = self.art / 'installed-base.apk'

        def save():
            evidence.write_text(json.dumps(self.provenance, indent=2) + '\n')

        def command(*args, timeout=40):
            if identity != (os.environ['ANDROID_SERIAL'], os.environ['ADB_SERVER_SOCKET']):
                raise RuntimeError('Private ADB session identity changed during provenance')
            entry = {'command': self.redact(' '.join(self.adb + list(args)).encode()).decode()}
            self.provenance['commands'].append(entry)
            try:
                result = super(TwoDatabases, self).adb_run(*args, check=False, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                entry.update(error='timeout', stdout=self.redact(error.stdout or b'').decode(errors='replace'),
                             stderr=self.redact(error.stderr or b'').decode(errors='replace'))
                raise
            else:
                entry.update(returncode=result.returncode,
                             stdout=self.redact(result.stdout).decode(errors='replace'),
                             stderr=self.redact(result.stderr).decode(errors='replace'))
                return result
            finally:
                self.commands.append(dict(entry))
                (self.art / 'two-db-commands.json').write_text(json.dumps(self.commands, indent=2) + '\n')
                save()

        def package_paths():
            result = command('shell', 'pm', 'path', self.package)
            result.check_returncode()
            lines = result.stdout.decode().strip().splitlines()
            if not lines or any(not re.fullmatch(r'package:/[^\r\n]+\.apk', line) for line in lines):
                raise RuntimeError('Cannot identify installed APK paths')
            paths = [line.removeprefix('package:') for line in lines]
            if len(set(paths)) != len(paths):
                raise RuntimeError('Ambiguous installed APK paths')
            return paths

        try:
            paths = package_paths()
            self.provenance['package_paths_before'] = paths
            bases = [path for path in paths if Path(path).name == 'base.apk']
            if len(bases) != 1:
                raise RuntimeError('Expected exactly one installed base APK')
            try:
                normal = command('pull', bases[0], str(apk))
                normal.check_returncode()
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                self.provenance['standard_pull'] = {'status': 'failed',
                    'command_index': len(self.provenance['commands']) - 1,
                    'partial_bytes': apk.stat().st_size if apk.exists() else 0}
                apk.unlink(missing_ok=True)
                self.provenance['recovery'] = {'status': 'waiting-for-device', 'readiness_limit_seconds': 10}
                save()
                deadline = time.monotonic() + 10
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ConnectionError('Private device did not become ready within 10 seconds')
                    try:
                        ready = command('get-state', timeout=remaining)
                    except subprocess.TimeoutExpired:
                        raise ConnectionError('Private device readiness timed out') from None
                    if (time.monotonic() <= deadline and ready.returncode == 0 and
                            ready.stdout.strip() == b'device'):
                        break
                    remaining = deadline - time.monotonic()
                    if remaining > 0:
                        time.sleep(min(.25, remaining))
                recovered_paths = package_paths()
                self.provenance['package_paths_before_recovery'] = recovered_paths
                if recovered_paths != paths:
                    raise RuntimeError('Installed APK paths changed before recovery')
                self.provenance['recovery']['status'] = 'pulling-uncompressed'
                save()
                recovered = command('pull', '-Z', bases[0], str(apk))
                recovered.check_returncode()
                self.provenance['recovery'].update(status='transferred',
                    command_index=len(self.provenance['commands']) - 1)
            else:
                self.provenance['standard_pull'] = {'status': 'transferred',
                    'command_index': len(self.provenance['commands']) - 1}
            after = package_paths()
            self.provenance['package_paths_after'] = after
            if after != paths:
                raise RuntimeError('Installed APK paths changed while collecting provenance')
            data = apk.read_bytes()
            if not data:
                raise RuntimeError('Pulled installed base APK is empty')
            digest = hashlib.sha256(data).hexdigest()
            self.provenance.update(received_bytes=len(data), received_sha256=digest)
            guest = command('shell', 'sha256sum', bases[0])
            guest.check_returncode()
            fields = guest.stdout.decode().strip().split(maxsplit=1)
            if len(fields) != 2 or fields[1] != bases[0] or not re.fullmatch(r'[0-9a-f]{64}', fields[0]):
                raise RuntimeError('Cannot identify independent installed guest SHA256')
            self.provenance['guest_sha256'] = fields[0]
            if digest != fields[0] or digest != APPROVED_APK:
                raise RuntimeError('Installed APK identity mismatch against guest or approved build')
            self.provenance['status'] = 'verified'
            if self.provenance['recovery']['status'] == 'transferred':
                self.provenance['recovery']['status'] = 'verified'
            return {'path': bases[0], 'artifact': str(apk.resolve()),
                    'source': 'installed-package-base', 'package_paths': paths,
                    'sha256': digest, 'guest_sha256': fields[0], 'bytes': len(data),
                    'provenance_evidence': str(evidence.resolve())}
        except Exception as error:
            self.transport_failed = True
            self.provenance.update(status='failed', error=str(error), error_type=type(error).__name__)
            if self.provenance['recovery']['status'] not in ('not-needed', 'verified'):
                self.provenance['recovery']['status'] = 'failed'
            raise
        finally:
            save()

    def adb_run(self, *args, **kwargs):
        # Keep the actual command sequence, including private serial. Mask only
        # synthetic password arguments, consistently with Journey evidence.
        if self.transport_failed:
            raise ConnectionError('Private ADB transport already failed; no further commands')
        command = self.redact((' '.join(self.adb + list(args))).encode()).decode()
        try:
            result = super().adb_run(*args, **kwargs)
        except subprocess.TimeoutExpired as error:
            self.transport_failed = True
            self.commands.append({'command': command, 'error': 'timeout'})
            raise ConnectionError('Private ADB command timed out; stopping session') from error
        except subprocess.CalledProcessError as error:
            self.transport_failed = True
            self.commands.append({'command': command, 'returncode': error.returncode,
                'stdout': self.redact(error.stdout or b'').decode(errors='replace'),
                'stderr': self.redact(error.stderr or b'').decode(errors='replace')})
            raise
        else:
            self.commands.append({'command': command, 'returncode': result.returncode})
            if result.returncode and any(marker in result.stderr.lower() for marker in
                    (b'error: closed', b'device offline', b'device not found', b'no devices',
                     b'protocol fault', b'connection reset', b'cannot connect', b'failed to read')):
                self.transport_failed = True
                raise ConnectionError('Private ADB transport failed; stopping session')
            return result
        finally:
            if hasattr(self, 'art'):
                (self.art / 'two-db-commands.json').write_text(json.dumps(self.commands, indent=2) + '\n')

    def record(self):
        (self.art / 'two-db-results.json').write_text(json.dumps({
            'apk': self.apk, 'package': self.package, 'started': self.started,
            'serial': os.environ['ANDROID_SERIAL'], 'private_adb': os.environ['ADB_SERVER_SOCKET'],
            'cases': self.results, 'observations': self.observations,
            'installed_provenance': self.provenance,
            'not_run': [name for name, result in self.results.items() if result['status'] == 'not-run'],
            'additional_not_run': ['canceled/failed reopen', 'database switch while reload prompt active',
                                   'cached provider replacement', 'direct internal intents',
                                   'history/TAN/stale callbacks and full acceptance matrix'],
            'route': 'two local DBs; normal selector and combined SearchResults; visible Sync targets CurrentDb',
            'search_ui': 'Advanced Search' if self.advanced_search else 'SearchView',
        }, indent=2) + '\n')

    def open_local(self, filename):
        # singleInstance selector does not consume OnNewIntent extras. Recreate
        # its Android task for this supported opening-only intent; keep the app
        # process and already-open DBs alive. Never address an internal activity.
        output = self.shell('am', 'start', '-f', '0x10008000',
                            '-a', 'kp2a.action.SelectCurrentDbActivity', '-p', self.package,
                            '--es', 'fileName', self.canonical_files + '/' + filename)
        (self.art / (self.current + '-' + filename + '-open.txt')).write_text(output)
        assert 'Error' not in output and 'Exception' not in output, output
        self.unlock()

    def select_current(self, owner):
        self.back_to_root()
        self.key(4)
        self.text('Select database')
        nodes = self.nodes()
        for name in ('Owner A', 'Owner B'):
            assert any(n.get('text', '').startswith(name + '\n') for n in nodes), 'Missing open DB ' + name
        self.snap('selector-two-open')
        self.tap(self.wait(lambda n: n.get('text', '').startswith(owner + '\n'), owner))
        self.text('Personal')

    def search(self, titles):
        if self.advanced_search:
            self.overflow('Advanced Search')
            self.fill('searchEditText', 'Shared Owner')
            assert self.by_id('cbSearchInTitle').get('checked') == 'true', 'Title search disabled'
            self.snap('advanced-search-query')
            self.tap(self.by_id('search_button'))
        else:
            self.overflow('Search')
            field = self.by_id('search_src_text')
            self.tap(field)
            self.shell('input', 'text', 'Shared%sOwner')
            entered = self.by_id('search_src_text')
            assert entered.get('focused') == 'true' and entered.get('text') == 'Shared Owner', 'Search query not entered'
            self.snap('search-view-query')
            self.key(66)
        for title in titles:
            self.text(title)
        self.snap('combined-results')

    def sync_menu(self, verify_parent=None):
        self.tap(self.wait(lambda n: n.get('content-desc') == 'More options', 'More options'))
        self.text('Synchronize database…')
        self.snap('visible-sync-menu')
        item = self.text('Synchronize database…')
        if verify_parent:
            self.parent_readback(verify_parent)
        self.tap(item)

    def returned_group(self, label):
        # Search Sync intentionally finishes its reader-owning temporary screen.
        # This assertion never navigates Back to make a blocked importer proceed.
        self.wait_nodes(lambda nodes: any(node.get('text') == 'Personal' and
                        node.get('resource-id') == self.package + ':id/group_text'
                        for node in nodes), 'real root after SearchResults Sync')
        self.snap(label + '-returned-group')
        activities = self.shell('dumpsys', 'activity', 'activities')
        (self.art / (self.current + '-' + label + '-activities.txt')).write_text(activities)
        resumed = [line.strip() for line in activities.splitlines()
                   if 'mResumedActivity:' in line or 'topResumedActivity=' in line]
        assert resumed and any('GroupActivity' in line for line in resumed), 'Real group is not resumed'
        assert not any('SearchResults' in line for line in resumed), 'SearchResults still resumed'
        self.observations[label + '_returned_screen'] = resumed

    def group_windows(self, label, expected):
        activities = self.shell('dumpsys', 'activity', 'activities')
        windows = self.shell('dumpsys', 'window', 'windows')
        stem = self.art / (self.current + '-' + label)
        stem.with_suffix('.activities.txt').write_text(activities)
        stem.with_suffix('.windows.txt').write_text(windows)
        resumed = re.findall(r'topResumedActivity=ActivityRecord\{([^ ]+) [^\n]*GroupActivity[^\n]*', activities)
        assert len(resumed) == 1, 'Expected one resumed GroupActivity'
        records = activities.split('* Hist')
        record = next((block for block in records[1:]
                       if re.search(r'ActivityRecord\{' + re.escape(resumed[0]) + r' ', block.splitlines()[0])), None)
        assert record is not None, 'Cannot locate resumed group record'
        attached = re.search(r'windows=\[([^\n]*)\]', record)
        assert attached, 'Cannot identify group windows'
        tokens = re.findall(r'Window\{([^ ]+) ', attached[1])
        headers = re.findall(r'Window #\d+ Window\{([^ ]+) [^\n]*GroupActivity[^\n]*', windows)
        observation = {'elapsed_since_sync_seconds': time.monotonic() - self.sync_started,
                       'activity_record': resumed[0], 'attached_windows': tokens,
                       'window_dump_group_headers': headers,
                       'expected_windows_including_base': expected}
        self.observations[label + '_windows'] = observation
        self.record()
        assert len(tokens) == expected, 'Expected base plus ' + str(expected - 1) + ' dialog(s): ' + repr(tokens)
        assert all(token in headers for token in tokens), 'Attached group window absent from window dump'
        return observation

    def observe_no_reload(self, decision, seconds=10):
        started = time.monotonic()
        samples = []
        while True:
            nodes = self.nodes()
            assert not any(node.get('text') in (PROMPT, 'Reload file?') for node in nodes), 'Reload prompt resurrected'
            sample = self.group_windows(decision + '-no-resurrection-' + str(len(samples) + 1), 1)
            samples.append(sample)
            self.observations[decision + '_no_resurrection'] = {
                'elapsed_seconds': time.monotonic() - started, 'samples': samples}
            self.record()
            if time.monotonic() - started >= seconds:
                return
            time.sleep(.5)

    def wait_operations_idle(self, label, titles=(), seconds=90, returned_group=False):
        # EndLogging hides this container only after the operation runner drains
        # its queue. Export availability alone does not establish completion.
        end = time.monotonic() + seconds
        idle_since = None
        samples = []
        while time.monotonic() < end:
            nodes = self.nodes()
            texts = {node.get('text') for node in nodes}
            assert all(title in texts for title in titles), 'Wrong screen during operation completion check'
            if returned_group:
                assert any(node.get('text') == 'Personal' and
                           node.get('resource-id') == self.package + ':id/group_text'
                           for node in nodes), 'Real root missing during operation completion check'
            busy = [node for node in nodes if node.get('resource-id', '').rsplit('/', 1)[-1] in
                    ('background_ops_container', 'background_ops_message',
                     'background_ops_submessage', 'cancel_background') or
                    node.get('class', '').endswith('ProgressBar')]
            sample = {'elapsed_seconds': seconds - max(0, end - time.monotonic()),
                      'busy_nodes': [dict(node.attrib) for node in busy]}
            samples.append(sample)
            stem = self.art / (self.current + '-' + label + '-poll-' + str(len(samples)))
            stem.with_suffix('.xml').write_bytes(self.last_xml)
            (self.art / (self.current + '-' + label + '-status.json')).write_text(
                json.dumps(samples, indent=2) + '\n')
            if busy:
                idle_since = None
            elif idle_since is None:
                idle_since = time.monotonic()
            elif time.monotonic() - idle_since >= 3:
                self.snap(label + '-idle')
                self.observations[label] = {'ui_queue_idle': True, 'polls': len(samples),
                                            'idle_seconds_at_least': 3}
                return
            time.sleep(.5)
        self.snap(label + '-not-idle')
        raise AssertionError('Background operations did not become visibly idle: ' + label)

    def parent_readback(self, label, require_replacement=True):
        # Read guest bytes independently of push/cp success, including immediately
        # before the captured visible sync item is tapped.
        path = self.pull('main.kdbx', label + '-parent.kdbx')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        guest = self.shell('run-as', self.package, 'sha256sum', 'files/main.kdbx').split()[0]
        self.observations[label + '_parent'] = {
            'readback_sha256': digest, 'guest_sha256': guest,
            'replacement_sha256': self.observations['changed_parent_sha256'],
            'matches_replacement': digest == self.observations['changed_parent_sha256']}
        self.record()
        assert digest == guest, 'Guest parent changed during readback'
        if require_replacement:
            assert digest == self.observations['changed_parent_sha256'], 'Guest parent differs from replacement'

    def reset_local_phase(self, label):
        # Process reset isolates declined changed files without consuming a
        # foreground prompt or attributing that prompt to visible Sync.
        self.observations[label + '_reset'] = {'force_stop': True,
            'fresh_fixtures': True, 'normal_password_unlock': True}
        self.record()
        self.adb_run('shell', 'am', 'force-stop', self.package)
        self.files = self.art / (label + '-fixtures')
        self.entry_uuid = prepare(self.files)
        for path in self.files.iterdir():
            self.push(path)
        self.launch()
        self.open_local('main.kdbx')
        self.open_local('clone.kdbx')
        self.select_current('Owner A')
        self.search((TITLE_A, TITLE_B))

    def baseline_sync(self, label):
        self.wait_operations_idle(label + '-before-sync', (TITLE_A, TITLE_B))
        self.sync_menu()
        self.returned_group(label)
        self.wait_operations_idle(label + '-complete', returned_group=True)
        baseline = self.eventually_file('personal-export.kdbx.share',
            lambda path: export_has_title(path, TITLE_A), label + '-baseline.kdbx.share')
        self.baseline = baseline.read_bytes()
        self.observations[label + '_export_sha256'] = hashlib.sha256(self.baseline).hexdigest()

    def mutate_parent_in_search(self, label):
        # Establish real combined results FIRST. No app lifecycle/navigation
        # transition occurs between guest replacement and the visible Sync tap.
        self.search((TITLE_A, TITLE_B))
        self.wait_operations_idle(label + '-search-before-mutation', (TITLE_A, TITLE_B))
        activities = self.shell('dumpsys', 'activity', 'activities')
        resumed_before = [line.strip() for line in activities.splitlines()
                          if 'topResumedActivity=' in line]
        assert len(resumed_before) == 1 and 'SearchResults' in resumed_before[0], 'Mutation requires real search'
        before = self.pull('main.kdbx', label + '-before-parent-change.kdbx')
        assert_entry(before, self.entry_uuid, TITLE_A)
        self.observations[label + '_before_parent_change_sha256'] = hashlib.sha256(before.read_bytes()).hexdigest()
        current = database(before)
        entry_by_uuid(current, self.entry_uuid).title = RELOADED_A
        entry_by_uuid(current, self.entry_uuid).touch(modify=True)
        changed = self.files / 'main.kdbx'
        current.save(changed)
        self.observations['changed_parent_sha256'] = hashlib.sha256(changed.read_bytes()).hexdigest()
        self.push(changed)
        self.parent_readback(label + '-immediately-after-cp')
        activities = self.shell('dumpsys', 'activity', 'activities')
        resumed_after = [line.strip() for line in activities.splitlines()
                         if 'topResumedActivity=' in line]
        assert resumed_after == resumed_before, 'Resumed activity changed across external mutation'
        self.observations[label + '_mutation_screen'] = {'before': resumed_before, 'after': resumed_after,
            'captured_parent_ioc': self.canonical_files + '/main.kdbx'}
        self.snap(label + '-changed-parent-still-in-search')
        self.record()

    def unchanged_original(self, label):
        actual = self.pull('main.kdbx', label + '-original.kdbx')
        assert actual.read_bytes() == self.original_bytes, 'Original clone was saved by an owner operation'
        assert_entry(actual, self.entry_uuid, self.original_title)
        self.observations[label + '_owner_a_sha256'] = hashlib.sha256(actual.read_bytes()).hexdigest()

    def await_clone(self, predicate, label):
        return self.eventually_file('clone.kdbx', lambda path: predicate(database(path)), label + '-clone.kdbx')

    def entry_ready(self, title):
        # A fresh Android 13+ install may cover the entry with this app-owned
        # onboarding dialog. Resolve only its exact visible controls; permission
        # state and database writability are never changed outside normal UI.
        nodes = self.wait_nodes(lambda nodes: any(
            node.get('resource-id') == self.package + ':id/entry_edit' or
            (node.get('resource-id') == self.package + ':id/alertTitle' and
             node.get('text') == 'Allow notifications') for node in nodes),
            'entry edit control or notification onboarding')
        if any(node.get('resource-id') == self.package + ':id/alertTitle' and
               node.get('text') == 'Allow notifications' for node in nodes):
            expected = {
                'android:id/message': 'Keepass2Android can show notifications with buttons to copy values like passwords and TOTPs to clipboard, or to bring up the built-in keyboard. This is useful to transfer values into other apps without switching to Keepass2Android repeatedly. Do you want to enable such notifications?',
                'android:id/button1': 'Allow notifications',
                'android:id/button2': 'Disable this feature',
                'android:id/button3': 'Not now',
            }
            for resource, text in expected.items():
                assert any(node.get('resource-id') == resource and node.get('text') == text
                           for node in nodes), 'Unexpected notification dialog: ' + resource
            self.snap('notification-onboarding')
            button = self.wait(lambda node: node.get('resource-id') == 'android:id/button2' and
                               node.get('text') == 'Disable this feature', 'Disable this feature')
            self.tap(button)
            self.observations['notification_onboarding'] = {
                'visible_action': 'Disable this feature', 'permission_bypass': False}
            self.record()
        self.wait_nodes(lambda nodes: any(node.get('text') == title for node in nodes) and
                        any(node.get('resource-id') == self.package + ':id/entry_edit' and
                            node.get('enabled') == 'true' for node in nodes),
                        'expected writable owner entry: ' + title)
        self.snap('entry-ready')

    def select_recycled_owner(self):
        # Completing deletion from combined results returns to the selector.
        # Re-enter B explicitly instead of backing past this terminal screen.
        self.text('Select database')
        nodes = self.nodes()
        for owner, filename in (('Owner A', 'main.kdbx'), ('Owner B', 'clone.kdbx')):
            expected = owner + '\n' + self.canonical_files + '/' + filename
            assert any(node.get('text') == expected for node in nodes), 'Missing exact owner selector: ' + owner
        self.snap('post-recycle-selector')
        self.tap(self.text('Owner B\n' + self.canonical_files + '/clone.kdbx'))
        self.wait_nodes(lambda nodes: all(any(node.get('text') == title and
                        node.get('resource-id') == self.package + ':id/group_text'
                        for node in nodes) for title in ('Personal', 'Recycle Bin')),
                        'owner B root with recycled entry')
        self.snap('owner-b-root-after-recycle')

    def delete_prompt(self):
        self.overflow('Delete')
        self.text('Delete permanently?')
        self.snap('delete-prompt')

    def run(self):
        with self.case('prepare'):
            self.entry_uuid = prepare(self.files)
            self.observations['duplicate_entry_uuid'] = self.entry_uuid
            self.canonical_files = '/data/data/' + self.package + '/files'
            self.shell('run-as', self.package, 'mkdir', '-p', 'files')
            for path in self.files.iterdir():
                self.push(path)
        with self.case('open-two-local-databases'):
            self.launch()
            self.by_id('start_open_file', 60)
            self.open_local('main.kdbx')
            self.open_local('clone.kdbx')
        with self.case('select-current-and-combined-search'):
            self.select_current('Owner A')
            self.search((TITLE_A, TITLE_B))
        with self.case('sync-baseline'):
            self.baseline_sync('initial')
        # Accept first establishes the priority automatic-Both oracle. Each
        # subsequent decision starts with unchanged files in a new process.
        for decision in ('accept', 'decline', 'dismiss'):
            if decision != 'accept':
                with self.case('reload-reset-' + decision):
                    self.reset_local_phase(decision)
                    self.baseline_sync(decision)
            name = 'sync-reload-' + decision + ('-automatic-export' if decision == 'accept' else '')
            with self.case(name):
                self.mutate_parent_in_search(decision)
                self.sync_started = time.monotonic()
                self.sync_menu(verify_parent=decision + '-before-dispatch')
                try:
                    self.text(PROMPT)
                except AssertionError:
                    self.snap('missing-reload-prompt-status')
                    self.pull('main.kdbx', decision + '-missing-prompt-parent.kdbx')
                    self.parent_readback(decision + '-missing-prompt', require_replacement=False)
                    raise
                self.observations[decision + '_prompt_detected_seconds'] = time.monotonic() - self.sync_started
                self.snap('reload-prompt')
                self.group_windows(decision + '-single-prompt', 2)
                activities = self.shell('dumpsys', 'activity', 'activities')
                (self.art / (self.current + '-live-prompt-activities.txt')).write_text(activities)
                resumed = [line.strip() for line in activities.splitlines()
                           if 'mResumedActivity:' in line or 'topResumedActivity=' in line]
                assert resumed and any('GroupActivity' in line for line in resumed), 'Prompt missing live returned group'
                assert not any('SearchResults' in line for line in resumed), 'Prompt on search UI'
                self.observations[decision + '_prompt_resumed'] = resumed
                assert self.pull('personal-export.kdbx.share', decision + '-at-prompt.kdbx.share').read_bytes() == self.baseline, 'Export ran while reload was pending'
                self.parent_readback(decision + '-at-prompt')
                self.observations[decision] = {'prompt_export_unchanged': True}
                self.observations[decision]['decision_seconds_since_sync'] = time.monotonic() - self.sync_started
                if decision == 'dismiss':
                    self.key(4)
                else:
                    self.tap(self.wait(lambda n: n.get('resource-id') ==
                        ('android:id/button1' if decision == 'accept' else 'android:id/button2'), decision))
                if decision != 'accept':
                    self.returned_group(decision)
                    self.wait_operations_idle(decision + '-complete', returned_group=True)
                    self.observe_no_reload(decision)
                    assert self.pull('personal-export.kdbx.share', decision + '-after.kdbx.share').read_bytes() == self.baseline, 'Export ran after ' + decision
                    self.parent_readback(decision + '-after-decision')
                    self.observations[decision]['after_export_unchanged'] = True
                else:
                    self.text('Personal', 60)
                    self.tap(self.text('Personal'))
                    self.text(RELOADED_A)
                    accepted = self.pull('main.kdbx', 'accepted-parent.kdbx')
                    assert_entry(accepted, self.entry_uuid, RELOADED_A)
                    self.eventually_file('personal-export.kdbx.share',
                        lambda path: export_has_title(path, RELOADED_A), 'automatic-export-after-reopen.kdbx.share')
                    self.wait_operations_idle('accepted-complete', (RELOADED_A,))
                    self.observations[decision]['update_idle_seconds_since_sync'] = time.monotonic() - self.sync_started
                    self.group_windows(decision + '-accepted-idle', 1)
                    self.observations[decision]['automatic_changed_parent_export'] = True
                    self.observations[decision]['explicit_share_sync_used'] = False

        with self.case('reload-phase-reset'):
            # Restore both original titles after reload before owner assertions.
            # Keep all priority Sync/reload evidence from this same session.
            self.adb_run('shell', 'am', 'force-stop', self.package)
            self.files = self.art / 'reload-fixtures'
            self.entry_uuid = prepare(self.files)
            self.observations['reload_duplicate_entry_uuid'] = self.entry_uuid
            for path in self.files.iterdir():
                self.push(path)
            self.launch()
            self.open_local('main.kdbx')
            self.open_local('clone.kdbx')
            self.select_current('Owner A')
            self.search((TITLE_A, TITLE_B))
        with self.case('owner-baseline'):
            self.wait_operations_idle('owner-before-mutations', (TITLE_A, TITLE_B))
            self.original_title = TITLE_A
            self.original_bytes = self.pull('main.kdbx', 'owner-original-baseline.kdbx').read_bytes()
            self.observations['owner_a_baseline_sha256'] = hashlib.sha256(self.original_bytes).hexdigest()
        with self.case('owner-open-edit'):
            self.select_current('Owner A')
            self.search((self.original_title, TITLE_B))
            self.tap(self.text(TITLE_B))
            self.entry_ready(TITLE_B)
            self.snap('later-opened-clone-entry')
            self.tap(self.by_id('entry_edit'))
            self.fill('entry_title', EDITED_B)
            self.overflow('Save')
            self.entry_ready(EDITED_B)
            self.await_clone(lambda db: (entry_by_uuid(db, self.entry_uuid).title == EDITED_B), 'edited')
            self.unchanged_original('edited')
        with self.case('owner-delete-cancel'):
            before = self.pull('clone.kdbx', 'before-delete-cancel.kdbx').read_bytes()
            self.delete_prompt()
            self.tap(self.text('Cancel'))
            self.entry_ready(EDITED_B)
            assert self.pull('clone.kdbx', 'after-delete-cancel.kdbx').read_bytes() == before, 'Cancel saved clone'
            self.unchanged_original('cancel')
        with self.case('owner-delete-recycle'):
            self.delete_prompt()
            self.tap(self.text('No'))
            path = self.await_clone(lambda db: entry_by_uuid(db, self.entry_uuid).parentgroup.name == 'Recycle Bin', 'recycled')
            assert_entry(path, self.entry_uuid, EDITED_B, 'Recycle Bin')
            assert not tombstoned(path, self.entry_uuid), 'Recycling added a permanent tombstone'
            self.unchanged_original('recycled')
        with self.case('owner-delete-permanent'):
            self.select_recycled_owner()
            self.tap(self.text('Recycle Bin'))
            self.tap(self.text(EDITED_B))
            self.entry_ready(EDITED_B)
            self.delete_prompt()
            self.tap(self.text('Yes'))
            path = self.await_clone(lambda db: entry_by_uuid(db, self.entry_uuid) is None, 'permanent')
            assert tombstoned(path, self.entry_uuid), 'Permanent deletion omitted tombstone'
            self.unchanged_original('permanent')



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--advanced-search', action='store_true', help='Use normal Advanced Search instead of SearchView')
    args = parser.parse_args()
    try:
        journey = TwoDatabases(advanced_search=args.advanced_search)
    except Exception as error:
        traceback.print_exc()
        # Provenance collection precedes the first case. Keep an honest startup
        # failure inventory even when no Journey instance can be returned.
        artifacts = os.environ.get('KP2A_E2E_ARTIFACTS')
        if artifacts:
            destination = Path(artifacts) / 'keeshare'
            destination.mkdir(parents=True, exist_ok=True)
            (destination / 'two-db-startup-failure.json').write_text(json.dumps({
                'status': 'failed', 'phase': 'startup-installed-apk-provenance',
                'error': str(error), 'type': type(error).__name__,
                'installed_apk_sha256': None,
                'cases': {name: {'status': 'not-run'} for name in CASES},
                'serial': os.environ.get('ANDROID_SERIAL'),
                'private_adb': os.environ.get('ADB_SERVER_SOCKET'),
            }, indent=2) + '\n')
        return 1
    try:
        journey.run()
    except Exception:
        traceback.print_exc()
        print('FAIL:', journey.current, 'Evidence:', journey.art, flush=True)
        return 1
    finally:
        try:
            if not journey.transport_failed:
                logs = journey.adb_run('logcat', '-d').stdout
                (journey.art / 'two-db-logcat.txt').write_bytes(journey.redact(logs))
        finally:
            journey.record()
    print('PASS: two-local-DB SyncUtil reload and duplicate UUID owner edit/delete', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
