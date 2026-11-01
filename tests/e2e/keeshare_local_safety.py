#!/usr/bin/env python3
"""Real Android KeeShare local placement safety slice (fresh kp2a e2e only).

Each invocation performs UI moves/recycling, imports older/equal remote placement,
then checks one atomic collision. Use --collision for separate fresh-session controls.
No source or reviewed journey modifications, host engine, or privileged UI bridge.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).with_name('keeshare')))
from keeshare_journey import Journey
from local_safety_data import (prepare, load_share, remote_input, protected_state,
                               assert_preserved, assert_export_excludes, full_state)
from pykeepass import PyKeePass

CASES = ['prepare', 'open-import', 'ui-move-entry', 'ui-move-nested-group',
         'ui-recycle-entry', 'older-remote-preserves-outside',
         'equal-second-preserves-outside', 'collision-atomic',
         'cold-reopen-preserves-outside']


class LocalSafety(Journey):
    def __init__(self, collision):
        super().__init__()
        expected_apk = '4207369bb9d2349bd58befdfba55e5735f53fe7b6757d6f472950ca326f9179b'
        assert self.apk['sha256'] == expected_apk, 'Installed APK differs from approved safety build'
        self.collision = collision
        self.results = {name: {'status': 'not-run'} for name in CASES}
        self.stale = self.art / 'stale-before-ui-moves.kdbx.share'

    def record(self):
        (self.art / 'local-safety-results.json').write_text(json.dumps({
            'package': self.package, 'serial': os.environ['ANDROID_SERIAL'],
            'private_adb': os.environ['ADB_SERVER_SOCKET'], 'started': self.started,
            'apk': self.apk, 'phase': 'local-safety', 'collision': self.collision,
            'cases': self.results,
            'unverified': [name for name, result in self.results.items()
                           if result['status'] != 'passed'],
            'collision_controls_not_run_in_this_session': [name for name in (
                'newer-entry', 'newer-descendant', 'different-creation', 'different-type')
                if name != self.collision],
            'remaining': ['duplicate UUID two-open-DB ownership and direct intents',
                          'read-only stale callbacks/history/TAN guards',
                          'remaining acceptance cases in keeshare/coverage.md'],
        }, indent=2) + '\n')

    @contextmanager
    def case(self, name):
        before = {str(path.relative_to(self.art)) for path in self.art.rglob('*') if path.is_file()}
        try:
            with super().case(name):
                yield
        finally:
            after = {str(path.relative_to(self.art)) for path in self.art.rglob('*') if path.is_file()}
            self.results[name]['artifacts'] = sorted(after - before - {'local-safety-results.json', 'latest.xml'})
            self.record()

    def db(self, label):
        return PyKeePass(self.pull('main.kdbx', label + '.kdbx'), password='main-pass')

    def open_main(self, first=False):
        if first:
            self.launch()
            self.by_id('start_open_file', 60)
        output = self.shell('am', 'start', '-a', 'kp2a.action.SelectCurrentDbActivity',
                            '-p', self.package, '--es', 'fileName',
                            '/data/data/' + self.package + '/files/main.kdbx')
        (self.art / (self.current + '-open-intent.txt')).write_text(output)
        assert 'Error' not in output and 'Exception' not in output, output
        self.unlock()

    def move_out(self, title):
        self.back_to_root()
        self.tap(self.text('Team Sync'))
        self.tap(self.text(title), long=True)
        self.by_id('action_mode_close_button')
        self.tap(self.by_id('menu_move'))
        self.by_id('insert_element')
        # Back retains the moving task while going up the real group stack.
        self.key(4)
        self.text('Personal')
        self.by_id('insert_element')
        self.tap(self.text('Personal'))
        self.by_id('insert_element')
        self.snap('destination-before-insert')
        self.tap(self.by_id('insert_element'))
        self.text(title)
        self.back_to_root()

    def await_db(self, predicate, label):
        return PyKeePass(self.eventually_file('main.kdbx',
            lambda path: predicate(PyKeePass(path, password='main-pass')),
            label + '.kdbx'), password='main-pass')

    def sync_marker(self, marker, *, placement):
        before = self.db(self.current + '-before')
        remote_input(self.stale, self.files / 'team-sync.kdbx.share', before,
                     marker=marker, placement=placement)
        (self.art / (self.current + '-remote-input.kdbx.share')).write_bytes(
            (self.files / 'team-sync.kdbx.share').read_bytes())
        self.push(self.files / 'team-sync.kdbx.share')
        self.row_button('Team Sync', 'keeshare_row_sync')
        after = self.await_db(lambda db: db.find_entries(title=marker, first=True) is not None,
                              self.current + '-after')
        self.wait_status('Team Sync', lambda value: 'failed' not in value.lower()
                         and ('imported' in value.lower() or 'exported' in value.lower()),
                         'successful marker import/export')
        assert_preserved(before, after)
        def exported(path):
            remote = load_share(path)
            if remote.find_entries(title=marker, first=True) is None:
                return False
            assert_export_excludes(remote, before)
            return True
        self.eventually_file('team-sync.kdbx.share', exported, self.current + '-export.kdbx.share')
        self.results[self.current]['assertions'] = [
            'Fresh remote marker imported by Android and exported',
            'Exactly one copy of each outside UUID, original parent and full decrypted subtree unchanged',
            'All custom icons and tombstones unchanged; export excludes moved/recycled UUIDs']

    def run(self):
        with self.case('prepare'):
            prepare(self.files)
            self.shell('run-as', self.package, 'mkdir', '-p', 'files')
            for name in ('main.kdbx', 'team-import.kdbx', 'team-sync.kdbx.share'):
                self.push(self.files / name)
        with self.case('open-import'):
            self.open_main(first=True)
            self.tap(self.text('Team Sync'))
            for title in ('Move Outside Entry', 'Recycle Outside Entry', 'Move Outside Group'):
                self.text(title, 60)
            self.back_to_root()
            self.config()
            self.row_button('Team Sync', 'keeshare_row_sync')
            self.wait_status('Team Sync', lambda value: value in (
                'No changes detected.', 'Database exported successfully!',
                'Imported changes from KeeShare', 'Database synchronized successfully!'), 'initial synchronization')
            self.pull('team-sync.kdbx.share', self.stale.name)
            assert load_share(self.stale).find_entries(title='Atomic Inside Control', first=True) is not None, 'Initial export missing local control'
            initial = self.db('initial-import-main')
            for title in ('Move Outside Entry', 'Recycle Outside Entry', 'Nested Outside Entry'):
                assert initial.find_entries(title=title, first=True) is not None
            self.back_to_root()
        with self.case('ui-move-entry'):
            self.move_out('Move Outside Entry')
            self.await_db(lambda db: db.find_entries(title='Move Outside Entry', first=True).parentgroup.name == 'Personal',
                          'ui-moved-entry-main')
        with self.case('ui-move-nested-group'):
            self.move_out('Move Outside Group')
            self.await_db(lambda db: db.find_groups(name='Move Outside Group', first=True).parentgroup.name == 'Personal',
                          'ui-moved-group-main')
        with self.case('ui-recycle-entry'):
            self.tap(self.text('Team Sync'))
            self.tap(self.text('Recycle Outside Entry'), long=True)
            self.by_id('action_mode_close_button')
            self.tap(self.by_id('menu_delete'))
            self.text('Delete permanently?')
            self.wait(lambda node: node.get('text', '').startswith(
                'Do you want to delete the selected elements permanently? Press No to recycle.'),
                'recycle confirmation with optional owner database display name')
            self.snap('recycle-confirmation')
            self.tap(self.text('No'))
            self.await_db(lambda db: db.find_entries(title='Recycle Outside Entry', first=True).parentgroup.name == 'Recycle Bin',
                          'ui-recycled-main')
            self.back_to_root()
            self.tap(self.text('Recycle Bin'))
            self.text('Recycle Outside Entry')
            self.back_to_root()
            protected_state(self.db('outside-baseline-main'))
            self.config()
        with self.case('older-remote-preserves-outside'):
            self.sync_marker('Older Placement Imported Marker', placement='older')
        with self.case('equal-second-preserves-outside'):
            self.sync_marker('Equal Placement Imported Marker', placement='equal')
        # Check cold reopen before injecting collision so first-open metadata and
        # other shares cannot contaminate a failed-import equality baseline.
        with self.case('cold-reopen-preserves-outside'):
            before = self.db('cold-before-main')
            self.back_to_root()
            self.shell('am', 'force-stop', self.package)
            self.open_main()
            self.tap(self.text('Personal'))
            self.text('Move Outside Entry')
            self.text('Move Outside Group')
            self.back_to_root()
            self.tap(self.text('Recycle Bin'))
            self.text('Recycle Outside Entry')
            self.back_to_root()
            self.config()
            self.row_button('Team Sync', 'keeshare_row_sync')
            self.wait_status('Team Sync', lambda value: value in (
                'No changes detected.', 'Database exported successfully!',
                'Imported changes from KeeShare', 'Database synchronized successfully!'),
                'cold-open import/export completed')
            assert_preserved(before, self.db('cold-after-main'))
            assert_export_excludes(load_share(self.pull('team-sync.kdbx.share', 'cold-export.kdbx.share')), before)
        with self.case('collision-atomic'):
            before = self.db('collision-before-main')
            before_bytes = (self.art / 'collision-before-main.kdbx').read_bytes()
            remote_input(self.stale, self.files / 'team-sync.kdbx.share', before,
                         marker='Collision Must Never Import', collision=self.collision)
            self.push(self.files / 'team-sync.kdbx.share')
            remote_bytes = (self.files / 'team-sync.kdbx.share').read_bytes()
            (self.art / 'collision-remote-input.kdbx.share').write_bytes(remote_bytes)
            self.row_button('Team Sync', 'keeshare_row_sync')
            self.wait_status('Team Sync', lambda value: 'already present outside the shared group' in value,
                             'visible outside-placement collision failure')
            self.snap('collision-refused')
            after = self.db('collision-after-main')
            assert full_state(after) == full_state(before), 'Failed collision modified decrypted main database'
            assert (self.art / 'collision-after-main.kdbx').read_bytes() == before_bytes, 'Failed collision saved main database'
            assert self.pull('team-sync.kdbx.share', 'collision-after-remote.kdbx.share').read_bytes() == remote_bytes, 'Failed collision exported over remote input'
            assert after.find_entries(title='Collision Must Never Import', first=True) is None
            assert_preserved(before, after)
            self.results[self.current]['assertions'] = [
                'Visible collision refusal from real Android importer',
                'Exact main file and complete decrypted XML unchanged',
                'Remote input byte-identical, new entry/icon/tombstone not merged']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collision', default='newer-entry', choices=(
        'newer-entry', 'newer-descendant', 'different-creation', 'different-type'))
    args = parser.parse_args()
    journey = LocalSafety(args.collision)
    try:
        journey.run()
    except Exception:
        traceback.print_exc()
        print('FAIL:', journey.current, 'Evidence:', journey.art, flush=True)
        return 1
    finally:
        journey.record()
    print('PASS: bounded local safety slice; remaining coverage is explicit in results', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
