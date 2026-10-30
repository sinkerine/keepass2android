#!/usr/bin/env python3
"""Run a behavior check or a custom command on a disposable Android emulator."""
import argparse
import contextlib
import fcntl
import os
import re
import signal
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=kwargs.pop('timeout', 60), **kwargs)


def available(port):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


@contextlib.contextmanager
def emulator_ports():
    # Serialize allocation across repository checkouts and concurrent test runs.
    for port in range(5554, 5682, 2):
        with open(f'/tmp/kp2a-emulator-{os.getuid()}-{port}.lock', 'w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            if available(port) and available(port + 1):
                yield port
                return
    raise RuntimeError('No unused emulator port pair available')


def smoke(adb, package, artifacts):
    run(adb + ['shell', 'am', 'force-stop', package])
    launch = run(adb + ['shell', 'monkey', '-p', package, '-c',
                        'android.intent.category.LAUNCHER', '1'], capture_output=True, text=True)
    (artifacts / 'launch.txt').write_text(launch.stdout + launch.stderr)
    # Assert actual first-run controls, then exercise opening the database creation UI.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        run(adb + ['shell', 'uiautomator', 'dump', '/sdcard/window.xml'],
            stdout=subprocess.DEVNULL)
        xml = run(adb + ['exec-out', 'cat', '/sdcard/window.xml'], capture_output=True).stdout
        (artifacts / 'window.xml').write_bytes(xml)
        try:
            tree = ET.fromstring(xml)
        except ET.ParseError:
            time.sleep(1)
            continue
        create = next((n for n in tree.iter('node') if n.get('resource-id') == f'{package}:id/start_create'), None)
        if create is not None:
            coords = list(map(int, re.findall(r'\d+', create.attrib['bounds'])))
            run(adb + ['shell', 'input', 'tap', str((coords[0] + coords[2]) // 2),
                        str((coords[1] + coords[3]) // 2)])
            break
        time.sleep(1)
    else:
        raise RuntimeError('First-run Create database control did not appear')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        run(adb + ['shell', 'uiautomator', 'dump', '/sdcard/window.xml'], stdout=subprocess.DEVNULL)
        xml = run(adb + ['exec-out', 'cat', '/sdcard/window.xml'], capture_output=True).stdout
        (artifacts / 'create-database.xml').write_bytes(xml)
        try:
            nodes = ET.fromstring(xml).iter('node')
        except ET.ParseError:
            time.sleep(1)
            continue
        if any(n.get('class') == 'android.widget.EditText' and n.get('package') == package for n in nodes):
            print('PASS: first-run screen and database creation form')
            return
        time.sleep(1)
    raise RuntimeError('Database creation form did not appear after tapping Create database')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, help='Signed APK (defaults to the newest Debug APK)')
    parser.add_argument('--gui', action='store_true', help='Show the isolated emulator window')
    parser.add_argument('--boot-timeout', type=int, default=240)
    parser.add_argument('command', nargs=argparse.REMAINDER, help='Optional command after --; receives ANDROID_SERIAL and private ADB server environment')
    args = parser.parse_args()
    # Convert normal termination into an exception so the finally block cleans up.
    def terminate(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    for tool in ('adb', 'emulator', 'avdmanager', 'aapt'):
        if not shutil.which(tool):
            parser.error(f'{tool} is missing; run inside nix develop')
    if not os.access('/dev/kvm', os.R_OK | os.W_OK):
        parser.error('Readable/writable /dev/kvm required (enable KVM and grant your user access)')
    apks = list((ROOT / 'src/keepass2android-app/bin/Debug').rglob('*-Signed.apk'))
    apk = args.apk or (max(apks, key=lambda p: p.stat().st_mtime) if apks else None)
    if apk is None or not apk.is_file():
        parser.error('No APK found; run kp2a build or supply --apk')
    apk = apk.resolve()
    badging = run(['aapt', 'dump', 'badging', str(apk)], capture_output=True, text=True).stdout
    package = re.search(r"package: name='([^']+)'", badging).group(1)
    artifacts_root = ROOT / '.dev/e2e'
    artifacts_root.mkdir(parents=True, exist_ok=True)
    artifacts = Path(tempfile.mkdtemp(prefix='run-', dir=artifacts_root))
    print(f'Artifacts: {artifacts}', flush=True)
    with tempfile.TemporaryDirectory(prefix='kp2a-e2e-') as temporary, emulator_ports() as port:
        private = Path(temporary)
        env = os.environ.copy()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            adb_port = sock.getsockname()[1]
        env.update(ANDROID_USER_HOME=str(private / 'android'),
                   ANDROID_EMULATOR_HOME=str(private / 'android'),
                   ANDROID_AVD_HOME=str(private / 'avd'),
                   ANDROID_SERIAL=f'emulator-{port}',
                   ANDROID_ADB_SERVER_PORT=str(adb_port),
                   ADB_SERVER_SOCKET=f'tcp:127.0.0.1:{adb_port}',
                   KP2A_E2E_ARTIFACTS=str(artifacts), KP2A_E2E_PACKAGE=package)
        for key in ('ANDROID_USER_HOME', 'ANDROID_AVD_HOME'):
            Path(env[key]).mkdir(parents=True)
        adb = ['adb', '-P', str(adb_port), '-s', env['ANDROID_SERIAL']]
        emulator = None
        with open(artifacts / 'emulator.log', 'w') as log:
            try:
                run(['adb', '-P', str(adb_port), 'start-server'], env=env)
                run(['avdmanager', 'create', 'avd', '--name', 'kp2a-e2e', '--package',
                     'system-images;android-36;google_apis;x86_64', '--device', 'pixel_2'],
                    input='no\n', text=True, env=env)
                command = ['emulator', '-avd', 'kp2a-e2e', '-port', str(port),
                           '-no-snapshot', '-wipe-data', '-no-audio', '-no-boot-anim',
                           '-gpu', 'swiftshader_indirect', '-accel', 'on', '-memory', '2048']
                if not args.gui:
                    command.append('-no-window')
                emulator = subprocess.Popen(command, env=env, stdout=log, stderr=log)
                deadline = time.monotonic() + args.boot_timeout
                while time.monotonic() < deadline:
                    if emulator.poll() is not None:
                        raise RuntimeError('Emulator exited; inspect emulator.log')
                    boot = subprocess.run(adb + ['shell', 'getprop', 'sys.boot_completed'],
                                          env=env, capture_output=True, text=True, timeout=10)
                    if boot.stdout.strip() == '1':
                        break
                    time.sleep(2)
                else:
                    raise RuntimeError('Emulator boot timed out')
                run(adb + ['shell', 'input', 'keyevent', '82'], env=env)
                for name in ('window_animation_scale', 'transition_animation_scale', 'animator_duration_scale'):
                    run(adb + ['shell', 'settings', 'put', 'global', name, '0'], env=env)
                run(adb + ['install', '--no-incremental', '-r', str(apk)], env=env, timeout=120)
                custom = args.command
                if custom[:1] == ['--']:
                    custom = custom[1:]
                if custom:
                    run(custom, env=env, timeout=None)
                else:
                    # adb has explicit server/device arguments, including in the default smoke test.
                    smoke(adb, package, artifacts)
            finally:
                if emulator is not None:
                    for name, command in [('logcat.txt', ['logcat', '-d']),
                                          ('screen.png', ['exec-out', 'screencap', '-p'])]:
                        with open(artifacts / name, 'wb') as output:
                            try:
                                subprocess.run(adb + command, env=env, stdout=output,
                                               stderr=subprocess.DEVNULL, timeout=15)
                            except (OSError, subprocess.TimeoutExpired):
                                pass
                    emulator.terminate()
                    try:
                        emulator.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        emulator.kill()
                        emulator.wait(timeout=10)
                subprocess.run(['adb', '-P', str(adb_port), 'kill-server'], env=env, timeout=15)


if __name__ == '__main__':
    main()
