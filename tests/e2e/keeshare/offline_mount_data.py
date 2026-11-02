"""Dedicated synthetic KDBX fixtures and loopback WebDAV for offline/mount E2E.

The server only stores bytes; the installed Android app performs all KeeShare work.
No authentication, external binding, filesystem routing or cloud implementation.
"""
import base64
from contextlib import AbstractContextManager
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

from lxml import etree
from pykeepass import PyKeePass, create_database
from make_fixtures import set_reference

MOUNT_PREFIX = 'KP2A/KeeShare/Mounts/'
IOC_PREFIX = 'KP2A/KeeShare/Ioc/'
DESKTOP = '/mnt/synthetic'


def custom(element):
    root = element.tree.find('Meta') if isinstance(element, PyKeePass) else element._element
    return {item.findtext('Key'): item.findtext('Value')
            for item in root.findall('CustomData/Item')}


def group(db, name):
    result = db.find_groups(name=name, first=True)
    assert result is not None, 'Missing group: ' + name
    return result


def mounts(db):
    result = {}
    for key, value in custom(db).items():
        if key.startswith(MOUNT_PREFIX):
            result[key] = [tuple(base64.b64decode(field, validate=True).decode()
                                 for field in row.split('\t'))
                           for row in (value or '').splitlines()]
    return result


def parent(path, references):
    db = create_database(path, password='main-pass')
    for name in ('Team Import', 'Team Sync', 'Personal'):
        target = db.add_group(db.root_group, name)
        if name in references:
            set_reference(target, references[name])
    db.save()
    return db


def share(path, title):
    db = create_database(path, password='share-pass')
    db.add_entry(db.root_group, title, 'synthetic', 'synthetic')
    db.save()
    return path.read_bytes()


def add_marker(data, path, title):
    path.write_bytes(data)
    db = PyKeePass(path, password='share-pass')
    db.add_entry(db.root_group, title, 'synthetic', 'synthetic')
    db.save()
    return path.read_bytes()


def prepare(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    parent(outdir / 'remote-parent.kdbx', {'Team Import': 'remote-share.kdbx'})
    parent(outdir / 'local-control.kdbx', {'Team Import': 'local-share.kdbx'})
    parent(outdir / 'mount-parent.kdbx', {
        'Team Import': DESKTOP + '/team.kdbx', 'Team Sync': DESKTOP + '/peer.kdbx'})
    files = {
        '/remote-parent.kdbx': (outdir / 'remote-parent.kdbx').read_bytes(),
        '/remote-share.kdbx': share(outdir / 'remote-share.kdbx', 'Network Initial Marker'),
        '/shares/team.kdbx': share(outdir / 'team.kdbx', 'Mapped Picked Marker'),
        '/shares/peer.kdbx': share(outdir / 'peer.kdbx', 'Mapped Peer Marker'),
    }
    share(outdir / 'local-share-updated.kdbx', 'Offline Local Control Marker')
    local = create_database(outdir / 'local-share.kdbx', password='share-pass')
    local.save()
    for filename in ('remote-parent.kdbx', 'local-control.kdbx', 'mount-parent.kdbx'):
        db = PyKeePass(outdir / filename, password='main-pass')
        assert not mounts(db), 'Fixture preloads mount data'
        assert not any(key.startswith(IOC_PREFIX) for g in db.groups for key in custom(g)), \
            'Fixture preloads a device IOC'
    return files


class LoopbackDav(AbstractContextManager):
    """A byte store limited to this runner, with a durable request ledger."""
    def __init__(self, artifact):
        self.artifact = Path(artifact)
        self.lock = threading.RLock()
        self.files = {}
        self.ledger = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def log_message(self, *_args):
                pass

            def handle_one_request(self):
                # Unknown methods must enter the same ledger as supported methods.
                self.logged = False
                super().handle_one_request()

            def send_response(self, code, message=None):
                if not self.logged:
                    self.logged = True
                    with owner.lock:
                        owner.ledger.append({'sequence': len(owner.ledger), 'time': time.time(),
                            'method': self.command, 'path': self.path, 'status': code,
                            'depth': self.headers.get('Depth'),
                            'destination': self.headers.get('Destination')})
                        owner.persist()
                super().send_response(code, message)

            def respond(self, status, body=b'', content_type='application/octet-stream'):
                self.send_response(status)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Content-Type', content_type)
                self.send_header('Connection', 'close')
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(body)
                self.close_connection = True

            def read_body(self):
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 8 * 1024 * 1024:
                    raise ValueError('Unexpected fixture request size')
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError('Incomplete fixture request')
                return body

            def do_GET(self):
                with owner.lock:
                    data = owner.files.get(self.path)
                self.respond(404 if data is None else 200, data or b'')

            do_HEAD = do_GET

            def do_PROPFIND(self):
                self.read_body()
                depth = self.headers.get('Depth', '0')
                if depth not in ('0', '1'):
                    self.respond(403)
                    return
                # Only these two synthetic collections exist. No filesystem routing.
                path = self.path
                collection = path in ('/', '/shares', '/shares/')
                href = '/shares/' if path in ('/shares', '/shares/') else path
                with owner.lock:
                    files = dict(owner.files)
                if not collection and path not in files:
                    self.respond(404)
                    return
                resources = [(href, collection)]
                if collection and depth == '1':
                    if href == '/':
                        resources += [(name, False) for name in sorted(files)
                                      if name.count('/') == 1]
                        resources.append(('/shares/', True))
                    else:
                        resources += [(name, False) for name in sorted(files)
                                      if name.startswith('/shares/') and name.count('/') == 2]
                responses = []
                for name, is_collection in resources:
                    display = name.rstrip('/').rsplit('/', 1)[-1] or 'Synthetic root'
                    resource_type = '<d:collection/>' if is_collection else ''
                    size = 0 if is_collection else len(files[name])
                    responses.append(
                        '<d:response><d:href>' + escape(name) + '</d:href><d:propstat><d:prop>'
                        '<d:displayname>' + escape(display) + '</d:displayname>'
                        '<d:resourcetype>' + resource_type + '</d:resourcetype>'
                        '<d:getcontentlength>' + str(size) + '</d:getcontentlength>'
                        '<d:getlastmodified>' + formatdate(1600000000, usegmt=True) + '</d:getlastmodified>'
                        '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>')
                xml = ('<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">' +
                       ''.join(responses) + '</d:multistatus>').encode()
                self.respond(207, xml, 'application/xml')

            def do_PUT(self):
                data = self.read_body()
                # Only parent saves are writable; share files remain test-controlled inputs.
                if not (self.path == '/remote-parent.kdbx' or
                        (self.path.startswith('/remote-parent_tmp_') and self.path.endswith('.kdbx'))):
                    self.respond(403)
                    return
                owner.replace(self.path, data)
                self.respond(201)

            def do_MOVE(self):
                destination = urlsplit(self.headers.get('Destination', ''))
                if (destination.hostname not in ('127.0.0.1', '10.0.2.2') or
                        destination.port != owner.server.server_port or
                        destination.path != '/remote-parent.kdbx' or destination.query or
                        not self.path.startswith('/remote-parent_tmp_')):
                    self.respond(403)
                    return
                with owner.lock:
                    data = owner.files.pop(self.path, None)
                    if data is not None:
                        owner.files[destination.path] = data
                self.respond(404 if data is None else 204)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.base = 'http://10.0.2.2:' + str(self.server.server_port)

    def persist(self):
        self.artifact.write_text(json.dumps(self.ledger, indent=2) + '\n')

    def replace(self, path, data):
        with self.lock:
            self.files[path] = data

    def read(self, path):
        with self.lock:
            return self.files[path]

    def snapshot(self):
        with self.lock:
            self.persist()
            return list(self.ledger)

    def __enter__(self):
        self.persist()
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive(), 'Owned loopback server failed to stop'
        self.snapshot()


def self_check():
    """Exercise fixture metadata, byte updates and actual HTTP methods without Android."""
    import tempfile
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    with tempfile.TemporaryDirectory(prefix='kp2a-offline-mount-') as temporary:
        root = Path(temporary)
        files = prepare(root / 'fixtures')
        with LoopbackDav(root / 'ledger.json') as service:
            service.files.update(files)
            host = 'http://127.0.0.1:' + str(service.server.server_port)
            def request(path, method='GET', data=None, headers=None):
                with urlopen(Request(host + path, data=data, method=method, headers=headers or {})) as response:
                    return response.status, response.read()
            assert request('/remote-share.kdbx')[1] == files['/remote-share.kdbx']
            status, xml = request('/remote-parent.kdbx', 'PROPFIND', b'<propfind/>', {'Depth': '0'})
            assert status == 207 and etree.fromstring(xml).tag == '{DAV:}multistatus'
            temp = '/remote-parent_tmp_deadbeef.kdbx'
            assert request(temp, 'PUT', files['/remote-parent.kdbx'])[0] == 201
            assert request(temp, 'MOVE', headers={'Destination': host + '/remote-parent.kdbx'})[0] == 204
            assert service.read('/remote-parent.kdbx') == files['/remote-parent.kdbx']
            updated = add_marker(files['/remote-share.kdbx'], root / 'changed.kdbx', 'Online Recovery Marker')
            service.replace('/remote-share.kdbx', updated)
            assert request('/remote-share.kdbx')[1] == updated
            assert [row['method'] for row in service.snapshot()] == ['GET', 'PROPFIND', 'PUT', 'MOVE', 'GET']
            ns = {'d': 'DAV:'}
            def propfind(path, depth):
                status, xml = request(path, 'PROPFIND', b'<propfind/>', {'Depth': str(depth)})
                assert status == 207
                responses = etree.fromstring(xml).findall('d:response', ns)
                result = {}
                for response in responses:
                    href = response.findtext('d:href', namespaces=ns)
                    assert response.findtext('d:propstat/d:status', namespaces=ns) == 'HTTP/1.1 200 OK'
                    prop = response.find('d:propstat/d:prop', ns)
                    result[href] = {
                        'name': prop.findtext('d:displayname', namespaces=ns),
                        'collection': prop.find('d:resourcetype/d:collection', ns) is not None,
                        'size': int(prop.findtext('d:getcontentlength', namespaces=ns))}
                    assert prop.findtext('d:getlastmodified', namespaces=ns)
                assert len(result) == len(responses), 'Duplicate response href'
                return result
            root0 = propfind('/', 0)
            assert set(root0) == {'/'} and root0['/']['collection']
            root1 = propfind('/', 1)
            assert set(root1) == {'/', '/shares/', '/remote-parent.kdbx', '/remote-share.kdbx'}
            assert root1['/shares/']['collection'] and root1['/shares/']['name'] == 'shares'
            assert root1['/remote-share.kdbx'] == {
                'name': 'remote-share.kdbx', 'collection': False, 'size': len(updated)}
            for folder in ('/shares', '/shares/'):
                folder0 = propfind(folder, 0)
                assert set(folder0) == {'/shares/'} and folder0['/shares/']['collection']
                folder1 = propfind(folder, 1)
                assert set(folder1) == {'/shares/', '/shares/team.kdbx', '/shares/peer.kdbx'}
                for filename in ('team.kdbx', 'peer.kdbx'):
                    assert folder1['/shares/' + filename] == {
                        'name': filename, 'collection': False, 'size': len(files['/shares/' + filename])}
            assert propfind('/shares/peer.kdbx', 1) == {
                '/shares/peer.kdbx': {'name': 'peer.kdbx', 'collection': False,
                                      'size': len(files['/shares/peer.kdbx'])}}
            for missing in ('/missing', '/shares/missing.kdbx', '/shares/nested/'):
                for depth in (0, 1):
                    try:
                        propfind(missing, depth)
                    except HTTPError as error:
                        assert error.code == 404
                    else:
                        raise AssertionError('Nonexisting fixture path did not return404')
            try:
                propfind('/', 'infinity')
            except HTTPError as error:
                assert error.code == 403
            else:
                raise AssertionError('Unbounded depth unexpectedly supported')
            print('PASS real HTTP root/shares Depth0/1, collection types, immediate child href/name/size, file response, missing404, unbounded403')
            assert service.server.server_address[0] == '127.0.0.1'
            print('PASS fixture metadata, no seeded device/mount keys, real GET/PROPFIND/PUT/MOVE ledger, marker update, loopback binding')
        print('PASS owned server thread cleanup')


if __name__ == '__main__':
    self_check()
