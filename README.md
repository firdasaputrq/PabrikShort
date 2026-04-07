# PabrikShort

📋 Setup Astro Shorts Engine — Panduan Lengkap & Akurat
Pipeline yang Sebenarnya
idea_generator.py → script_formatter.py → video_renderer.py → youtube_uploader.py
   (Gemini API)        (Gemini API)          (MoviePy lokal)      (YouTube API)
Video dibuat fully local — pakai MoviePy dengan animasi starfield, text, planet grafik. Tidak perlu Pexels atau ElevenLabs. Background music sudah ada di folder assets/audio/.

🔐 Secrets yang Dibutuhkan — Hanya 3
Pergi ke repo → Settings → Secrets and variables → Actions → New repository secret
Secret Name Isi :
GEMINI_API_KEYAPI -> key Google Gemini (gratis)
YOUTUBE_TOKENJSON -> token OAuth (lihat cara buat di bawah)
YOUTUBE_CLIENT_SECRETJSON -> isi file client_secret.json dari Google Cloud

🎫 Step 1 — Dapatkan GEMINI_API_KEY

Buka aistudio.google.com/apikey
Klik Create API Key
Copy key-nya → paste sebagai secret GEMINI_API_KEY

Gratis, tidak perlu kartu kredit.

🎬 Step 2 — Setup YouTube OAuth (bagian terpenting)
A. Buat Google Cloud Project & Credentials:

Buka console.cloud.google.com
Buat project baru (atau pakai yang ada)
Pergi ke APIs & Services → Enable APIs → cari dan enable YouTube Data API v3
Pergi ke APIs & Services → OAuth consent screen → pilih External → isi nama app → Save
Pergi ke APIs & Services → Credentials → Create Credentials → OAuth client ID
Application type: Desktop app → beri nama → Create
Download file JSON-nya (namanya client_secret_xxx.json)

Isi file itu akan dipakai sebagai secret YOUTUBE_CLIENT_SECRET.

B. Generate Refresh Token (jalankan lokal sekali):
bashpip install google-auth-oauthlib google-auth google-api-python-client
Buat file get_token.py:
pythonfrom google_auth_oauthlib.flow import InstalledAppFlow
import json

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret_xxx.json',  # ganti nama file
    scopes=['https://www.googleapis.com/auth/youtube.upload']
)
creds = flow.run_local_server(port=0)

# Print YOUTUBE_TOKEN (format yang dibutuhkan script)
token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes)
}
print("=== YOUTUBE_TOKEN ===")
print(json.dumps(token_data, indent=2))
bashpython get_token.py
Browser akan terbuka, login dengan akun YouTube channel kamu, authorize. Terminal akan print JSON — copy seluruh JSON itu sebagai secret YOUTUBE_TOKEN.

Jadi untuk 
YOUTUBE_TOKEN → paste seluruh JSON dari { "token": ..., "refresh_token": ... }

C. Isi secret YOUTUBE_CLIENT_SECRET:
Buka file client_secret_xxx.json yang tadi di-download, copy seluruh isinya sebagai secret YOUTUBE_CLIENT_SECRET.

⚙️ Step 3 — Enable Repository Permissions
Workflow ini melakukan git push (commit ideas.json yang diupdate). Perlu di-enable:

Pergi ke repo → Settings → Actions → General
Scroll ke Workflow permissions
Pilih "Read and write permissions"
Centang "Allow GitHub Actions to create and approve pull requests"
Klik Save


🚀 Step 4 — Jalankan Manual untuk Test

Pergi ke tab Actions di repo
Pilih workflow "Generate Short Idea"
Klik "Run workflow" → "Run workflow"
Pantau log tiap step

Kalau berhasil, akan ada:

File baru di scripts_output/
File MP4 di videos_output/
Commit otomatis ke repo
Video terupload ke YouTube channel


⏰ Jadwal Otomatis
Dari workflow yang ada:
WorkflowJadwalFungsiGenerate Short IdeaSetiap 8 jam (jam 00, 08, 16 UTC = 07, 15, 23 WIB)Generate + upload 1 videoAnalytics & LearningSetiap hari jam 06 UTC (13.00 WIB)Analisa performa, update strategi
Jadi 3 video/hari otomatis, dan sistem belajar sendiri dari analytics YouTube untuk pilih topik yang perform bagus.

⚠️ Hal Penting
Ganti branch protection jika ada — workflow butuh push langsung ke main.
YouTube quota limit — YouTube Data API v3 punya default 10.000 unit/hari. Upload 1 video = ~1600 unit. Jadi aman untuk 3 video/hari (total ~4800 unit).
Refresh token tidak kedaluwarsa selama aplikasi Google Cloud kamu masih aktif dan token tidak di-revoke.








