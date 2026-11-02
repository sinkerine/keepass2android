#!/usr/bin/env python3
"""One bounded fresh-emulator session for remaining original AC4/5/6 checks.

Use kp2a e2e --apk <approved repair5> -- timeout --signal=TERM --kill-after=10s
900s python3 -B tests/e2e/keeshare_final_acceptance.py. The outer runner is
bounded to 1050s. Only the approved exported local-file opening intent is used.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

sys.dont_write_bytecode = True
from keeshare_offline_mount import OfflineMount
from keeshare_local_acceptance import APPROVED_APK, EXPECTED_APK_BYTES
from adb_transfer import pull_verified
from final_acceptance_data import (prepare, database, group, reference, tree,
                                   assert_no_sharing, assert_source_edit_unchanged,
                                   IOC_PREFIX, MARKER, custom)
from offline_mount_data import LoopbackDav
from pykeepass import PyKeePass

CASES = ('prepare', 'AC6-move-into-import-root-and-subgroup',
         'AC6-export-only-normal-edit', 'AC4-keepgroups-false-populated-export',
         'AC5-empty-path-picked-current-device-ioc')


class FinalAcceptance(OfflineMount):
    def __init__(self):
        self.readbacks = []
        super().__init__()
        self.results = {name: {'status': 'not-run'} for name in CASES}
        self.deadline = time.monotonic() + 850
        self.empty_path_only = '--empty-path-only' in sys.argv[1:]
        self.remaining_only = '--remaining-only' in sys.argv[1:]
        if self.empty_path_only:
            for name in CASES[1:4]:
                self.results[name] = {'status': 'not-run',
                    'reason': 'Completed in prior sessions; targeted empty-path IOC session only'}
        elif self.remaining_only:
            self.results[CASES[1]] = {'status': 'not-run',
                'reason': 'Already passed in run-tjc6g7gx; retry covers remaining three cases'}

    def record(self):
        if not hasattr(self, 'observations'):
            return
        body = {'apk': self.apk, 'package': self.package, 'started': self.started,
                'serial': os.environ['ANDROID_SERIAL'], 'private_adb': os.environ['ADB_SERVER_SOCKET'],
                'cases': self.results, 'observations': self.observations,
                'installed_provenance': self.provenance, 'readbacks': self.readbacks,
                'scope': 'Extra empty-desktop-path/current-device IOC only' if self.empty_path_only else
                         'Remaining three original AC4/5/6 checks' if self.remaining_only else
                         'Four final narrow original AC4/5/6 checks only'}
        path = self.art / 'final-acceptance-results.json'
        with path.open('wb') as output:
            output.write(self.redact(json.dumps(body, indent=2).encode()) + b'\n')
            output.flush()
            os.fsync(output.fileno())

    def pull(self, name, label=None, required=True):
        # Expose a private immutable copy only for transfer; never mutate the input.
        label = label or name
        remote = '/sdcard/Download/final-verified-readback.kdbx'
        identity = self.shell('run-as', self.package, 'sha256sum', 'files/' + name).split()[0]
        self.shell('touch', '/data/local/tmp/final-readback.kdbx')
        self.shell('chmod', '666', '/data/local/tmp/final-readback.kdbx')
        self.shell('run-as', self.package, 'cp', 'files/' + name, '/data/local/tmp/final-readback.kdbx')
        self.shell('cp', '/data/local/tmp/final-readback.kdbx', remote)
        after_copy = self.shell('run-as', self.package, 'sha256sum', 'files/' + name).split()[0]
        assert identity == after_copy, 'Database changed during readback snapshot'
        path = self.art / label
        evidence = path.with_suffix(path.suffix + '.transfer.json')
        result = pull_verified(remote, path, expected_sha256=identity, attempts=2,
                               reconnect_limit=10, idle_limit=30, timeout=20, record_path=evidence)
        self.readbacks.append({'source': name, 'artifact': str(path),
                              'guest_source_sha256': identity, 'transfer': result})
        self.record()
        return path

    def fresh_open(self, filename):
        with self.navigation('open independent fixture: ' + filename, 80):
            self.open_fixture(filename)

    def move_into(self):
        self.fresh_open('move-parent.kdbx')
        before_path = self.pull(self.filename, 'move-before.kdbx')
        before = database(before_path)
        self.tap(self.text('Personal'))
        self.tap(self.text('Ordinary Move Candidate'), long=True)
        self.by_id('action_mode_close_button')
        self.snap('ordinary-selected-move-available')
        self.tap(self.by_id('menu_move'))
        self.by_id('cancel_insert_element')
        self.by_id('insert_element')
        self.snap('move-active-editable-source-insert-visible')
        self.back_to_root()
        self.tap(self.text('Team Import'))
        self.assert_move_forbidden('Import Root Anchor', 'root')
        self.tap(self.text('Import Subgroup'))
        self.assert_move_forbidden('Import Child Anchor', 'subgroup')
        self.tap(self.by_id('cancel_insert_element'))
        self.back_to_root()
        self.wait_operations_idle('move-refused', titles=('Personal',))
        after_path = self.pull(self.filename, 'move-after.kdbx')
        after = database(after_path)
        self.assert_feature(tree(before) == tree(after), 'Move refusal changed persisted parent tree')
        self.assert_feature(before_path.read_bytes() == after_path.read_bytes(), 'Refused move wrote parent bytes')
        self.observations['move'] = {'attempt': 'normal selection > Move > root/subgroup navigation',
            'source_insert_visible': True, 'target_insert_absent': ['root', 'subgroup'],
            'whole_parent_tree_unchanged': True, 'whole_parent_bytes_unchanged': True,
            'candidate_parent': after.find_entries(title='Ordinary Move Candidate', first=True).parentgroup.name}

    def assert_move_forbidden(self, anchor, label):
        nodes = self.nodes({'text': anchor},
            {'resource-id': self.package + ':id/cancel_insert_element'},
            {'resource-id': self.package + ':id/keeshare_readonly_info'})
        self.snap('move-target-' + label + '-fresh-anchors')
        self.assert_feature(not any(n.get('resource-id') == self.package + ':id/insert_element'
                                    for n in nodes), 'Import target exposes Insert: ' + label)
        self.observations['move-' + label] = {'anchor': anchor, 'cancel_move_visible': True,
            'readonly_banner_visible': True, 'insert_visible': False}
        self.record()

    def export_edit(self, stem, keep):
        filename = stem + '-parent.kdbx'
        self.fresh_open(filename)
        before_path = self.pull(filename, stem + '-before.kdbx')
        before = database(before_path)
        source = group(before, 'Team Sync')
        xml = reference(source)
        self.assert_feature(xml.find('Type/Import') is None and xml.find('Type/Export') is not None,
                            'Fixture is not Export-only')
        self.assert_feature(xml.findtext('KeepGroups') == ('True' if keep else 'False'), 'Wrong KeepGroups')
        title = stem + ' Root Entry'
        changed = title + ' Edited'
        entry = before.find_entries(title=title, first=True)
        self.tap(self.text('Team Sync'))
        self.tap(self.text(title))
        self.local_entry_ready(title)
        self.snap('normal-entry-pencil')
        self.tap(self.by_id('entry_edit'))
        self.fill('entry_title', changed)
        self.overflow('Save')
        self.local_entry_ready(changed)
        self.snap('normal-pencil-save-persisted-title')
        self.back_to_root()
        self.wait_operations_idle(stem + '-save-export', titles=('Personal',))
        after_path = self.pull(filename, stem + '-after.kdbx')
        exported_path = self.pull(stem + '-output.kdbx', stem + '-actual-export.kdbx')
        exported = PyKeePass(exported_path, password='share-pass')
        after = database(after_path)
        edited = after.find_entries(uuid=entry.uuid, first=True)
        self.assert_feature(edited is not None and edited.title == changed and
                            edited.parentgroup.uuid == source.uuid, 'Normal Export edit did not persist')
        self.observations[stem + '-navigation-access-differences'] = assert_source_edit_unchanged(
            before, after, entry.uuid)
        self.assert_feature(len(edited.history) == len(entry.history) + 1 and
                            edited.history[-1].title == title, 'Normal Save history is not preserved')
        self.assert_feature(edited.username == entry.username and edited.password == entry.password,
                            'Normal title edit changed credentials')
        self.assert_feature(tree(before, group(before, stem + ' Populated Subgroup')) ==
                            tree(after, group(after, stem + ' Populated Subgroup')),
                            'Export mutated populated source subgroup')
        self.assert_feature(exported.find_entries(uuid=entry.uuid, first=True).title == changed,
                            'Actual app export lacks saved root entry')
        expected_entries = {str(edited.uuid)}
        if keep:
            expected_entries.add(str(before.find_entries(title=stem + ' Child Entry', first=True).uuid))
        self.assert_feature({str(e.uuid) for e in exported.entries} == expected_entries,
                            'Export entry membership differs from KeepGroups setting')
        self.assert_feature(len(exported.root_group.subgroups) == (1 if keep else 0),
                            'Export subgroup membership differs from KeepGroups setting')
        assert_no_sharing(exported)
        self.observations[stem] = {'normal_pencil_save': True, 'persisted_title': changed,
            'export_only': True, 'keep_groups': keep, 'source_subgroup_populated': True,
            'source_unchanged_except_entry_edit_history_and_exact_navigation_access': True,
            'export_opened_independently': str(exported_path), 'export_entries': [e.title for e in exported.entries],
            'export_groups': [g.name for g in exported.groups], 'sharing_metadata_absent': True}

    def presave(self, label, initial, share_bytes):
        parent = self.pull(self.filename, label + '-parent.kdbx')
        self.assert_feature(parent.read_bytes() == initial, 'Picker wrote parent before Save: ' + label)
        self.assert_feature(self.service.read('/shares/final-picked.kdbx') == share_bytes,
                            'Picker mutated picked share before Save')
        ledger = self.service.snapshot()
        self.assert_feature(not any(r['method'] in ('PUT', 'MOVE', 'DELETE', 'COPY', 'POST', 'MKCOL')
                                    for r in ledger), 'Picker attempted a write before Save')
        self.observations.setdefault('presave', []).append({'label': label,
            'parent_sha256': hashlib.sha256(initial).hexdigest(), 'parent_unchanged': True,
            'share_unchanged': True, 'requests': ledger})
        self.record()

    def picked_empty(self):
        self.fresh_open('empty-parent.kdbx')
        # This loopback-only fixture uses HTTP; enable the provider's required
        # preference through its normal UI before collecting the parent baseline.
        self.set_app_checkbox('File handling', 'Allow clear-text network traffic in WebDav', True)
        self.observations['http_preference_setup'] = {
            'route': 'Settings > App settings > File handling',
            'title': 'Allow clear-text network traffic in WebDav',
            'checked_state_asserted_by_existing_helper': True}
        self.record()
        self.back_to_root()
        before_path = self.pull(self.filename, 'empty-before.kdbx')
        initial = before_path.read_bytes()
        seed = database(before_path)
        self.config()
        self.wait_status('Team Import', lambda value: value == 'Location not set on this device', 'empty path unset')
        self.assert_feature(self.status('Inactive Control') == '', 'Inactive control ran before picker')
        self.row_button('Team Import', 'keeshare_row_edit')
        self.assert_feature(self.by_id('keeshare_path').get('text', '') == '', 'Desktop path not empty')
        self.snap('empty-reference-before-pick')
        self.tap(self.scroll_to_id('keeshare_pick_device_file'))
        self.snap('normal-storage-selection')
        share_bytes = (self.files / 'picked-share.kdbx').read_bytes()
        self.presave('storage-picker-before-choice', initial, share_bytes)
        self.choose_http('/shares/final-picked.kdbx')
        self.scroll_to_id('keeshare_save')
        self.snap('picked-http-before-save')
        self.presave('picked-http-before-save', initial, share_bytes)
        self.tap(self.scroll_to_id('keeshare_save'))
        self.by_id('keeshare_list')
        saved_path = self.pull(self.filename, 'empty-picked-saved-before-sync.kdbx')
        saved = database(saved_path)
        saved_group = group(saved, 'Team Import')
        saved_iocs = {key: value for key, value in custom(saved_group).items() if key.startswith(IOC_PREFIX)}
        self.assert_feature(len(saved_iocs) == 1 and
                            '/shares/final-picked.kdbx' in next(iter(saved_iocs.values())),
                            'Save did not persist the actual UI-picked device IOC')
        self.assert_feature((reference(saved_group).findtext('Path') or '') == '',
                            'Save changed empty desktop path')
        self.assert_feature(tree(seed, group(seed, 'Inactive Control')) ==
                            tree(saved, group(saved, 'Inactive Control')), 'Save changed inactive control')
        self.observations['picked_saved_ioc'] = {'key': next(iter(saved_iocs)),
            'reference_path': '', 'inactive_tree_unchanged': True, 'artifact': str(saved_path)}
        self.record()
        self.row_button('Team Import', 'keeshare_row_sync')
        self.wait_status('Team Import', lambda value: value == 'Imported changes from KeeShare', 'picked empty-path import')
        self.assert_feature(self.status('Inactive Control') == '', 'Inactive control became active')
        self.snap('empty-path-picked-import-result')
        self.back_to_root()
        self.wait_operations_idle('picked-empty-import', titles=('Personal',))
        path = self.pull(self.filename, 'empty-after.kdbx')
        db = database(path)
        imported = db.find_entries(title=MARKER, first=True)
        self.assert_feature(imported is not None and imported.parentgroup.name == 'Team Import',
                            'Picked share marker did not import')
        target = group(db, 'Team Import')
        self.assert_feature((reference(target).findtext('Path') or '') == '', 'Picker supplied a desktop path')
        iocs = {k: v for k, v in custom(target).items() if k.startswith(IOC_PREFIX)}
        self.assert_feature(len(iocs) == 1 and '/shares/final-picked.kdbx' in next(iter(iocs.values())),
                            'Actual UI did not persist one current-device picked IOC')
        self.assert_feature(tree(seed, group(seed, 'Inactive Control')) == tree(db, group(db, 'Inactive Control')),
                            'Inactive control changed')
        self.assert_feature(any(r['method'] == 'GET' and r['path'] == '/shares/final-picked.kdbx'
                                for r in self.service.snapshot()), 'No actual picked share GET')
        self.observations['empty_path_ioc'] = {'reference_path': '', 'actual_ui_persisted_key': next(iter(iocs)),
            'marker': MARKER, 'inactive_tree_unchanged': True, 'preseeded_ioc': False,
            'route': 'KeeShare edit > Pick device file > HTTP (WebDav) > OK > Save > Sync'}

    def run(self):
        with self.case('prepare'):
            with self.navigation('prepare independent fixtures', 60):
                self.observations['fixtures'] = prepare(self.files)
                self.shell('run-as', self.package, 'mkdir', '-p', 'files')
                for path in self.files.iterdir():
                    self.push(path)
                self.service = LoopbackDav(self.art / 'final-http-ledger.json')
                self.service.__enter__()
                self.service.replace('/shares/final-picked.kdbx', (self.files / 'picked-share.kdbx').read_bytes())
                self.launch()
                self.by_id('start_open_file', 30)
                (self.art / 'final-private-runtime.json').write_text(json.dumps({key: os.environ.get(key) for key in
                    ('ANDROID_SERIAL', 'ANDROID_ADB_SERVER_PORT', 'ADB_SERVER_SOCKET', 'ANDROID_AVD_HOME',
                     'ANDROID_USER_HOME', 'KP2A_E2E_ARTIFACTS')}, indent=2))
        for name, action in ((CASES[1], self.move_into),
                             (CASES[2], lambda: self.export_edit('export-edit', True)),
                             (CASES[3], lambda: self.export_edit('export-flat', False)),
                             (CASES[4], self.picked_empty)):
            if (self.empty_path_only and name != CASES[4]) or (self.remaining_only and name == CASES[1]):
                continue
            if self.transport_failed or self.feature_failure or time.monotonic() >= self.deadline:
                break
            try:
                with self.case(name):
                    with self.navigation(name, 420 if self.empty_path_only else
                                         240 if self.remaining_only else 185):
                        action()
            except Exception:
                # Only locator/onboarding failures may leave independent cases runnable.
                # A concrete product assertion or transport failure ends this session.
                if self.transport_failed or self.feature_failure:
                    break
        self.record()


def main():
    journey = None
    def stop(*_):
        raise TimeoutError('Final acceptance child deadline/termination')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(890)
    try:
        journey = FinalAcceptance()
        for path in (Path(__file__), Path(__file__).with_name('keeshare') / 'final_acceptance_data.py'):
            (journey.art / ('executed-' + path.name)).write_bytes(path.read_bytes())
        journey.run()
        required = ([CASES[0], CASES[4]] if journey.empty_path_only else
                    [name for name in CASES if not (journey.remaining_only and name == CASES[1])])
        return 0 if all(journey.results[name]['status'] == 'passed' for name in required) else 1
    except Exception as error:
        traceback.print_exc()
        if journey is None:
            art = Path(os.environ['KP2A_E2E_ARTIFACTS']) / 'keeshare'
            art.mkdir(exist_ok=True)
            (art / 'final-acceptance-results.json').write_text(json.dumps({
                'target_apk_sha256': APPROVED_APK, 'expected_bytes': EXPECTED_APK_BYTES,
                'startup_error': str(error), 'cases': {name: {'status': 'not-run'} for name in CASES}}, indent=2))
        return 1
    finally:
        signal.alarm(0)
        if journey is not None:
            journey.navigation_deadline = None
            journey.record()
            if journey.service is not None:
                journey.service.__exit__(None, None, None)
            if not journey.transport_failed:
                (journey.art / 'final-acceptance-logcat.txt').write_bytes(journey.adb_run('logcat', '-d').stdout)


if __name__ == '__main__':
    raise SystemExit(main())
