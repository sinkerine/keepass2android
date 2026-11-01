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

using System.Security.Cryptography;
using System.Text;

namespace keepass2android.KeeShare;

public static class KeeShareTreeFingerprint
{
  public static string Compute(IEnumerable<(string Uuid, string Parent, long LastMod, long LocChanged, int History)> items)
  {
    using var bytes = new MemoryStream();
    using (var writer = new BinaryWriter(bytes, Encoding.UTF8, leaveOpen: true))
    {
      foreach (var item in items.OrderBy(i => i.Uuid, StringComparer.Ordinal)
                 .ThenBy(i => i.Parent, StringComparer.Ordinal).ThenBy(i => i.LastMod)
                 .ThenBy(i => i.LocChanged).ThenBy(i => i.History))
      {
        writer.Write(item.Uuid);
        writer.Write(item.Parent);
        writer.Write(item.LastMod);
        writer.Write(item.LocChanged);
        writer.Write(item.History);
      }
    }
    return Convert.ToHexString(SHA256.HashData(bytes.ToArray()));
  }
}
