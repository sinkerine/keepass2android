---
name: android-release
description: Build and verify a locally signed Keepass2Android Release APK using this repository's Nix environment and persistent local signing key.
---

# Local Android release APK

Use this skill only in this repository. Run commands from the repository root. Read `docs/development.md` and the local release signing section in `AGENTS.md`.

1. If the writable SDK/workload is absent, run `nix develop --command kp2a setup`.
2. Reuse `$HOME/.local/share/keepass2android/signing/release.keystore` (alias `kp2a`) and `release.password` in the same directory. Never print the password, copy signing material into the repository, or regenerate an existing identity. Only for first-time setup with neither file present, run `nix develop --command kp2a release-key`. This creates a 4096-bit RSA PKCS12 key valid for 10,000 days, with directory mode 700 and file mode 600. Preserve and back up both files; future updates require the same key. If only one file exists, stop and recover the missing file rather than replacing the identity.
3. Run `nix develop --command kp2a release`. This builds Java/native dependencies, selects `Manifests/AndroidManifest_net.xml`, publishes the online `Net` flavor in `Release` configuration, signs with file/environment password references (the key password is loaded from the local password file without printing it), verifies with `apksigner`, and prints the APK SHA-256. Extra arguments pass through to `dotnet publish`; do not override signing, flavor or configuration for a normal release.
4. The resulting APK is `src/keepass2android-app/bin/Release/net9.0-android/publish/keepass2android.keepass2android-Signed.apk`. Inspect `apksigner verify --verbose --print-certs` output and confirm its signer matches the keystore certificate (`keytool -list -v -alias kp2a -keystore "$HOME/.local/share/keepass2android/signing/release.keystore" -storepass:file "$HOME/.local/share/keepass2android/signing/release.password"`). Run these tools inside `nix run . -- -c '…'` when needed. Check package/version and absence of a debuggable application with `aapt dump badging`.
5. Skip emulator checks for release builds unless the user explicitly requests one. If requested, apply `.agents/skills/android-e2e/SKILL.md` and run `nix develop --command kp2a e2e --apk "$PWD/src/keepass2android-app/bin/Release/net9.0-android/publish/keepass2android.keepass2android-Signed.apk"`. Every run must create a fresh isolated emulator through this runner. Never install on existing devices.
6. Report the APK path, checksum, signer fingerprint and verification/test outcome. This local certificate differs from upstream releases, so it cannot update an upstream-signed installation in place. Building does not authorize publishing or uploading the APK or signing material.

The manifest symlink is ignored by Git. `kp2a build` selects the Debug manifest again. Build sequentially because Debug and Release share that symlink and Java/native outputs. Keep credentials out of logs and avoid diagnostic MSBuild logs that may capture secrets.
