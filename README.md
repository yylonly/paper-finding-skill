# paper-finding

A Claude Code skill for finding academic papers via [DBLP](https://dblp.org/) with CCF ranking filtering, IEEE reference generation, and automatic save to `.md` + `.bib`.

## Installation

Install using the `skills` CLI:

```bash
# Install globally (recommended)
npx skills add yylonly/paper-finding --global

# Or install locally in current project
npx skills add yylonly/paper-finding
```

For more commands, see `npx skills --help`.

## Features

- **DBLP search** with CCF-A/B filtering for Software Engineering and AI venues
- **IEEE-format references** auto-generated
- **Automatic save** to `.md` (literature review) and `.bib` (BibTeX)
- **Polite rate-limiting** — 1.5s delay between DBLP requests to avoid 429 errors

---

## Natural Language Examples

Use the skill whenever you want to find papers. Describe what you need in plain language.

### Example 1 — CCF-A SE, 3 years

**Input:**
> find papers about LLM for software testing, only CCF-A venues in recent 3 years

**Output saved to:**
```
~/literature-review-llm-for-software-testing.md    # .md with IEEE refs + BibTeX block
~/literature-review-llm-for-software-testing.bib    # .bib for reference managers
```

---

### Example 2 — CCF-A + CCF-B SE, 5 years

**Input:**
> search for papers on requirements validation, CCF-A and CCF-B in software engineering, last 5 years

**Output saved to:**
```
~/literature-review-requirements-validation.md
~/literature-review-requirements-validation.bib
```

---

### Example 3 — Broad CCF-A AI+SE

**Input:**
> find papers about AI for requirements engineering, save as md and bibtex

**Output saved to:**
```
~/literature-review-ai-for-requirements-engineering.md
~/literature-review-ai-for-requirements-engineering.bib
```

---

### Example 4 — Specific year range

**Input:**
> literature review on model-based testing, CCF-A software engineering, 2020-2025

**Output saved to:**
```
~/literature-review-model-based-testing.md
~/literature-review-model-based-testing.bib
```

---

### What the skill does automatically

```
1. Infers:  topic, CCF category (SE/AI/ALL), rank (A/B/ALL), year range
2. Searches:  DBLP API with correct CCF venue filtering
3. Saves:     TOPIC.md  +  TOPIC.bib  to ~/ (home directory)
```

---

## Command Line

```bash
# All-in-one: search + filter + BibTeX + save
python3 scripts/generate_report.py "requirements validation" \
    --ccf ALL --rank A --years 2021-2025 \
    --output ~ --basename req-validation

# Search only (JSON output)
python3 scripts/search_dblp.py "LLM requirements engineering" \
    --ccf SE --rank A --years 2023-2025 --json

# Fetch BibTeX for known DBLP keys
python3 scripts/fetch_bibtex.py conf/icse/Pan024 conf/icse/ChangGY23 \
    --output ~/refs.bib
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--ccf SE\|AI\|ALL` | Filter by CCF category | ALL |
| `--rank A\|B\|ALL` | Filter by CCF rank | ALL |
| `--years YYYY-YYYY` | Year range | Last 5 years |
| `--hits N` | Max DBLP hits per query | 100 |
| `--output DIR` | Output directory | Current dir |
| `--basename NAME` | Base filename (no extension) | Auto-generated |

---

## Output Files

Two files are saved side-by-side:

- **`NAME.md`** — Literature review containing:
  - Papers grouped by CCF rank (CCF-A SE → CCF-B SE → CCF-A AI → CCF-B AI)
  - IEEE-format references
  - Embedded BibTeX block
  - DBLP links for each paper

- **`NAME.bib`** — Raw BibTeX file for LaTeX / reference managers

---

## CCF Venue Coverage

### Software Engineering / System Software / Programming Languages

**CCF-A:** ICSE, FSE, ASE, ISSTA, PLDI, POPL, SOSP, OOPSLA, OSDI, FM / TOPLAS, TOSEM, TSE, TSC

**CCF-B:** RE, CAiSE, ECOOP, ETAPS, ICPC, ICFP, LCTES, MoDELS, CP, ICSOC, SANER, ICSME, VMCAI, ICWS, Middleware, SAS, ESEM, ISSRE, HotOS / ASE, ESE, IET Software, IST, JFP, JSEP, JSS, Requirements Engineering, SCP, SoSyM, STVR, SPE

### Artificial Intelligence

**CCF-A:** AAAI, NeurIPS, ACL, CVPR, ICCV, ICML, IJCAI, ECCV / AI, TPAMI, IJCV, JMLR

**CCF-B:** EMNLP, ECAI, ICRA, ICAPS, ICCBR, COLING, KR, UAI, AAMAS, PPSN, NAACL, COLT / TAP, CL, CVIU, DKE, EC, TAC, TASLP, TCYB, TEC, TFS, TNNLS, IJAR, JAIR, JAR, JSLHR, ML, NC, NN, PR, TACL

See `references/ccf_venues.md` for the complete list.

---

## Requirements

- Python 3
- `curl` (for DBLP API calls)
- No external Python dependencies — uses only stdlib

## License

MIT
