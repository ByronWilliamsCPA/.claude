"""AnkiConnect HTTP client.

AnkiConnect is an Anki Desktop add-on (code ``2055492159``) that exposes the
open collection over plain HTTP on ``127.0.0.1:8765``. Anki Desktop must be
running for any call here to succeed; there is no headless mode and no cloud
endpoint. AnkiWeb is a sync service, not an API, so it cannot substitute.

The transport is :mod:`http.client` rather than :mod:`urllib.request` because
AnkiConnect is always plain HTTP on a fixed host and port. Taking host and port
instead of a URL removes the arbitrary-scheme handling that ``urllib`` would
require and keeps the request surface narrow.

#ASSUME API version 6 is current and accepts every action used here.
#VERIFY :meth:`AnkiConnectClient.preflight` reports the live version on the
    operator's machine and :meth:`AnkiConnectClient.supports` probes individual
    actions, so a version mismatch surfaces as a named error on first run
    rather than as corrupt output. Upstream docs were unreachable when this was
    written (the FooSoft repo redirects to git.sr.ht, and both sr.ht and
    foosoft.net are blocked by the egress proxy), so the version floor below is
    unconfirmed against a primary source.
"""

from __future__ import annotations

import http.client
import json
import os
from typing import Any, Final

API_VERSION: Final = 6
DEFAULT_HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 8765
DEFAULT_TIMEOUT: Final = 10.0
ADDON_CODE: Final = "2055492159"

_INSTALL_HINT: Final = (
    "Anki is not answering on {host}:{port}.\n"
    "  1. Open the Anki desktop app and leave it open.\n"
    "  2. Check the AnkiConnect add-on is installed: Tools > Add-ons.\n"
    f"     If it is missing, use Get Add-ons and paste code {ADDON_CODE},\n"
    "     then restart Anki.\n"
    "  3. Run this command again."
)


class AnkiError(Exception):
    """Base class for every AnkiConnect failure."""


class AnkiUnreachableError(AnkiError):
    """Anki Desktop is not running, or AnkiConnect is not installed."""


class AnkiActionError(AnkiError):
    """AnkiConnect accepted the request but reported an error."""


class AnkiProtocolError(AnkiError):
    """AnkiConnect returned a response that could not be understood."""


class AnkiConnectClient:
    """Minimal AnkiConnect client covering the card-pipeline actions.

    Args:
        host (str): Interface AnkiConnect is bound to.
        port (int): TCP port AnkiConnect listens on.
        api_key (str | None): Value for the add-on's optional ``apiKey``
            setting. Omitted from the payload when ``None``.
        timeout (float): Per-request socket timeout in seconds.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._api_key = api_key

    @classmethod
    def from_env(cls) -> AnkiConnectClient:
        """Build a client from ``ANKI_CONNECT_*`` environment variables.

        Reads ``ANKI_CONNECT_HOST``, ``ANKI_CONNECT_PORT`` and
        ``ANKI_CONNECT_API_KEY``, falling back to the add-on defaults.

        Returns:
            AnkiConnectClient: Client configured from the environment.
        """
        return cls(
            host=os.environ.get("ANKI_CONNECT_HOST", DEFAULT_HOST),
            port=int(os.environ.get("ANKI_CONNECT_PORT", DEFAULT_PORT)),
            api_key=os.environ.get("ANKI_CONNECT_API_KEY") or None,
        )

    def invoke(self, action: str, **params: Any) -> Any:
        """Call a single AnkiConnect action.

        Propagates :class:`AnkiUnreachableError` from the transport and
        :class:`AnkiActionError` or :class:`AnkiProtocolError` from response
        handling.

        Args:
            action (str): AnkiConnect action name, for example ``addNotes``.
            **params (Any): Action parameters, passed through as ``params``.

        Returns:
            Any: The ``result`` member of the AnkiConnect response.
        """
        payload: dict[str, Any] = {"action": action, "version": API_VERSION}
        if params:
            payload["params"] = params
        if self._api_key is not None:
            payload["key"] = self._api_key
        body = self._post(json.dumps(payload))
        return self._unwrap(action, body)

    def _post(self, body: str) -> str:
        """Send one JSON request body and return the raw response text.

        Args:
            body (str): Serialized JSON request payload.

        Returns:
            str: Raw response body decoded as UTF-8.

        Raises:
            AnkiUnreachableError: The socket could not be established or the
                request did not complete.
        """
        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            conn.request(
                "POST",
                "/",
                body=body.encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            return conn.getresponse().read().decode("utf-8")
        except (OSError, http.client.HTTPException) as exc:
            hint = _INSTALL_HINT.format(host=self.host, port=self.port)
            raise AnkiUnreachableError(hint) from exc
        finally:
            conn.close()

    @staticmethod
    def _unwrap(action: str, body: str) -> Any:
        """Validate the response envelope and return its ``result``.

        Args:
            action (str): Action name, used only for error messages.
            body (str): Raw response body.

        Returns:
            Any: The ``result`` member of the response.

        Raises:
            AnkiActionError: The response carried a non-null ``error``.
            AnkiProtocolError: The body was not a JSON object with ``result``.
        """
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            msg = f"{action}: Anki sent a reply that was not JSON: {body[:200]!r}"
            raise AnkiProtocolError(msg) from exc
        if not isinstance(parsed, dict) or "result" not in parsed:
            msg = f"{action}: Anki reply had no 'result' field: {parsed!r}"
            raise AnkiProtocolError(msg)
        error = parsed.get("error")
        if error is not None:
            msg = f"{action}: Anki refused the request: {error}"
            raise AnkiActionError(msg)
        return parsed["result"]

    def preflight(self) -> int:
        """Confirm Anki is reachable and report its API version.

        Propagates :class:`AnkiUnreachableError` when Anki Desktop is not
        accepting connections.

        Returns:
            int: API version reported by the add-on.

        Raises:
            AnkiProtocolError: The version was not an integer.
        """
        version = self.invoke("version")
        if not isinstance(version, int):
            msg = f"version: expected an integer, got {version!r}"
            raise AnkiProtocolError(msg)
        return version

    def supports(self, action: str) -> bool:
        """Report whether the running add-on exposes ``action``.

        Args:
            action (str): AnkiConnect action name to probe.

        Returns:
            bool: True when the add-on lists the action.
        """
        try:
            reflected = self.invoke("apiReflect", scopes=["actions"], actions=[action])
        except AnkiError:
            return False
        if isinstance(reflected, dict):
            return action in (reflected.get("actions") or [])
        return False

    def deck_names(self) -> list[str]:
        """List every deck in the open collection.

        Returns:
            list[str]: Fully qualified deck names.
        """
        return list(self.invoke("deckNames"))

    def create_deck(self, deck: str) -> None:
        """Create ``deck`` if it does not already exist.

        AnkiConnect treats this as idempotent and returns the deck id either
        way, so no existence check is needed first.

        Args:
            deck (str): Fully qualified deck name, ``::`` separated.
        """
        self.invoke("createDeck", deck=deck)

    def find_notes(self, query: str) -> list[int]:
        """Search the collection and return matching note ids.

        Args:
            query (str): Anki browser search string, for example ``deck:X``.

        Returns:
            list[int]: Matching note ids.
        """
        return list(self.invoke("findNotes", query=query))

    def notes_info(self, note_ids: list[int]) -> list[dict[str, Any]]:
        """Fetch field values and tags for ``note_ids``.

        Args:
            note_ids (list[int]): Note ids to look up.

        Returns:
            list[dict[str, Any]]: Note records as returned by AnkiConnect.
        """
        if not note_ids:
            return []
        return list(self.invoke("notesInfo", notes=note_ids))

    def can_add_notes(self, notes: list[dict[str, Any]]) -> list[bool]:
        """Ask Anki which notes it would accept.

        This catches exact first-field duplicates using Anki's own rules,
        which the pipeline's similarity check cannot see.

        Args:
            notes (list[dict[str, Any]]): Note payloads in ``addNotes`` shape.

        Returns:
            list[bool]: One flag per note, positionally aligned with ``notes``.
        """
        if not notes:
            return []
        return list(self.invoke("canAddNotes", notes=notes))

    def add_notes(self, notes: list[dict[str, Any]]) -> list[int | None]:
        """Add notes to the collection.

        Args:
            notes (list[dict[str, Any]]): Note payloads in ``addNotes`` shape.

        Returns:
            list[int | None]: New note ids, with ``None`` where Anki rejected
                the note. Positionally aligned with ``notes``.
        """
        if not notes:
            return []
        return list(self.invoke("addNotes", notes=notes))

    def export_package(
        self,
        deck: str,
        path: str,
        include_sched: bool = True,
    ) -> bool:
        """Write ``deck`` to an ``.apkg`` file.

        Args:
            deck (str): Deck to export. Exporting a parent deck includes its
                subdecks.
            path (str): Absolute destination path for the ``.apkg`` file.
            include_sched (bool): Whether to embed scheduling state, which is
                what makes the file a usable restore point.

        Returns:
            bool: True when the add-on reported a successful write.
        """
        return bool(
            self.invoke(
                "exportPackage",
                deck=deck,
                path=path,
                includeSched=include_sched,
            )
        )

    def sync(self) -> None:
        """Trigger an AnkiWeb sync so other devices see the new cards."""
        self.invoke("sync")
