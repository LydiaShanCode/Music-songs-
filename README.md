# Music-songs-
Songs for DJ — a small helper around [yt-dlp](https://github.com/yt-dlp/yt-dlp) that turns a tracklist into tagged, DJ-software-ready audio files.

## Setup (once)

1. Install **Python 3.10+** and **ffmpeg** (`brew install ffmpeg` on Mac, `winget install ffmpeg` on Windows, `sudo apt install ffmpeg` on Linux).
2. Install yt-dlp:
   ```
   pip install -r requirements.txt
   ```
   Keep it current — sites change often and old versions break: `pip install -U yt-dlp`.

## Use

1. Put your tracks in `tracklist.txt`, one per line — a link **or** just `Artist - Title`:
   ```
   https://www.youtube.com/watch?v=XXXXXXXXXXX
   https://soundcloud.com/artist/track-name
   Artist Name - Track Title (Extended Mix)
   ```
2. Check what it will grab (nothing is downloaded):
   ```
   python dj_download.py --dry-run
   ```
3. Download:
   ```
   python dj_download.py              # MP3, best quality
   python dj_download.py -f aiff      # AIFF (Rekordbox / Serato / CDJs)
   ```

Files land in `downloads/` as `Artist - Title.mp3` with artist/title tags and square cover art.
Re-running is safe: tracks already downloaded are skipped, so just keep adding lines to `tracklist.txt`.

### Options

| Option | What it does |
|---|---|
| `-f mp3\|aiff\|flac\|wav\|m4a` | Output format (default `mp3`). AIFF/WAV have no cover art in some software. |
| `-o FOLDER` | Output folder (default `downloads`) |
| `-s soundcloud` | Search SoundCloud instead of YouTube for `Artist - Title` lines |
| `--playlists` | A link inside a playlist downloads the whole playlist |
| `--cookies-from-browser chrome` | Use your browser login (age-restricted / members-only tracks) |
| `-n`, `--dry-run` | List matches without downloading |
| `--ytdlp-arg ARG` | Pass any extra raw option through to yt-dlp |

## Tips for DJs

- **Search for the right version.** Add `Extended Mix`, `Original Mix`, `Radio Edit` or the label name to the line; always `--dry-run` first and swap in a direct link if the top hit is a live cut or lyric video.
- **Quality ceiling.** YouTube audio is lossy (~128–160 kbps Opus/AAC). Saving as AIFF/FLAC/320 doesn't add quality back — it only avoids a second lossy step. For club systems, buy lossless from Bandcamp/Beatport/Traktrain etc. when you can.
- **Analyse after import.** Let Rekordbox/Serato/Traktor analyse BPM, key and gain; the script doesn't normalise loudness on purpose.
- **Rights.** Only download tracks you're allowed to (your own, free/Creative Commons releases, or where the artist permits it), and check a venue/stream's licensing for public play.
