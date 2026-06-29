# adif2cabrillo

Convert amateur-radio **ADIF** logs (`.adi` / `.adif`) to **Cabrillo 3.0**
contest logs. Ships as both a standalone command-line tool and a
[Claude](https://claude.ai) skill.

Default profile: **ARRL Field Day** (`CONTEST: ARRL-FD`), exchange = operating
class + ARRL/RAC section (e.g. `1D GA`).

Most ham loggers (MacLoggerDX, WSJT-X, fldigi, Log4OM, HAMRS, N3FJP) export ADIF
but ARRL and CQ contests want Cabrillo. This bridges that gap with no external
dependencies.

## Quick start (command line)

```bash
python3 scripts/adif2cabrillo.py myfieldday.adi -o myfieldday.log \
  --callsign KK4BSA \
  --club "NE GA Council Radio Club" \
  --cat-operator MULTI-OP --cat-station PORTABLE \
  --cat-transmitter ONE --cat-power LOW --cat-mode MIXED
```

`--class` and `--section` are auto-detected from the ADIF `STX_STRING` field if
present; pass them explicitly otherwise. See `--help` for all options.

## Use as a Claude skill

This repo is structured as a Claude skill (`SKILL.md` at the root). Install it
in Claude Code / Cowork by placing the folder under your skills directory, or
package it with the `skill-creator` tooling. Then just ask Claude:

> Convert my Field Day ADIF export to Cabrillo. My call is KK4BSA, class 1D, section GA.

Claude reads `SKILL.md`, runs the script, and hands back the `.log` file.

## What it does

- Length-correct ADIF parsing (`<FIELD:len>value`), tolerant of missing `<EOR>`.
- Mode mapping to Cabrillo `CW` / `PH` / `DG` (FT8/FT4/RTTY/PSK → DG; FM → PH for FD).
- Frequency to integer kHz; chronological sort; CRLF output per the Cabrillo spec.
- Field Day exchange from `STX_STRING` / `SRX_STRING`, with `CLASS`+`ARRL_SECT`
  fallbacks for other loggers.
- QSO-points estimate printed to stderr (phone 1, CW/digital 2 × power multiplier).

## What it does NOT do

- It is **not** a full Field Day entry. Submit the ARRL summary sheet at
  <https://field-day.arrl.org/fdentry.php>; the Cabrillo attaches there in lieu
  of the dupe sheet (Field Day Rule 8.7).
- It does not compute bonus points or remove duplicate QSOs.

## Other contests

Pass `--contest CQ-WW-CW` etc. The QSO-line layout is currently the Field Day
class+section exchange; other exchanges (serial, zone, grid) would need a small
template addition — PRs welcome.

## Privacy & security

Runs fully offline, no dependencies, no telemetry. ADIF logs hold personal data
(names, emails, locations of stations you worked); the Cabrillo output copies
**only** contest fields and omits all personal fields. Review before publishing.

## References

- Cabrillo specification — World Wide Radio Operators Foundation: <https://wwrof.org/cabrillo/>
- ARRL Cabrillo format & tutorial: <http://www.arrl.org/cabrillo-format-tutorial>
- ARRL Field Day: <https://field-day.arrl.org/>

## License

MIT — see [LICENSE](LICENSE).
