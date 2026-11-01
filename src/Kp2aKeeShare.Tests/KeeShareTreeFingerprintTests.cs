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

public class KeeShareTreeFingerprintTests
{
  [Fact]
  public void FingerprintIsOrderIndependentAndIncludesEveryField()
  {
    (string Uuid, string Parent, long LastMod, long LocChanged, int History) item = ("01", "root", 10, 20, 1);
    var second = ("02", "01", 30L, 40L, 0);
    var expected = KeeShareTreeFingerprint.Compute(new[] { item, second });
    Assert.Equal(64, expected.Length);
    Assert.Equal(expected, KeeShareTreeFingerprint.Compute(new[] { second, item }));
    foreach (var changed in new[] { item with { Uuid = "03" }, item with { Parent = "other" }, item with { LastMod = 11 }, item with { LocChanged = 21 }, item with { History = 2 } })
      Assert.NotEqual(expected, KeeShareTreeFingerprint.Compute(new[] { changed, second }));
    Assert.NotEqual(expected, KeeShareTreeFingerprint.Compute(new[] { item }));
    Assert.Equal("E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855", KeeShareTreeFingerprint.Compute([]));
  }
}
