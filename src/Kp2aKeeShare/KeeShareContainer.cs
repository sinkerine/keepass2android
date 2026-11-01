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

namespace keepass2android.KeeShare;

public enum KeeShareContainerKind { Kdbx, Zip }

public static class KeeShareContainer
{
  public const string ZipDatabaseEntryName = "container.share.kdbx";
  public const string ZipSignatureEntryName = "container.share.signature";

  public static KeeShareContainerKind KindForWrite(string fileNameOrPath) =>
    fileNameOrPath.EndsWith(".kdbx.share", StringComparison.OrdinalIgnoreCase) ? KeeShareContainerKind.Zip : KeeShareContainerKind.Kdbx;

  public static byte[] ExtractDatabase(byte[] containerBytes)
  {
    if (containerBytes.Length < 4 || containerBytes[0] != 0x50 || containerBytes[1] != 0x4b ||
        !((containerBytes[2] == 3 && containerBytes[3] == 4) ||
          (containerBytes[2] == 5 && containerBytes[3] == 6) ||
          (containerBytes[2] == 7 && containerBytes[3] == 8))) return containerBytes;
    using var input = new MemoryStream(containerBytes);
    using var zip = new ZipArchive(input, ZipArchiveMode.Read);
    var entry = zip.GetEntry(ZipDatabaseEntryName)
      ?? throw new KeeShareFormatException("zip has no container.share.kdbx");
    using var database = entry.Open();
    using var output = new MemoryStream();
    database.CopyTo(output);
    return output.ToArray();
  }

  public static byte[] WrapForWrite(byte[] kdbxBytes, KeeShareContainerKind kind)
  {
    if (kind == KeeShareContainerKind.Kdbx) return kdbxBytes;
    using var output = new MemoryStream();
    using (var zip = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
    using (var entry = zip.CreateEntry(ZipDatabaseEntryName).Open()) entry.Write(kdbxBytes);
    return output.ToArray();
  }
}

public sealed class KeeShareFormatException(string message) : Exception(message);
