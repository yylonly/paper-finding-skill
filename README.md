# paper-finding

A Claude Code skill for finding academic papers via [DBLP](https://dblp.org/) with CCF ranking filtering, IEEE reference generation, and automatic save to `.md` + `.bib`.

## Features

- **DBLP search** with CCF-A/B filtering for Software Engineering and AI venues
- **IEEE-format references** auto-generated
- **Automatic save** to `.md` (literature review) and `.bib` (BibTeX)
- **Polite rate-limiting** — 1.5s delay between DBLP requests to avoid 429 errors

## Quick Start

```bash
# One-shot: search + generate report
python3 scripts/generate_report.py "requirements validation" \
    --ccf ALL --rank A --years 2021-2025 \
    --output ~/papers --basename req-validation-review

# Search only (JSON output)
python3 scripts/search_dblp.py "LLM requirements engineering" \
    --ccf SE --rank A --years 2023-2025 --json

# Fetch BibTeX for known papers
python3 scripts/fetch_bibtex.py conf/icse/Pan024 conf/icse/ChangGY23 -o refs.bib
```

## Scripts

| Script | Purpose |
|--------|---------|
| `generate_report.py` | All-in-one: search + filter + BibTeX + save `.md` + `.bib` |
| `search_dblp.py` | DBLP search with CCF venue filtering (JSON or table output) |
| `fetch_bibtex.py` | Fetch BibTeX by DBLP key (supports batch, rate-limit delay) |

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--ccf SE\|AI\|ALL` | Filter by CCF category | ALL |
| `--rank A\|B\|ALL` | Filter by CCF rank | ALL |
| `--years YYYY-YYYY` | Year range | Last 5 years |
| `--hits N` | Max DBLP hits per query | 100 |
| `--output DIR` | Output directory | Current dir |
| `--basename NAME` | Base filename (no extension) | Auto-generated |

## Output Files

Two files are saved side-by-side:

- `NAME.md` — Literature review with:
  - Papers grouped by CCF rank
  - IEEE-format references
  - Embedded BibTeX block
  - DBLP links for each paper

- `NAME.bib` — Raw BibTeX file for LaTeX / reference managers

## CCF Venue Coverage

### Software Engineering / System Software / Programming Languages

**CCF-A:** ICSE, FSE, ASE, ISSTA, PLDI, POPL, SOSP, OOPSLA, OSDI, FM / TOPLAS, TOSEM, TSE, TSC

**CCF-B:** RE, CAiSE, ECOOP, ETAPS, ICPC, ICFP, LCTES, MoDELS, CP, ICSOC, SANER, ICSME, VMCAI, ICWS, Middleware, SAS, ESEM, ISSRE, HotOS / ASE, ESE, IET Software, IST, JFP, JSEP, JSS, Requirements Engineering, SCP, SoSyM, STVR, SPE

### Artificial Intelligence

**CCF-A:** AAAI, NeurIPS, ACL, CVPR, ICCV, ICML, IJCAI, ECCV / AI, TPAMI, IJCV, JMLR

**CCF-B:** EMNLP, ECAI, ICRA, ICAPS, ICCBR, COLING, KR, UAI, AAMAS, PPSN, NAACL, COLT / TAP, CL, CVIU, DKE, EC, TAC, TASLP, TCYB, TEC, TFS, TNNLS, IJAR, JAIR, JAR, JSLHR, ML, NC, NN, PR, TACL

See `references/ccf_venues.md` for the full list.

## Requirements

- Python 3
- `curl` (for DBLP API calls)
- No external Python dependencies — uses only stdlib

## License

MIT
