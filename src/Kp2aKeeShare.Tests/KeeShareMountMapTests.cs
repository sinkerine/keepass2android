// This file is part of Keepass2Android, Copyright 2025 Philipp Crocoll.
//
//   Keepass2Android is free software: you can redistribute it and/or modify
//   it under the terms of the GNU General Public License as published by
//   the Free Software Foundation, either version 3 of the License, or
//   (at your option) any later version.
//
//   Keepass2Android is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//   GNU General Public License for more details.
//
//   You should have received a copy of the GNU General Public License
//   along with Keepass2Android.  If not, see <http://www.gnu.org/licenses/>.

using keepass2android.KeeShare;

namespace Kp2aKeeShare.Tests;

public class KeeShareMountMapTests
{
  [Fact]
  public void CodecRoundTripPreservesUnicodeAndSerializedIocVerbatim()
  {
    var map = KeeShareMountMap.Decode(null).With(new("/mnt/共享", "ioc\twith\ncredentials:p@ss"));
    Assert.Equal("L21udC/lhbHkuqs=\taW9jCXdpdGgKY3JlZGVudGlhbHM6cEBzcw==", map.Encode());
    Assert.Equal(map.Mounts, KeeShareMountMap.Decode(map.Encode()).Mounts);
    Assert.Empty(map.Without("/mnt/共享").Mounts);
  }

  [Theory]
  [InlineData("\n")]
  [InlineData("\r\n\r\n")]
  public void CodecToleratesTrailingEmptyLines(string ending)
  {
    var map = KeeShareMountMap.Decode(null).With(new("/mnt/nas", "folder-ioc"));
    Assert.Equal(map.Mounts, KeeShareMountMap.Decode(map.Encode() + ending).Mounts);
  }

  [Theory]
  [InlineData(null)]
  [InlineData("")]
  [InlineData("bad")]
  [InlineData("!\t!")]
  [InlineData("L21udA==\t/w==")]
  [InlineData("L21udA==\t")]
  [InlineData("L21udA==\taW9j\nbad")]
  public void InvalidCodecReturnsEmpty(string? value) => Assert.Empty(KeeShareMountMap.Decode(value).Mounts);

  [Fact]
  public void LongestPrefixAndBoundaryMatching()
  {
    var map = KeeShareMountMap.Decode(null).With(new("/mnt/nas", "nas")).With(new("/mnt/nas/team/", "team"));
    Assert.True(map.TryMatch("/mnt/nas/team/a.kdbx", out var mount, out var remaining));
    Assert.Equal("team", mount.SerializedFolderIoc);
    Assert.Equal(new[] { "a.kdbx" }, remaining);
    Assert.True(map.TryMatch("/mnt/nas/x", out mount, out remaining));
    Assert.Equal("nas", mount.SerializedFolderIoc);
    Assert.Equal(new[] { "x" }, remaining);
    Assert.True(map.TryMatch("/mnt/nas", out _, out remaining));
    Assert.Empty(remaining);
    Assert.False(map.TryMatch("/mnt/nas2/x", out _, out _));
    Assert.False(map.TryMatch("/mnt/NAS/x", out _, out _));
    Assert.True(KeeShareMountMap.Decode(null).With(new("/", "root")).TryMatch("/file", out _, out remaining));
    Assert.Equal(new[] { "file" }, remaining);
  }

  [Fact]
  public void SmbMountPrefixPreservesSchemeAndSegmentBoundary()
  {
    var map = KeeShareMountMap.Decode(null).With(new("smb://nas/share", "folder"));
    Assert.True(map.TryMatch("smb://nas/share/team.kdbx", out var mount, out var segments));
    Assert.Equal("folder", mount.SerializedFolderIoc);
    Assert.Equal(new[] { "team.kdbx" }, segments);
    Assert.False(map.TryMatch("smb://nas/share2/team.kdbx", out _, out _));
  }

  [Theory]
  [InlineData("Z:\\NAS", "z:/nas/TEAM.kdbx")]
  [InlineData("\\\\HOST\\Share", "//host/share/TEAM.kdbx")]
  public void WindowsPrefixesMatchAndReplaceIgnoringCase(string prefix, string path)
  {
    var map = KeeShareMountMap.Decode(null).With(new(prefix, "old")).With(new(prefix.ToLowerInvariant(), "new"));
    Assert.Single(map.Mounts);
    Assert.True(map.TryMatch(path, out var mount, out var remaining));
    Assert.Equal("new", mount.SerializedFolderIoc);
    Assert.Equal(new[] { "TEAM.kdbx" }, remaining);
    Assert.Empty(map.Without(prefix.ToUpperInvariant()).Mounts);
  }

  [Fact]
  public void DerivedUncMappingResolvesSiblingsWithoutMatchingUnrelatedUnixPaths()
  {
    Assert.True(KeeShareMountMap.TryDerive(@"\\nas\share\keeshare\team.kdbx",
      KeeSharePath.Segments("smb://nas/share/keeshare/team.kdbx"), out var prefix, out var steps));
    Assert.Equal(2, steps);
    var map = KeeShareMountMap.Decode(null).With(new(prefix, "share-folder-ioc"));
    Assert.True(map.TryMatch("//nas/share/other.kdbx", out var mount, out var remaining));
    Assert.Equal("share-folder-ioc", mount.SerializedFolderIoc);
    Assert.Equal(new[] { "other.kdbx" }, remaining);
    Assert.False(map.TryMatch("/unrelated/other.kdbx", out _, out _));
    Assert.False(map.TryMatch("//nas/other/other.kdbx", out _, out _));
  }

  [Theory]
  [InlineData("/mnt/nas/keeshare/team.kdbx", "smb://host/share/keeshare/team.kdbx", true, "/mnt/nas", 2)]
  [InlineData("/mnt/nas/keeshare/team.kdbx", "smb://host/share/other/team.kdbx", true, "/mnt/nas/keeshare", 1)]
  [InlineData("/mnt/nas/keeshare/team.kdbx", "smb://host/share/keeshare/other.kdbx", false, "", 0)]
  [InlineData("Z:\\NAS\\KeeShare\\TEAM.KDBX", "smb://host/share/keeshare/team.kdbx", true, "Z:/NAS", 2)]
  [InlineData("/mnt/nas/team.kdbx", "smb://host/share/TEAM.KDBX", false, "", 0)]
  [InlineData("/team.kdbx", "smb://host/share/team.kdbx", true, "/", 1)]
  [InlineData("smb://nas/share/team.kdbx", "smb://other/share/team.kdbx", true, "smb://nas/share", 1)]
  [InlineData("smb://nas/share/keeshare/team.kdbx", "smb://nas/share/keeshare/team.kdbx", true, "smb://nas/share", 2)]
  [InlineData("\\\\nas\\share\\keeshare\\team.kdbx", "smb://nas/share/keeshare/team.kdbx", true, "//nas/share", 2)]
  [InlineData("//nas/share/keeshare/team.kdbx", "smb://nas/share/keeshare/team.kdbx", true, "//nas/share", 2)]
  [InlineData("//nas/share/keeshare/TEAM.KDBX", "smb://nas/share/KEESHARE/team.kdbx", true, "//nas/share", 2)]
  [InlineData("/mnt/share/keeshare/team.kdbx", "smb://nas/share/keeshare/team.kdbx", true, "/mnt/share", 2)]
  [InlineData("//nas/share/team.kdbx", "smb://nas/share/team.kdbx", true, "//nas/share", 1)]
  [InlineData("//nas/share", "smb://other/share", false, "", 0)]
  [InlineData("/mnt/share", "smb://nas/share", false, "", 0)]
  [InlineData("Z:\\team.kdbx", "smb://nas/share/team.kdbx", true, "Z:", 1)]
  [InlineData("relative/team.kdbx", "smb://host/share/team.kdbx", false, "", 0)]
  [InlineData("/mnt/../team.kdbx", "smb://host/share/team.kdbx", false, "", 0)]
  public void DeriveUsesLongestTrailingRun(string reference, string picked, bool expected, string prefix, int steps)
  {
    Assert.Equal(expected, KeeShareMountMap.TryDerive(reference, KeeSharePath.Segments(picked), out var actualPrefix, out var actualSteps));
    Assert.Equal(prefix, actualPrefix);
    Assert.Equal(steps, actualSteps);
  }
}
