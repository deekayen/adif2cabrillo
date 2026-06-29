---
name: adif2cabrillo
description: >-
  Convert amateur-radio ADIF logs (.adi/.adif) to Cabrillo 3.0 contest logs.
  Defaults to ARRL Field Day (CONTEST: ARRL-FD, exchange = class + section).
  Use when a ham wants to turn a log exported from MacLoggerDX, WSJT-X, N3FJP,
  HAMRS, fldigi, Log4OM, or similar into a Cabrillo file for upload to ARRL
  (contest-log-submission.arrl.org or field-day.arrl.org). Triggers: "convert
  ADIF to Cabrillo", "Field Day log", ".adi to .cbr", "Cabrillo format".
license: MIT
---

# ADIF → Cabrillo converter

Converts an ADIF log into a Cabrillo 3.0 file. The default profile is **ARRL
Field Day** (`CONTEST: ARRL-FD`), whose exchange is the operating *class* plus
the ARRL/RAC *section*, e.g. `1D GA`.

## When to use

A ham has an ADIF export (most loggers only export ADIF) and the contest sponsor
requires Cabrillo. ARRL accepts a Cabrillo file in lieu of a dupe sheet for Field
Day, and requires Cabrillo for most other ARRL/CQ contests.

## How it works

`scripts/adif2cabrillo.py` is dependency-free Python 3. It:

1. Parses ADIF with proper `<FIELD:length>` length-based reading (so values with
   spaces/commas are safe).
2. Maps each QSO to a Cabrillo `QSO:` line. For Field Day the line is:
   `QSO: freq mode date time MYCALL MYCLASS MYSECT THEIRCALL THEIRCLASS THEIRSECT`
3. Builds a Cabrillo header. Writes the file with CRLF line endings (Cabrillo spec).

### Field mapping (Field Day)

| Cabrillo field      | ADIF source                                            |
|---------------------|--------------------------------------------------------|
| freq (kHz)          | `FREQ` (MHz × 1000, rounded); falls back to `BAND`     |
| mode (CW/PH/DG)     | `MODE`/`SUBMODE` → CW, phone→PH, data→DG (FM→PH for FD) |
| date / time (UTC)   | `QSO_DATE` / `TIME_ON`                                  |
| my call             | `--callsign`                                            |
| my class + section  | `--class` / `--section`, else parsed from `STX_STRING`  |
| their call          | `CALL`                                                  |
| their class+section | `SRX_STRING` (e.g. "5A TN"), else `CLASS`+`ARRL_SECT`   |

Mode buckets: CW counts 2 pts, digital (FT8/FT4/RTTY/PSK/MFSK/…) → `DG` 2 pts,
phone (SSB/FM/AM) → `PH` 1 pt. FM is scored as phone for Field Day.

## Usage

```bash
python3 scripts/adif2cabrillo.py INPUT.adi -o OUTPUT.log \
  --callsign KK4BSA \
  --club "NE GA Council Radio Club" \
  --cat-operator MULTI-OP --cat-station PORTABLE \
  --cat-transmitter ONE --cat-power LOW --cat-mode MIXED
```

If `--class`/`--section` are omitted they are read from the ADIF `STX_STRING`
field (MacLoggerDX, WSJT-X contest mode, and N3FJP all populate it). Override
them when your logger didn't store the sent exchange.

Run `python3 scripts/adif2cabrillo.py -h` for all options (other contests via
`--contest`, address/name/email/soapbox header lines, FM-as-FM, score estimate).

## Important notes for the operator

- **Cabrillo is not a complete Field Day entry.** ARRL still needs the summary
  sheet submitted at https://field-day.arrl.org/fdentry.php; the Cabrillo file
  attaches there in lieu of the dupe sheet. (Rule 8.7.)
- **Verify the header before submitting.** `CATEGORY-*`, `CLAIMED-SCORE`, and
  power class are operator-specific; the converter fills sensible defaults but
  the operator is responsible for correctness.
- The score line printed to stderr is a **QSO-points estimate only** (no bonus
  points, no dupe removal). Use it as a sanity check, not the official score.
- The tool does not remove duplicate QSOs; loggers usually flag dupes already.

## Privacy / security

The script runs entirely locally, has no network access, and no third-party
dependencies. ADIF logs contain personal data (names, emails, addresses of
worked stations from `NAME`/`EMAIL`/`QTH` fields). The Cabrillo output
deliberately includes **only** the contest-relevant fields (call, exchange,
time, band, mode) — none of the personal fields are copied into the output.
Review any file before sharing it publicly.
