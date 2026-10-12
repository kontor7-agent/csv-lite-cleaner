# csv-lite-cleaner

**Fix messy whitespace and remove duplicate rows in any CSV – one file, no dependencies, dry-run by default.**

## What it does

`csv_lite.py` has two commands:

| Command | What it does |
|---|---|
| `trim` | Strips spaces, converts non-breaking spaces, removes zero-width characters, collapses repeated spaces in every cell |
| `dedupe` | Removes duplicate rows (ignoring case and surrounding spaces), over all columns or only `--keys` you choose |

Also: auto-detects encoding (UTF-8 / Windows-1252) and delimiter (`, ; tab |`).

**Safe by design**
- No network access, no telemetry.
- Dry run by default – you see a summary; nothing is written until you add `--apply`.
- Your original file is never modified or deleted. Results go to a new file (`*.trimmed.csv`, `*.deduped.csv`).
- An existing output file is only replaced with `--overwrite`.

## Quick start

```bash
# 1. Preview (writes nothing)
python csv_lite.py trim sample.csv
python csv_lite.py dedupe sample.csv --keys email

# 2. Write cleaned copies
python csv_lite.py trim sample.csv --apply
python csv_lite.py dedupe sample.trimmed.csv --keys email --apply
```

Result: `sample.trimmed.deduped.csv` – the second "Ann Lee" row is gone, because the e-mail matches after trimming and ignoring case.

Handy options: `-o OUT.csv`, `--out-encoding utf-8-sig` (for old Excel), `--delimiter ";"`, `--show 50`.

## Requirements

- Python 3.8+ (standard library only)
- Works on Windows, macOS and Linux

## Limits of the lite version

CSV only (no Excel files), no rules files, no change-report file, no `--keep last/most-complete`.

Created with AI assistance by an automated system.

## Full version

The lite version covers two everyday jobs. The full **CSV & Excel Data Cleaning Toolkit** adds, honestly:

- Normalising dates, phone numbers and numbers (e.g. `1.234,50` vs `1,234.50`) via a YAML/JSON rules file
- Validation with a problem report (required, unique, type, regex, ranges, allowed values)
- Repair of broken encodings (mojibake like `CafÃ©`)
- Merge and split tools, `.xlsx` read/write, keep-last / most-complete dedupe, saved duplicate and change reports
- Sample data, expected outputs, tests and a cheat sheet

Get it here: https://kontor7-agent.github.io/p/csv-cleaning-toolkit-python?s=github

License of this lite version: MIT (see `LICENSE`).
