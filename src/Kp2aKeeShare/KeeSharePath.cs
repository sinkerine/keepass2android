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

namespace keepass2android.KeeShare;

public abstract record KeeShareLocation
{
  public sealed record DeviceIoc(string SerializedIoc) : KeeShareLocation;
  public sealed record Mapped(string SerializedFolderIoc, IReadOnlyList<string> Segments) : KeeShareLocation;
  public sealed record Unc(string Host, string Share, IReadOnlyList<string> Segments) : KeeShareLocation;
  public sealed record RelativeToDatabase(IReadOnlyList<string> Segments) : KeeShareLocation;
  public sealed record NotSet : KeeShareLocation;
}

public static class KeeSharePath
{
  public const string DeviceIocKeyPrefix = "KP2A/KeeShare/Ioc/";
  public static string DeviceIocKey(string deviceId) => DeviceIocKeyPrefix + deviceId;

  public static IReadOnlyList<string> Segments(string path)
  {
    var segments = path.Replace('\\', '/').Split('/', StringSplitOptions.RemoveEmptyEntries).Where(s => s != ".").ToArray();
    if (segments.Contains("..")) throw new ArgumentException("Parent path segments are not supported.", nameof(path));
    return segments;
  }

  private static bool HasDrive(string path) => path.Length >= 2 && char.IsAsciiLetter(path[0]) && path[1] == ':';
  public static bool IsAbsolute(string path) => path.StartsWith('/') || path.StartsWith('\\') || HasDrive(path) || path.Contains("://", StringComparison.Ordinal);
  public static bool IsWindowsStyle(string path) => HasDrive(path) || path.StartsWith("\\\\", StringComparison.Ordinal) || path.StartsWith("//", StringComparison.Ordinal);

  public static KeeShareLocation Choose(string? deviceIocValue, string referencePath, KeeShareMountMap mounts)
  {
    if (!string.IsNullOrEmpty(deviceIocValue)) return new KeeShareLocation.DeviceIoc(deviceIocValue);
    try
    {
      var segments = Segments(referencePath);
      if (segments.Count == 0) return new KeeShareLocation.NotSet();
      if (mounts.TryMatch(referencePath, out var mount, out var remaining))
        return new KeeShareLocation.Mapped(mount.SerializedFolderIoc, remaining);
      if (KeeShareSmbPath.TryParseUnc(referencePath, out var host, out var share, out var uncSegments))
        return new KeeShareLocation.Unc(host, share, uncSegments);
      if (!IsAbsolute(referencePath)) return new KeeShareLocation.RelativeToDatabase(segments);
    }
    catch (ArgumentException) { }
    return new KeeShareLocation.NotSet();
  }
}
