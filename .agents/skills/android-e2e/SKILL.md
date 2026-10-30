---
name: android-e2e
description: Build Keepass2Android and test behavior using a fresh isolated Android emulator, with screenshots, UI hierarchy and logcat evidence.
---

# Android behavior testing

Run commands from the repository root inside `nix develop` (or use `nix develop --command kp2a …`; for a sequence use `nix run . -- -c '…'`). Read `docs/development.md` for prerequisites and troubleshooting.

1. On first use, run `kp2a setup` to prepare the writable local .NET SDK and Android workload and initialize the Argon2 submodule.
2. Run `kp2a test` for the existing Autofill parser tests.
3. Run `kp2a build` to produce a signed Debug APK containing its managed assemblies.
4. Run `kp2a e2e` for the first-run/database-creation smoke check. Each invocation creates a new AVD, wipes its data, disables snapshots, allocates separate emulator ports, starts a private ADB server and waits for Android to finish booting. It installs only on that emulator, then destroys the emulator and temporary AVD on exit.
5. For task-specific behavior, write a repeatable script and run `kp2a e2e -- python3 path/to/check.py`. The child inherits `ANDROID_SERIAL`, `ANDROID_ADB_SERVER_PORT`, `ADB_SERVER_SOCKET`, `KP2A_E2E_PACKAGE` and `KP2A_E2E_ARTIFACTS`. Use `adb -s "$ANDROID_SERIAL"` in that child; the inherited server socket directs it to this run's private server. Check visible UI state and resulting behavior, not just a successful launch or command exit.
6. For interactive investigation, use `kp2a e2e --gui -- bash`. Keep all adb interaction inside that child shell. Exit to stop and remove the isolated emulator. Supply `--apk /absolute/path/to/app-Signed.apk` to test a particular build.
7. Inspect `.dev/e2e/run-*/`: `emulator.log`, `logcat.txt`, `screen.png`, and (for the default smoke test) UI hierarchy XML and launch output. Report which APK and behavior were tested, results, and artifact location. Record a blocker honestly if build, boot or assertions fail.

Every behavior-test session must start a **new isolated emulator** through this runner. Do not attach to existing emulators or physical devices, reuse AVD state, run a global `adb kill-server`, or use an unqualified adb command outside the runner's child environment. Use synthetic databases and credentials only. Add task-specific assertions to the scripted checks when needed; the default smoke test covers only first run and opening the creation form.
