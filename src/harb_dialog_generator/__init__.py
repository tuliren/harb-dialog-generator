from .generator import (
    DialogGenerator,
    assign_voices,
    chunk_dialog_turns,
    get_unique_speakers,
    parse_script,
)

__version__ = "0.1.0"

__all__ = [
    "DialogGenerator",
    "parse_script",
    "get_unique_speakers",
    "assign_voices",
    "chunk_dialog_turns",
]
