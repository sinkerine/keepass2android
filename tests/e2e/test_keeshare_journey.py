#!/usr/bin/env python3
"""Host-only harness regressions; no emulator, APK build or feature simulation.

Run inside the fixture Python environment:
  python3 -B -m unittest discover -s tests/e2e -p test_keeshare_journey.py -v
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location('keeshare_journey', Path(__file__).with_name('keeshare_journey.py'))
journey_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journey_module)
Journey = journey_module.Journey

XML = b'<hierarchy><node text="main-pass" resource-id="test:id/control"/></hierarchy>'
REMOTE = '/data/local/tmp/keeshare-window.xml'


def result(code=0, stdout=b'', stderr=b''):
    return subprocess.CompletedProcess([], code, stdout, stderr)


class DumpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.journey = Journey.__new__(Journey)
        self.journey.art = Path(self.temporary.name)
        self.journey.last_xml = XML
        self.journey.current = 'test'
        self.journey.package = 'test'
        self.journey.results = {}
        (self.journey.art / 'latest.xml').write_bytes(XML)

    def assert_no_current_xml(self):
        self.assertEqual(self.journey.last_xml, b'')
        self.assertFalse((self.journey.art / 'latest.xml').exists())

    def test_failed_dump_cannot_read_stale_remote_file_and_can_retry(self):
        remote_files = {REMOTE: XML}
        calls = []

        def adb_run(*args, **kwargs):
            calls.append(args)
            if args[:3] == ('shell', 'rm', '-f'):
                remote_files.pop(args[3], None)
                return result()
            if args[:3] == ('shell', 'uiautomator', 'dump'):
                return result(1, b'failed main-pass', b'no idle window')
            self.fail('Failed dump must not read a potentially stale file')

        self.journey.adb_run = adb_run
        with self.assertRaisesRegex(AssertionError, 'fresh UI hierarchy'):
            self.journey.nodes()
        self.assertEqual(remote_files, {})
        self.assertEqual(calls, [('shell', 'rm', '-f', REMOTE),
                                 ('shell', 'uiautomator', 'dump', REMOTE)])
        self.assert_no_current_xml()
        evidence = (self.journey.art / 'dump-error.txt').read_bytes()
        self.assertIn(b'returncode: 1', evidence)
        self.assertIn(b'no idle window', evidence)
        self.assertNotIn(b'main-pass', evidence)
        self.journey.adb_run = Mock(side_effect=[result(), result(), result(stdout=XML)])
        self.assertEqual(len(self.journey.nodes()), 1)
        self.assertNotIn(b'main-pass', self.journey.last_xml)
        self.assertEqual((self.journey.art / 'dump-error.txt').read_bytes(), evidence)

    def test_failed_dump_cannot_satisfy_wait_and_retry_remains_bounded(self):
        self.journey.adb_run = Mock(side_effect=[result(), result(1)])
        with patch.object(journey_module.time, 'monotonic', side_effect=[0, 0, 1]), \
                patch.object(journey_module.time, 'sleep'):
            with self.assertRaisesRegex(AssertionError, 'Missing UI: prior control'):
                self.journey.wait(lambda node: node.get('text') == 'main-pass',
                                  'prior control', seconds=1)
        self.assertEqual(self.journey.adb_run.call_count, 2)
        self.assert_no_current_xml()

    def test_wait_retries_transient_dump_failure_before_observing_match(self):
        self.journey.adb_run = Mock(side_effect=[result(), result(1),
                                                result(), result(), result(stdout=XML)])
        with patch.object(journey_module.time, 'monotonic', side_effect=[0, 0, .5]), \
                patch.object(journey_module.time, 'sleep') as sleep:
            node = self.journey.wait(lambda node: node.get('text') == 'main-pass',
                                     'actual control', seconds=1)
        self.assertEqual(node.get('resource-id'), 'test:id/control')
        self.assertEqual(self.journey.adb_run.call_count, 5)
        sleep.assert_called_once_with(.4)

    def test_nodes_requires_anchor_in_current_capture(self):
        self.journey.adb_run = Mock(side_effect=[result(), result(), result(stdout=XML)])
        with self.assertRaisesRegex(AssertionError, 'expected-screen anchor'):
            self.journey.nodes({'resource-id': 'test:id/keeshare_readonly_info'})

    def readonly_xml(self, selection=False, extra=None):
        root = ET.Element('hierarchy')
        for attributes in ({'resource-id': 'test:id/keeshare_readonly_info'},
                           {'resource-id': 'test:id/entry_text', 'text': 'Imported Entry'},
                           {'text': 'Team Import'}):
            ET.SubElement(root, 'node', attributes)
        if selection:
            ET.SubElement(root, 'node', {'resource-id': 'test:id/check_mark', 'content-desc': 'Selected'})
            ET.SubElement(root, 'node', {'resource-id': 'test:id/action_mode_close_button'})
        if extra:
            ET.SubElement(root, 'node', extra)
        return ET.tostring(root)

    def run_readonly(self, captures):
        replies = []
        for capture in captures:
            if capture is None:
                replies.extend([result(), result(1, stderr=b'no idle window')])
            else:
                replies.extend([result(), result(), result(stdout=capture)])
        self.journey.adb_run = Mock(side_effect=replies)
        self.journey.record = Mock()
        self.journey.tap = Mock()
        self.journey.text = Mock(return_value=ET.Element('node'))
        self.journey.key = Mock()
        # Snapshot capture stays real; only the screenshot subprocess is replaced.
        original = self.journey.adb_run
        def adb_run(*args, **kwargs):
            if args == ('exec-out', 'screencap', '-p'):
                return result(stdout=b'PNG')
            return original(*args, **kwargs)
        self.journey.adb_run = Mock(side_effect=adb_run)
        self.journey.readonly_case()

    def test_failed_negative_capture_then_successful_unrelated_snapshot_cannot_pass_04(self):
        for selection in (False, True):
            with self.subTest(selection=selection):
                captures = ([self.readonly_xml(), self.readonly_xml(True)] if selection else [])
                # The next capture fails at the negative assertion. The later
                # unrelated capture succeeds for failure evidence, never passing 04.
                with self.assertRaisesRegex(AssertionError, 'fresh UI hierarchy'):
                    self.run_readonly(captures + [None, XML])
                self.assertEqual(self.journey.results['04-readonly']['status'], 'failed')
                self.assertNotIn('snapshot_error', self.journey.results['04-readonly'])
                self.assertFalse((self.journey.art / '04-readonly-passed.xml').exists())
                self.assertIn(b'control', (self.journey.art / '04-readonly-failed.xml').read_bytes())
                self.journey.key.assert_not_called()

    def test_readonly_rejects_unrelated_screen_or_missing_selection_anchor(self):
        for captures in ([XML, XML],
                         [self.readonly_xml(), self.readonly_xml(), self.readonly_xml(), XML]):
            with self.subTest(captures=captures):
                with self.assertRaisesRegex(AssertionError, 'expected-screen anchor'):
                    self.run_readonly(captures)
                self.assertEqual(self.journey.results['04-readonly']['status'], 'failed')

    def test_readonly_rejects_add_and_modification_controls(self):
        for control in ('fabAddNew', 'fabAddNewEntry', 'fabAddNewGroup',
                        'menu_delete', 'menu_move', 'menu_copy', 'menu_edit'):
            with self.subTest(control=control):
                selection = control.startswith('menu_')
                bad = self.readonly_xml(selection, {'resource-id': 'test:id/' + control})
                captures = ([self.readonly_xml(), self.readonly_xml(True)] if selection else [])
                with self.assertRaisesRegex(AssertionError, 'Read-only'):
                    self.run_readonly(captures + [bad, XML])
                self.assertEqual(self.journey.results['04-readonly']['status'], 'failed')

    def test_readonly_valid_observations_and_final_snapshot_pass(self):
        self.run_readonly([self.readonly_xml(), self.readonly_xml(True), self.readonly_xml(True), XML])
        self.assertEqual(self.journey.results['04-readonly']['status'], 'passed')
        self.assertEqual(self.journey.key.call_count, 2)

    def test_template_offer_is_not_skipped_after_failed_or_unrelated_capture(self):
        offer = b'<hierarchy><node text="Add templates?"/><node text="No"/></hierarchy>'
        self.journey.dump = Mock(side_effect=[None, ET.fromstring(XML), ET.fromstring(offer)])
        self.journey.tap = Mock()
        self.journey.by_id = Mock()
        with patch.object(journey_module.time, 'monotonic', side_effect=[0, 0, .5, 1]), \
                patch.object(journey_module.time, 'sleep'):
            self.journey.decline_templates()
        self.assertEqual(self.journey.tap.call_args.args[0].get('text'), 'No')
        self.journey.by_id.assert_called_once_with('entry_title')

    def test_template_poll_times_out_without_observed_offer_or_editor(self):
        self.journey.dump = Mock(return_value=None)
        self.journey.tap = Mock()
        self.journey.by_id = Mock()
        with patch.object(journey_module.time, 'monotonic', side_effect=[0, 0, 36]), \
                patch.object(journey_module.time, 'sleep'):
            with self.assertRaisesRegex(AssertionError, 'template offer or entry editor'):
                self.journey.decline_templates()
        self.journey.tap.assert_not_called()
        self.journey.by_id.assert_not_called()

    def test_template_branch_requires_decline_button_or_observed_editor(self):
        self.journey.dump = Mock(return_value=ET.fromstring(
            b'<hierarchy><node text="Add templates?"/></hierarchy>'))
        with self.assertRaisesRegex(AssertionError, 'no No button'):
            self.journey.decline_templates()
        self.journey.dump = Mock(return_value=ET.fromstring(
            b'<hierarchy><node resource-id="test:id/entry_title"/></hierarchy>'))
        self.journey.tap = Mock()
        self.journey.by_id = Mock()
        self.journey.decline_templates()
        self.journey.tap.assert_not_called()
        self.journey.by_id.assert_called_once_with('entry_title')

    def test_failed_remove_stops_before_dump(self):
        self.journey.adb_run = Mock(return_value=result(1, stderr=b'permission denied'))
        self.assertIsNone(self.journey.dump())
        self.assertEqual(self.journey.adb_run.call_count, 1)
        self.assert_no_current_xml()

    def test_failed_read_rejects_even_valid_stdout(self):
        self.journey.adb_run = Mock(side_effect=[result(), result(), result(1, XML)])
        self.assertIsNone(self.journey.dump())
        self.assert_no_current_xml()

    def test_missing_malformed_or_empty_hierarchy_is_rejected(self):
        for raw in (b'', b'<broken', b'<node/>', b'<hierarchy/>'):
            with self.subTest(raw=raw):
                self.journey.adb_run = Mock(side_effect=[result(), result(), result(stdout=raw)])
                self.assertIsNone(self.journey.dump())
                self.assert_no_current_xml()

    def test_timeout_retains_redacted_evidence(self):
        self.journey.adb_run = Mock(side_effect=[result(), subprocess.TimeoutExpired(
            'uiautomator', 40, output=b'main-pass', stderr=b'busy share-pass')])
        self.assertIsNone(self.journey.dump())
        self.assert_no_current_xml()
        evidence = (self.journey.art / 'dump-error.txt').read_bytes()
        self.assertIn(b'timed out', evidence)
        self.assertIn(b'busy', evidence)
        self.assertNotIn(b'main-pass', evidence)
        self.assertNotIn(b'share-pass', evidence)

    def test_success_returns_actual_input_but_only_persists_redacted_xml(self):
        self.journey.adb_run = Mock(side_effect=[result(), result(), result(stdout=XML)])
        root = self.journey.dump()
        self.assertEqual(root.find('node').get('text'), 'main-pass')
        self.assertEqual(self.journey.last_xml, (self.journey.art / 'latest.xml').read_bytes())
        self.assertNotIn(b'main-pass', self.journey.last_xml)
        self.assertIn(b'[synthetic-secret-redacted]', self.journey.last_xml)

    def test_snapshot_failure_never_writes_previous_xml(self):
        self.journey.adb_run = Mock(return_value=result(1))
        with self.assertRaisesRegex(AssertionError, 'fresh UI hierarchy'):
            self.journey.snap('passed')
        self.assertFalse((self.journey.art / 'test-passed.xml').exists())
        self.assert_no_current_xml()

    def test_case_preserves_original_failure_if_failure_snapshot_also_fails(self):
        self.journey.adb_run = Mock(return_value=result(1))
        self.journey.record = Mock()
        with self.assertRaisesRegex(ValueError, 'original failure'):
            with self.journey.case('test'):
                raise ValueError('original failure')
        self.assertEqual(self.journey.results['test']['status'], 'failed')
        self.assertEqual(self.journey.results['test']['type'], 'ValueError')
        self.assertIn('snapshot_error', self.journey.results['test'])
        self.assertIn('original failure', (self.journey.art / 'test-traceback.txt').read_text())

    def test_passing_body_requires_fresh_snapshot(self):
        self.journey.adb_run = Mock(return_value=result(1))
        self.journey.record = Mock()
        with self.assertRaisesRegex(AssertionError, 'fresh UI hierarchy'):
            with self.journey.case('test'):
                pass
        self.assertEqual(self.journey.results['test']['status'], 'failed')


class ReloadNavigationTests(unittest.TestCase):
    def setUp(self):
        self.journey = Journey.__new__(Journey)
        for name in ('tap', 'text', 'by_id', 'key', 'launch', 'fill', 'snap',
                     'back_to_root', 'overflow', 'scroll_text'):
            setattr(self.journey, name, Mock())

    def preference_xml(self, checked):
        return ET.fromstring('<hierarchy><node><node text="Other preference"/>'
                             '<node checkable="true" checked="false"/></node>'
                             '<node><node text="Sync after QuickUnlock"/>'
                             '<node checkable="true" checked="' + checked + '"/>'
                             '</node></hierarchy>')

    def test_checkbox_checks_own_row_and_verifies_changed_state(self):
        self.journey.dump = Mock(side_effect=[self.preference_xml('false'),
                                             self.preference_xml('true')])
        self.journey.set_app_checkbox('File handling', 'Sync after QuickUnlock', True)
        self.journey.text.assert_any_call('Sync after QuickUnlock')
        self.assertEqual(self.journey.dump.call_count, 2)
        self.journey.snap.assert_called_once()

    def test_checkbox_already_enabled_does_not_toggle(self):
        self.journey.dump = Mock(return_value=self.preference_xml('true'))
        self.journey.set_app_checkbox('File handling', 'Sync after QuickUnlock', True)
        self.journey.text.assert_called_once_with('App settings')

    def test_checkbox_refuses_unobserved_state_change(self):
        self.journey.dump = Mock(return_value=self.preference_xml('false'))
        with self.assertRaisesRegex(AssertionError, 'Preference not set'):
            self.journey.set_app_checkbox('File handling', 'Sync after QuickUnlock', True)
        self.journey.snap.assert_not_called()


class InstalledApkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.environment = {
            'ANDROID_SERIAL': 'emulator-harness-test',
            'ADB_SERVER_SOCKET': 'tcp:127.0.0.1:19999',
            'KP2A_E2E_PACKAGE': 'test.package',
            'KP2A_E2E_ARTIFACTS': self.temporary.name,
        }
        self.base = '/data/app/explicit-runner-apk/base.apk'
        self.paths = 'package:' + self.base + '\n'
        self.installed_bytes = b'bytes of installed explicit runner APK'

    def construct(self, paths_after=None, pull_error=False):
        paths = iter([self.paths, self.paths if paths_after is None else paths_after])

        def run(command, **kwargs):
            # Check the actual subprocess boundary; no real ADB is ever invoked.
            self.assertEqual(command[:3], ['adb', '-s', self.environment['ANDROID_SERIAL']])
            self.assertEqual(os.environ['ADB_SERVER_SOCKET'], self.environment['ADB_SERVER_SOCKET'])
            self.assertTrue(kwargs['check'])
            if command[3:] == ['shell', 'pm', 'path', 'test.package']:
                return result(stdout=next(paths).encode())
            if command[3] == 'pull':
                self.assertEqual(command[4], self.base)
                if pull_error:
                    raise subprocess.CalledProcessError(1, command, stderr=b'pull failed')
                Path(command[5]).write_bytes(self.installed_bytes)
                return result()
            self.fail('Unexpected ADB command: ' + repr(command))

        with patch.dict(os.environ, self.environment), \
                patch.object(journey_module.subprocess, 'run', side_effect=run), \
                patch.object(Path, 'rglob', side_effect=AssertionError('Must not choose a host APK')):
            return Journey()

    def test_explicit_installed_base_identity_and_retained_hash_evidence(self):
        journey = self.construct()
        self.assertEqual(journey.apk['path'], self.base)
        self.assertEqual(journey.apk['sha256'], hashlib.sha256(self.installed_bytes).hexdigest())
        self.assertEqual(Path(journey.apk['artifact']).read_bytes(), self.installed_bytes)
        self.assertEqual(journey.apk['source'], 'installed-package-base')

    def test_splits_are_reported_but_base_is_hashed(self):
        self.paths += 'package:/data/app/explicit-runner-apk/split_config.en.apk\n'
        journey = self.construct()
        self.assertEqual(len(journey.apk['package_paths']), 2)
        self.assertEqual(journey.apk['path'], self.base)

    def test_missing_ambiguous_duplicate_or_malformed_identity_fails(self):
        for paths in ('', 'package:/data/app/only-split.apk\n',
                      self.paths + 'package:/data/app/other/base.apk\n',
                      self.paths * 2, 'Error: package missing\n'):
            with self.subTest(paths=paths), tempfile.TemporaryDirectory() as directory:
                self.environment['KP2A_E2E_ARTIFACTS'] = directory
                self.paths = paths
                with self.assertRaises(RuntimeError):
                    self.construct()

    def test_install_path_change_during_pull_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'paths changed'):
            self.construct(paths_after='package:/data/app/replaced/base.apk\n')

    def test_failed_pull_fails_closed(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.construct(pull_error=True)

    def test_empty_pull_fails_closed(self):
        self.installed_bytes = b''
        with self.assertRaisesRegex(RuntimeError, 'empty'):
            self.construct()


if __name__ == '__main__':
    unittest.main()
