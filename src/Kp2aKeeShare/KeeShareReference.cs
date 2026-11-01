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

using System.Text;
using System.Xml;
using System.Xml.Linq;

namespace keepass2android.KeeShare;

[Flags]
public enum KeeShareType { Inactive = 0, Import = 1, Export = 2, Synchronize = Import | Export }

public sealed record KeeShareReference(
  KeeShareType Type, byte[] GroupUuid, string Path, string Password, bool KeepGroups)
{
  public bool IsImporting => (Type & KeeShareType.Import) != 0 && Path != "";
  public bool IsExporting => (Type & KeeShareType.Export) != 0 && Path != "";
  public bool IsValid => Type != KeeShareType.Inactive && Path != "";
}

public static class KeeShareReferenceCodec
{
  public const string CustomDataKey = "KeeShare/Reference";
  private static readonly Encoding Utf8 = new UTF8Encoding(false, true);

  public static bool TryDecode(string customDataValue, out KeeShareReference reference)
  {
    reference = null!;
    if (string.IsNullOrWhiteSpace(customDataValue)) return false;
    try
    {
      using var input = new StringReader(Utf8.GetString(Convert.FromBase64String(customDataValue)));
      using var reader = XmlReader.Create(input, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null });
      var root = XElement.Load(reader);
      if (root.Name != "KeeShare") return false;
      var type = root.Element("Type");
      var group = root.Element("Group");
      var path = root.Element("Path");
      var password = root.Element("Password");
      if (type == null || group == null || path == null || password == null) return false;
      var uuid = Convert.FromBase64String(group.Value);
      if (uuid.Length != 16) return false;
      var flags = (type.Element("Import") != null ? KeeShareType.Import : 0)
        | (type.Element("Export") != null ? KeeShareType.Export : 0);
      var keep = root.Element("KeepGroups");
      reference = new KeeShareReference(flags, uuid,
        Utf8.GetString(Convert.FromBase64String(path.Value)),
        Utf8.GetString(Convert.FromBase64String(password.Value)),
        keep?.Value == "True");
      return true;
    }
    catch (Exception e) when (e is FormatException or XmlException or DecoderFallbackException or ArgumentException)
    {
      return false;
    }
  }

  public static string Encode(KeeShareReference reference)
  {
    if (reference.GroupUuid.Length != 16) throw new ArgumentException("Group UUID must contain 16 bytes.", nameof(reference));
    var root = new XElement("KeeShare",
      new XElement("Type",
        (reference.Type & KeeShareType.Import) != 0 ? new XElement("Import") : null,
        (reference.Type & KeeShareType.Export) != 0 ? new XElement("Export") : null),
      new XElement("Group", Convert.ToBase64String(reference.GroupUuid)),
      new XElement("Path", Convert.ToBase64String(Utf8.GetBytes(reference.Path))),
      new XElement("Password", Convert.ToBase64String(Utf8.GetBytes(reference.Password))),
      new XElement("KeepGroups", reference.KeepGroups ? "True" : "False"));
    return Convert.ToBase64String(Utf8.GetBytes("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + root.ToString(SaveOptions.DisableFormatting)));
  }
}
