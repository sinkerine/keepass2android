#!/usr/bin/env python3
"""Check expected entry titles in a plain KDBX or zipped KeeShare container."""
import argparse
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, is_zipfile

from pykeepass import PyKeePass


class ShareVerificationError(ValueError):
    """A verifier assertion whose message is safe to show in CLI output."""


def verify_share(path, password, expected_titles, *, no_reference=False):
    # Detect the container from its contents, as KeePassXC does, not its suffix.
    if is_zipfile(path):
        with ZipFile(path) as share:
            database = PyKeePass(BytesIO(share.read('container.share.kdbx')), password=password)
    else:
        database = PyKeePass(path, password=password)
    titles = {entry.title for entry in database.entries}
    missing = set(expected_titles) - titles
    if missing:
        raise ShareVerificationError('Missing expected titles: ' + ', '.join(sorted(missing)))
    if no_reference and database.root_group._element.xpath(
        './CustomData/Item[Key="KeeShare/Reference" or starts-with(Key, "KP2A/KeeShare/")]'
    ):
        raise ShareVerificationError('Export root contains KeeShare reference or device metadata')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-reference', action='store_true',
                        help='also check that the export root has no KeeShare metadata')
    parser.add_argument('path', type=Path)
    parser.add_argument('password')
    parser.add_argument('expected_titles', nargs='+')
    args = parser.parse_args()
    try:
        verify_share(args.path, args.password, args.expected_titles,
                     no_reference=args.no_reference)
    except ShareVerificationError as error:
        parser.exit(1, f'FAIL: {error}\n')
    except Exception as error:
        # Do not include credentials or library exception text in CLI output.
        parser.exit(1, f'FAIL: share verification failed ({type(error).__name__})\n')
    print('PASS: all expected titles are present')


if __name__ == '__main__':
    main()
