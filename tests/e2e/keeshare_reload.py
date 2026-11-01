#!/usr/bin/env python3
"""One bounded foreground-parent reload check through normal Android UI.

Run under kp2a e2e with --seed pointing at prior synthetic journey artifacts.
This checks the shared foreground reload handoff, not SyncUtil's Both request.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
from keeshare_journey import Journey, PyKeePass, BytesIO, ZipFile

APPROVED_APK = '4207369bb9d2349bd58befdfba55e5735f53fe7b6757d6f472950ca326f9179b'
PROMPT = 'The file which is currently open was changed by another program. Do you want to reload it?'
CHANGED_TITLE = 'Foreground Reloaded Personal Entry'


def export_has_title(path, title):
    with ZipFile(path) as archive:
        database = PyKeePass(BytesIO(archive.read('container.share.kdbx')), password='exp-pass')
    return database.find_entries(title=title, first=True) is not None


class ForegroundReload(Journey):
    def recreation_case(self):
        # Independent existing passing evidence; leave its result not-run here.
        pass

    def reload_prompt(self):
        nodes = self.nodes()
        if not any(n.get('text') == PROMPT for n in nodes):
            if any(n.get('text') == 'App settings' for n in nodes):
                self.key(4)  # Settings -> group OnResume performs the file check.
            else:
                assert any(n.get('text') == 'Personal' and
                           n.get('resource-id', '').endswith('group_text') for n in nodes), 'Expected root groups before foreground transition'
                self.overflow('Settings')  # Settings OnResume performs the check.
        self.text(PROMPT)
        self.nodes({'text': PROMPT}, {'resource-id': 'android:id/button1'},
                   {'resource-id': 'android:id/button2'})

    def trigger_regressions(self):
        with self.case('foreground-parent-reload'):
            assert self.apk['sha256'] == APPROVED_APK, 'Unexpected installed APK'
            # Establish an app-written export before changing only the parent.
            self.sync_now()
            baseline = self.eventually_file(
                'personal-export.kdbx.share', lambda path: export_has_title(path, 'Personal Entry'),
                'foreground-export-baseline.kdbx.share').read_bytes()
            self.back_to_root()
            parent = self.main_db('foreground-parent-before')
            original = parent.find_entries(title='Personal Entry', first=True)
            assert original is not None
            original_uuid = str(original.uuid)
            original.title = CHANGED_TITLE
            original.touch(modify=True)
            changed = self.files / 'main.kdbx'
            parent.save(changed)
            self.push(changed)
            summary = {
                'route': 'CheckForOpenFileChanged via Settings/group foreground transitions',
                'syncutil_trigger_exercised': False,
                'parent_ioc': self.canonical_files + '/main.kdbx',
                'changed_entry_uuid': original_uuid,
                'baseline_export_sha256': hashlib.sha256(baseline).hexdigest(),
                'changed_parent_sha256': hashlib.sha256(changed.read_bytes()).hexdigest(),
                'decisions': [],
            }
            for decision in ('decline', 'dismiss', 'accept'):
                self.reload_prompt()
                self.snap('prompt-' + decision)
                observed = self.pull('personal-export.kdbx.share', 'foreground-prompt-' + decision + '.kdbx.share')
                assert observed.read_bytes() == baseline, 'Export before reload decision: ' + decision
                summary['decisions'].append({'decision': decision, 'prompt_export_unchanged': True})
                (self.art / 'foreground-reload-observations.json').write_text(json.dumps(summary, indent=2) + '\n')
                if decision == 'dismiss':
                    self.key(4)
                else:
                    button = 'android:id/button1' if decision == 'accept' else 'android:id/button2'
                    self.tap(self.wait(lambda n: n.get('resource-id') == button, 'reload ' + decision))
                if decision != 'accept':
                    self.wait_nodes(lambda nodes: any(n.get('text') in ('App settings', 'Personal') for n in nodes),
                                    'settings or groups after reload ' + decision)
                    time.sleep(2)
                    after = self.pull('personal-export.kdbx.share', 'foreground-after-' + decision + '.kdbx.share')
                    assert after.read_bytes() == baseline, 'Export after reload ' + decision
                    summary['decisions'][-1]['after_export_unchanged'] = True
                    self.snap('after-' + decision)
            self.text('Team Import', 50)
            self.tap(self.text('Personal'))
            self.text(CHANGED_TITLE)
            self.snap('accepted-visible-changed-parent')
            current = self.main_db('foreground-parent-accepted')
            entry = current.find_entries(title=CHANGED_TITLE, first=True)
            assert entry is not None and str(entry.uuid) == original_uuid, 'Accepted reload opened incorrect parent content'
            time.sleep(5)
            automatic = self.pull('personal-export.kdbx.share', 'foreground-after-accept.kdbx.share')
            if automatic.read_bytes() == baseline:
                summary['automatic_export'] = 'unchanged during five-second observation; foreground reload does not request Both'
            else:
                assert export_has_title(automatic, CHANGED_TITLE), 'Accepted reload overwrote share without changed parent content'
                summary['automatic_export'] = 'changed parent exported after accepted reload; SyncUtil Both not proven'
            self.back_to_root()
            self.config()
            self.sync_now()
            self.eventually_file('personal-export.kdbx.share', lambda path: export_has_title(path, CHANGED_TITLE),
                                 'foreground-explicit-sync-export.kdbx.share')
            summary['explicit_share_sync_exported_changed_parent'] = True
            summary['limits'] = 'Foreground route only: SyncUtil-specific reload-pending/Both, canceled or failed reopen, database switching and cached replacement remain unverified.'
            (self.art / 'foreground-reload-observations.json').write_text(json.dumps(summary, indent=2) + '\n')
            self.results[self.current]['note'] = summary['limits']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    args = parser.parse_args()
    journey = ForegroundReload(extended=True, resume_regressions=args.seed, remaining_only=True)
    try:
        journey.resume_remaining()
    except Exception:
        traceback.print_exc()
        print('FAIL:', journey.current, 'Evidence:', journey.art, flush=True)
        return 1
    finally:
        journey.record()
    print('PASS: foreground reload handoff; SyncUtil-specific trigger remains unverified', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
