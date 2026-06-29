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
`3A`, `2F`. The class-letter definitions, battery variants, power multipliers,
and QSO point values are saved authoritatively in
**`reference/field_day_classes.txt`** (sourced from ARRL Field Day Rules
Sections 4, 5, and 7) — read that file and use it to explain the options; do not
re-derive them or rely on training memory. The rules are static, but the
operator's actual setup is not, so confirm rather than copy `STX_STRING` (class
can change year to year):

- Ask the **number of simultaneous transmitters** (the number prefix, 1–20+).
- Ask the **class letter** (`A`–`F`, plus `AB`/`BB` battery variants), using the
  definitions in the reference file.
- Show last year's value from `STX_STRING` as a default, but confirm.

### Step 4 — Confirm the SECTION

Ask for the ARRL/RAC section abbreviation (e.g. `GA`). Validate it against
`reference/arrl_sections.txt`. DX stations use `DX`. Pre-fill from `STX_STRING`
but confirm.

### Step 5 — Ask the Cabrillo CATEGORY fields (do NOT default these)

These header fields are **not in the ADIF** and must be **asked**, not assumed —
silently defaulting them produced wrong headers in the past. Use
`AskUserQuestion`. Derive a *suggested* answer from the log where possible
(mark it recommended) but always let the user confirm or override:

- **CATEGORY-OPERATOR** (`SINGLE-OP` / `MULTI-OP` / `CHECKLOG`): suggest by the
  distinct `OPERATOR` calls in the log (one operator → SINGLE-OP), but confirm,
  since helpers may not appear in the file.
- **CATEGORY-STATION** (`FIXED` / `PORTABLE` / `MOBILE`): suggest from the class
  letter — `D`/`E` (home) → FIXED, `A`/`B`/`F` (field/EOC) → PORTABLE, `C` →
  MOBILE — then confirm.
- **CATEGORY-POWER** + `--power-mult`: derive a suggestion from `TX_PWR` and the
  multiplier rules in `reference/field_day_classes.txt`, then confirm:
  - ≤5 W on battery/solar/water → `--cat-power QRP --power-mult 5`
  - ≤5 W on mains/generator, or any contact up to 100 W → `--cat-power LOW --power-mult 2`
  - any contact above 100 W → `--cat-power HIGH --power-mult 1`
- **CATEGORY-ASSISTED** (`ASSISTED` / `NON-ASSISTED`): cannot be derived; ask.
  Note it is not used for FD scoring but the header requires it.
- **CATEGORY-MODE** (`DIGI` / `CW` / `SSB` / `MIXED`): suggest from the modes
  actually present (all digital → DIGI; a true mix → MIXED), then confirm.
- **CATEGORY-TRANSMITTER**: set from the class number prefix (1 → ONE, 2 → TWO).

Pass each confirmed value via the matching `--cat-*` flag in Step 6.

### Step 6 — Convert, validate, deliver

```bash
python3 scripts/adif2cabrillo.py INPUT.adi -o OUTPUT.log \
  --callsign <CONFIRMED-CALL> --class <CONFIRMED-CLASS> --section <CONFIRMED-SECTION> \
  --club "<CLUB NAME>" \
  --cat-operator <OP> --cat-station <STATION> --cat-transmitter <TX> \
  --cat-power <POWER> --cat-assisted <ASSISTED> --cat-mode <MODE> --power-mult <N>
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
