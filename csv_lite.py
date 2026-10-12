#!/usr/bin/env python3
"""csv_lite - two small, safe CSV cleaners in one file (standard library only).

  python csv_lite.py trim   FILE [--apply]
      Strip spaces, turn non-breaking spaces into normal ones, remove zero-width
      characters and collapse repeated spaces in every cell.

  python csv_lite.py dedupe FILE [--keys email,name] [--apply]
      Remove duplicate rows (ignores case and surrounding spaces).

Safety: no network access. Your input file is never modified or deleted.
Without --apply nothing is written (dry run): you only get a summary.
With --apply a NEW file is written next to the input (<name>.trimmed.csv or
<name>.deduped.csv). An existing file is only replaced with --overwrite.
"""
import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path

csv.field_size_limit(2**30)

_INVISIBLE = {0x200B: None, 0x200C: None, 0x200D: None, 0x2060: None, 0xFEFF: None,
              0x00A0: " ", 0x202F: " ", 0x2009: " ", 0x2007: " "}


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(2)


def read_csv(path, encoding, delimiter):
    p = Path(path)
    if not p.is_file():
        die(f"File not found: {path}")
    raw = p.read_bytes()
    if encoding == "auto":
        if raw.startswith(b"\xef\xbb\xbf"):
            encoding = "utf-8-sig"
        else:
            try:
                raw.decode("utf-8")
                encoding = "utf-8"
            except UnicodeDecodeError:
                encoding = "cp1252"
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError) as exc:
        die(f"Cannot decode {path} as {encoding}: {exc}. Try --encoding cp1252 or latin-1.")
    text = text.lstrip("﻿")
    if delimiter == "auto":
        delimiter = sniff(text)
    rows = [r for r in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
            if any(c.strip() for c in r)]
    if not rows:
        die(f"{path} is empty.")
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows[0], rows[1:], encoding, delimiter


def sniff(text):
    lines = [ln for ln in text.splitlines()[:25] if ln.strip()]
    best, best_score = ",", 0
    for cand in (",", ";", "\t", "|"):
        counts = [len(r) for r in csv.reader(lines, delimiter=cand)]
        if not counts or counts[0] < 2:
            continue
        score = sum(1 for c in counts if c == counts[0]) * 1000 + counts[0]
        if score > best_score:
            best, best_score = cand, score
    return best


def clean(value):
    s = value.translate(_INVISIBLE)
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r" ?(\r\n|\r|\n) ?", "\n", s)
    return s.strip()


def find_col(headers, name):
    norm = lambda s: re.sub(r"[\W_]+", "", s).casefold()
    for i, h in enumerate(headers):
        if h == name or norm(h) == norm(name):
            return i
    die(f"Column '{name}' not found. Columns: " + ", ".join(repr(h) for h in headers))


def write_new(args, tag, headers, rows, delimiter):
    src = Path(args.input)
    out = Path(args.output) if args.output else src.with_name(src.stem + tag + ".csv")
    if os.path.normcase(str(out.resolve())) == os.path.normcase(str(src.resolve())):
        die("Refusing to overwrite the input file. Choose a different -o.")
    if out.is_dir():
        die(f"{out} is a folder.")
    if out.exists() and not args.overwrite:
        die(f"{out} already exists. Use --overwrite or choose another name with -o.")
    with open(out, "w", encoding=args.out_encoding, newline="") as fh:
        w = csv.writer(fh, delimiter=delimiter, lineterminator="\n")
        w.writerow(headers)
        w.writerows(rows)
    return out


def show(events, limit):
    for e in events[:limit]:
        print("   ", e)
    if len(events) > limit:
        print(f"    ... and {len(events) - limit} more (use --show N)")


def cmd_trim(args):
    headers, rows, enc, delim = read_csv(args.input, args.encoding, args.delimiter)
    events, changed = [], 0
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            new = clean(v)
            if new != v:
                row[ci] = new
                changed += 1
                events.append(f"row {ri + 2} | {headers[ci]} | {v!r} -> {new!r}")
    print(f"== trim{'' if args.apply else ' - DRY RUN, nothing written'} ==")
    print(f"  input: {args.input} (encoding {enc}, delimiter {delim!r}, {len(rows)} data rows)")
    print(f"  cells changed: {changed}")
    show(events, args.show)
    if args.apply:
        print("  written:", write_new(args, ".trimmed", headers, rows, delim))
    else:
        print("  add --apply to write a cleaned copy.")


def cmd_dedupe(args):
    headers, rows, enc, delim = read_csv(args.input, args.encoding, args.delimiter)
    if args.keys:
        idx = [find_col(headers, k.strip()) for k in args.keys.split(",") if k.strip()]
    else:
        idx = list(range(len(headers)))
    seen, kept, events = {}, [], []
    for ri, row in enumerate(rows):
        key = tuple(clean(row[i]).casefold() for i in idx)
        if not any(key):  # rows with empty keys are never treated as duplicates
            kept.append(row)
            continue
        if key in seen:
            events.append(f"row {ri + 2} duplicates row {seen[key]}: " + " | ".join(key))
        else:
            seen[key] = ri + 2
            kept.append(row)
    print(f"== dedupe{'' if args.apply else ' - DRY RUN, nothing written'} ==")
    print(f"  input: {args.input} (encoding {enc}, delimiter {delim!r}, {len(rows)} data rows)")
    print(f"  compared columns: {', '.join(headers[i] for i in idx)}")
    print(f"  duplicates found: {len(events)} (first occurrence is kept)")
    show(events, args.show)
    if args.apply:
        print("  written:", write_new(args, ".deduped", headers, kept, delim))
    else:
        print("  add --apply to write a copy without the duplicates.")


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="csv_lite", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("trim", cmd_trim), ("dedupe", cmd_dedupe)):
        sp = sub.add_parser(name)
        sp.add_argument("input", metavar="FILE")
        sp.add_argument("--apply", action="store_true", help="write the result (default: dry run)")
        sp.add_argument("-o", "--output", help="output file (default: <name>.trimmed.csv / .deduped.csv)")
        sp.add_argument("--overwrite", action="store_true", help="replace an existing output file")
        sp.add_argument("--encoding", default="auto")
        sp.add_argument("--out-encoding", default="utf-8", help="utf-8 (default) or utf-8-sig for old Excel")
        sp.add_argument("--delimiter", default="auto", help="auto (default) or one character")
        sp.add_argument("--show", type=int, default=10, help="lines of detail to print")
        if name == "dedupe":
            sp.add_argument("--keys", help="comma-separated columns that identify a duplicate (default: all)")
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    if args.delimiter != "auto" and len(args.delimiter) != 1:
        die("--delimiter must be 'auto' or a single character.")
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
