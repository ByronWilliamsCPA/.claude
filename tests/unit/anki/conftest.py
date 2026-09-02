"""Shared fixtures: a fake AnkiConnect server and an in-memory stub client."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from claude_config.anki.connect import AnkiConnectClient


class FakeAnki:
    """In-memory stand-in for AnkiConnectClient, recording what it was asked."""

    def __init__(self, decks=None, notes=None, version=6, supports=True):
        self.decks = list(decks or ["Ariannah"])
        self.notes = list(notes or [])
        self.version = version
        self._supports = supports
        self.added = []
        self.synced = False
        self.created = []
        self.exported = []
        self.export_result = True

    def preflight(self):
        return self.version

    def supports(self, action):
        return self._supports

    def deck_names(self):
        return list(self.decks)

    def create_deck(self, deck):
        self.created.append(deck)
        self.decks.append(deck)

    def find_notes(self, query):
        self.last_query = query
        return list(range(len(self.notes)))

    def notes_info(self, note_ids):
        return [
            {"noteId": i, "fields": {"Front": {"value": self.notes[i], "order": 0}}}
            for i in note_ids
        ]

    def add_notes(self, notes):
        self.added.extend(notes)
        return [1000 + i for i, _ in enumerate(notes)]

    def sync(self):
        self.synced = True

    def export_package(self, deck, path, include_sched=True):
        self.exported.append((deck, path, include_sched))
        if self.export_result:
            with open(path, "wb") as handle:
                handle.write(b"apkg")
        return self.export_result


@pytest.fixture
def fake_anki():
    return FakeAnki()


@pytest.fixture
def anki_server():
    """Run a scripted AnkiConnect-shaped HTTP server on an ephemeral port."""
    responses = {}
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            request = json.loads(self.rfile.read(length))
            received.append(request)
            canned = responses.get(request["action"], {"result": None, "error": None})
            body = canned if isinstance(canned, str) else json.dumps(canned)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = AnkiConnectClient(host="127.0.0.1", port=server.server_address[1])
    yield client, responses, received
    server.shutdown()
    server.server_close()
