import os

from elevenlabs import VoiceSettings

from harb_dialog_generator import (
    DialogGenerator,
    assign_voices,
    get_unique_speakers,
    parse_script,
)

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
MODEL_ID = "eleven_v3"

# 声音生成参数，参考文档：
# https://elevenlabs.io/docs/api-reference/text-to-speech/convert#request.body.voice_settings
VOICE_SETTINGS = VoiceSettings(
    stability=0.5, similarity_boost=0.75, speed=1.0, style=0.0, use_speaker_boost=True
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
# ruff: noqa: E501
SCRIPT = """
HarbKidsFun： 哈喽大家新年好呀！欢迎来到 HarbKidsFun 2026年的第一期访谈。今天呢，我们特别幸运地连线到了两位教过汉基——就是大家常说的CIS——小学部的中文老师。一位是现在还在职的A老师，另一位是已经离职的B老师。我们想请她们来跟大家随便聊聊汉基小学阶段，就是从Reception学前班到Y六这段的中文教学特色。这也算是继去年推出了好几篇港漂妈妈择校访谈之后，我们开始把访谈对象扩展到香港本地的老师群体了。新的一年里呢，在择校这条资讯线上，我们在推出更多真人访谈的同时，也会努力涵盖香港学校生态圈里更多不同的角色，大家敬请期待哈。

HarbKidsFun： 两位老师新年好！大家都知道汉基是香港国际学校里的顶流嘛，特别是以扎实的双语教学出名，而两位老师都是这里面的主力军，所以我们真的特别荣幸能有机会直接向两位老师请教。能不能先请你们介绍一下各自在汉基的工作经历呢？

A老师： 大家好。我目前在汉基小学部主要负责三块工作：第一，担任某两个年级的中文课程主任；第二，负责其中一个年级的中文课堂教学；第三，担任该年级某班的中文 Homeroom Teacher，也就是中文班主任。

B老师： 大家好呀！我呢，是在几年前第二个孩子出生后离开了工作十多年的汉基，现在还是在家带娃的状态。在汉基的那十多年里，我一开始是担任 Reception——就是学前班，收生年龄对应香港本地学校K二——的中文班主任，后来转去做 Y一到Y六 的中文支援老师，主要是给中文程度相对落后的孩子提供 Foundation或者Ab initio 的辅导课程。

HarbKidsFun： 看来两位老师的工作范围和任职时间都有些不一样哈。我们先来了解一下，现在汉基小学部各年级的人数是怎样的？
"""

# Parse and display
dialog_turns = parse_script(SCRIPT)
unique_speakers = get_unique_speakers(dialog_turns)

print(f"✅ Parsed {len(dialog_turns)} dialog turns")
print(f"📋 Found {len(unique_speakers)} unique speakers:\n")
for i, speaker in enumerate(unique_speakers, 1):
    print(f"  {i}. {speaker}")

# Assign voices
try:
    complete_voice_map, unmapped_speakers = assign_voices(
        unique_speakers, VOICE_MAP, DEFAULT_VOICES
    )

    print("🎙️  Voice Assignments:\n")
    for speaker in unique_speakers:
        voice_id = complete_voice_map[speaker]
        status = "✓ (custom)" if speaker in VOICE_MAP else "⚙️ (default)"
        print(f"  {status} {speaker}: {voice_id}")

    if unmapped_speakers:
        print(f"\nℹ️  {len(unmapped_speakers)} speaker(s) using default voices from pool")

except ValueError as e:
    print(str(e))
    raise

# Generate dialog audio
if __name__ == "__main__":
    # Check API key
    if ELEVENLABS_API_KEY == "your_api_key_here":
        print("❌ Please set ELEVENLABS_API_KEY environment variable")
        exit(1)

    # Initialize generator
    generator = DialogGenerator(
        api_key=ELEVENLABS_API_KEY,
        model_id=MODEL_ID,
        voice_settings=VOICE_SETTINGS,
        pause_range_ms=PAUSE_RANGE_MS,
    )

    # Generate audio (this may take a while)
    print("\n🎙️  Starting audio generation...")
    final_file, metadata = generator.generate(
        dialog_turns=dialog_turns,
        voice_map=complete_voice_map,
        output_dir="output",
    )

    print("\n✅ All done! Check the output directory for the generated audio files.")
