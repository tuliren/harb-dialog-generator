# Harb Dialog Generator

Generate audio dialogs from text using the ElevenLabs API.

## Features

- Parse dialog scripts with multiple speakers
- Automatic voice assignment from a voice pool
- Support for custom voice mapping per speaker
- Audio chunking for optimal quality
- Configurable pauses between speakers
- Metadata tracking for generated audio

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install dependencies
uv sync
```

## Setup

1. Get your ElevenLabs API key from https://elevenlabs.io/app/settings/api-keys

2. Set your API key as an environment variable:

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
```

Or create a `.env` file (see `.env.example`)

## Usage

### As a script

Run the example script:

```bash
uv run python generator.py
```

### As a library

```python
import os
from elevenlabs import VoiceSettings
from harb_dialog_generator import (
    DialogGenerator,
    parse_script,
    get_unique_speakers,
    assign_voices,
)

# Your dialog script
SCRIPT = """
Speaker1： Hello, this is the first speaker.

Speaker2： And this is the second speaker responding.
"""

# Parse the script
dialog_turns = parse_script(SCRIPT)
unique_speakers = get_unique_speakers(dialog_turns)

# Configure voices
VOICE_MAP = {
    "Speaker1": "voice_id_1",
    "Speaker2": "voice_id_2",
}

DEFAULT_VOICES = ["default_voice_id_1", "default_voice_id_2"]

# Assign voices
complete_voice_map, _ = assign_voices(unique_speakers, VOICE_MAP, DEFAULT_VOICES)

# Generate audio
generator = DialogGenerator(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    model_id="eleven_v3",
    voice_settings=VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        speed=1.0,
        style=0.0,
        use_speaker_boost=True
    ),
    pause_range_ms=(600, 1000),
)

final_file, metadata = generator.generate(
    dialog_turns=dialog_turns,
    voice_map=complete_voice_map,
    output_dir="output",
)

print(f"Generated audio: {final_file}")
```

## Dialog Script Format

Dialog scripts should follow this format:

- Each speaker's dialog should be on a separate paragraph
- Speaker name followed by a colon (`:` or `：`)
- Separate speakers with blank lines

Example:

```
Speaker1： First speaker's text here.

Speaker2： Second speaker's text here.

Speaker1： First speaker again.
```

## Development

### Run linting and formatting checks

```bash
# Check code
uv run ruff check .

# Format code
uv run ruff format .

# Check formatting without modifying files
uv run ruff format --check .
```

## License

See LICENSE file for details.
