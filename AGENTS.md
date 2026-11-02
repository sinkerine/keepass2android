# Repository instructions

## Build and test

Use `nix develop` on x86_64 Linux for the Android SDK/NDK, JDK and .NET environment. See [the development guide](docs/development.md) for setup, unit tests and APK builds.

## Local release signing

The local release keystore is `/home/sinkerine/.local/share/keepass2android/signing/release.keystore`, alias `kp2a`. Its password is in `/home/sinkerine/.local/share/keepass2android/signing/release.password`; never print it or commit signing material. The directory has mode 700 and the key/password files have mode 600. Preserve and back up both files to retain the signing identity for updates; do not regenerate or overwrite them. This is a local signing identity, distinct from the upstream app's certificate.

Run `nix develop --command kp2a release` for a signed online Release APK. Output: `src/keepass2android-app/bin/Release/net9.0-android/publish/keepass2android.keepass2android-Signed.apk`. Verify the APK signature after building. Do not run an emulator check for release builds unless the user explicitly requests one. See the repository release skill below.

## Skills

- [Android release APK](.agents/skills/android-release/SKILL.md): use to build and verify a local signed release APK with the existing signing key.
- [Android E2E testing](.agents/skills/android-e2e/SKILL.md): use for Android behavior checks, UI regressions and manual emulator testing. Every test session must start a new isolated emulator with disposable AVD data and a private ADB server through `kp2a e2e`. Never target an existing emulator or physical device.
