# nppes-profession-counts

Counts people per profession in the NPPES NPI file: dentists, physicians, nurse practitioners, pharmacists and veterinarians, in total, by practice state, by enumeration year, by sex and by sole-proprietor flag.

This is the script [ProfessionLens](https://professionlens.com/) runs for its NPPES counts, for example [how many dentists are there in the US](https://professionlens.com/dentists) and [nurse practitioners by state](https://professionlens.com/lists/nurse-practitioners-by-state). Run on the September 2026 file it reproduces those pages' numbers.

## Rules

- Individuals only (entity type 1). Organisation NPIs are dropped.
- An NPI deactivated and never reactivated is dropped.
- A person counts once per profession if any of the 15 taxonomy slots holds one of that profession's codes. The primary-taxonomy count is written next to it.
- Profession code lists are built from the NUCC taxonomy code set, not hard-coded.
- Counts under 5 are written as `<5`.

## Run

Python 3.9 or later, standard library only.

```
python3 count_nppes.py npidata_pfile.csv nucc_taxonomy_261.csv --out counts
```

- NPPES full replacement file: https://download.cms.gov/nppes/NPI_Files.html
- NUCC taxonomy code set (CSV): https://www.nucc.org/index.php/code-sets-mainmenu-41/provider-taxonomy-mainmenu-40/csv-mainmenu-57

A file with only the needed columns works too. On an 800 MB column subset of the September 2026 file the run took 20 seconds.

## Output

| File | Rows |
|---|---|
| `nppes_totals.csv` | profession, people, people by primary taxonomy |
| `nppes_by_state.csv` | profession, state, people, flag for non-state codes |
| `nppes_by_enumeration_year.csv` | profession, year NPI issued, people |
| `nppes_by_sex.csv` | profession, sex code, people |
| `nppes_sole_proprietor.csv` | profession, sole-proprietor flag, people |

## License

MIT
