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

using System.IO.Compression;
using keepass2android.KeeShare;

namespace Kp2aKeeShare.Tests;

public class KeeShareContainerTests
{
  private static readonly byte[] Database = [0x03, 0xd9, 0xa2, 0x9a, 0x67, 0xfb, 0x4b, 0xb5];

  [Theory]
  [InlineData("file.kdbx", KeeShareContainerKind.Kdbx)]
  [InlineData("file.KDBX.SHARE", KeeShareContainerKind.Zip)]
  [InlineData("/a/file.kdbx.share", KeeShareContainerKind.Zip)]
  [InlineData("smb://host/share/a.kdbx.share", KeeShareContainerKind.Zip)]
  [InlineData("file.zip", KeeShareContainerKind.Kdbx)]
  [InlineData("file.kdbx.share.bak", KeeShareContainerKind.Kdbx)]
  public void WriteKindUsesSuffix(string path, KeeShareContainerKind expected) => Assert.Equal(expected, KeeShareContainer.KindForWrite(path));

  [Fact]
  public void WrapZipHasOnlyDatabaseAndIsDetectedByMagic()
  {
    var bytes = KeeShareContainer.WrapForWrite(Database, KeeShareContainerKind.Zip);
    using var zip = new ZipArchive(new MemoryStream(bytes));
    Assert.Equal(KeeShareContainer.ZipDatabaseEntryName, Assert.Single(zip.Entries).FullName);
    Assert.Equal(Database, KeeShareContainer.ExtractDatabase(bytes));
    Assert.Same(Database, KeeShareContainer.ExtractDatabase(Database));
    Assert.Same(Database, KeeShareContainer.WrapForWrite(Database, KeeShareContainerKind.Kdbx));
    Assert.Empty(KeeShareContainer.ExtractDatabase([]));
    Assert.Equal(new byte[] { 0x50, 0x4b, 1, 2 }, KeeShareContainer.ExtractDatabase([0x50, 0x4b, 1, 2]));
  }

  [Fact]
  public void SignatureIsIgnoredAndMissingDatabaseIsReported()
  {
    using var output = new MemoryStream();
    using (var zip = new ZipArchive(output, ZipArchiveMode.Create, true))
    {
      using (var signature = zip.CreateEntry(KeeShareContainer.ZipSignatureEntryName).Open()) signature.Write([1, 2]);
      using (var database = zip.CreateEntry(KeeShareContainer.ZipDatabaseEntryName).Open()) database.Write(Database);
    }
    Assert.Equal(Database, KeeShareContainer.ExtractDatabase(output.ToArray()));
    using var empty = new MemoryStream();
    using (new ZipArchive(empty, ZipArchiveMode.Create, true)) { }
    var error = Assert.Throws<KeeShareFormatException>(() => KeeShareContainer.ExtractDatabase(empty.ToArray()));
    Assert.Equal("zip has no container.share.kdbx", error.Message);
    Assert.Throws<InvalidDataException>(() => KeeShareContainer.ExtractDatabase([0x50, 0x4b, 3, 4]));
  }
}
