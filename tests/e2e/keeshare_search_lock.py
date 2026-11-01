#!/usr/bin/env python3
"""One bounded SearchResults lifetime-lock diagnosis on a fresh kp2a e2e device.

This is diagnostic evidence, not acceptance of Sync completing on search.
Reuse the dedicated two-DB fixtures and full installed-byte/guest provenance gate.
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
from keeshare_two_databases import TwoDatabases, prepare, TITLE_A, TITLE_B
from keeshare_reload import export_has_title


class SearchLockDiagnosis(TwoDatabases):
    def __init__(self):
        super().__init__(advanced_search=True)
        self.timeline = []
        self.samples = {}
        self.current = 'search-lock'
        self.diagnosis = {'status': 'running', 'on_search_acceptance': 'not-passed'}

    def save(self):
        (self.art / 'search-lock-results.json').write_text(json.dumps({
            'apk': self.apk, 'package': self.package,
            'serial': os.environ['ANDROID_SERIAL'],
            'private_adb': os.environ['ADB_SERVER_SOCKET'],
            'pid': getattr(self, 'pid', None), 'timeline': self.timeline,
            'samples': self.samples, 'diagnosis': self.diagnosis,
        }, indent=2) + '\n')

    def mark(self, event):
        stamp = {'event': event, 'host_epoch': time.time(),
                 'monotonic': time.monotonic(),
                 'guest_date': self.shell('date', '+%m-%d_%H:%M:%S.%N')}
        self.timeline.append(stamp)
        self.save()
        print(json.dumps(stamp), flush=True)
        return stamp

    def logs(self, label):
        raw = self.adb_run('logcat', '-d', '-v', 'threadtime').stdout
        (self.art / ('search-lock-' + label + '-logcat.txt')).write_bytes(self.redact(raw))
        app = '\n'.join(line for line in raw.decode(errors='replace').splitlines()
                        if re.match(r'^\S+\s+\S+\s+' + re.escape(self.pid) + r'\s', line))
        (self.art / ('search-lock-' + label + '-app-logcat.txt')).write_text(app + '\n')
        return app

    def sample(self, label, expected_search):
        start = time.monotonic()
        nodes = self.nodes()
        texts = {node.get('text', '') for node in nodes}
        on_search = any(text.startswith('Search results (') for text in texts)
        if expected_search:
            assert on_search and TITLE_A in texts and TITLE_B in texts, 'SearchResults changed during observation'
        else:
            assert not on_search and any(
                node.get('text') == 'Select database' or
                (node.get('text') == 'Personal' and node.get('resource-id', '').endswith('/group_text'))
                for node in nodes), 'Missing real group/selector anchor after Back'
        busy = [dict(node.attrib) for node in nodes if
                node.get('resource-id', '').rsplit('/', 1)[-1] in
                ('background_ops_container', 'background_ops_message',
                 'background_ops_submessage', 'cancel_background') or
                node.get('class', '').endswith('ProgressBar')]
        samples = self.samples.setdefault(label, [])
        sample = {'host_epoch': time.time(), 'monotonic': time.monotonic(),
                  'capture_start_monotonic': start, 'on_search': on_search,
                  'busy_nodes': busy}
        samples.append(sample)
        (self.art / ('search-lock-' + label + '-' + str(len(samples)) + '.xml')).write_bytes(self.last_xml)
        self.save()
        return sample

    def output(self, label):
        path = self.pull('personal-export.kdbx.share', 'search-lock-' + label + '.kdbx.share')
        result = {'path': str(path), 'bytes': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'has_owner_a_title': export_has_title(path, TITLE_A)}
        assert result['has_owner_a_title'], 'Export missing expected Owner A title'
        self.diagnosis[label + '_output'] = result
        self.save()

    def run(self):
        self.mark('prepare-start')
        self.entry_uuid = prepare(self.files)
        self.canonical_files = '/data/data/' + self.package + '/files'
        self.shell('run-as', self.package, 'mkdir', '-p', 'files')
        for path in self.files.iterdir():
            self.push(path)
        self.launch()
        self.by_id('start_open_file', 60)
        self.open_local('main.kdbx')
        self.open_local('clone.kdbx')
        self.select_current('Owner A')
        self.search((TITLE_A, TITLE_B))
        self.pid = self.shell('pidof', self.package)
        assert re.fullmatch(r'\d+', self.pid), 'Expected one app PID'
        self.mark('search-ready')
        self.wait_operations_idle('before-sync', (TITLE_A, TITLE_B), seconds=15)
        self.sample('idle-baseline', True)
        self.output('before-sync')
        self.logs('before-sync')

        self.tap(self.wait(lambda n: n.get('content-desc') == 'More options', 'More options'))
        item = self.text('Synchronize database…')
        self.snap('visible-sync-menu')
        self.mark('sync-tap-before')
        self.tap(item)
        dispatch = self.mark('sync-tap-after')
        # No navigation, tap, key, fixture replacement or process mutation here.
        deadline = dispatch['monotonic'] + 12
        while time.monotonic() < deadline:
            self.sample('on-search-after-sync', True)
            time.sleep(.4)
        self.mark('on-search-observation-ended')
        before_back = self.logs('before-back')
        self.diagnosis['search_lifecycle_before_back'] = [
            line for line in before_back.splitlines() if 'SearchResults.On' in line]
        self.save()
        self.mark('normal-back-before')
        self.key(4)
        back = self.mark('normal-back-after')
        deadline = back['monotonic'] + 45
        # Normal Back may finish directly into the group or the two-DB selector.
        self.wait_nodes(lambda nodes: any(
            n.get('text') == 'Select database' or
            (n.get('text') == 'Personal' and n.get('resource-id', '').endswith('/group_text'))
            for n in nodes), 'group or selector after normal Back', seconds=15)
        self.mark('group-or-selector-anchored')
        idle_since = None
        complete = False
        while time.monotonic() < deadline:
            sample = self.sample('after-back', False)
            if sample['busy_nodes']:
                idle_since = None
            elif idle_since is None:
                idle_since = time.monotonic()
            elif time.monotonic() - idle_since >= 3:
                complete = True
                break
            time.sleep(.4)
        self.mark('after-back-observation-ended')
        self.output('after-back')
        after_back = self.logs('after-back')
        self.diagnosis.update(
            status='observed', post_back_visibly_idle=complete,
            same_pid_after_back=self.shell('pidof', self.package) == self.pid,
            search_lifecycle_after_back=[line for line in after_back.splitlines()
                                         if 'SearchResults.On' in line],
            limitation='No direct worker stack, lock ownership or lock counters captured; not repaired behavior.')
        self.snap('final-group-or-selector')
        self.save()


def main():
    journey = None
    try:
        journey = SearchLockDiagnosis()
        journey.run()
        print('DIAGNOSTIC COMPLETE:', journey.art, flush=True)
        return 0
    except Exception as error:
        traceback.print_exc()
        if journey is not None:
            journey.diagnosis.update(status='failed', error=str(error))
            journey.save()
        else:
            path = Path(os.environ['KP2A_E2E_ARTIFACTS']) / 'keeshare' / 'search-lock-startup-failure.json'
            path.write_text(json.dumps({'status': 'failed', 'error': str(error)}, indent=2) + '\n')
        return 1
    finally:
        if journey is not None and not journey.transport_failed:
            journey.logs('final')


if __name__ == '__main__':
    sys.exit(main())
