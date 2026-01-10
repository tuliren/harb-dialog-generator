#    https://colab.research.google.com/drive/1yx0kF2tOYYi8SrPCVVW7V0Rax2jGAhh9

# 安装依赖包
!pip install elevenlabs pydub

import re
import os
import io
from pathlib import Path
from typing import Dict, List, Tuple
from elevenlabs import ElevenLabs, VoiceSettings
from pydub import AudioSegment
import json
from datetime import datetime

# 🔑 API Key
# https://elevenlabs.io/app/settings/api-keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your_api_key_here")

# 🎙️ 音频设定
# 每段话之间的间隔范围 (milliseconds)
# 生成时，会随机在以下范围选取一个随机值
PAUSE_RANGE_MS = (600, 1000)

# 是否下载分段音频文件
DOWNLOAD_CHUNKS = False

# 模型
# v3 以下的模型似乎中英夹杂都不太行
# https://elevenlabs.io/docs/overview/models#character-limits
MODEL_ID="eleven_v3"

# 声音生成参数，参考文档：
# https://elevenlabs.io/docs/api-reference/text-to-speech/convert#request.body.voice_settings
VOICE_SETTINGS = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    speed=1.0,
    style=0.0,
    use_speaker_boost=True
)

# 🎙️ 默认声音库
# 如果不指定每个 speaker 的声音，就会从以下列表里依次选取
# 浏览所有声音：https://elevenlabs.io/app/voice-library
DEFAULT_VOICES = [
    # Lucy
    # https://elevenlabs.io/app/voice-library?voiceId=lcMyyd2HUfFzxdCaC4Ta
    "lcMyyd2HUfFzxdCaC4Ta",
    # Zhile
    # https://elevenlabs.io/app/voice-library?voiceId=bdt3B5N3GXM2nOc0SUW7
    "bdt3B5N3GXM2nOc0SUW7",
    # Evan Zhao
    # https://elevenlabs.io/app/voice-library?voiceId=MI36FIkp9wRP7cpWKPTl
    "MI36FIkp9wRP7cpWKPTl",
    # Chihiro Yoko
    # https://elevenlabs.io/app/voice-library?voiceId=NIqnuIdrAT3LLSSxN05L
    "NIqnuIdrAT3LLSSxN05L",
    # James Gao
    # https://elevenlabs.io/app/voice-library?voiceId=4VZIsMPtgggwNg7OXbPY
    "4VZIsMPtgggwNg7OXbPY",
    # Stacy
    # https://elevenlabs.io/app/voice-library?voiceId=hkfHEbBvdQFNX4uWHqRF
    "hkfHEbBvdQFNX4uWHqRF",
    # Julia
    # https://elevenlabs.io/app/voice-library?voiceId=tOuLUAIdXShmWH7PEUrU
    "tOuLUAIdXShmWH7PEUrU",
    # Angela
    # https://elevenlabs.io/app/voice-library?voiceId=FUfBrNit0NNZAwb58KWH
    "FUfBrNit0NNZAwb58KWH",
]

if ELEVENLABS_API_KEY == "your_api_key_here":
    print("❌ Please set your ElevenLabs API key in ELEVENLABS_API_KEY")
else:
    print("✅ API key configured")
print(f"✅ Default voice pool has {len(DEFAULT_VOICES)} voices")

# 给 script 里的每个 speaker 指定声音
VOICE_MAP = {
    "HarbKidsFun": "RILOU7YmBhvwJGDGjNmP",
    "A老师": "lcMyyd2HUfFzxdCaC4Ta",
    "B老师": "tOuLUAIdXShmWH7PEUrU",
}

# 每个 speaker 之间需要有额外空行
# 每个 speaker 开头，必须紧跟英文或者中文冒号
SCRIPT = """
HarbKidsFun： 哈喽大家新年好呀！欢迎来到 HarbKidsFun 2026年的第一期访谈。今天呢，我们特别幸运地连线到了两位教过汉基——就是大家常说的CIS——小学部的中文老师。一位是现在还在职的A老师，另一位是已经离职的B老师。我们想请她们来跟大家随便聊聊汉基小学阶段，就是从Reception学前班到Y六这段的中文教学特色。这也算是继去年推出了好几篇港漂妈妈择校访谈之后，我们开始把访谈对象扩展到香港本地的老师群体了。新的一年里呢，在择校这条资讯线上，我们在推出更多真人访谈的同时，也会努力涵盖香港学校生态圈里更多不同的角色，大家敬请期待哈。

HarbKidsFun： 两位老师新年好！大家都知道汉基是香港国际学校里的顶流嘛，特别是以扎实的双语教学出名，而两位老师都是这里面的主力军，所以我们真的特别荣幸能有机会直接向两位老师请教。能不能先请你们介绍一下各自在汉基的工作经历呢？

A老师： 大家好。我目前在汉基小学部主要负责三块工作：第一，担任某两个年级的中文课程主任；第二，负责其中一个年级的中文课堂教学；第三，担任该年级某班的中文 Homeroom Teacher，也就是中文班主任。

B老师： 大家好呀！我呢，是在几年前第二个孩子出生后离开了工作十多年的汉基，现在还是在家带娃的状态。在汉基的那十多年里，我一开始是担任 Reception——就是学前班，收生年龄对应香港本地学校K二——的中文班主任，后来转去做 Y一到Y六 的中文支援老师，主要是给中文程度相对落后的孩子提供 Foundation或者Ab initio 的辅导课程。

HarbKidsFun： 看来两位老师的工作范围和任职时间都有些不一样哈。我们先来了解一下，现在汉基小学部各年级的人数是怎样的？
"""

def parse_script(script_text: str) -> List[Tuple[str, str]]:
    """Parse script into (speaker, text) tuples."""
    dialog_turns = []

    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in script_text.strip().split('\n\n') if p.strip()]

    # Pattern matches "Speaker: " or "Speaker： " (Chinese colon)
    pattern = r'^([^:：]+)[：:]\s*(.+)$'

    for para in paragraphs:
        match = re.match(pattern, para, re.DOTALL)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
            dialog_turns.append((speaker, text))

    return dialog_turns

def get_unique_speakers(dialog_turns: List[Tuple[str, str]]) -> List[str]:
    """Extract unique speakers in order of first appearance."""
    speakers = []
    seen = set()
    for speaker, _ in dialog_turns:
        if speaker not in seen:
            speakers.append(speaker)
            seen.add(speaker)
    return speakers

# Parse and display
dialog_turns = parse_script(SCRIPT)
unique_speakers = get_unique_speakers(dialog_turns)

print(f"✅ Parsed {len(dialog_turns)} dialog turns")
print(f"📋 Found {len(unique_speakers)} unique speakers:\n")
for i, speaker in enumerate(unique_speakers, 1):
    print(f"  {i}. {speaker}")

def assign_voices(
    speakers: List[str],
    voice_map: Dict[str, str],
    default_voices: List[str]
) -> Dict[str, str]:
    """
    Assign voices to all speakers.
    Speakers with explicit mappings keep their voices.
    Unmapped speakers get unique voices from default_voices pool.
    """
    unmapped_speakers = [s for s in speakers if s not in voice_map]

    # 如果默认声音库里的声音不够，会报错
    if len(unmapped_speakers) > len(default_voices):
        raise ValueError(
            f"❌ Not enough default voices!\n"
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

    # 如果给不同 speaker 指定的声音有重复，会报错
    duplicates = {voice_id: speakers for voice_id, speakers in voice_to_speakers.items() if len(speakers) > 1}

    if duplicates:
        error_msg = "❌ Multiple speakers are assigned the same voice:\n"
        for voice_id, speakers_list in duplicates.items():
            error_msg += f"   Voice {voice_id}:\n"
            for speaker in speakers_list:
                error_msg += f"     - {speaker}\n"
        error_msg += "\n   Each speaker must have a unique voice. Please update VOICE_MAP."
        raise ValueError(error_msg)

    return complete_mapping, unmapped_speakers

# Assign voices
try:
    complete_voice_map, unmapped_speakers = assign_voices(
        unique_speakers,
        VOICE_MAP,
        DEFAULT_VOICES
    )

    print("🎙️  Voice Assignments:\n")
    for speaker in unique_speakers:
        voice_id = complete_voice_map[speaker]
        if speaker in VOICE_MAP:
            status = "✓ (custom)"
        else:
            status = "⚙️ (default)"
        print(f"  {status} {speaker}: {voice_id}")

    if unmapped_speakers:
        print(f"\nℹ️  {len(unmapped_speakers)} speaker(s) using default voices from pool")

except ValueError as e:
    print(str(e))
    raise

def chunk_dialog_turns(
    dialog_turns: List[Tuple[str, str]],
    max_chunk_chars: int = 2000
) -> List[List[Tuple[str, str]]]:
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

def generate_dialog_audio(
    dialog_turns: List[Tuple[str, str]],
    voice_map: Dict[str, str],
    api_key: str,
    output_dir: str = "output",
    max_chunk_chars: int = 2000,
    pause_range_ms: Tuple[int, int] = PAUSE_RANGE_MS
):
    """Generate audio for dialog with chunking strategy."""

    import random

    # Initialize client
    client = ElevenLabs(api_key=api_key)

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
        "pause_range_ms": pause_range_ms,
        "chunks": []
    }

    # Generate each chunk
    for chunk_idx, chunk_turns in enumerate(chunked_turns, 1):
        print(f"🎙️  Generating chunk {chunk_idx}/{len(chunked_turns)}...")

        chunk_segments = []

        for turn_idx, (speaker, text) in enumerate(chunk_turns):
            voice_id = voice_map[speaker]

            print(f"   Turn {turn_idx + 1}: {speaker} ({len(text)} chars)")

            # Generate audio for this turn
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=MODEL_ID,
                voice_settings=VOICE_SETTINGS
            )

            # Collect audio bytes
            audio_bytes = b"".join(audio_generator)

            # Save individual turn (optional, for debugging)
            turn_file = chunks_dir / f"chunk_{chunk_idx:03d}_turn_{turn_idx + 1:02d}_{speaker}.mp3"
            with open(turn_file, "wb") as f:
                f.write(audio_bytes)

            chunk_segments.append((speaker, audio_bytes))

        # Concatenate all turns in this chunk with random pauses
        chunk_audio = AudioSegment.empty()
        prev_speaker = None

        for idx, (speaker, audio_bytes) in enumerate(chunk_segments):
            segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

            # Add random pause before this segment if speaker changed
            if prev_speaker is not None and prev_speaker != speaker:
                pause_duration = random.randint(pause_range_ms[0], pause_range_ms[1])
                silence = AudioSegment.silent(duration=pause_duration)
                chunk_audio += silence

            chunk_audio += segment
            prev_speaker = speaker

        # Save chunk
        chunk_file = chunks_dir / f"chunk_{chunk_idx:03d}.mp3"
        chunk_audio.export(chunk_file, format="mp3")
        chunk_files.append(chunk_file)

        metadata["chunks"].append({
            "chunk_id": chunk_idx,
            "file": str(chunk_file),
            "turns": len(chunk_turns),
            "duration_ms": len(chunk_audio)
        })

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

    print(f"\n✅ Complete!")
    print(f"📁 Final audio: {final_file}")
    print(f"📊 Duration: {len(final_audio) / 1000:.1f} seconds")
    print(f"📋 Metadata: {metadata_file}")

    return final_file, metadata

# 生成对话（这一步可能要等很长时间）
final_file, metadata = generate_dialog_audio(
    dialog_turns=dialog_turns,
    voice_map=complete_voice_map,
    api_key=ELEVENLABS_API_KEY,
    output_dir="output",
    pause_range_ms=PAUSE_RANGE_MS
)

from google.colab import files

# 下载文件
print("📥 下载最终对话文件...")
files.download(str(final_file))

if DOWNLOAD_CHUNKS:
    print("📥 下载分段文件...")
    for chunk_file in Path("output/chunks").glob("chunk_*.mp3"):
        files.download(str(chunk_file))

print("\n✅ All done! Check your downloads folder.")
