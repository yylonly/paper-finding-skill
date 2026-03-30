---
name: paper-finding
description: Find and retrieve academic papers from DBLP with CCF ranking filtering. Use whenever the user wants to search for papers on a topic, find CCF-A or CCF-B papers in Software Engineering or AI, do a literature review, search for papers by conference/journal, get BibTeX entries, or filter papers by year range, CCF rank, venue, or page count. Triggers on "find papers on X", "search for papers about Y", "search DBLP", "CCF-A papers", "requirements validation papers", "literature review", "get BibTeX", "fetch paper", "what papers exist on Z", or any academic paper search task.
author: yylonly
version: 0.2.0
---

# Paper Finding Skill

This skill finds academic papers using [DBLP](https://dblp.org/) — a free, open computer science bibliography with 6.5M+ papers — and filters them by CCF ranking, year, venue, and page count.

## Bundled Scripts

- `scripts/search_dblp.py` — Search DBLP with CCF venue filtering
- `scripts/fetch_bibtex.py` — Fetch BibTeX entries by DBLP key
- `scripts/generate_report.py` — One-shot: search, filter, fetch BibTeX, and save as `.md` + `.bib`
- `references/ccf_venues.md` — CCF-A/B venue lists for SE and AI

See the "Quick Reference" section at the bottom for one-liners.

---

## Workflow: Finding Papers

### Step 1 — Determine the user's need

Ask (or infer) these filters:

| Filter | Options | Default |
|--------|---------|---------|
| Topic | Any search keywords | (required) |
| CCF Category | SE, AI, or ALL | ALL |
| CCF Rank | A, B, or ALL | ALL |
| Year range | e.g. 2021–2025 | Last 5 years |
| Page count | Minimum pages | None |

### Step 2 — Use the search script

**Basic search (last 5 years, all CCF):**
```bash
python3 scripts/search_dblp.py "requirements validation"
```

**CCF-A SE papers only:**
```bash
python3 scripts/search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025
```

**CCF-A AI papers:**
```bash
python3 scripts/search_dblp.py "requirements validation" --ccf AI --rank A --years 2021-2025
```

**JSON output for further processing:**
```bash
python3 scripts/search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025 --json
```

### Step 3 — Verify relevance via abstract

DBLP search is by title/keyword only — it matches titles containing your keywords. **Always verify relevance** by checking the abstract. Use one of:

- **Semantic Scholar API** (free, good abstract coverage):
  ```bash
  curl "https://api.semanticscholar.org/graph/v1/paper/search?query=KEYWORD&limit=5&fields=title,abstract,year,venue"
  ```
- **CrossRef API** (less reliable for CS abstracts):
  ```bash
  curl "https://api.crossref.org/works?query=KEYWORD&rows=5"
  ```
- **Direct web search** — search for the title to find the paper page

A paper is **relevant** if its abstract confirms it addresses the user's topic (not just mentions it in passing).

### Step 4 — Check page count

For filtering to full papers (>8 pages), check the page range:
- Search the DBLP key on **ACM Digital Library** or **IEEE Xplore**
- Or use the fetch script's `--pages` flag

Typical page counts:
- ICSE/FSE full papers: 10–12 pages
- ICSE NIER/Companion: 4–6 pages (short papers)
- RE (Requirements Engineering) journal: 20–30 pages
- ASE/ISSTA: 10–12 pages

### Step 5 — Fetch BibTeX

Once you have the DBLP keys, fetch BibTeX:

**Single paper:**
```bash
python3 scripts/fetch_bibtex.py conf/icse/Pan024
```

**Multiple papers:**
```bash
python3 scripts/fetch_bibtex.py conf/icse/Pan024 conf/icse/ChangGY23 conf/icse/MashkoorLE21
```

**With page counts:**
```bash
python3 scripts/fetch_bibtex.py conf/icse/Pan024 --pages
```

**Raw BibTeX (no cleanup):**
```bash
python3 scripts/fetch_bibtex.py conf/icse/Pan024 --raw
```

---

## CCF Venue Quick Reference

### CCF-A Software Engineering
**Conferences:** ICSE, FSE, ASE, ISSTA, PLDI, POPL, SOSP, OOPSLA, OSDI, FM
**Journals:** TOPLAS, TOSEM, TSE, TSC

### CCF-B Software Engineering
**Conferences:** RE, CAiSE, ECOOP, ETAPS, ICPC, ICFP, LCTES, MoDELS, CP, ICSOC, SANER, ICSME, VMCAI, ICWS, Middleware, SAS, ESEM, ISSRE, HotOS
**Journals:** ASE, ESE, IET Software, IST, JFP, JSEP, JSS, Requirements Engineering, SCP, SoSyM, STVR, SPE

### CCF-A Artificial Intelligence
**Conferences:** AAAI, NeurIPS, ACL, CVPR, ICCV, ICML, IJCAI, ECCV
**Journals:** AI, TPAMI, IJCV, JMLR

### CCF-B Artificial Intelligence
**Conferences:** EMNLP, ECAI, ICRA, ICAPS, ICCBR, COLING, KR, UAI, AAMAS, PPSN, NAACL, COLT
**Journals:** TAP, CL, CVIU, DKE, EC, TAC, TASLP, TCYB, TEC, TFS, TNNLS, IJAR, JAIR, JAR, JSLHR, ML, NC, NN, PR, TACL

For the full list, see `references/ccf_venues.md`.

---

## DBLP API One-Liners

When the bundled scripts aren't available, use these direct API calls:

### Search publications
```bash
curl "https://dblp.org/search/publ/api?q=KEYWORD&format=json&h=50"
```

### Search with year filter
```bash
curl "https://dblp.org/search/publ/api?q=KEYWORD+year:2024&format=json&h=50"
```

### Search by author
```bash
curl "https://dblp.org/search/author/api?q=author:NAME&format=json&h=20"
```

### Fetch BibTeX by DBLP key
```bash
curl "https://dblp.org/rec/bib/CONF_OR_JOURNAL/KEY.bib"
```

### Fetch paper metadata (JSON)
```bash
curl "https://dblp.org/rec/KEY.json"
```

---

## Important Notes

- **DBLP is free, no API key needed.** Be polite — add `--max-time` and delay between bulk requests.
- **Verification ≠ Validation:** "Requirements verification" checks implementation against spec; "Requirements validation" checks spec against stakeholder needs. Both are valid topics — don't exclude papers that use "verification" in the title.
- **Abstract-based relevance is critical** — DBLP keyword search only matches titles. A paper titled "InputGen" with "requirements validation" in the abstract but not the title would be missed by pure title search. Always cross-check abstracts.
- **Venue matching in DBLP is strict** — DBLP uses specific abbreviations. "RE" matches "Requirements Engineering" but "REQUIREMENTS ENGINEERING" won't match "RE" in substring matching.
- **Page counts** — ICSE NIER/Companion tracks are short papers (4–6 pages). If the user wants full papers, always check page counts.

---

## One-Shot Report Generator

The `generate_report.py` script does everything in one command: search, filter by CCF rank/category/year, verify abstracts, fetch BibTeX (with rate-limit delay), and save as `.md` + `.bib`.

**Basic usage:**
```bash
python3 scripts/generate_report.py "AI for Requirements Engineering" --ccf ALL --rank A --years 2023-2025
```

**Specify output directory and base filename:**
```bash
python3 scripts/generate_report.py "requirements validation" --ccf SE --rank A --years 2021-2025 --output ~/papers --basename req-validation-review
```

**Output:** Two files are saved:
- `TOPIC.md` — Literature review with IEEE references, paper list grouped by CCF rank, and BibTeX embedded
- `TOPIC.bib` — Raw BibTeX file for LaTeX / reference managers

**Options:**
| Flag | Description |
|------|-------------|
| `--ccf SE\|AI\|ALL` | Filter by CCF category (default: ALL) |
| `--rank A\|B\|ALL` | Filter by CCF rank (default: ALL) |
| `--years YYYY-YYYY` | Year range (default: last 5 years) |
| `--hits N` | Max DBLP hits per query (default: 100) |
| `--output DIR` | Output directory (default: current dir) |
| `--basename NAME` | Base filename without extension |

## Quick Reference

```bash
# One-shot: generate full report (.md + .bib) for a topic
python3 scripts/generate_report.py "TOPIC" --ccf SE --rank A --years 2021-2025

# Search papers only (output JSON)
python3 scripts/search_dblp.py "TOPIC" --ccf SE --rank A --years 2021-2025 --json

# Fetch BibTeX for known DBLP keys
python3 scripts/fetch_bibtex.py conf/icse/Pan024 conf/icse/ChangGY23 -o refs.bib

# Check abstracts on Semantic Scholar
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=TOPIC&limit=5&fields=title,abstract,year,venue"

# Get CCF venue reference
cat references/ccf_venues.md
```
