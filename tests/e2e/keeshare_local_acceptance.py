#!/usr/bin/env python3
"""Bounded independent original AC5/6/7/9 local checks on the approved APK.

Run once in a fresh kp2a e2e session. Only exported file opening uses an intent;
all configuration and mutations use visible UI. Companion code prepares synthetic
metadata and inspects persisted KDBX output; the installed app executes KeeShare.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

sys.dont_write_bytecode = True
from adb_transfer import pull_verified, TransferError
from keeshare_two_databases import TwoDatabases
from keeshare_journey import Journey
from local_acceptance_data import prepare, database, group, state, custom, PREFIX, FOREIGN_KEY

APPROVED_APK = 'b50e06bf1e48eb7dd8657610d84f1ceaa89fd31058e3c6fa1680d743b730b8f2'
EXPECTED_APK_BYTES = 278924175

CASES = ('prepare', 'AC5-foreign-device-relative-fallback',
         'AC5-missing-unresolvable-location', 'AC6-import-nested-readonly',
         'AC6-regular-editable', 'AC6-sync-editable',
         'AC7-failure-continues-later-share', 'AC9-remove-sharing-device-keys',
         'AC5-empty-path-device-ioc')


class LocalAcceptance(TwoDatabases):
    def __init__(self):
        # Reuse UI/command methods without TwoDatabases' historical APK pin.
        self.commands = []
        self.transport_failed = False
        self.advanced_search = False
        self.provenance = {'status': 'collecting', 'commands': [],
                           'recovery': {'status': 'not-needed'}, 'transport_root_cause': 'unknown'}
        Journey.__init__(self)
        assert self.apk['sha256'] == APPROVED_APK, 'Installed APK differs from dedicated approved build'
        self.observations = {}
        self.results = {name: {'status': 'not-run'} for name in CASES}
        self.deadline = time.monotonic() + 18 * 60
        self.canonical_files = '/data/data/' + self.package + '/files'
        self.filename = 'main.kdbx'
        self.feature_failure = False

    def installed_apk(self):
        """Require shared verified transfer plus the approved size/hash and pm paths."""
        evidence = self.art / 'local-acceptance-installed-provenance.json'
        transfer_evidence = self.art / 'local-acceptance-verified-pull.json'
        artifact = self.art / 'installed-base.apk'
        identity = (os.environ['ANDROID_SERIAL'], os.environ['ADB_SERVER_SOCKET'])
        self.provenance.update(transport='adb-pull-verified',
            expected_bytes=EXPECTED_APK_BYTES, expected_sha256=APPROVED_APK,
            transfer_evidence=str(transfer_evidence.resolve()))

        def package_paths():
            if identity != (os.environ['ANDROID_SERIAL'], os.environ['ADB_SERVER_SOCKET']):
                raise RuntimeError('Private ADB session identity changed during provenance')
            result = self.adb_run('shell', 'pm', 'path', self.package)
            lines = result.stdout.decode().strip().splitlines()
            if not lines or any(not re.fullmatch(r'package:/[^\r\n]+\.apk', line) for line in lines):
                raise RuntimeError('Cannot identify installed APK paths')
            paths = [line.removeprefix('package:') for line in lines]
            if len(paths) != len(set(paths)):
                raise RuntimeError('Ambiguous installed APK paths')
            return paths

        try:
            paths = package_paths()
            self.provenance['package_paths_before'] = paths
            bases = [path for path in paths if Path(path).name == 'base.apk']
            if len(bases) != 1:
                raise RuntimeError('Expected exactly one installed base APK')

            def stable_paths():
                current = package_paths()
                if current != paths:
                    raise RuntimeError('Installed APK paths changed during provenance')
                return current

            transfer = pull_verified(bases[0], artifact, expected_sha256=APPROVED_APK,
                check=stable_paths, attempts=3, reconnect_limit=20, idle_limit=90,
                timeout=90, record_path=transfer_evidence)
            self.provenance['transfer'] = transfer
            if transfer['guest_size'] != EXPECTED_APK_BYTES or transfer['received_bytes'] != EXPECTED_APK_BYTES:
                raise RuntimeError('Verified installed APK byte count differs from approved size')
            if transfer['received_sha256'] != APPROVED_APK or transfer['guest_sha256'] != APPROVED_APK:
                raise RuntimeError('Verified installed APK differs from approved hash')
            self.provenance.update(status='verified', package_paths_after=transfer['check_after'])
            return {'path': bases[0], 'artifact': str(artifact.resolve()),
                    'source': 'installed-package-base-verified-pull', 'package_paths': paths,
                    'sha256': transfer['received_sha256'], 'guest_sha256': transfer['guest_sha256'],
                    'bytes': transfer['received_bytes'], 'provenance_evidence': str(evidence.resolve())}
        except Exception as error:
            self.transport_failed = True
            if isinstance(error, TransferError):
                self.provenance['transfer'] = error.record
            self.provenance.update(status='failed', error=str(error), error_type=type(error).__name__)
            raise
        finally:
            evidence.write_text(json.dumps(self.provenance, indent=2) + '\n')

    def record(self):
        (self.art / 'local-acceptance-results.json').write_text(json.dumps({
            'apk': self.apk, 'package': self.package, 'started': self.started,
            'serial': os.environ['ANDROID_SERIAL'], 'private_adb': os.environ['ADB_SERVER_SOCKET'],
            'cases': self.results, 'observations': self.observations,
            'installed_provenance': self.provenance,
            'scope': 'Original AC5/6/7/9 bounded local gaps; no provider or lifecycle acceptance',
        }, indent=2) + '\n')

    def open_fixture(self, filename):
        self.filename = filename
        self.shell('am', 'force-stop', self.package)
        self.shell('am', 'start', '-a', 'kp2a.action.SelectCurrentDbActivity',
                   '-p', self.package, '--es', 'fileName', self.canonical_files + '/' + filename)
        self.unlock()
        self.wait_operations_idle('open-' + filename, titles=('Personal',))

    def output_db(self, label):
        return database(self.pull(self.filename, label + '.kdbx'))

    def assert_feature(self, condition, message):
        if not condition:
            self.feature_failure = True
            raise AssertionError(message)

    def inspect_selection(self, title, readonly):
        self.tap(self.text(title), long=True)
        self.by_id('action_mode_close_button')
        self.by_id('check_mark')
        self.snap('selection-' + title.replace(' ', '-'))
        nodes = self.nodes({'resource-id': self.package + ':id/action_mode_close_button'})
        ids = {n.get('resource-id', '').rsplit('/', 1)[-1] for n in nodes}
        expected = {'menu_edit', 'menu_delete', 'menu_move', 'menu_copy'}
        if readonly:
            self.assert_feature(not (ids & expected), 'Readonly selection exposes ' + str(ids & expected))
            more = next((n for n in nodes if n.get('content-desc') == 'More options'), None)
            if more is not None:
                self.tap(more)
                self.snap('selection-overflow')
                nodes = self.nodes()
                self.assert_feature(not any(n.get('text') in ('Edit', 'Delete', 'Move', 'Copy')
                                            for n in nodes), 'Readonly overflow offers mutation')
                self.key(4)
        else:
            entry_controls = expected - {'menu_edit'}
            self.assert_feature(entry_controls <= ids,
                                'Editable selection missing controls: ' + str(entry_controls - ids))
        self.key(4)

    def local_entry_ready(self, title, readonly=False):
        # Entry screens can be covered by this exact app-owned first-use offer.
        nodes = self.wait_nodes(lambda nodes: any(
            node.get('text') == title or
            (node.get('resource-id') == self.package + ':id/alertTitle' and
             node.get('text') == 'Allow notifications') for node in nodes),
            'expected entry or notification onboarding: ' + title)
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
                           and node.get('package') == self.package for node in nodes), \
                    'Unexpected notification dialog: ' + resource
            self.snap('notification-onboarding')
            self.tap(next(node for node in nodes if node.get('resource-id') == 'android:id/button2'))
            self.observations['notification_onboarding'] = {
                'visible_action': 'Disable this feature', 'permission_bypass': False}
        nodes = self.wait_nodes(lambda nodes: any(node.get('text') == title for node in nodes) and
            all(any(node.get('resource-id') == self.package + ':id/' + resource for node in nodes)
                for resource in ('entry_scroll', 'entry_table')),
            'expected entry screen: ' + title)
        edit = [node for node in nodes if node.get('resource-id') == self.package + ':id/entry_edit']
        self.assert_feature(not edit if readonly else any(node.get('enabled') == 'true' for node in edit),
                            'Unexpected entry edit availability: ' + title)
        self.snap('entry-ready')
        return nodes

    def foreign(self):
        self.open_fixture('main.kdbx')
        self.tap(self.text('Team Import'))
        self.text('Imported Entry')
        self.text('Imported Nested')
        db = self.output_db('foreign-imported-main')
        self.assert_feature(db.find_entries(title='Imported Entry', first=True) is not None,
                            'Foreign IOC prevented relative import')
        self.assert_feature(custom(group(db, 'Team Import')).get(FOREIGN_KEY) ==
                            custom(group(database(self.files / 'main.kdbx'), 'Team Import'))[FOREIGN_KEY],
                            'Foreign device IOC was mutated')
        self.back_to_root()
        self.config()
        row = self.config_row('Team Import')
        self.snap('relative-row')
        self.assert_feature(any('next to database' in n.get('text', '').lower() for n in row.iter('node')),
                            'Foreign device IOC selected instead of relative fallback')
        self.observations['foreign_device'] = {'key': FOREIGN_KEY,
            'bad_file': str(self.files / 'bad.kdbx'), 'fallback_marker': 'Imported Entry',
            'actual_device_confirmed_by': 'AC9 UI picker persisted key, if passed'}

    def missing(self):
        before = (self.files / 'missing.kdbx').read_bytes()
        seed = database(self.files / 'missing.kdbx')
        self.open_fixture('missing.kdbx')
        self.config()
        for name in ('Team Import', 'Unresolved Location'):
            row = self.config_row(name)
            self.wait_status(name, lambda text: text == 'Location not set on this device', name + ' notset')
            self.assert_feature(any(n.get('resource-id', '').endswith('/keeshare_row_location') and
                                n.get('text') == 'Location not set on this device' for n in row.iter('node')),
                                'Missing location label is not visible')
            self.snap(name.replace(' ', '-') + '-notset')
        self.assert_feature(self.status('Inactive Control') == '', 'Inactive share acquired an operation result')
        self.snap('inactive-no-result')
        self.row_button('Team Import', 'keeshare_row_sync')
        for name in ('Team Import', 'Unresolved Location'):
            self.wait_status(name, lambda text: text == 'Location not set on this device', name + ' explicit notset')
        self.assert_feature(self.status('Inactive Control') == '', 'Explicit Sync activated inactive share')
        self.snap('explicit-sync-notset-and-inactive')
        time.sleep(2)
        self.back_to_root()
        self.wait_operations_idle('missing-explicit-sync', titles=('Personal',))
        after = self.pull('missing.kdbx', 'missing-after-sync.kdbx').read_bytes()
        self.assert_feature(after == before, 'Skipped locations mutated parent bytes')
        persisted = database(self.art / 'missing-after-sync.kdbx')
        for name in ('Team Import', 'Unresolved Location', 'Inactive Control'):
            self.assert_feature(state(persisted, name) == state(seed, name), 'Skipped/inactive subtree changed: ' + name)
        self.observations['missing'] = {'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'visible_result': 'Location not set on this device',
            'inactive_unchanged': True,
            'outcome_limit': 'UI maps Skipped/notset to this message; internal enum not instrumented'}

    def empty_device_ioc(self):
        # First the no-location case proves no writes; then configure via real UI.
        self.open_fixture('missing.kdbx')
        filename = 'empty-path-valid-share.kdbx'
        self.adb_run('push', str(self.files / 'team-import.kdbx'), '/sdcard/Download/' + filename)
        self.config()
        self.row_button('Team Import', 'keeshare_row_edit')
        self.assert_feature(self.by_id('keeshare_path').get('text', '') == '', 'Fixture reference path is not empty')
        self.tap(self.scroll_to_id('keeshare_pick_device_file'))
        self.choose_document(filename)
        self.tap(self.scroll_to_id('keeshare_save'))
        self.by_id('keeshare_list')
        def selected(path):
            values = custom(group(database(path), 'Team Import'))
            return any(key.startswith(PREFIX) and filename in value for key, value in values.items())
        self.eventually_file('missing.kdbx', selected, 'empty-device-before-sync.kdbx')
        self.row_button('Team Import', 'keeshare_row_sync')
        self.wait_status('Team Import', lambda text: text == 'Imported changes from KeeShare', 'empty path device import')
        self.snap('empty-path-device-imported')
        path = self.eventually_file('missing.kdbx', lambda path:
            database(path).find_entries(title='Imported Entry', first=True) is not None,
            'empty-device-after-sync.kdbx')
        db = database(path)
        values = custom(group(db, 'Team Import'))
        import base64
        import xml.etree.ElementTree as ET
        reference = ET.fromstring(base64.b64decode(values['KeeShare/Reference']))
        self.assert_feature((reference.findtext('Path') or '') == '', 'UI unexpectedly supplied reference path')
        keys = [key for key, value in values.items() if key.startswith(PREFIX) and filename in value]
        self.assert_feature(len(keys) == 1 and keys[0] == self.observations['actual_device_key'],
                            'Empty-path IOC did not use confirmed current device')
        self.assert_feature(state(db, 'Inactive Control') == state(database(self.files / 'missing.kdbx'), 'Inactive Control'),
                            'Valid device IOC operation mutated inactive control')
        self.observations['empty_device_ioc'] = {'key': keys[0], 'reference_path': '',
            'imported_marker': 'Imported Entry', 'visible_result': 'Imported changes from KeeShare'}

    def readonly(self):
        self.open_fixture('main.kdbx')
        self.tap(self.text('Team Import'))
        self.inspect_selection('Imported Nested', True)
        self.tap(self.text('Imported Nested'))
        self.text('Nested Readonly Entry')
        nodes = self.nodes({'resource-id': self.package + ':id/keeshare_readonly_info'})
        self.assert_feature(not any(n.get('resource-id', '').rsplit('/', 1)[-1] in
                            ('fabAddNew', 'fabAddNewEntry', 'fabAddNewGroup') for n in nodes),
                            'Imported descendant offers Add')
        self.snap('descendant-no-add')
        self.inspect_selection('Nested Readonly Entry', True)
        self.tap(self.text('Nested Readonly Entry'))
        nodes = self.local_entry_ready('Nested Readonly Entry', readonly=True)
        self.assert_feature(not any(n.get('resource-id', '').endswith('/entry_edit') for n in nodes),
                            'Imported descendant entry offers edit')
        self.snap('entry-no-edit')

    def editable(self, name, title):
        self.open_fixture('main.kdbx')
        self.tap(self.text(name))
        self.by_id('fabAddNew')
        self.inspect_selection(title, False)
        self.tap(self.text(title))
        self.local_entry_ready(title)
        self.tap(self.by_id('entry_edit'))
        self.by_id('entry_title')
        changed = title + ' Local Acceptance'
        self.fill('entry_title', changed)
        self.overflow('Save')
        self.local_entry_ready(changed)
        self.snap('actual-edit-saved')
        def saved(path):
            return database(path).find_entries(title=changed, first=True) is not None
        self.eventually_file('main.kdbx', saved, name.replace(' ', '-') + '-edited.kdbx')
        self.observations[name + '_editable'] = {'saved_title': changed,
            'observed_controls': ['Add', 'Edit', 'Delete', 'Move', 'Copy'],
            'actual_mutation': 'entry title edit and Save through visible UI'}

    def continuation(self):
        seed = database(self.files / 'continuation.kdbx')
        before = state(seed, 'Team Import')
        self.open_fixture('continuation.kdbx')
        self.config()
        self.wait_status('Team Import', lambda value: any(word in value.lower() for word in
                         ('fail', 'signature', 'corrupt')), 'first share failure')
        self.snap('first-share-failed')
        self.wait_status('Team Sync', lambda value: bool(value) and not any(word in value.lower()
                         for word in ('fail', 'signature', 'corrupt')), 'later share success')
        self.snap('later-share-result')
        after = self.output_db('continuation-after-main')
        self.assert_feature(state(after, 'Team Import') == before, 'Failed share subtree mutated')
        marker = after.find_entries(title='Later Share Success Marker', first=True)
        self.assert_feature(marker is not None and marker.parentgroup.name == 'Team Sync',
                            'Later share marker was not imported into successful group')
        self.observations['continuation'] = {'failed_subtree_before': before,
            'failed_subtree_after': state(after, 'Team Import'),
            'successful_marker': 'Later Share Success Marker',
            'fixture_order': ['Team Import (corrupt)', 'Team Sync (valid)']}

    def remove(self):
        self.open_fixture('main.kdbx')
        self.adb_run('push', str(self.files / 'bad.kdbx'), '/sdcard/Download/local-acceptance-bad.kdbx')
        self.config()
        self.row_button('Team Import', 'keeshare_row_edit')
        self.tap(self.scroll_to_id('keeshare_pick_device_file'))
        self.choose_document('local-acceptance-bad.kdbx')
        self.tap(self.scroll_to_id('keeshare_save'))
        self.by_id('keeshare_list')
        def picked(path):
            values = custom(group(database(path), 'Team Import'))
            return any(key.startswith(PREFIX) and key != FOREIGN_KEY and
                       'local-acceptance-bad.kdbx' in value for key, value in values.items())
        path = self.eventually_file('main.kdbx', picked, 'remove-before-device-picked.kdbx')
        before = database(path)
        values = custom(group(before, 'Team Import'))
        keys = [key for key, value in values.items() if key.startswith(PREFIX) and
                key != FOREIGN_KEY and 'local-acceptance-bad.kdbx' in value]
        self.assert_feature(len(keys) == 1, 'UI choice did not establish exactly one current device key')
        self.observations['actual_device_key'] = keys[0]
        self.assert_feature(keys[0] != FOREIGN_KEY, 'Foreign fixture device matches actual device')
        self.snap('device-choice-saved')
        self.row_button('Team Import', 'keeshare_row_edit')
        self.tap(self.scroll_to_id('keeshare_remove'))
        self.by_id('keeshare_list')
        def removed(path):
            data = custom(group(database(path), 'Team Import'))
            return 'KeeShare/Reference' not in data and not any(key.startswith(PREFIX) for key in data)
        path = self.eventually_file('main.kdbx', removed, 'remove-after-main.kdbx')
        after = database(path)
        self.assert_feature(after.find_entries(title='Imported Entry', first=True) is not None,
                            'Removing sharing removed imported content')
        self.assert_feature(state(before, 'Team Sync') == state(after, 'Team Sync'),
                            'Removing sharing changed unrelated sync group')
        self.snap('reference-and-all-device-keys-removed')
        self.observations['remove'] = {'before_custom': values,
            'after_custom': custom(group(after, 'Team Import')),
            'content_preserved': True, 'unrelated_sync_group_unchanged': True}

    def run(self):
        with self.case('prepare'):
            self.observations['fixtures'] = prepare(self.files, self.canonical_files)
            self.shell('run-as', self.package, 'mkdir', '-p', 'files')
            for path in self.files.iterdir():
                self.push(path)
            self.launch()
            self.by_id('start_open_file', 60)
        cases = [('AC5-foreign-device-relative-fallback', self.foreign),
                 ('AC6-import-nested-readonly', self.readonly),
                 ('AC6-regular-editable', lambda: self.editable('Personal', 'Personal Entry')),
                 ('AC6-sync-editable', lambda: self.editable('Team Sync', 'Remote Sync Entry')),
                 ('AC7-failure-continues-later-share', self.continuation),
                 ('AC9-remove-sharing-device-keys', self.remove),
                 ('AC5-missing-unresolvable-location', self.missing),
                 ('AC5-empty-path-device-ioc', self.empty_device_ioc)]
        for name, action in cases:
            if self.transport_failed or self.feature_failure or time.monotonic() >= self.deadline:
                break
            try:
                with self.case(name):
                    action()
            except Exception:
                # A bounded unavailable UI branch must not conceal independent cases.
                # Confirmed feature assertions stop the run; product fixes require the owner.
                if self.transport_failed or self.feature_failure:
                    break
        self.record()


def main():
    journey = None
    try:
        journey = LocalAcceptance()
        journey.run()
        return 0 if all(result['status'] == 'passed' for result in journey.results.values()) else 1
    except Exception as error:
        traceback.print_exc()
        if journey is None and os.environ.get('KP2A_E2E_ARTIFACTS'):
            # Constructor provenance failures must still leave a durable ledger.
            # A failed startup gate never turns unexecuted behavioral cases into failures.
            art = Path(os.environ['KP2A_E2E_ARTIFACTS']) / 'keeshare'
            art.mkdir(exist_ok=True)
            (art / 'local-acceptance-results.json').write_text(json.dumps({
                'target_apk_sha256': APPROVED_APK,
                'installed_identity': 'unverified',
                'serial': os.environ.get('ANDROID_SERIAL'),
                'private_adb': os.environ.get('ADB_SERVER_SOCKET'),
                'startup': {'status': 'failed', 'error': str(error),
                            'type': type(error).__name__},
                'cases': {name: {'status': 'not-run', 'reason': 'Startup provenance gate failed'}
                          for name in CASES},
                'observations': {},
            }, indent=2) + '\n')
        return 1
    finally:
        if journey is not None:
            journey.record()
            if not journey.transport_failed:
                (journey.art / 'local-acceptance-logcat.txt').write_bytes(journey.adb_run('logcat', '-d').stdout)


if __name__ == '__main__':
    raise SystemExit(main())
