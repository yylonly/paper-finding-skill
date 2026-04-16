---
name: paper-finding
description: Find academic papers from DBLP with CCF ranking filtering and generate ready-to-use BibTeX + LaTeX. Use whenever the user wants to search for papers on a topic, find CCF-A or CCF-B papers in Software Engineering or AI, do a literature review, get BibTeX entries, or produce a .bib file and .tex file with \\cite{} commands. Triggers on "find papers on X", "search for papers about Y", "CCF-A papers", "requirements validation papers", "literature review", "get BibTeX", "fetch paper", "generate .bib and .tex", "save papers as BibTeX", or any academic paper search task.
author: yylonly
version: 0.5.0
---

# Paper Finding Skill (v0.5)

Finds academic papers using [DBLP](https://dblp.org/) and generates `.bib` + `.tex` files ready for LaTeX.

## Bundled Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `scripts/search_dblp.py` | Search DBLP for papers | keyword + filters | JSON (with `--json`) |
| `scripts/filter_by_abstract.py` | Filter by abstract relevance | JSON from search_dblp.py | JSON (filtered) |
| `scripts/fetch_bibtex.py` | Fetch BibTeX by DOI | JSON or DOI URLs | `.bib` file |
| `scripts/bib2tex.py` | Merge bibs, generate LaTeX | `.bib` files | `.bib` (merged) + `.tex` |

---

## Recommended Workflow

Run the 4 scripts in sequence:

```bash
# Step 1: Search DBLP → JSON
python3 scripts/search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025 --json > papers.json

# Step 2: Filter by abstract relevance (optional but recommended)
python3 scripts/filter_by_abstract.py papers.json "requirements validation" -o filtered.json -v

# Step 3: Fetch BibTeX → .bib
python3 scripts/fetch_bibtex.py filtered.json -o refs.bib

# Step 4: Merge + generate LaTeX → .bib + .tex
python3 scripts/bib2tex.py refs.bib -o . --basename mypaper
```

---

## Step 1: search_dblp.py

Search DBLP for papers by keyword, filter by CCF rank/category/year.

```bash
# Search only (human-readable table)
python3 scripts/search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025

# Search + JSON output (for piping to fetch_bibtex.py)
python3 scripts/search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025 --json
```

**Options:**

| Flag | Description |
|------|-------------|
| `--ccf SE\|AI\|ALL` | Filter by CCF category |
| `--rank A\|B\|ALL` | Filter by CCF rank |
| `--years YYYY-YYYY` | Year range |
| `--hits N` | Max DBLP hits (default: 100) |
| `--json` | Output JSON (for fetch_bibtex.py) |
| `--enrich-doi` | Fetch missing DOIs from DBLP JSON (slow) |
| `--doi-delay N` | Delay between DBLP DOI requests (default: 1.0s) |

DBLP search is **title-only**. Run multiple query variants for broader coverage:
```bash
python3 scripts/search_dblp.py "requirements validation" --json
python3 scripts/search_dblp.py "requirements verification" --json
python3 scripts/search_dblp.py "NLP requirements engineering" --json
python3 scripts/search_dblp.py "LLM requirements engineering" --json
```

---

## Step 2: filter_by_abstract.py

Filter papers by abstract relevance using Semantic Scholar API. DBLP search is **title-only** — this step removes false positives (papers whose title matches but abstract doesn't address the topic).

```bash
python3 scripts/filter_by_abstract.py papers.json "requirements validation" -o filtered.json -v
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--min-overlap N` | Min fraction of query terms in abstract (0.0–1.0) | 0.15 |
| `--scholar-delay N` | Delay between API requests (s) | 0.5 |

**Relevance rules:**
- **Title overlap ≥ 40%** → always keep
- **Abstract has ≥ 15% of query terms** → keep
- **Some title overlap but abstract empty** → keep (lenient)
- Otherwise → drop

If Semantic Scholar returns 429 rate-limit, falls back to title-overlap-only mode (still effective).

---

## Step 3: fetch_bibtex.py

Fetch BibTeX for papers given a JSON file (from `search_dblp.py --json`) or individual DOI URLs.

```bash
# From JSON (output of search_dblp.py --json)
python3 scripts/fetch_bibtex.py papers.json -o refs.bib

# Individual DOI URLs
python3 scripts/fetch_bibtex.py https://doi.org/10.1109/RE.2024.00011 -o refs.bib

# Multiple .bib files via --file flag
python3 scripts/fetch_bibtex.py --file refs1.bib --file refs2.bib -o merged.bib

# With IEEE Playwright (Cite This → BibTeX tab)
python3 scripts/fetch_bibtex.py papers.json --ieee -o refs.bib -v
```

**Pipeline:**

```
DOI
  → IEEE via Playwright (if --ieee)  [bypasses Cloudflare on IEEE Xplore]
  → CrossRef API by DOI              [primary — reliable, no rate limits]
  → DBLP .bib endpoint              [fallback — rate-limited]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--output, -o FILE` | Output .bib file |
| `--ieee` | Use Playwright to fetch from IEEE Xplore (Cite This → BibTeX tab) |
| `--delay N` | Delay between CrossRef requests (s, default: 0.3) |
| `--verbose, -v` | Show source per entry |

**IEEE Playwright note:** Requires `pip install playwright && playwright install chromium`. Uses `headless=False` to bypass Cloudflare protection. The browser opens visibly to perform the Cite This → BibTeX click automation.

---

## Step 4: bib2tex.py

Merge multiple `.bib` files into one and generate a LaTeX `.tex` file with `\cite{}` for each entry.

```bash
# Merge two .bib files
python3 scripts/bib2tex.py refs1.bib refs2.bib -o . --basename combined

# Merge all .bib in current directory
python3 scripts/bib2tex.py *.bib -o . --basename allpapers

# Merge from a directory
python3 scripts/bib2tex.py --file mybibdir -o . --basename merged
```

**Options:**

| Flag | Description |
|------|-------------|
| `--file, -f` | Additional .bib files (can be repeated or glob pattern) |
| `--output DIR` | Output directory |
| `--basename NAME` | Base filename (no ext) |

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

## Verify Relevance via Abstract

DBLP search is **title-only**. Always verify relevance by checking the abstract:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=KEYWORD&limit=5&fields=title,abstract,year,venue"
```

A paper is **relevant** if its abstract confirms it addresses the user's topic (not just mentions it in passing).

---

## Important Notes

- **No API key needed** — DBLP, CrossRef, and IEEE are all free. The DBLP `.bib` endpoint is rate-limited; use CrossRef as the primary BibTeX source.
- **Verification ≠ Validation** — "Requirements verification" checks implementation against spec; "Requirements validation" checks spec against stakeholder needs. Both are valid topics.
- **Run multiple query variants** — DBLP title-only search misses papers. Use different keyword combinations: "requirements validation", "requirements verification", "NLP requirements engineering", "LLM requirements engineering", etc.
- **Filter by abstract** — use `filter_by_abstract.py` to remove false positives. DBLP title-only search returns irrelevant papers (e.g. "Roll for Robot" was dropped for "AI for design" because its abstract didn't discuss AI design. Run it after search and before fetching BibTeX.
- **Page counts** — ICSE NIER/Companion = 4–6 pages (short). RE full papers = 10–15 pages. Check the `pages` field after fetching.
- **DBLP JSON API is unreliable** — DBLP's JSON endpoint returns 404 for some records. Use the DOI from the `ee` field as the primary lookup; only fall back to DBLP JSON when no DOI is available.

---

## Quick Reference

```bash
# Step 1: Search DBLP → JSON
python3 scripts/search_dblp.py "TOPIC" --ccf SE --rank A --years 2021-2025 --json > papers.json

# Step 2: Filter by abstract relevance (optional but recommended)
python3 scripts/filter_by_abstract.py papers.json "TOPIC" -o filtered.json -v

# Step 3: Fetch BibTeX → .bib
python3 scripts/fetch_bibtex.py filtered.json -o refs.bib

# Step 4: Merge + generate LaTeX → .bib + .tex
python3 scripts/bib2tex.py refs.bib -o . --basename mypaper

# IEEE via Playwright (bypasses Cloudflare)
python3 scripts/fetch_bibtex.py filtered.json --ieee -o refs.bib -v
```
