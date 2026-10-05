import os
import re
import subprocess
import whisper
import pandas as pd
import requests
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# Discord Webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1555935895243333682/BtcF4AEpeI4R1rlXoXB9sXEJ3g8wsvy-zrOz3KhuiLY4bOVLpWGYUOFPkQnEd59ArElH"

# FFmpeg Path
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Stream URL Pepper 96.6
STREAM_URL = "http://n05.radiojar.com/pepper"

# Διάρκεια κάθε ηχογράφησης σε δευτερόλεπτα (π.χ. 300 = 5 λεπτά)
RECORD_DURATION = "300"

# Prompt καθοδήγησης για το Whisper AI
WHISPER_PROMPT = "Pepper 96.6, Pepper Password, Pepper Experience, Παρίσι, Duran Duran, κωδικός είναι."

# ---------------------------------------------------------------------------
# ΕΙΔΟΠΟΙΗΣΗ DISCORD
# ---------------------------------------------------------------------------
def send_discord_alert(password_text, timestamp_str):
    """Στέλνει Push Notification στο Discord όταν βρεθεί password"""
    if not DISCORD_WEBHOOK_URL:
        return
    
    payload = {
        "content": (
            f"🌶️ **PEPPER PASSWORD FOUND!** 🌶️\n\n"
            f"🕒 **Ώρα:** `{timestamp_str}`\n"
            f"🔑 **Password:** `{password_text.upper()}`\n\n"
            f"@everyone"
        )
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code in (200, 204):
            print("✅ Η ειδοποίηση στάλθηκε επιτυχώς στο Discord!")
        else:
            print(f"⚠️ Σφάλμα Discord Webhook (Code: {response.status_code})")
    except Exception as e:
        print(f"⚠️ Αποτυχία αποστολής στο Discord: {e}")

# ---------------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------
def main():
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M")
    time_formatted = now.strftime("%Y-%m-%d %H:%M")

    audio_file = f"{timestamp}.mp3"
    transcript_file = f"{timestamp}_transcript.txt"
    password_file = f"{timestamp}_password.txt"

    print("Recording...")
    subprocess.run([
        r"C:\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-i", STREAM_URL,
        "-t", RECORD_DURATION,
        audio_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Loading Whisper model...")
    model = whisper.load_model("medium")

    print("Transcribing...")
    result = model.transcribe(
        audio_file,
        language="el",
        fp16=False,
        initial_prompt=WHISPER_PROMPT
    )

    # 1. Αποθήκευση Transcript με Timestamps
    with open(transcript_file, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            line = f"[{segment['start']:.1f}s - {segment['end']:.1f}s] {segment['text']}\n"
            f.write(line)

    print(f"Transcript saved: {transcript_file}")

    # 2. Smart Password Extraction
    password = None
    segments = result["segments"]

    for i, segment in enumerate(segments):
        current_text = segment["text"].lower()

        if any(k in current_text for k in ["pepper password", "πέπερ πασβαρντ", "πασβαρντ", "password"]):
            print(f"🎯 Trigger found: {segment['text']}")

            # 1ος Τρόπος: Αναζήτηση μετά από "είναι" (επιτρέποντας τελείες, αποσιωπητικά, παύλες)
            for j in range(i, min(i + 3, len(segments))):
                next_text = segments[j]["text"]
                match = re.search(r"είναι[\.\s:\-]*([a-zA-Zα-ώΑ-ΩάέήίόύώΆΈΉΊΌΎΏ]+)", next_text, flags=re.IGNORECASE)

                if match:
                    candidate = match.group(1).strip().lower()
                    if candidate not in ["το", "pepper", "password", "για"] and len(candidate) > 2:
                        password = candidate
                        break

            # 2ος Τρόπος (Fallback): Αν δεν βρέθηκε με το "είναι", παίρνει την επόμενη καθαρή λέξη
            if not password and i + 1 < len(segments):
                next_seg = segments[i + 1]["text"].strip().lower()
                words = re.findall(r'[a-zA-Zα-ώΑ-ΩάέήίόύώΆΈΉΊΌΎΏ]+', next_seg)
                if words:
                    password = words[0]

            if password:
                break

    print("\n==========")
    print("RESULT")
    print("==========\n")

    if password:
        print(f"🎉 ΕΝΤΟΠΙΣΤΗΚΕ PASSWORD: {password}")

        # Αποθήκευση σε .txt
        with open(password_file, "w", encoding="utf-8") as f:
            f.write(password)

        # Αποθήκευση σε Excel
        row = {
            "Date": now.strftime("%Y-%m-%d"),
            "Time": now.strftime("%H:%M"),
            "Password": password
        }

        try:
            df = pd.read_excel("passwords.xlsx")
            if password.lower() not in df["Password"].astype(str).str.lower().values:
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        except Exception:
            df = pd.DataFrame([row])

        df.to_excel("passwords.xlsx", index=False)

        print(f"Saved txt: {password_file}")
        print("Saved Excel: passwords.xlsx")

        # Αποστολή στο Discord
        send_discord_alert(password, time_formatted)

    else:
        print("❌ Δεν εντοπίστηκε password.")

    print("\nDone")

if __name__ == "__main__":
    main()
