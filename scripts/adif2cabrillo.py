#!/usr/bin/env python3
"""
adif2cabrillo.py - Convert an ADIF log to a Cabrillo 3.0 contest log.

Default contest profile is ARRL Field Day (CONTEST: ARRL-FD), whose exchange is
"<class> <section>" (e.g. "1D GA"). The tool reads ADIF QSO records exported by
loggers such as MacLoggerDX, N3FJP, WSJT-X, HAMRS, fldigi, Log4OM, etc., and emits
a Cabrillo file suitable for upload at https://contest-log-submission.arrl.org/
or as the dupe-sheet attachment at https://field-day.arrl.org/fdentry.php.

No third-party dependencies. Python 3.7+.

Cabrillo spec: https://wwrof.org/cabrillo/
ARRL Field Day rules: https://field-day.arrl.org/

Author: built as a reusable Claude skill. MIT licensed.
"""

import argparse
import re
import sys
from datetime import datetime

# --------------------------------------------------------------------------- #
# ADIF parsing
# --------------------------------------------------------------------------- #

# Matches an ADIF field spec: <NAME:LENGTH[:TYPE]>  then we read LENGTH chars.
_FIELD_RE = re.compile(r"<([A-Za-z0-9_]+):(\d+)(?::[^>]*)?>", re.IGNORECASE)
_EOH_RE = re.compile(r"<EOH>", re.IGNORECASE)
_EOR_RE = re.compile(r"<EOR>", re.IGNORECASE)


def parse_adif(text):
    """Parse ADIF text into a list of QSO dicts (field names upper-cased).

    Length-based parsing per the ADIF spec, so values containing spaces, commas,
    or angle brackets are handled correctly.
    """
    # Strip the optional header (everything up to and including <EOH>).
    m = _EOH_RE.search(text)
    body = text[m.end():] if m else text

    records = []
    current = {}
    i = 0
    n = len(body)
    while i < n:
        # Look for the next tag.
        lt = body.find("<", i)
        if lt == -1:
            break
        # End-of-record?
        eor = _EOR_RE.match(body, lt)
        if eor:
            if current:
                records.append(current)
                current = {}
            i = eor.end()
            continue
        fm = _FIELD_RE.match(body, lt)
        if not fm:
            # Unknown/garbage tag; skip this '<'.
            i = lt + 1
            continue
        name = fm.group(1).upper()
        length = int(fm.group(2))
        val_start = fm.end()
        value = body[val_start:val_start + length]
        current[name] = value
        i = val_start + length

    if current:  # tolerate a missing final <EOR>
        records.append(current)
    return records


# --------------------------------------------------------------------------- #
# Mode and frequency mapping
# --------------------------------------------------------------------------- #

# Cabrillo modes: CW, PH (phone), FM, RY (RTTY), DG (digital).
# ARRL Field Day buckets everything into CW / PH / DG (FM counts as phone).
_CW_MODES = {"CW"}
_PHONE_MODES = {"SSB", "USB", "LSB", "AM", "FM", "PHONE", "PH", "DIGITALVOICE",
                "C4FM", "DMR", "DSTAR", "FUSION"}
# Anything else that is a keyboard/data mode is treated as digital (DG).
_DIGITAL_HINTS = {"FT8", "FT4", "MFSK", "RTTY", "PSK", "PSK31", "PSK63", "PSK125",
                  "JT65", "JT9", "JS8", "OLIVIA", "CONTESTI", "HELL", "DOMINO",
                  "THOR", "MT63", "FSK441", "JT4", "JT6M", "QRA64", "Q65",
                  "ROS", "PAX", "PACKET", "AMTOR", "PACTOR", "GTOR", "DATA",
                  "DIGITAL", "DIG"}


def adif_mode_to_cabrillo(mode, submode, fd_phone_as_ph=True):
    """Return a Cabrillo mode token (CW / PH / DG / FM / RY)."""
    mode = (mode or "").upper().strip()
    submode = (submode or "").upper().strip()
    candidates = [mode, submode]

    if mode in _CW_MODES:
        return "CW"
    if mode in _PHONE_MODES:
        # For Field Day FM is scored as phone; emit PH unless caller wants FM.
        if mode == "FM" and not fd_phone_as_ph:
            return "FM"
        return "PH"
    # Digital: most contest/data modes.
    for c in candidates:
        if c in _DIGITAL_HINTS:
            return "DG"
    # RTTY special-case (Cabrillo "RY"); but Field Day lumps it under DG.
    if "RTTY" in candidates:
        return "DG"
    # Fall back to digital for anything unrecognised but clearly not CW/phone.
    return "DG"


def adif_freq_to_khz(freq_mhz, band):
    """Convert an ADIF FREQ (MHz, string) to integer kHz for Cabrillo.

    Falls back to a representative band-edge frequency if FREQ is missing.
    """
    if freq_mhz:
        try:
            return str(int(round(float(freq_mhz) * 1000)))
        except ValueError:
            pass
    band_khz = {
        "160M": "1800", "80M": "3500", "60M": "5350", "40M": "7000",
        "30M": "10100", "20M": "14000", "17M": "18100", "15M": "21000",
        "12M": "24900", "10M": "28000", "6M": "50", "2M": "144",
        "1.25M": "222", "70CM": "432",
    }
    return band_khz.get((band or "").upper(), "0")


# Valid ARRL/RAC Field Day sections (plus DX). Used to warn on typos.
VALID_SECTIONS = {
    # ARRL
    "CT", "EMA", "ME", "NH", "RI", "VT", "WMA", "ENY", "NLI", "NNY", "SNJ",
    "NNJ", "WNY", "DE", "EPA", "MDC", "WPA", "AL", "GA", "KY", "NC", "NFL",
    "SC", "SFL", "TN", "VA", "VI", "WCF", "PR", "AR", "LA", "MS", "NM", "NTX",
    "OK", "STX", "WTX", "EB", "LAX", "ORG", "SB", "SCV", "SDG", "SF", "SJV",
    "SV", "PAC", "NV", "AZ", "EWA", "ID", "MT", "NNV", "ON", "UT", "WWA", "WY",
    "AK", "OR", "IA", "KS", "MN", "MO", "ND", "NE", "SD", "IL", "IN", "WI",
    "MI", "OH", "WV", "CO",
    # RAC (Canada)
    "NL", "MAR", "QC", "ONE", "ONN", "ONS", "GTA", "MB", "SK", "AB", "BC",
    "TER",
    # DX entrants
    "DX",
}


# --------------------------------------------------------------------------- #
# Exchange parsing
# --------------------------------------------------------------------------- #

def split_exchange(s):
    """Split a Field Day exchange string like '1D GA' or '3A ONE' into
    (class, section). Returns (None, None) if it can't."""
    if not s:
        return (None, None)
    parts = s.split()
    if len(parts) >= 2:
        return (parts[0].upper(), " ".join(parts[1:]).upper())
    if len(parts) == 1:
        return (parts[0].upper(), None)
    return (None, None)


def received_exchange(rec, default_section=None):
    """Determine the worked station's (class, section) from a QSO record.

    Preference order:
      1. SRX_STRING (full FD exchange, e.g. '5A TN')
      2. CLASS + ARRL_SECT / STATE
    """
    cls, sec = split_exchange(rec.get("SRX_STRING"))
    if cls and sec:
        return cls, sec
    # Fallbacks for loggers that store the pieces separately.
    cls = cls or rec.get("CLASS") or rec.get("APP_N3FJP_CLASS")
    sec = (sec or rec.get("ARRL_SECT") or rec.get("APP_N3FJP_SECTION")
           or rec.get("STATE") or default_section)
    if cls:
        cls = cls.upper()
    if sec:
        sec = sec.upper()
    return cls, sec


# --------------------------------------------------------------------------- #
# Cabrillo generation
# --------------------------------------------------------------------------- #

def build_qso_line(rec, my_call, my_class, my_section, fd_phone_as_ph=True):
    """Build one 'QSO:' line, or None if the record can't be mapped."""
    freq = adif_freq_to_khz(rec.get("FREQ"), rec.get("BAND"))
    mode = adif_mode_to_cabrillo(rec.get("MODE"), rec.get("SUBMODE"),
                                 fd_phone_as_ph)

    qd = rec.get("QSO_DATE", "")
    if len(qd) == 8:
        date = f"{qd[0:4]}-{qd[4:6]}-{qd[6:8]}"
    else:
        date = qd

    t = rec.get("TIME_ON") or rec.get("TIME_OFF") or ""
    time = t[0:4] if len(t) >= 4 else t  # HHMM

    their_call = (rec.get("CALL") or "").upper()
    their_class, their_section = received_exchange(rec)

    if not (their_call and their_class and their_section):
        return None, f"missing call/class/section (CALL={their_call!r})"

    # Field Day QSO line:
    #   QSO: freq mo date time SENTcall SENTclass SENTsect RCVDcall RCVDclass RCVDsect
    return (
        "QSO: {freq:>5} {mo:>2} {date} {time} "
        "{sc:<10} {scl:<3} {ssec:<5} "
        "{rc:<10} {rcl:<3} {rsec:<5}"
    ).format(
        freq=freq, mo=mode, date=date, time=time,
        sc=my_call, scl=my_class, ssec=my_section,
        rc=their_call, rcl=their_class, rsec=their_section,
    ).rstrip(), None


def build_cabrillo(records, cfg):
    """Return (cabrillo_text, qso_count, warnings)."""
    lines = []
    A = lines.append
    A("START-OF-LOG: 3.0")
    A(f"CONTEST: {cfg['contest']}")
    A(f"CALLSIGN: {cfg['callsign']}")
    A(f"LOCATION: {cfg['section']}")
    A(f"CATEGORY-OPERATOR: {cfg['cat_operator']}")
    A(f"CATEGORY-STATION: {cfg['cat_station']}")
    A(f"CATEGORY-TRANSMITTER: {cfg['cat_transmitter']}")
    A(f"CATEGORY-POWER: {cfg['cat_power']}")
    A(f"CATEGORY-ASSISTED: {cfg['cat_assisted']}")
    A(f"CATEGORY-BAND: {cfg['cat_band']}")
    A(f"CATEGORY-MODE: {cfg['cat_mode']}")
    if cfg.get("claimed_score") is not None:
        A(f"CLAIMED-SCORE: {cfg['claimed_score']}")
    if cfg.get("club"):
        A(f"CLUB: {cfg['club']}")
    if cfg.get("operators"):
        A(f"OPERATORS: {cfg['operators']}")
    if cfg.get("name"):
        A(f"NAME: {cfg['name']}")
    for addr in cfg.get("address", []):
        A(f"ADDRESS: {addr}")
    if cfg.get("email"):
        A(f"EMAIL: {cfg['email']}")
    A(f"CREATED-BY: adif2cabrillo (Claude skill) {datetime.utcnow():%Y-%m-%d}")
    for sb in cfg.get("soapbox", []):
        A(f"SOAPBOX: {sb}")

    warnings = []
    qso_lines = []
    for idx, rec in enumerate(records, 1):
        line, err = build_qso_line(
            rec, cfg["callsign"], cfg["class"], cfg["section"],
            cfg["fd_phone_as_ph"])
        if line:
            qso_lines.append((rec, line))
        else:
            warnings.append(f"  record {idx}: skipped ({err})")

    # Sort chronologically (Cabrillo expects time order; nice-to-have).
    def sort_key(item):
        r = item[0]
        return (r.get("QSO_DATE", ""), r.get("TIME_ON", ""))
    qso_lines.sort(key=sort_key)

    for _, line in qso_lines:
        A(line)
    A("END-OF-LOG:")
    return "\n".join(lines) + "\n", len(qso_lines), warnings


def estimate_fd_score(records, power_mult, fd_phone_as_ph=True):
    """Rough QSO-point estimate for ARRL Field Day (no bonus points).
    Phone=1, CW=2, Digital=2; total points * power multiplier."""
    pts = 0
    for r in records:
        mo = adif_mode_to_cabrillo(r.get("MODE"), r.get("SUBMODE"),
                                   fd_phone_as_ph)
        pts += 1 if mo in ("PH", "FM") else 2
    return pts, pts * power_mult


def inspect(records):
    """Print a human-readable summary of the log to help interview the operator.

    Writes nothing; used to confirm callsign, class, and section before a real
    conversion (these are not always reliably present in the ADIF and change
    year to year)."""
    from collections import Counter

    def distinct(field):
        return sorted({(r.get(field) or "").strip()
                       for r in records if (r.get(field) or "").strip()})

    call_candidates = []
    for f in ("OPERATOR", "STATION_CALLSIGN", "OWNER_CALLSIGN", "MY_CALL"):
        for v in distinct(f):
            call_candidates.append(f"{v} (from {f})")

    bands = Counter((r.get("BAND") or "?").upper() for r in records)
    modes = Counter(adif_mode_to_cabrillo(r.get("MODE"), r.get("SUBMODE"))
                    for r in records)

    rx_sections = set()
    for r in records:
        _, sec = received_exchange(r)
        if sec:
            rx_sections.add(sec)
    unknown = sorted(s for s in rx_sections if s not in VALID_SECTIONS)

    out = sys.stdout
    print("ADIF log inspection", file=out)
    print(f"  QSO records: {len(records)}", file=out)
    print("  Callsign candidates (the submission call may NOT be in the file):",
          file=out)
    if call_candidates:
        for c in call_candidates:
            print(f"    - {c}", file=out)
    else:
        print("    - (none found - you must supply --callsign)", file=out)
    print(f"  Sent exchange STX_STRING: {distinct('STX_STRING') or '(none)'}",
          file=out)
    print(f"  Bands: {dict(bands)}", file=out)
    print(f"  Cabrillo modes: {dict(modes)}", file=out)
    if unknown:
        print(f"  WARNING unrecognized received sections: {unknown}", file=out)
    print("\nNext: confirm CALLSIGN (watch for an alternate/special call),",
          file=out)
    print("CLASS (#transmitters + letter A-F), and SECTION, then run without",
          file=out)
    print("--inspect to write the Cabrillo file.", file=out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Convert an ADIF log to Cabrillo 3.0 (default: ARRL Field Day).")
    p.add_argument("input", help="input ADIF file (.adi/.adif)")
    p.add_argument("-o", "--output", help="output Cabrillo file (default: stdout)")
    p.add_argument("--inspect", action="store_true",
                   help="summarize the log (callsign/class/section candidates) and exit")
    p.add_argument("--callsign", default=None, help="your station callsign, e.g. KK4BSA")
    p.add_argument("--class", dest="fdclass", default=None,
                   help="your Field Day class, e.g. 1D (default: read from STX_STRING)")
    p.add_argument("--section", default=None,
                   help="your ARRL/RAC section, e.g. GA (default: read from STX_STRING)")
    p.add_argument("--contest", default="ARRL-FD", help="Cabrillo CONTEST tag")
    p.add_argument("--club", default="", help="club name")
    p.add_argument("--operators", default="", help="space/comma list of operator calls")
    p.add_argument("--name", default="", help="submitter name")
    p.add_argument("--address", action="append", default=[], help="address line (repeatable)")
    p.add_argument("--email", default="", help="contact email")
    p.add_argument("--soapbox", action="append", default=[], help="SOAPBOX line (repeatable)")
    p.add_argument("--cat-operator", default="MULTI-OP")
    p.add_argument("--cat-station", default="PORTABLE")
    p.add_argument("--cat-transmitter", default="ONE")
    p.add_argument("--cat-power", default="LOW",
                   help="HIGH / LOW / QRP (LOW = <=100W typical for FD class D)")
    p.add_argument("--cat-assisted", default="ASSISTED")
    p.add_argument("--cat-band", default="ALL")
    p.add_argument("--cat-mode", default="MIXED")
    p.add_argument("--claimed-score", type=int, default=None)
    p.add_argument("--power-mult", type=int, default=2,
                   help="FD power multiplier for score estimate (1/2/5; default 2)")
    p.add_argument("--fm-as-fm", action="store_true",
                   help="emit FM instead of PH for FM contacts")
    args = p.parse_args(argv)

    try:
        with open(args.input, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        p.error(f"cannot read input: {e}")

    records = parse_adif(text)
    if not records:
        p.error("no QSO records found in input")

    if args.inspect:
        inspect(records)
        return 0

    if not args.callsign:
        p.error("--callsign is required (run --inspect first to find candidates)")

    # Determine our sent class/section: CLI overrides, else infer from STX_STRING.
    my_class = args.fdclass
    my_section = args.section
    if not (my_class and my_section):
        for r in records:
            c, s = split_exchange(r.get("STX_STRING"))
            my_class = my_class or c
            my_section = my_section or s
            if my_class and my_section:
                break
    if not (my_class and my_section):
        p.error("could not determine your class/section; pass --class and --section")

    cfg = {
        "contest": args.contest,
        "callsign": args.callsign.upper(),
        "class": my_class.upper(),
        "section": my_section.upper(),
        "club": args.club,
        "operators": args.operators,
        "name": args.name,
        "address": args.address,
        "email": args.email,
        "soapbox": args.soapbox,
        "cat_operator": args.cat_operator,
        "cat_station": args.cat_station,
        "cat_transmitter": args.cat_transmitter,
        "cat_power": args.cat_power,
        "cat_assisted": args.cat_assisted,
        "cat_band": args.cat_band,
        "cat_mode": args.cat_mode,
        "claimed_score": args.claimed_score,
        "fd_phone_as_ph": not args.fm_as_fm,
    }

    if cfg["section"] not in VALID_SECTIONS:
        print(f"WARNING: '{cfg['section']}' is not a recognized ARRL/RAC "
              f"section - double-check before submitting.", file=sys.stderr)

    cab, count, warnings = build_cabrillo(records, cfg)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(cab)
        qpts, score = estimate_fd_score(records, args.power_mult, cfg["fd_phone_as_ph"])
        print(f"Wrote {count} QSO(s) to {args.output}", file=sys.stderr)
        print(f"Your exchange: {cfg['class']} {cfg['section']}  ({cfg['callsign']})",
              file=sys.stderr)
        print(f"QSO points (no bonuses): {qpts}  x{args.power_mult} = {score}",
              file=sys.stderr)
        if warnings:
            print(f"{len(warnings)} record(s) skipped:", file=sys.stderr)
            print("\n".join(warnings), file=sys.stderr)
    else:
        sys.stdout.write(cab)
        for w in warnings:
            print(w, file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
