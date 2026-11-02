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

public class KeeSharePathTests
{
  [Theory]
  [InlineData("/mnt/a", true, false)]
  [InlineData("\\root", true, false)]
  [InlineData("C:\\a", true, true)]
  [InlineData("z:a", true, true)]
  [InlineData("\\\\host\\share", true, true)]
  [InlineData("//host/share", true, true)]
  [InlineData("smb://host/share", true, false)]
  [InlineData("content://provider/file", true, false)]
  [InlineData("folder/file", false, false)]
  [InlineData("", false, false)]
  public void PathClassification(string path, bool absolute, bool windows)
  {
    Assert.Equal(absolute, KeeSharePath.IsAbsolute(path));
    Assert.Equal(windows, KeeSharePath.IsWindowsStyle(path));
  }

  [Fact]
  public void SegmentsNormalizeSeparatorsAndRejectParentTraversal()
  {
    Assert.Equal(new[] { "a", "b", "c" }, KeeSharePath.Segments("/a//./b\\c/"));
    Assert.Empty(KeeSharePath.Segments("./"));
    Assert.Throws<ArgumentException>(() => KeeSharePath.Segments("a/../b"));
    Assert.Equal("KP2A/KeeShare/Ioc/device", KeeSharePath.DeviceIocKey("device"));
  }

  [Theory]
  [InlineData("device", "/mnt/share/a.kdbx", "device")]
  [InlineData("device", "../invalid", "device")]
  [InlineData("device", "", "device")]
  [InlineData(null, "/mnt/share/a.kdbx", "mapped")]
  [InlineData(null, "//host/share/a.kdbx", "mapped")]
  [InlineData(null, "smb://host/share/a.kdbx", "unc")]
  [InlineData(null, "\\\\other\\share\\a.kdbx", "unc")]
  [InlineData("", "folder/a.kdbx", "relative")]
  [InlineData(null, "/elsewhere/a.kdbx", "notset")]
  [InlineData(null, "C:\\elsewhere\\a.kdbx", "notset")]
  [InlineData(null, "content://provider/a", "notset")]
  [InlineData(null, "../a.kdbx", "notset")]
  [InlineData(null, "", "notset")]
  [InlineData("", "", "notset")]
  [InlineData(null, ".", "notset")]
  public void ChooseHonorsPrecedence(string? device, string path, string expected)
  {
    var mounts = KeeShareMountMap.Decode(null).With(new("/mnt/share", "folder-ioc")).With(new("//host/share", "folder-ioc"));
    var location = KeeSharePath.Choose(device, path, mounts);
    switch (expected)
    {
      case "device": Assert.Equal(device, Assert.IsType<KeeShareLocation.DeviceIoc>(location).SerializedIoc); break;
      case "mapped":
        var mapped = Assert.IsType<KeeShareLocation.Mapped>(location);
        Assert.Equal("folder-ioc", mapped.SerializedFolderIoc);
        Assert.Equal(new[] { "a.kdbx" }, mapped.Segments);
        break;
      case "unc":
        var unc = Assert.IsType<KeeShareLocation.Unc>(location);
        Assert.Equal("share", unc.Share);
        Assert.Equal(new[] { "a.kdbx" }, unc.Segments);
        break;
      case "relative": Assert.Equal(new[] { "folder", "a.kdbx" }, Assert.IsType<KeeShareLocation.RelativeToDatabase>(location).Segments); break;
      default: Assert.IsType<KeeShareLocation.NotSet>(location); break;
    }
  }
}
