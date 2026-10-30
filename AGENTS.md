# Repository instructions

## Build and test

Use `nix develop` on x86_64 Linux for the Android SDK/NDK, JDK and .NET environment. See [the development guide](docs/development.md) for setup, unit tests and APK builds.

## Skills

- [Android E2E testing](.agents/skills/android-e2e/SKILL.md): use for Android behavior checks, UI regressions and manual emulator testing. Every test session must start a new isolated emulator with disposable AVD data and a private ADB server through `kp2a e2e`. Never target an existing emulator or physical device.
