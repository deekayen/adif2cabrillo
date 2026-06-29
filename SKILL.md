---
name: adif2cabrillo
description: >-
  Convert a ham radio ADIF log (.adi/.adif) into a Cabrillo 3.0 contest log,
  defaulting to ARRL Field Day (CONTEST: ARRL-FD). Trigger whenever the user
  mentions converting, exporting, or submitting a Field Day log, an ADIF/ADI
  file, or a Cabrillo/.cbr/.log file — e.g. "convert my Field Day ADIF export to
  Cabrillo", "turn my .adi into Cabrillo", "make a Cabrillo file for Field Day",
  "ADIF to Cabrillo", "prepare my log for fdentry". Works with exports from
  MacLoggerDX, WSJT-X, N3FJP, HAMRS, fldigi, Log4OM, and similar loggers.
license: MIT
---

# ADIF → Cabrillo converter (ARRL Field Day)

Converts an ADIF log into a Cabrillo 3.0 file. Default profile is **ARRL Field
Day** (`CONTEST: ARRL-FD`); the Field Day exchange is the operating *class* plus
the ARRL/RAC *section*, e.g. `1D GA`.

`scripts/adif2cabrillo.py` is dependency-free Python 3. Run it from the skill
directory.

## ⚠️ Required workflow: interview the operator BEFORE converting

The submission callsign, class, and section are **not always reliably present in
the ADIF**, and they change from year to year. Do not silently trust the file.
Always run this interview first, then convert.

### Step 1 — Inspect the file

Run the inspector to see what the log actually contains:

```bash
python3 scripts/adif2cabrillo.py --inspect INPUT.adi
```

This prints, without writing anything: callsign candidates found in the log
(`OPERATOR`, `STATION_CALLSIGN`, `OWNER_CALLSIGN`), the distinct sent exchanges
(`STX_STRING`), distinct received-section values, the bands and modes worked, the
QSO count, and any sections it does not recognize.

### Step 2 — Confirm the submission CALLSIGN (alternate-callsign reminder)

Field Day groups frequently operate under a **special or alternate callsign**
that is *different* from the operator's personal call and is often **absent from
the ADIF export** (MacLoggerDX, for example, stores the operator in `OPERATOR`
but not the station/club call). Explicitly remind the user:

> "Your logger recorded the operator as `<OPERATOR>`. Field Day is often run
> under a club call or a special 1×1 callsign (like W4S) that may not be in this
> export. **What callsign did you submit under this year?**"

Use the `AskUserQuestion` tool. Offer the detected candidates plus "Other" so the
user can type a different/alternate call. Never assume last year's call carries
over.

### Step 3 — Build the CLASS together

The Field Day class is **<number of transmitters><class letter>**, e.g. `1D`,
`3A`, `2F`. Construct it with the user — do not just copy `STX_STRING`, since the
group's class can change year to year:

- Ask the **number of simultaneous transmitters** (1–20+).
- Ask the **class letter**:
  - `A` — Club/group portable (3+ people), not at a permanent station
  - `B` — 1 or 2 person portable
  - `C` — Mobile
  - `D` — Home station on commercial power
  - `E` — Home station on emergency power
  - `F` — Emergency Operations Center (EOC)
  - Append `B` for the 5 W battery variants (Class A-Battery, etc.) only if applicable
- Show the user what was in the log last (`STX_STRING`) as a default, but confirm.

### Step 4 — Confirm the SECTION

Ask for the ARRL/RAC section abbreviation (e.g. `GA`). Validate it against
`reference/arrl_sections.txt`. DX stations use `DX`. Pre-fill from `STX_STRING`
but confirm.

### Step 5 — Confirm category/power details

Confirm (defaults in parentheses): operator category (MULTI-OP), station
(PORTABLE), transmitters (from class number), power class (LOW = ≤100 W; QRP =
≤5 W; HIGH otherwise), and the power multiplier for the score estimate (×2 for
≤150 W, ×5 for the 5 W natural-power level, ×1 for >100 W on classes A/B/C).

### Step 6 — Convert, validate, deliver

```bash
python3 scripts/adif2cabrillo.py INPUT.adi -o OUTPUT.log \
  --callsign <CONFIRMED-CALL> --class <CONFIRMED-CLASS> --section <CONFIRMED-SECTION> \
  --club "<CLUB NAME>" --cat-power <POWER> --power-mult <N>
```

Then sanity-check the output (QSO count matches, no skipped records, all
sections valid) and present the `.log` file.

## Field mapping (Field Day)

| Cabrillo field      | ADIF source                                            |
|---------------------|--------------------------------------------------------|
| freq (kHz)          | `FREQ` (MHz × 1000, rounded); falls back to `BAND`     |
| mode (CW/PH/DG)     | `MODE`/`SUBMODE` → CW, phone→PH, data→DG (FM→PH for FD) |
| date / time (UTC)   | `QSO_DATE` / `TIME_ON`                                  |
| my call/class/sect  | from the interview (Steps 2–4)                          |
| their call          | `CALL`                                                  |
| their class+section | `SRX_STRING` (e.g. "5A TN"), else `CLASS`+`ARRL_SECT`   |

Mode points: phone (SSB/FM/AM) → `PH` = 1 pt; CW = 2 pts; digital
(FT8/FT4/RTTY/PSK/MFSK/…) → `DG` = 2 pts. FM counts as phone for Field Day.

## Important reminders for the operator

- **Cabrillo is not a complete Field Day entry.** Submit the summary sheet at
  https://field-day.arrl.org/fdentry.php; the Cabrillo attaches there in lieu of
  the dupe sheet (Field Day Rule 8.7).
- The stderr score line is a **QSO-points estimate only** — no bonus points, no
  dupe removal. Use it as a sanity check.
- The tool does not remove duplicate QSOs.

## Other contests

Pass `--contest CQ-WW-CW` etc. The current QSO-line layout is the Field Day
class+section exchange; other exchanges (serial, zone, grid) would need a small
template addition.

## Privacy / security

Runs entirely locally, no network, no dependencies. ADIF logs contain personal
data (worked stations' names, emails, addresses in `NAME`/`EMAIL`/`QTH`). The
Cabrillo output copies **only** contest fields (call, exchange, time, band,
mode) and omits all personal fields. Review before sharing publicly.
