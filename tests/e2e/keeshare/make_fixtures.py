#!/usr/bin/env python3
"""Generate synthetic KeeShare databases for the Android E2E journey."""
import argparse
import base64
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree
from pykeepass import create_database


def set_reference(group, path, *, synchronize=False, keep_groups=False):
    """Write the KeePassXC reference directly into the group's CustomData."""
    def b64(value):
        return base64.b64encode(value).decode('ascii')

    # UUID.bytes is RFC-4122 order, matching KeePassXC's 16 raw UUID bytes.
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<KeeShare><Type><Import/>'
        + ('<Export/>' if synchronize else '')
        + '</Type><Group>' + b64(group.uuid.bytes) + '</Group>'
        + '<Path>' + b64(path.encode('utf-8')) + '</Path>'
        + '<Password>' + b64(b'share-pass') + '</Password>'
        + '<KeepGroups>' + ('True' if keep_groups else 'False')
        + '</KeepGroups></KeeShare>'
    )
    custom_data = group._element.find('CustomData')
    if custom_data is None:
        custom_data = etree.SubElement(group._element, 'CustomData')
    item = etree.SubElement(custom_data, 'Item')
    etree.SubElement(item, 'Key').text = 'KeeShare/Reference'
    etree.SubElement(item, 'Value').text = b64(xml.encode('utf-8'))


def make_fixtures(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    main = create_database(outdir / 'main.kdbx', password='main-pass')
    import_group = main.add_group(main.root_group, 'Team Import')
    set_reference(import_group, 'team-import.kdbx')
    sync_group = main.add_group(main.root_group, 'Team Sync')
    set_reference(sync_group, 'team-sync.kdbx.share', synchronize=True, keep_groups=True)
    personal_group = main.add_group(main.root_group, 'Personal')
    main.add_entry(personal_group, 'Personal Entry', 'synthetic-user', 'synthetic-pass')
    main.save()

    imported = create_database(outdir / 'team-import.kdbx', password='share-pass')
    imported.add_entry(imported.root_group, 'Imported Entry', 'synthetic-user', 'synthetic-pass')
    imported.save()

    container = BytesIO()
    synced = create_database(container, password='share-pass')
    synced.add_entry(synced.root_group, 'Remote Sync Entry', 'synthetic-user', 'synthetic-pass')
    container.seek(0)
    container.truncate()
    synced.save(container)
    with ZipFile(outdir / 'team-sync.kdbx.share', 'w', ZIP_DEFLATED) as share:
        share.writestr('container.share.kdbx', container.getvalue())
    print(f'Created KeeShare fixtures in {outdir}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('outdir', type=Path)
    args = parser.parse_args()
    make_fixtures(args.outdir)


if __name__ == '__main__':
    main()
