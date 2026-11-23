#!/usr/bin/env python3
"""Download tracks for a DJ set with yt-dlp.

Reads a tracklist (one entry per line) where each entry is either:
  * a URL (single video, SoundCloud track, playlist, ...), or
  * a search query such as "Daft Punk - One More Time" (searched on YouTube,
    or SoundCloud with --source soundcloud).

Each track is saved as audio, tagged (artist/title + cover art where the format
supports it) and named "Artist - Title.ext" so it drops cleanly into
Rekordbox / Serato / Traktor / VirtualDJ.

Already-downloaded tracks are remembered in downloads/.archive.txt and skipped
on the next run, so you can keep adding lines to the same tracklist.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Formats that can hold embedded cover art via yt-dlp.
ART_FORMATS = {"mp3", "m4a", "flac", "opus"}
SEARCH_PREFIX = {"youtube": "ytsearch1:", "soundcloud": "scsearch1:"}


def read_tracklist(path: Path, source: str) -> list[str]:
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line or line.startswith(("ytsearch", "scsearch")):
            entries.append(line)
        else:
            entries.append(SEARCH_PREFIX[source] + line)
    return entries


def build_command(args, entries: list[str], done_file: str | None) -> list[str]:
    out_dir = Path(args.out)
    # yt-dlp can't write AIFF itself: grab FLAC (keeps tags), convert afterwards.
    ytdlp_format = "flac" if args.format == "aiff" else args.format
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format", "bestaudio/best",
        "--extract-audio",
        "--audio-format", ytdlp_format,
        "--audio-quality", "0",               # best quality for lossy formats
        "--paths", str(out_dir),
        "--output", "%(artist,uploader)s - %(track,title)s.%(ext)s",
        "--windows-filenames",                # safe on USB sticks / CDJs
        "--download-archive", str(out_dir / ".archive.txt"),
        "--no-overwrites",
        "--ignore-errors",                    # one bad track won't stop the set
        # If the video title looks like "Artist - Title", use that for the tags.
        "--parse-metadata", "title:%(artist)s - %(title)s",
        "--parse-metadata", "%(artist,uploader)s:%(artist)s",
        "--embed-metadata",
    ]
    if ytdlp_format in ART_FORMATS:
        cmd += [
            "--embed-thumbnail",
            "--convert-thumbnails", "jpg",
            # Crop the 16:9 YouTube thumbnail to square cover art.
            "--ppa",
            "ThumbnailsConvertor+FFmpeg_o:-c:v mjpeg "
            "-vf crop=\"'if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'\"",
        ]
    if not args.playlists:
        cmd.append("--no-playlist")           # a video link with &list= = just that video
    if args.cookies_from_browser:
        cmd += ["--cookies-from-browser", args.cookies_from_browser]
    if args.dry_run:
        cmd += ["--simulate", "--print", "%(artist,uploader)s - %(track,title)s  [%(duration_string)s]  %(webpage_url)s"]
    if done_file:
        cmd += ["--print-to-file", "after_move:filepath", done_file]
    cmd += args.ytdlp_arg or []
    return cmd + ["--"] + entries


def flac_to_aiff(paths: list[Path]) -> int:
    """Convert finished FLAC downloads to AIFF, keeping tags and cover art."""
    failures = 0
    for src in paths:
        if src.suffix.lower() != ".flac" or not src.is_file():
            continue
        dst = src.with_suffix(".aiff")
        result = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src),
             "-map", "0:a", "-map", "0:v?", "-c:a", "pcm_s16be", "-c:v", "copy",
             "-map_metadata", "0", "-write_id3v2", "1", str(dst)])
        if result.returncode == 0:
            src.unlink()
            print(f"[aiff] {dst.name}")
        else:
            failures += 1
            print(f"[aiff] FAILED, kept {src.name}", file=sys.stderr)
    return failures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tracklist", nargs="?", default="tracklist.txt", help="file with one URL or search per line (default: tracklist.txt)")
    p.add_argument("-f", "--format", default="mp3", choices=["mp3", "aiff", "flac", "wav", "m4a"],
                   help="output format (default: mp3 at best VBR quality)")
    p.add_argument("-o", "--out", default="downloads", help="output folder (default: downloads)")
    p.add_argument("-s", "--source", default="youtube", choices=sorted(SEARCH_PREFIX),
                   help="where plain-text searches are looked up (default: youtube)")
    p.add_argument("--playlists", action="store_true", help="when a link points into a playlist, download the whole playlist")
    p.add_argument("--cookies-from-browser", metavar="BROWSER",
                   help="use your browser's login (e.g. chrome, firefox) for age-restricted tracks")
    p.add_argument("--ytdlp-arg", action="append", metavar="ARG", help="extra raw option passed to yt-dlp (repeatable)")
    p.add_argument("-n", "--dry-run", action="store_true", help="show what would be downloaded without downloading")
    args = p.parse_args()

    tracklist = Path(args.tracklist)
    if not tracklist.is_file():
        p.error(f"tracklist not found: {tracklist}")
    if not args.dry_run and shutil.which("ffmpeg") is None:
        p.error("ffmpeg is required for audio conversion: https://ffmpeg.org/download.html")
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        p.error("yt-dlp is not installed. Run: pip install -r requirements.txt")

    entries = read_tracklist(tracklist, args.source)
    if not entries:
        print(f"No tracks in {tracklist}.")
        return 0
    Path(args.out).mkdir(parents=True, exist_ok=True)
    print(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} -> {args.out}/ as {args.format}")
    convert = args.format == "aiff" and not args.dry_run
    fd, done_file = tempfile.mkstemp(suffix=".txt") if convert else (None, None)
    if fd is not None:
        os.close(fd)
    try:
        code = subprocess.call(build_command(args, entries, done_file))
        if convert:
            done = [Path(l) for l in Path(done_file).read_text(encoding="utf-8").splitlines() if l]
            code = code or flac_to_aiff(done)
    finally:
        if done_file:
            os.unlink(done_file)
    return code


if __name__ == "__main__":
    sys.exit(main())
