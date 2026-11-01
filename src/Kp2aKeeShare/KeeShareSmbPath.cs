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

public static class KeeShareSmbPath
{
  public static bool TryParseUnc(string referencePath, out string host, out string share, out IReadOnlyList<string> segments)
  {
    host = share = "";
    segments = Array.Empty<string>();
    string path;
    if (referencePath.StartsWith("smb://", StringComparison.OrdinalIgnoreCase)) path = referencePath[6..];
    else if (referencePath.StartsWith("\\\\", StringComparison.Ordinal) || referencePath.StartsWith("//", StringComparison.Ordinal)) path = referencePath[2..];
    else return false;
    try
    {
      var parts = KeeSharePath.Segments(path);
      if (parts.Count < 2 || parts[0].Contains('@') || parts[0].Contains(':') || parts[0].Any(char.IsWhiteSpace)) return false;
      host = parts[0];
      share = parts[1];
      segments = parts.Skip(2).ToArray();
      return true;
    }
    catch (ArgumentException) { return false; }
  }

  public static string? BorrowCredentials(string dbIocPath, string host, string share, IReadOnlyList<string> segments)
  {
    if (!dbIocPath.StartsWith("smb://", StringComparison.OrdinalIgnoreCase)) return null;
    var authorityEnd = dbIocPath.IndexOf('/', 6);
    var authority = authorityEnd < 0 ? dbIocPath[6..] : dbIocPath[6..authorityEnd];
    var separator = authority.LastIndexOf('@');
    if (separator <= 0 || !string.Equals(authority[(separator + 1)..], host, StringComparison.OrdinalIgnoreCase)) return null;
    return "smb://" + authority[..(separator + 1)] + host + "/" + share +
      (segments.Count == 0 ? "" : "/" + string.Join("/", segments));
  }
}
