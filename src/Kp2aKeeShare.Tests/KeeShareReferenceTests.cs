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
using System.Xml.Linq;
using keepass2android.KeeShare;

namespace Kp2aKeeShare.Tests;

public class KeeShareReferenceTests
{
  // Fixed KeePassXC wire-format fixtures: UUID 00112233-4455-6677-8899-aabbccddeeff.
  public static IEnumerable<object[]> GoldenReferences()
  {
    // Qt QXmlStreamWriter style: indented output, no encoding in the declaration.
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIj8+CjxLZWVTaGFyZT4KICAgIDxUeXBlPgogICAgICAgIDxJbXBvcnQvPgogICAgICAgIDxFeHBvcnQvPgogICAgPC9UeXBlPgogICAgPEdyb3VwPkFCRWlNMFJWWm5lSW1hcTd6TjN1L3c9PTwvR3JvdXA+CiAgICA8UGF0aD5kR1ZoYlM1clpHSjQ8L1BhdGg+CiAgICA8UGFzc3dvcmQ+YzJWamNtVjA8L1Bhc3N3b3JkPgogICAgPEtlZXBHcm91cHM+VHJ1ZTwvS2VlcEdyb3Vwcz4KPC9LZWVTaGFyZT4K", KeeShareType.Synchronize, "team.kdbx", "secret", true };
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEtlZVNoYXJlPjxUeXBlPjxJbXBvcnQvPjwvVHlwZT48R3JvdXA+QUJFaU0wUlZabmVJbWFxN3pOM3Uvdz09PC9Hcm91cD48UGF0aD5kR1ZoYlM1clpHSjQ8L1BhdGg+PFBhc3N3b3JkPmMyVmpjbVYwPC9QYXNzd29yZD48S2VlcEdyb3Vwcz5UcnVlPC9LZWVwR3JvdXBzPjwvS2VlU2hhcmU+", (KeeShareType)1, "team.kdbx", "secret", true };
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEtlZVNoYXJlPjxUeXBlPjxFeHBvcnQvPjwvVHlwZT48R3JvdXA+QUJFaU0wUlZabmVJbWFxN3pOM3Uvdz09PC9Hcm91cD48UGF0aD5kR1ZoYlM1clpHSjQ8L1BhdGg+PFBhc3N3b3JkPmMyVmpjbVYwPC9QYXNzd29yZD48S2VlcEdyb3Vwcz5GYWxzZTwvS2VlcEdyb3Vwcz48L0tlZVNoYXJlPg==", (KeeShareType)2, "team.kdbx", "secret", false };
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEtlZVNoYXJlPjxUeXBlPjxJbXBvcnQvPjxFeHBvcnQvPjwvVHlwZT48R3JvdXA+QUJFaU0wUlZabmVJbWFxN3pOM3Uvdz09PC9Hcm91cD48UGF0aD5kR1ZoYlM1clpHSjQ8L1BhdGg+PFBhc3N3b3JkPmMyVmpjbVYwPC9QYXNzd29yZD48S2VlcEdyb3Vwcz5UcnVlPC9LZWVwR3JvdXBzPjwvS2VlU2hhcmU+", (KeeShareType)3, "team.kdbx", "secret", true };
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEtlZVNoYXJlPjxUeXBlPjxJbXBvcnQvPjwvVHlwZT48R3JvdXA+QUJFaU0wUlZabmVJbWFxN3pOM3Uvdz09PC9Hcm91cD48UGF0aD5iMnhrTG10a1luZz08L1BhdGg+PFBhc3N3b3JkPmMyVmpjbVYwPC9QYXNzd29yZD48L0tlZVNoYXJlPg==", (KeeShareType)1, "old.kdbx", "secret", false };
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEtlZVNoYXJlPjxUeXBlPjxFeHBvcnQvPjwvVHlwZT48R3JvdXA+QUJFaU0wUlZabmVJbWFxN3pOM3Uvdz09PC9Hcm91cD48UGF0aD5aVzF3ZEhrdWEyUmllQT09PC9QYXRoPjxQYXNzd29yZD48L1Bhc3N3b3JkPjxLZWVwR3JvdXBzPkZhbHNlPC9LZWVwR3JvdXBzPjwvS2VlU2hhcmU+", (KeeShareType)2, "empty.kdbx", "", false };
    yield return new object[] { "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEtlZVNoYXJlPjxUeXBlPjxJbXBvcnQvPjxFeHBvcnQvPjwvVHlwZT48R3JvdXA+QUJFaU0wUlZabmVJbWFxN3pOM3Uvdz09PC9Hcm91cD48UGF0aD41WVd4NUxxckw4T3BjWFZwY0dYd241U1JMbXRrWW5nPTwvUGF0aD48UGFzc3dvcmQ+Y01Pa2MzTT08L1Bhc3N3b3JkPjxLZWVwR3JvdXBzPlRydWU8L0tlZXBHcm91cHM+PC9LZWVTaGFyZT4=", (KeeShareType)3, "共享/équipe🔑.kdbx", "päss", true };
  }

  [Theory]
  [MemberData(nameof(GoldenReferences))]
  public void DecodeGoldenReference(string encoded, KeeShareType type, string path, string password, bool keep)
  {
    Assert.True(KeeShareReferenceCodec.TryDecode(encoded, out var reference));
    Assert.Equal(type, reference.Type);
    Assert.Equal(path, reference.Path);
    Assert.Equal(password, reference.Password);
    Assert.Equal(keep, reference.KeepGroups);
    Assert.Equal(Convert.FromHexString("00112233445566778899AABBCCDDEEFF"), reference.GroupUuid);
    Assert.True(reference.IsValid);
    Assert.Equal((type & KeeShareType.Import) != 0, reference.IsImporting);
    Assert.Equal((type & KeeShareType.Export) != 0, reference.IsExporting);
  }

  [Theory]
  [MemberData(nameof(GoldenReferences))]
  public void RoundTripAndEncodedXml(string encoded, KeeShareType type, string path, string password, bool keep)
  {
    Assert.True(KeeShareReferenceCodec.TryDecode(encoded, out var reference));
    var output = KeeShareReferenceCodec.Encode(reference);
    var xml = XElement.Parse(Encoding.UTF8.GetString(Convert.FromBase64String(output)));
    Assert.Equal("KeeShare", xml.Name.LocalName);
    Assert.Equal("ABEiM0RVZneImaq7zN3u/w==", xml.Element("Group")!.Value);
    Assert.Equal(keep ? "True" : "False", xml.Element("KeepGroups")!.Value);
    Assert.Equal((type & KeeShareType.Import) != 0, xml.Element("Type")!.Element("Import") != null);
    Assert.Equal((type & KeeShareType.Export) != 0, xml.Element("Type")!.Element("Export") != null);
    Assert.True(KeeShareReferenceCodec.TryDecode(output, out var decoded));
    Assert.Equal(reference.GroupUuid, decoded.GroupUuid);
    Assert.Equal(reference with { GroupUuid = decoded.GroupUuid }, decoded);
    Assert.Equal(path, decoded.Path);
    Assert.Equal(password, decoded.Password);
  }

  [Theory]
  [InlineData(null)]
  [InlineData("")]
  [InlineData("not base64!")]
  [InlineData("/w==")]
  [InlineData("PG9vcHMvPg==")]
  public void InvalidInputReturnsFalse(string? value) => Assert.False(KeeShareReferenceCodec.TryDecode(value!, out _));

  [Theory]
  [InlineData("<KeeShare>")]
  [InlineData("<KeeShare/>")]
  [InlineData("<KeeShare><Type/><Group>AA==</Group><Path/><Password/></KeeShare>")]
  [InlineData("<KeeShare><Type/><Group>ABEiM0RVZneImaq7zN3u/w==</Group><Path>!</Path><Password/></KeeShare>")]
  [InlineData("<KeeShare><Type/><Group>ABEiM0RVZneImaq7zN3u/w==</Group><Path>/w==</Path><Password/></KeeShare>")]
  [InlineData("<!DOCTYPE KeeShare [<!ENTITY a 'x'>]><KeeShare>&a;</KeeShare>")]
  public void MalformedXmlReturnsFalse(string xml) => Assert.False(KeeShareReferenceCodec.TryDecode(Convert.ToBase64String(Encoding.UTF8.GetBytes(xml)), out _));

  [Theory]
  [InlineData("True", true)]
  [InlineData("False", false)]
  [InlineData("true", false)]
  [InlineData("TRUE", false)]
  [InlineData(" True ", false)]
  [InlineData("maybe", false)]
  [InlineData("", false)]
  public void KeepGroupsMatchesKeePassXcExactTrueValue(string value, bool expected)
  {
    var xml = "<KeeShare><Type><Import/></Type><Group>ABEiM0RVZneImaq7zN3u/w==</Group>" +
      "<Path>dGVhbS5rZGJ4</Path><Password/><KeepGroups>" + value + "</KeepGroups></KeeShare>";
    Assert.True(KeeShareReferenceCodec.TryDecode(Convert.ToBase64String(Encoding.UTF8.GetBytes(xml)), out var reference));
    Assert.Equal(expected, reference.KeepGroups);
  }

  [Theory]
  [InlineData(KeeShareType.Inactive, false, false)]
  [InlineData(KeeShareType.Import, true, false)]
  [InlineData(KeeShareType.Export, false, true)]
  [InlineData(KeeShareType.Synchronize, true, true)]
  public void EmptyPathPreservesDirectionWithoutChangingValidity(KeeShareType type, bool importing, bool exporting)
  {
    var reference = new KeeShareReference(type, new byte[16], "", "", false);
    Assert.True(KeeShareReferenceCodec.TryDecode(KeeShareReferenceCodec.Encode(reference), out var decoded));
    Assert.Equal("", decoded.Path);
    Assert.False(decoded.IsValid);
    Assert.Equal(importing, decoded.IsImporting);
    Assert.Equal(exporting, decoded.IsExporting);
  }

  [Fact]
  public void InactiveAndEmptyPathsAreNotValidAndUnknownElementsAreIgnored()
  {
    var xml = "<KeeShare><Unknown>future</Unknown><Type/><Group>ABEiM0RVZneImaq7zN3u/w==</Group><Path/><Password/></KeeShare>";
    Assert.True(KeeShareReferenceCodec.TryDecode(Convert.ToBase64String(Encoding.UTF8.GetBytes(xml)), out var reference));
    Assert.False(reference.IsValid);
    Assert.False(reference.IsImporting);
    Assert.False(reference.IsExporting);
    Assert.False((reference with { Type = KeeShareType.Synchronize }).IsValid);
    Assert.Throws<ArgumentException>(() => KeeShareReferenceCodec.Encode(reference with { GroupUuid = [1] }));
  }
}
