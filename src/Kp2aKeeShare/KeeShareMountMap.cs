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

namespace keepass2android.KeeShare;

public sealed class KeeShareMountMap
{
  public const string DatabaseCustomDataKeyPrefix = "KP2A/KeeShare/Mounts/";
  public sealed record Mount(string DesktopPrefix, string SerializedFolderIoc);
  public IReadOnlyList<Mount> Mounts { get; }

  private KeeShareMountMap(IEnumerable<Mount> mounts) => Mounts = Array.AsReadOnly(mounts.ToArray());

  public static KeeShareMountMap Decode(string? value)
  {
    var result = new KeeShareMountMap([]);
    if (string.IsNullOrEmpty(value)) return result;
    try
    {
      var utf8 = new UTF8Encoding(false, true);
      foreach (var line in value.TrimEnd('\r', '\n').Split('\n'))
      {
        var fields = line.TrimEnd('\r').Split('\t');
        if (fields.Length != 2) return new KeeShareMountMap([]);
        var prefix = utf8.GetString(Convert.FromBase64String(fields[0]));
        var ioc = utf8.GetString(Convert.FromBase64String(fields[1]));
        if (!KeeSharePath.IsAbsolute(prefix) || string.IsNullOrEmpty(ioc)) return new KeeShareMountMap([]);
        KeeSharePath.Segments(prefix);
        result = result.With(new Mount(prefix, ioc));
      }
      return result;
    }
    catch (ArgumentException) { return new KeeShareMountMap([]); }
    catch (FormatException) { return new KeeShareMountMap([]); }
  }

  public string Encode() => string.Join("\n", Mounts.Select(m =>
    Convert.ToBase64String(Encoding.UTF8.GetBytes(m.DesktopPrefix)) + "\t" +
    Convert.ToBase64String(Encoding.UTF8.GetBytes(m.SerializedFolderIoc))));

  private static string Normalize(string path)
  {
    var normalized = path.Replace('\\', '/');
    var schemeEnd = normalized.IndexOf("://", StringComparison.Ordinal);
    if (schemeEnd >= 0)
      return normalized[..(schemeEnd + 3)] + string.Join("/", KeeSharePath.Segments(normalized[(schemeEnd + 3)..]));
    var leading = normalized.StartsWith("//", StringComparison.Ordinal) ? "//" : normalized.StartsWith('/') ? "/" : "";
    return leading + string.Join("/", KeeSharePath.Segments(path));
  }

  private static StringComparison Comparison(string path) => KeeSharePath.IsWindowsStyle(path)
    ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;

  private static bool EqualPrefix(string first, string second) =>
    string.Equals(Normalize(first), Normalize(second), Comparison(first));

  public KeeShareMountMap With(Mount mount) => new(Mounts.Where(m => !EqualPrefix(m.DesktopPrefix, mount.DesktopPrefix)).Append(mount));
  public KeeShareMountMap Without(string desktopPrefix) => new(Mounts.Where(m => !EqualPrefix(m.DesktopPrefix, desktopPrefix)));

  public bool TryMatch(string referencePath, out Mount mount, out IReadOnlyList<string> remainingSegments)
  {
    mount = null!;
    remainingSegments = Array.Empty<string>();
    var path = Normalize(referencePath);
    var bestLength = -1;
    foreach (var candidate in Mounts)
    {
      var prefix = Normalize(candidate.DesktopPrefix);
      if (prefix.Length <= bestLength || !path.StartsWith(prefix, Comparison(candidate.DesktopPrefix))) continue;
      if (path.Length != prefix.Length && !prefix.EndsWith('/') && path[prefix.Length] != '/') continue;
      mount = candidate;
      remainingSegments = KeeSharePath.Segments(path[prefix.Length..]);
      bestLength = prefix.Length;
    }
    return bestLength >= 0;
  }

  // Segments retains scheme and drive markers, so neither may be matched as file names.
  // SMB display paths also retain their host and share, which form the storage root.
  private static int RootSegmentCount(IReadOnlyList<string> segments)
  {
    if (segments.Count == 0 || !segments[0].EndsWith(':')) return 0;
    if (string.Equals(segments[0], "smb:", StringComparison.OrdinalIgnoreCase)) return 3;
    return segments[0].Length == 2 ? 1 : 2;
  }

  public static bool TryDerive(string referencePath, IReadOnlyList<string> pickedSegments,
    out string desktopPrefix, out int parentSteps)
  {
    desktopPrefix = "";
    parentSteps = 0;
    if (!KeeSharePath.IsAbsolute(referencePath)) return false;
    try
    {
      var reference = KeeSharePath.Segments(referencePath);
      var referenceRootSegments = RootSegmentCount(reference);
      if (referencePath.StartsWith("//", StringComparison.Ordinal) || referencePath.StartsWith("\\\\", StringComparison.Ordinal))
        referenceRootSegments = 2;
      var referenceFileSegments = reference.Count - referenceRootSegments;
      var pickedFileSegments = pickedSegments.Count - RootSegmentCount(pickedSegments);
      var common = 0;
      while (common < referenceFileSegments && common < pickedFileSegments &&
             string.Equals(reference[reference.Count - common - 1], pickedSegments[pickedSegments.Count - common - 1], Comparison(referencePath))) common++;
      if (common == 0) return false;
      var prefix = Normalize(referencePath);
      for (var i = 0; i < common; i++)
      {
        var separator = prefix.LastIndexOf('/');
        prefix = separator == 0 ? "/" : separator > 0 ? prefix[..separator] : "";
      }
      if (prefix.Length == 0 || !KeeSharePath.IsAbsolute(prefix)) return false;
      desktopPrefix = prefix;
      parentSteps = common;
      return true;
    }
    catch (ArgumentException) { return false; }
  }
}
