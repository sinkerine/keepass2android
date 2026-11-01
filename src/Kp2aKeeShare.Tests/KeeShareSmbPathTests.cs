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

public class KeeShareSmbPathTests
{
  [Theory]
  [InlineData("\\\\nas\\share\\a\\b")]
  [InlineData("//nas/share/a/b")]
  [InlineData("smb://nas/share/a/b")]
  [InlineData("SMB://nas/share/a/b")]
  public void ParseThreeUncSyntaxes(string path)
  {
    Assert.True(KeeShareSmbPath.TryParseUnc(path, out var host, out var share, out var segments));
    Assert.Equal("nas", host);
    Assert.Equal("share", share);
    Assert.Equal(new[] { "a", "b" }, segments);
  }

  [Theory]
  [InlineData("//nas")]
  [InlineData("smb://")]
  [InlineData("smb://user:pass@nas/share")]
  [InlineData("//nas/share/../file")]
  [InlineData("/mnt/nas/share")]
  [InlineData("https://nas/share")]
  public void RejectInvalidUnc(string path) => Assert.False(KeeShareSmbPath.TryParseUnc(path, out _, out _, out _));

  [Fact]
  public void BorrowPreservesCredentialTextVerbatimAndRequiresSameHost()
  {
    const string db = "smb://domain;user%40name:p%3Ass%40word@NAS/db/main.kdbx";
    Assert.Equal("smb://domain;user%40name:p%3Ass%40word@nas/share/共享/team.kdbx",
      KeeShareSmbPath.BorrowCredentials(db, "nas", "share", new[] { "共享", "team.kdbx" }));
    Assert.Null(KeeShareSmbPath.BorrowCredentials(db, "other", "share", []));
    Assert.Null(KeeShareSmbPath.BorrowCredentials("smb://nas/db/main.kdbx", "nas", "share", []));
    Assert.Null(KeeShareSmbPath.BorrowCredentials("/local/main.kdbx", "nas", "share", []));
    Assert.Equal("smb://u:p@NAS/share", KeeShareSmbPath.BorrowCredentials("smb://u:p@nas/db", "NAS", "share", []));
  }
}

