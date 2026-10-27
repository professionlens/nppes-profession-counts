#!/usr/bin/env python3
"""NPPES: person counts per profession, per state, per year, per sex.

Input : the NPPES full replacement file, or any subset of its columns that keeps
        entity type, the 15 taxonomy slots and primary switches, practice state,
        enumeration date, sex, sole proprietor and the deactivation fields;
        the NUCC taxonomy code set CSV, used to build the code lists.

Output (in --out): nppes_totals.csv, nppes_by_state.csv,
        nppes_by_enumeration_year.csv, nppes_by_sex.csv, nppes_sole_proprietor.csv
"""
import csv
import os
import sys
from collections import defaultdict

import argparse

ap = argparse.ArgumentParser(description="Person counts per profession from the NPPES file.")
ap.add_argument("nppes", help="NPPES full replacement file (npidata_pfile_*.csv) or a column subset of it")
ap.add_argument("nucc", help="NUCC taxonomy code set CSV (nucc_taxonomy_*.csv)")
ap.add_argument("--out", default="counts", help="output directory (default: counts)")
ARGS = ap.parse_args()
OUT = ARGS.out

SLIM = ARGS.nppes
NUCC = ARGS.nucc

# Real US states + DC. Territories and foreign practice addresses are kept in the
# by-state file but flagged, so a state map can drop them without recounting.
STATES = set("""AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS
MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY""".split())


def build_taxonomy_sets():
    """Profession -> set of taxonomy codes, built from the NUCC 26.1 code set."""
    dentists, physicians, nps, pharmacists, vets = set(), set(), set(), set(), set()
    with open(NUCC, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            code = (r.get("Code") or "").strip()
            grouping = (r.get("Grouping") or "").strip()
            classification = (r.get("Classification") or "").strip()
            if not code:
                continue
            if grouping == "Dental Providers" and classification == "Dentist":
                dentists.add(code)
            if grouping == "Allopathic & Osteopathic Physicians":
                physicians.add(code)
            if classification == "Nurse Practitioner" and code.startswith("363L"):
                nps.add(code)
            if classification == "Pharmacist" and code.startswith("1835"):
                pharmacists.add(code)
            if code.startswith("174M"):
                vets.add(code)
    return {
        "dentists": dentists,
        "physicians": physicians,
        "nurse_practitioners": nps,
        "pharmacists": pharmacists,
        "veterinarians": vets,
    }


def main():
    sets = build_taxonomy_sets()
    for k, v in sets.items():
        print(f"taxonomy {k}: {len(v)} codes", file=sys.stderr)

    # code -> profession (the profession sets are disjoint by construction)
    code2prof = {}
    for prof, codes in sets.items():
        for c in codes:
            code2prof[c] = prof

    profs = list(sets)
    totals = defaultdict(int)             # prof -> people (any slot)
    primary_totals = defaultdict(int)     # prof -> people whose PRIMARY taxonomy is that profession
    by_state = defaultdict(int)           # (prof, state) -> people
    by_year = defaultdict(int)            # (prof, year) -> people
    by_sex = defaultdict(int)             # (prof, sex) -> people
    by_sole = defaultdict(int)            # (prof, Y/N/blank) -> people

    read = 0
    org = 0
    deactivated = 0
    blank_entity = 0
    no_tax_match = 0
    multi_prof = 0

    with open(SLIM, newline="", encoding="utf-8", errors="replace") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        ix = {n: i for i, n in enumerate(hdr)}
        i_entity = ix["Entity Type Code"]
        i_state = ix["Provider Business Practice Location Address State Name"]
        i_enum = ix["Provider Enumeration Date"]
        i_deact = ix["NPI Deactivation Date"]
        i_react = ix["NPI Reactivation Date"]
        i_sex = ix["Provider Sex Code"]
        i_sole = ix["Is Sole Proprietor"]
        tax_ix = [ix[f"Healthcare Provider Taxonomy Code_{n}"] for n in range(1, 16)]
        sw_ix = [ix[f"Healthcare Provider Primary Taxonomy Switch_{n}"] for n in range(1, 16)]

        for row in rd:
            read += 1
            ent = row[i_entity].strip()
            if ent == "":
                blank_entity += 1
                continue
            # deactivated and never reactivated -> not a live record
            if row[i_deact].strip() and not row[i_react].strip():
                deactivated += 1
                continue
            if ent != "1":
                org += 1
                continue

            hits = set()
            primary_prof = None
            for k in range(15):
                code = row[tax_ix[k]].strip()
                if not code:
                    continue
                p = code2prof.get(code)
                if p:
                    hits.add(p)
                    if row[sw_ix[k]].strip().upper() == "Y":
                        primary_prof = p
            if not hits:
                no_tax_match += 1
                continue
            if len(hits) > 1:
                multi_prof += 1

            st = row[i_state].strip().upper()
            enum = row[i_enum].strip()
            year = enum[-4:] if len(enum) >= 4 else ""
            sex = row[i_sex].strip().upper() or "(blank)"
            sole = row[i_sole].strip().upper() or "(blank)"

            for p in hits:
                totals[p] += 1
                by_state[(p, st or "(blank)")] += 1
                by_year[(p, year or "(blank)")] += 1
                by_sex[(p, sex)] += 1
                by_sole[(p, sole)] += 1
            if primary_prof:
                primary_totals[primary_prof] += 1

    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(OUT, "nppes_totals.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["profession", "people_any_taxonomy_slot", "people_primary_taxonomy",
                    "taxonomy_codes_used"])
        for p in profs:
            w.writerow([p, totals[p], primary_totals[p], len(sets[p])])

    def dump(path, d, keyname, suppress=True):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["profession", keyname, "people"])
            for (p, k), n in sorted(d.items()):
                w.writerow([p, k, "<5" if (suppress and 0 < n < 5) else n])

    with open(os.path.join(OUT, "nppes_by_state.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["profession", "state", "people", "is_us_state_or_dc"])
        for (p, s), n in sorted(by_state.items()):
            w.writerow([p, s, "<5" if 0 < n < 5 else n, "yes" if s in STATES else "no"])

    dump(os.path.join(OUT, "nppes_by_enumeration_year.csv"), by_year, "enumeration_year")
    dump(os.path.join(OUT, "nppes_by_sex.csv"), by_sex, "sex_code")
    dump(os.path.join(OUT, "nppes_sole_proprietor.csv"), by_sole, "is_sole_proprietor")

    print(f"rows read          {read}")
    print(f"blank entity type  {blank_entity}  (deactivated-only stubs)")
    print(f"deactivated        {deactivated}")
    print(f"organisations (2)  {org}")
    print(f"no taxonomy match  {no_tax_match}")
    print(f"people in >1 prof  {multi_prof}")
    for p in profs:
        print(f"  {p:22s} {totals[p]:>9,}  (primary {primary_totals[p]:,})")


if __name__ == "__main__":
    main()
