import io
import json
import random
import re
from datetime import datetime
from pathlib import Path

from elevenlabs import ElevenLabs, VoiceSettings
from pydub import AudioSegment


def parse_script(script_text: str) -> list[tuple[str, str]]:
    """Parse script into (speaker, text) tuples."""
    dialog_turns = []

    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in script_text.strip().split("\n\n") if p.strip()]

    # Pattern matches "Speaker: " or "Speaker： " (Chinese colon)
    pattern = r"^([^:：]+)[：:]\s*(.+)$"

    for para in paragraphs:
        match = re.match(pattern, para, re.DOTALL)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
            dialog_turns.append((speaker, text))

    return dialog_turns


def get_unique_speakers(dialog_turns: list[tuple[str, str]]) -> list[str]:
    """Extract unique speakers in order of first appearance."""
    speakers = []
    seen = set()
    for speaker, _ in dialog_turns:
        if speaker not in seen:
            speakers.append(speaker)
            seen.add(speaker)
    return speakers


def assign_voices(
    speakers: list[str], voice_map: dict[str, str], default_voices: list[str]
) -> tuple[dict[str, str], list[str]]:
    """
    Assign voices to all speakers.
    Speakers with explicit mappings keep their voices.
    Unmapped speakers get unique voices from default_voices pool.

    Returns:
        Tuple of (complete_voice_mapping, unmapped_speakers)
    """
    unmapped_speakers = [s for s in speakers if s not in voice_map]

    # Check if we have enough default voices
    if len(unmapped_speakers) > len(default_voices):
        raise ValueError(
            f"Not enough default voices!\n"
            f"   Unmapped speakers: {len(unmapped_speakers)}\n"
            f"   Available default voices: {len(default_voices)}\n"
            f"   Please add more voices to DEFAULT_VOICES or specify voices in VOICE_MAP"
        )

    # Create complete voice mapping
    complete_mapping = dict(voice_map)

    # Assign default voices to unmapped speakers
    for idx, speaker in enumerate(unmapped_speakers):
        complete_mapping[speaker] = default_voices[idx]

    # Check for duplicate voice assignments
    voice_to_speakers = {}
    for speaker, voice_id in complete_mapping.items():
        if voice_id not in voice_to_speakers:
            voice_to_speakers[voice_id] = []
        voice_to_speakers[voice_id].append(speaker)

    # Raise error if duplicate voices found
    duplicates = {
        voice_id: speakers for voice_id, speakers in voice_to_speakers.items() if len(speakers) > 1
    }

    if duplicates:
        error_msg = "Multiple speakers are assigned the same voice:\n"
        for voice_id, speakers_list in duplicates.items():
            error_msg += f"   Voice {voice_id}:\n"
            for speaker in speakers_list:
                error_msg += f"     - {speaker}\n"
        error_msg += "\n   Each speaker must have a unique voice. Please update VOICE_MAP."
        raise ValueError(error_msg)

    return complete_mapping, unmapped_speakers


def chunk_dialog_turns(
    dialog_turns: list[tuple[str, str]], max_chunk_chars: int = 2000
) -> list[list[tuple[str, str]]]:
    """
    Chunk dialog turns to avoid quality degradation.
    Merges consecutive turns from same speaker when possible.
    """
    chunks = []
    current_chunk = []
    current_length = 0

    for speaker, text in dialog_turns:
        text_length = len(text)

        # If adding this turn exceeds limit and we have content, start new chunk
        if current_length + text_length > max_chunk_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0

        # Merge with previous turn if same speaker
        if current_chunk and current_chunk[-1][0] == speaker:
            prev_speaker, prev_text = current_chunk[-1]
            merged_text = prev_text + "\n\n" + text
            current_chunk[-1] = (speaker, merged_text)
            current_length += len("\n\n") + text_length
        else:
            current_chunk.append((speaker, text))
            current_length += text_length

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


class DialogGenerator:
    """Generate audio dialogs using ElevenLabs API."""

    def __init__(
        self,
        api_key: str,
        model_id: str = "eleven_v3",
        voice_settings: VoiceSettings | None = None,
        pause_range_ms: tuple[int, int] = (600, 1000),
    ):
        """
        Initialize the dialog generator.

        Args:
            api_key: ElevenLabs API key
            model_id: Model ID to use for generation
            voice_settings: Voice generation settings
            pause_range_ms: Range for random pauses between speakers (min, max) in milliseconds
        """
        self.client = ElevenLabs(api_key=api_key)
        self.model_id = model_id
        self.voice_settings = voice_settings or VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            speed=1.0,
            style=0.0,
            use_speaker_boost=True,
        )
        self.pause_range_ms = pause_range_ms

    def generate(
        self,
        dialog_turns: list[tuple[str, str]],
        voice_map: dict[str, str],
        output_dir: str = "output",
        max_chunk_chars: int = 2000,
    ) -> tuple[Path, dict]:
        """
        Generate audio for dialog with chunking strategy.

        Args:
            dialog_turns: List of (speaker, text) tuples
            voice_map: Mapping of speaker names to voice IDs
            output_dir: Directory to save output files
            max_chunk_chars: Maximum characters per chunk

        Returns:
            Tuple of (final_audio_path, metadata_dict)
        """
        # Create output directories
        output_path = Path(output_dir)
        chunks_dir = output_path / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # Chunk the dialog
        chunked_turns = chunk_dialog_turns(dialog_turns, max_chunk_chars)

        print(f"📊 Split into {len(chunked_turns)} chunks for generation\n")

        chunk_files = []
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "total_chunks": len(chunked_turns),
            "voice_map": voice_map,
            "pause_range_ms": self.pause_range_ms,
            "chunks": [],
        }

        # Generate each chunk
        for chunk_idx, chunk_turns in enumerate(chunked_turns, 1):
            print(f"🎙️  Generating chunk {chunk_idx}/{len(chunked_turns)}...")

            chunk_segments = []

            for turn_idx, (speaker, text) in enumerate(chunk_turns):
                voice_id = voice_map[speaker]

                print(f"   Turn {turn_idx + 1}: {speaker} ({len(text)} chars)")

                # Generate audio for this turn
                audio_generator = self.client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id=self.model_id,
                    voice_settings=self.voice_settings,
                )

                # Collect audio bytes
                audio_bytes = b"".join(audio_generator)

                # Save individual turn (for debugging)
                turn_file = (
                    chunks_dir / f"chunk_{chunk_idx:03d}_turn_{turn_idx + 1:02d}_{speaker}.mp3"
                )
                with open(turn_file, "wb") as f:
                    f.write(audio_bytes)

                chunk_segments.append((speaker, audio_bytes))

            # Concatenate all turns in this chunk with random pauses
            chunk_audio = AudioSegment.empty()
            prev_speaker = None

            for _idx, (speaker, audio_bytes) in enumerate(chunk_segments):
                segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

                # Add random pause before this segment if speaker changed
                if prev_speaker is not None and prev_speaker != speaker:
                    pause_duration = random.randint(self.pause_range_ms[0], self.pause_range_ms[1])
                    silence = AudioSegment.silent(duration=pause_duration)
                    chunk_audio += silence

                chunk_audio += segment
                prev_speaker = speaker

            # Save chunk
            chunk_file = chunks_dir / f"chunk_{chunk_idx:03d}.mp3"
            chunk_audio.export(chunk_file, format="mp3")
            chunk_files.append(chunk_file)

            metadata["chunks"].append(
                {
                    "chunk_id": chunk_idx,
                    "file": str(chunk_file),
                    "turns": len(chunk_turns),
                    "duration_ms": len(chunk_audio),
                }
            )

            print(f"   ✅ Saved: {chunk_file}\n")

        # Concatenate all chunks into final audio
        print("🎬 Creating final concatenated audio...")
        final_audio = AudioSegment.empty()
        for chunk_file in chunk_files:
            segment = AudioSegment.from_mp3(chunk_file)
            final_audio += segment

        # Save final output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = output_path / f"dialog_{timestamp}.mp3"
        final_audio.export(final_file, format="mp3")

        # Save metadata
        metadata_file = output_path / f"dialog_{timestamp}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print("\n✅ Complete!")
        print(f"📁 Final audio: {final_file}")
        print(f"📊 Duration: {len(final_audio) / 1000:.1f} seconds")
        print(f"📋 Metadata: {metadata_file}")

        return final_file, metadata
