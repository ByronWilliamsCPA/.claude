"""Anki card pipeline: distilled lecture notes to cards in the collection.

Public surface is the CLI in :mod:`claude_config.anki.cli`; the modules below
are importable for tests and for skills that need finer control.
"""

from claude_config.anki.cards import Card, CardBatch, CardFormatError
from claude_config.anki.connect import AnkiConnectClient, AnkiError
from claude_config.anki.pipeline import PipelineError, PushReport

__all__ = [
    "AnkiConnectClient",
    "AnkiError",
    "Card",
    "CardBatch",
    "CardFormatError",
    "PipelineError",
    "PushReport",
]
