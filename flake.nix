{
  description = "Keepass2Android build, unit test and isolated Android E2E environment";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; config = { allowUnfree = true; android_sdk.accept_license = true; }; };
    android = pkgs.androidenv.composeAndroidPackages {
      platformVersions = [ "35" "36" ];
      buildToolsVersions = [ "34.0.0" "35.0.0" "36.0.0" ];
      includeNDK = true;
      ndkVersions = [ "28.2.13676358" ];
      includeEmulator = true;
      includeSystemImages = true;
      systemImageTypes = [ "google_apis" ];
      abiVersions = [ "x86_64" ];
      includeSources = false;
      includeCmake = false;
    };
    dotnet = pkgs.dotnetCorePackages.combinePackages [ pkgs.dotnetCorePackages.sdk_9_0 pkgs.dotnetCorePackages.sdk_8_0 ];
    env = pkgs.buildFHSEnv {
      name = "kp2a-dev";
      targetPkgs = p: [ dotnet android.androidsdk p.jdk17 p.git p.gnumake (p.python3.withPackages (ps: [ ps.pykeepass ])) p.curl p.unzip p.zip p.which p.file p.procps p.util-linux p.bash p.coreutils p.findutils p.gnugrep p.gnused p.zlib p.icu p.openssl p.stdenv.cc.cc.lib p.libGL p.alsa-lib p.nss p.nspr p.expat p.libxkbcommon p.xorg.libX11 p.xorg.libxcb p.xorg.libXext p.xorg.libXdamage p.xorg.libXfixes p.xorg.libXcomposite p.xorg.libXrandr p.xorg.libXi p.xorg.libXtst ];
      profile = ''
        export KP2A_IN_FHS=1
        export KP2A_NIX_DOTNET=${dotnet}/share/dotnet
        export ANDROID_HOME=${android.androidsdk}/libexec/android-sdk
        export ANDROID_SDK_ROOT="$ANDROID_HOME"
        export ANDROID_NDK_ROOT="$ANDROID_HOME/ndk/28.2.13676358"
        export JAVA_HOME=${pkgs.jdk17.home}
        export PATH="$ANDROID_HOME/build-tools/36.0.0:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_NDK_ROOT:$PATH"
        export GRADLE_OPTS="-Dorg.gradle.project.android.aapt2FromMavenOverride=$ANDROID_HOME/build-tools/36.0.0/aapt2 ''${GRADLE_OPTS:-}"
        export DOTNET_CLI_TELEMETRY_OPTOUT=1
        export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
        export DOTNET_NOLOGO=1
        export KP2A_ROOT="$(git rev-parse --show-toplevel)"
        export DOTNET_ROOT="$KP2A_ROOT/.dev/dotnet"
        export DOTNET_CLI_HOME="$KP2A_ROOT/.dev/dotnet-home"
        export NUGET_PACKAGES="$KP2A_ROOT/.dev/nuget"
        export GRADLE_USER_HOME="$KP2A_ROOT/.dev/gradle"
        export PATH="$DOTNET_ROOT:$KP2A_ROOT/scripts:$PATH"
      '';
      runScript = "bash";
    };
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = [ (pkgs.writeShellScriptBin "kp2a" ''
        exec ${env}/bin/kp2a-dev -c 'exec "$@"' bash "$(git rev-parse --show-toplevel)/scripts/kp2a" "$@"
      '') pkgs.git (pkgs.python3.withPackages (ps: [ ps.pykeepass ])) ];

    };
    packages.${system}.default = env;
  };
}
