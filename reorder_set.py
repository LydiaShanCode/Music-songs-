#!/usr/bin/env python3
"""Number the songs in a folder to match the order of a set list CSV.

    python3 reorder_set.py ~/Music/SET-II            # preview only, changes nothing
    python3 reorder_set.py ~/Music/SET-II --apply    # rename the files
    python3 reorder_set.py ~/Music/SET-II --undo     # put the old names back

Files are matched to the CSV by song title (and artist) in the file name and
renamed to "001 - <original name>", "002 - ...", so they sort in set order.
An ordered playlist (SET-II.m3u8) is also written for Rekordbox/Serato/etc.
Safe to run again: existing "NNN - " prefixes are replaced, not stacked.
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

AUDIO = {".mp3", ".aiff", ".aif", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".alac"}
PREFIX = re.compile(r"^\d{3} - ")
UNDO_FILE = ".reorder-undo.json"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def score(row, file_key: str) -> float:
    title = norm(row["Song"])
    # Also try the title without "(feat. ...)", "- X Remix", "(VIP)" etc.
    core = norm(re.split(r"\s[-(\[]", row["Song"])[0])
    s = 0.0
    if title and title in file_key:
        s = 100 + len(title)
    elif core and len(core) >= 3 and core in file_key:
        s = 50 + len(core)
    if not s:
        return 0
    artists = [norm(a) for a in row["Artist"].split(",") if norm(a)]
    s += 20 * sum(a in file_key for a in artists)
    return s


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", type=Path)
    p.add_argument("--csv", type=Path, default=Path(__file__).with_name("set-ii.csv"))
    p.add_argument("--apply", action="store_true", help="actually rename the files")
    p.add_argument("--undo", action="store_true", help="restore the names from before the last --apply")
    args = p.parse_args()
    folder = args.folder.expanduser()
    if not folder.is_dir():
        p.error(f"folder not found: {folder}")

    if args.undo:
        undo = folder / UNDO_FILE
        if not undo.is_file():
            p.error("nothing to undo")
        for new, old in json.loads(undo.read_text(encoding="utf-8")).items():
            if (folder / new).exists():
                (folder / new).rename(folder / old)
        undo.unlink()
        print("Restored original names.")
        return 0

    rows = list(csv.DictReader(args.csv.open(encoding="utf-8-sig")))
    files = sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in AUDIO)
    keys = {f: norm(PREFIX.sub("", f.stem)) for f in files}

    # Best-first matching so each file and each song is used at most once.
    pairs = sorted(((score(r, keys[f]), i, f) for i, r in enumerate(rows) for f in files), key=lambda t: -t[0])
    match, used = {}, set()
    for s, i, f in pairs:
        if s and i not in match and f not in used:
            match[i] = f
            used.add(f)

    plan = []
    for i, row in enumerate(rows):
        f = match.get(i)
        if f is None:
            print(f"  MISSING  {int(row['#']):03d}  {row['Artist']} - {row['Song']}")
            continue
        new = f"{int(row['#']):03d} - {PREFIX.sub('', f.name)}"
        plan.append((f, folder / new))
        print(f"  {int(row['#']):03d}  {f.name}" + ("" if f.name == new else f"\n       -> {new}"))
    extra = [f for f in files if f not in used]
    for f in extra:
        print(f"  NOT IN LIST (left alone)  {f.name}")
    print(f"\nMatched {len(plan)}/{len(rows)} songs; {len(rows) - len(plan)} missing; {len(extra)} extra files.")

    if not args.apply:
        print("Preview only. Run again with --apply to rename.")
        return 0

    undo = {}
    for old, new in plan:
        if old != new:
            old.rename(new)
            undo[new.name] = old.name
    (folder / UNDO_FILE).write_text(json.dumps(undo, indent=1, ensure_ascii=False), encoding="utf-8")
    playlist = folder / f"{folder.name}.m3u8"
    playlist.write_text("#EXTM3U\n" + "".join(n.name + "\n" for _, n in plan), encoding="utf-8")
    print(f"Renamed {len(undo)} files. Playlist: {playlist.name}. Undo with --undo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
