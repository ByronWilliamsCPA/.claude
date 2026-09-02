"""Tests for the AnkiConnect transport and response handling."""

import pytest

from claude_config.anki.connect import (
    API_VERSION,
    AnkiActionError,
    AnkiConnectClient,
    AnkiProtocolError,
    AnkiUnreachableError,
)


class TestInvoke:
    def test_sends_action_and_api_version(self, anki_server):
        client, responses, received = anki_server
        responses["version"] = {"result": 6, "error": None}
        client.invoke("version")
        assert received[0] == {"action": "version", "version": API_VERSION}

    def test_nests_params_only_when_present(self, anki_server):
        client, responses, received = anki_server
        responses["findNotes"] = {"result": [], "error": None}
        client.invoke("findNotes", query="deck:X")
        assert received[0]["params"] == {"query": "deck:X"}

    def test_returns_the_result_member(self, anki_server):
        client, responses, _ = anki_server
        responses["deckNames"] = {"result": ["Default"], "error": None}
        assert client.invoke("deckNames") == ["Default"]

    def test_reported_error_raises(self, anki_server):
        client, responses, _ = anki_server
        responses["addNotes"] = {"result": None, "error": "collection is not open"}
        with pytest.raises(AnkiActionError, match="collection is not open"):
            client.invoke("addNotes")

    def test_non_json_reply_raises(self, anki_server):
        client, responses, _ = anki_server
        responses["version"] = "<html>not json</html>"
        with pytest.raises(AnkiProtocolError, match="not JSON"):
            client.invoke("version")

    def test_missing_result_key_raises(self, anki_server):
        client, responses, _ = anki_server
        responses["version"] = {"error": None}
        with pytest.raises(AnkiProtocolError, match="no 'result' field"):
            client.invoke("version")

    def test_api_key_is_sent_when_configured(self, anki_server):
        client, responses, received = anki_server
        configured = "abc123"
        keyed = AnkiConnectClient(
            host=client.host, port=client.port, api_key=configured
        )
        responses["version"] = {"result": 6, "error": None}
        keyed.invoke("version")
        assert received[0]["key"] == configured

    def test_api_key_is_omitted_by_default(self, anki_server):
        client, responses, received = anki_server
        responses["version"] = {"result": 6, "error": None}
        client.invoke("version")
        assert "key" not in received[0]


class TestUnreachable:
    def test_closed_port_raises_with_install_instructions(self):
        client = AnkiConnectClient(host="127.0.0.1", port=1, timeout=1.0)
        with pytest.raises(AnkiUnreachableError) as excinfo:
            client.invoke("version")
        message = str(excinfo.value)
        assert "2055492159" in message
        assert "Open the Anki desktop app" in message


class TestPreflight:
    def test_returns_the_reported_version(self, anki_server):
        client, responses, _ = anki_server
        responses["version"] = {"result": 6, "error": None}
        assert client.preflight() == 6

    def test_non_integer_version_raises(self, anki_server):
        client, responses, _ = anki_server
        responses["version"] = {"result": "six", "error": None}
        with pytest.raises(AnkiProtocolError, match="expected an integer"):
            client.preflight()


class TestSupports:
    def test_true_when_the_action_is_reflected(self, anki_server):
        client, responses, _ = anki_server
        responses["apiReflect"] = {
            "result": {"scopes": ["actions"], "actions": ["exportPackage"]},
            "error": None,
        }
        assert client.supports("exportPackage") is True

    def test_false_when_the_action_is_absent(self, anki_server):
        client, responses, _ = anki_server
        responses["apiReflect"] = {
            "result": {"scopes": ["actions"], "actions": []},
            "error": None,
        }
        assert client.supports("exportPackage") is False

    def test_false_when_reflection_itself_errors(self, anki_server):
        client, responses, _ = anki_server
        responses["apiReflect"] = {"result": None, "error": "unsupported action"}
        assert client.supports("exportPackage") is False

    def test_false_when_reflection_returns_a_non_mapping(self, anki_server):
        client, responses, _ = anki_server
        responses["apiReflect"] = {"result": ["exportPackage"], "error": None}
        assert client.supports("exportPackage") is False


class TestConvenienceWrappers:
    def test_empty_inputs_short_circuit_without_a_call(self, anki_server):
        client, _, received = anki_server
        assert client.notes_info([]) == []
        assert client.can_add_notes([]) == []
        assert client.add_notes([]) == []
        assert received == []

    def test_export_package_passes_scheduling_flag(self, anki_server):
        client, responses, received = anki_server
        responses["exportPackage"] = {"result": True, "error": None}
        assert client.export_package("D", "/tmp/x.apkg", include_sched=True) is True
        assert received[0]["params"]["includeSched"] is True

    def test_create_deck_passes_the_name(self, anki_server):
        client, responses, received = anki_server
        responses["createDeck"] = {"result": 1, "error": None}
        client.create_deck("A::B")
        assert received[0]["params"] == {"deck": "A::B"}

    def test_sync_is_invoked(self, anki_server):
        client, responses, received = anki_server
        responses["sync"] = {"result": None, "error": None}
        client.sync()
        assert received[0]["action"] == "sync"


class TestFromEnv:
    def test_reads_host_port_and_key(self, monkeypatch):
        monkeypatch.setenv("ANKI_CONNECT_HOST", "192.168.1.5")
        monkeypatch.setenv("ANKI_CONNECT_PORT", "9999")
        monkeypatch.setenv("ANKI_CONNECT_API_KEY", "k")
        client = AnkiConnectClient.from_env()
        assert (client.host, client.port, client._api_key) == ("192.168.1.5", 9999, "k")

    def test_falls_back_to_addon_defaults(self, monkeypatch):
        monkeypatch.delenv("ANKI_CONNECT_HOST", raising=False)
        monkeypatch.delenv("ANKI_CONNECT_PORT", raising=False)
        monkeypatch.delenv("ANKI_CONNECT_API_KEY", raising=False)
        client = AnkiConnectClient.from_env()
        assert (client.host, client.port, client._api_key) == ("127.0.0.1", 8765, None)

    def test_blank_api_key_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("ANKI_CONNECT_API_KEY", "")
        assert AnkiConnectClient.from_env()._api_key is None


class TestPassThroughWrappers:
    """The thin wrappers must forward params and coerce the result to a list."""

    def test_deck_names_returns_a_list(self, anki_server):
        client, responses, _ = anki_server
        responses["deckNames"] = {"result": ["A", "B"], "error": None}
        assert client.deck_names() == ["A", "B"]

    def test_find_notes_forwards_the_query(self, anki_server):
        client, responses, received = anki_server
        responses["findNotes"] = {"result": [1, 2], "error": None}
        assert client.find_notes('deck:"A"') == [1, 2]
        assert received[0]["params"] == {"query": 'deck:"A"'}

    def test_notes_info_forwards_the_ids(self, anki_server):
        client, responses, received = anki_server
        responses["notesInfo"] = {"result": [{"noteId": 1}], "error": None}
        assert client.notes_info([1]) == [{"noteId": 1}]
        assert received[0]["params"] == {"notes": [1]}

    def test_can_add_notes_forwards_the_payload(self, anki_server):
        client, responses, received = anki_server
        responses["canAddNotes"] = {"result": [True], "error": None}
        assert client.can_add_notes([{"deckName": "A"}]) == [True]
        assert received[0]["params"] == {"notes": [{"deckName": "A"}]}

    def test_add_notes_returns_ids_and_nulls(self, anki_server):
        client, responses, received = anki_server
        responses["addNotes"] = {"result": [123, None], "error": None}
        assert client.add_notes([{"a": 1}, {"b": 2}]) == [123, None]
        assert len(received[0]["params"]["notes"]) == 2


class TestListCoercion:
    """A null or scalar result where a list is expected is a protocol error.

    Regression: an add-on that does not know an action can answer
    ``{"result": null, "error": null}``. Passing that straight to ``list()``
    raised ``TypeError`` several frames away instead of naming the problem.
    """

    def test_null_result_raises_a_protocol_error(self, anki_server):
        client, responses, _ = anki_server
        responses["modelNames"] = {"result": None, "error": None}
        with pytest.raises(AnkiProtocolError, match="expected a list"):
            client.model_names()

    def test_error_names_the_action_and_the_likely_cause(self, anki_server):
        client, responses, _ = anki_server
        responses["modelNames"] = {"result": None, "error": None}
        with pytest.raises(AnkiProtocolError) as excinfo:
            client.model_names()
        assert "modelNames" in str(excinfo.value)
        assert "may not support the action" in str(excinfo.value)

    def test_scalar_result_raises_a_protocol_error(self, anki_server):
        client, responses, _ = anki_server
        responses["deckNames"] = {"result": 7, "error": None}
        with pytest.raises(AnkiProtocolError, match="expected a list"):
            client.deck_names()

    def test_model_names_returns_the_note_types(self, anki_server):
        client, responses, _ = anki_server
        responses["modelNames"] = {"result": ["Basic", "Cloze"], "error": None}
        assert client.model_names() == ["Basic", "Cloze"]

    def test_empty_list_is_a_valid_result(self, anki_server):
        client, responses, _ = anki_server
        responses["findNotes"] = {"result": [], "error": None}
        assert client.find_notes("deck:none") == []
