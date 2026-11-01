# Nix development and Android E2E tests

The flake supports **x86_64 Linux** with Nix flakes enabled. It pins nixpkgs in `flake.lock`, accepts the Android SDK license, and provides .NET 9 and 8, JDK 17, Android platforms 35 and 36, Build Tools 34/35/36, NDK 28.2.13676358, and Google APIs x86_64 emulator images. The `kp2a` commands run in a Linux FHS environment so downloaded .NET Android workload tools and Gradle's native dependencies can execute on NixOS too. Bubblewrap/user namespaces must be available.

```sh
nix develop
kp2a setup
kp2a test
kp2a build
kp2a e2e
```

For scripted use, run `nix develop --command kp2a test` (or `setup`, `build`, `e2e`). Use `nix run . -- -c 'kp2a setup && kp2a build && kp2a e2e'` to run a sequence inside one FHS shell.

First setup needs network access for Nix packages, NuGet/Android workloads, the Argon2 submodule and Gradle dependencies. Allow several GB for SDKs and emulator images. `kp2a setup` copies the pinned .NET SDK into `.dev/dotnet` before installing the Android workload; it never writes to the Nix store or your global .NET installation. NuGet, Gradle and .NET CLI state live under `.dev`. Workload/NuGet/Gradle downloads are not a fully offline, fixed-output Nix build. Rerun setup after changing the pinned SDK; remove `.dev/dotnet` first when deliberately switching SDK versions.

`kp2a test` runs the existing net8.0 Autofill parser suite. Additional arguments pass through to `dotnet test`. `kp2a build` builds Java and native dependencies and signs a Debug APK using the debug manifest, without requiring release signing keys or cloud credentials. Additional arguments pass through to `dotnet build`. APKs are under `src/keepass2android-app/bin/Debug/net9.0-android/`. The build embeds managed assemblies so `adb install` works without IDE fast deployment. Existing Makefile workflows remain available.

## Isolated emulator tests

Enable KVM on the host and give your user read/write access to `/dev/kvm` (typically membership in the `kvm` group; log in again after changing groups). The runner fails with a clear error if KVM is unavailable. A display is needed only with `--gui`.

`kp2a e2e` selects the newest signed Debug APK, starts a **fresh disposable Android 36 emulator**, waits for boot, installs the APK, and checks that the first-run Create database control opens a creation form. Each run has a temporary Android user directory, AVD directory, fresh writable disk, disabled snapshots, its own emulator port pair and its own ADB server. Existing devices and ADB servers are not used. The process and AVD data are removed on success or failure. Concurrent runs coordinate emulator ports using file locks.

```sh
# Test a specific APK
kp2a e2e --apk /path/to/app-Signed.apk
# Interactive investigation; exit the shell to clean up
kp2a e2e --gui -- bash
# Run additional behavior assertions on a fresh emulator
kp2a e2e -- python3 tests/e2e/my_scenario.py
```

A custom command inherits `ANDROID_SERIAL`, `ANDROID_ADB_SERVER_PORT`, `ADB_SERVER_SOCKET`, `KP2A_E2E_PACKAGE` and `KP2A_E2E_ARTIFACTS`. Within it, `adb -s "$ANDROID_SERIAL" …` targets the private server and this run's emulator. Always run custom checks through the runner. Exit nonzero when an assertion fails. The custom command owns its execution timeout; boot defaults to 240 seconds (`--boot-timeout` overrides it).

Before installing and again before starting the check, the runner waits until the guest CPU is mostly idle (`settle.txt` records the samples; `--settle-timeout` bounds the wait, 0 skips it). The emulator's ADB link can drop while the guest is saturated, as it is for about 20 seconds after boot: `adb pull` then fails and `adb exec-out cat` can exit 0 with truncated output. The runner also fails a run whose emulator exited before teardown. For large files, use `pull_verified` from `tests/e2e/adb_transfer.py`, which accepts bytes only when they match the guest's size and SHA-256 and retries a bounded number of times after reconnection. Never treat an adb exit status alone as proof of a complete transfer. `tests/e2e/adb_transfer_stress.py` measures transfer reliability on a fresh emulator.

Each run prints an artifact directory under `.dev/e2e/` containing emulator output, logcat and a screenshot, plus UI XML for the default smoke check. These can contain the synthetic data entered during testing. The repository agent skill is [Android E2E testing](../.agents/skills/android-e2e/SKILL.md).
