import os
import re
import subprocess
import whisper
import pandas as pd

from datetime import datetime

# FFmpeg
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

STREAM_URL = "http://n05.radiojar.com/pepper"

# Timestamp για όλα τα αρχεία
timestamp = datetime.now().strftime("%Y%m%d_%H%M")

audio_file = f"{timestamp}.mp3"
transcript_file = f"{timestamp}_transcript.txt"
password_file = f"{timestamp}_password.txt"

print("Recording...")

subprocess.run([
    r"C:\ffmpeg\bin\ffmpeg.exe",
    "-y",
    "-i",
    STREAM_URL,
    "-t",
    "300",
    audio_file
])

print("Loading Whisper model...")

model = whisper.load_model("medium")

print("Transcribing...")

result = model.transcribe(
    audio_file,
    language="el",
    fp16=False
)

# Transcript με timestamps
with open(transcript_file, "w", encoding="utf-8") as f:

    for segment in result["segments"]:

        line = (
            f"[{segment['start']:.1f}s - "
            f"{segment['end']:.1f}s] "
            f"{segment['text']}\n"
        )

        f.write(line)

print(f"Transcript saved: {transcript_file}")

# ==================================
# Εντοπισμός Password
# ==================================

password = None

segments = result["segments"]

for i, segment in enumerate(segments):

    current_text = segment["text"].lower()

    if (
        "pepper password" in current_text
        or "πέπερ πασβαρντ" in current_text
        or "πασβαρντ" in current_text
        or "password" in current_text
    ):

        print(f"Trigger found: {segment['text']}")

        # Ψάχνουμε στις επόμενες γραμμές
        for j in range(i, min(i + 4, len(segments))):

            next_text = segments[j]["text"]

            match = re.search(
                r"είναι[\.!\s]*([^\n,.!]+)",
                next_text,
                flags=re.IGNORECASE
            )

            if match:

                candidate = match.group(1).strip().lower()

                if (
                    len(candidate) > 2
                    and not candidate.isdigit()
                ):

                    password = candidate
                    break

        if password:
            break

print("\n==========")
print("PASSWORD")
print("==========\n")

if password:

    print("Password:", password)

    # TXT
    with open(
        password_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(password)

    # Excel row
    row = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Time": datetime.now().strftime("%H:%M"),
        "Password": password
    }

    try:

        df = pd.read_excel(
            "passwords.xlsx"
        )

        if password.lower() not in (
            df["Password"]
            .astype(str)
            .str.lower()
            .values
        ):

            df = pd.concat(
                [df, pd.DataFrame([row])],
                ignore_index=True
            )

    except:

        df = pd.DataFrame([row])

    df.to_excel(
        "passwords.xlsx",
        index=False
    )

    print(f"Saved password: {password}")
    print(f"Saved txt: {password_file}")
    print("Saved Excel: passwords.xlsx")

else:

    print("No password found")

print("\nDone")