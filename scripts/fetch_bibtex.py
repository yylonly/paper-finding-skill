#!/usr/bin/env python3
"""
Step 2: Fetch BibTeX entries for a list of papers.
Input: JSON file from search_dblp.py (or individual DOI URLs)
Output: .bib file with all BibTeX entries

Workflow:
    DOI from input
      → IEEE via Playwright (Cite This → BibTeX tab)  [if --ieee]
      → CrossRef API by DOI  [primary, always tried]
      → DBLP .bib endpoint   [fallback]

Usage:
    # From JSON file (output of search_dblp.py --json):
    python3 fetch_bibtex.py papers.json -o refs.bib

    # Individual DOIs:
    python3 fetch_bibtex.py https://doi.org/10.1109/RE.2024.00011 -o refs.bib

    # With IEEE Playwright:
    python3 fetch_bibtex.py papers.json --ieee -o refs.bib -v
"""

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
import re
import time

# Playwright support (optional)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ===== CrossRef =====

def fetch_bibtex_from_crossref(doi: str, timeout: int = 15) -> tuple:
    """Fetch BibTeX from CrossRef API. Returns (bibtex_str, success)."""
    if not doi:
        return '', False
    try:
        url = f'https://api.crossref.org/works/{doi}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())['message']

            ctype = 'inproceedings'
            if data.get('type') in ('journal-article', 'journal-issue'):
                ctype = 'article'

            authors_list = []
            for a in data.get('author', []):
                name = (a.get('given', '') + ' ' + a.get('family', '')).strip()
                authors_list.append(name)

            title = data.get('title', [''])[0] if data.get('title') else ''
            container = data.get('container-title', [''])[0] if data.get('container-title') else ''
            volume = data.get('volume', '')
            issue = data.get('issue', '')
            pages = data.get('page', '')
            year_obj = data.get('published-print', data.get('published-online', {}))
            year = ''
            if isinstance(year_obj, dict):
                parts = year_obj.get('date-parts', [['']])
                year = str(parts[0][0]) if parts and parts[0] else ''
            publisher = data.get('publisher', '')
            url2 = data.get('URL', f'https://doi.org/{doi}')

            key_base = re.sub(r'[^a-zA-Z0-9]', '', doi.split('/')[-1]) if '/' in doi else doi

            lines = [f'@{ctype}{{{key_base},']
            lines.append(f'  author       = {{{" and ".join(authors_list)}}},')
            lines.append(f'  title        = {{{title}}},')
            if container:
                lines.append(f'  booktitle    = {{{container}}},')
            if volume:
                lines.append(f'  volume       = {{{volume}}},')
            if issue:
                lines.append(f'  number       = {{{issue}}},')
            if pages:
                lines.append(f'  pages        = {{{pages}}},')
            if year:
                lines.append(f'  year         = {{{year}}},')
            if publisher:
                lines.append(f'  publisher    = {{{publisher}}},')
            lines.append(f'  doi          = {{{doi}}},')
            lines.append(f'  url          = {{{url2}}},')
            lines.append('}')

            return '\n'.join(lines), True
    except Exception as e:
        return '', False


# ===== DBLP fallback =====

def fetch_bibtex_from_dblp(dblp_key: str, timeout: int = 15) -> tuple:
    """Fetch BibTeX from DBLP .bib endpoint. Returns (bibtex_str, success)."""
    try:
        url = f'https://dblp.org/rec/{dblp_key}.bib'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.37'
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            bib = r.read().decode('utf-8', errors='replace')
            if bib.strip().startswith('@'):
                return bib.strip(), True
            return '', False
    except Exception:
        return '', False


# ===== IEEE via Playwright =====

def fetch_bibtex_from_ieee(doi: str, timeout: int = 60) -> tuple:
    """
    Fetch BibTeX from IEEE Xplore via Playwright.
    Navigates to https://doi.org/{doi}, clicks Cite This → BibTeX tab.
    Returns (bibtex_str, success).
    """
    if not PLAYWRIGHT_AVAILABLE or not doi:
        return '', False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            page.goto(f"https://doi.org/{doi}", wait_until="load", timeout=timeout * 1000)
            page.wait_for_timeout(5000)

            # Check redirect worked
            if '/document/' not in page.url:
                browser.close()
                return '', False

            # Click Cite This
            try:
                page.get_by_text("Cite This").click(force=True, timeout=5000)
            except Exception:
                browser.close()
                return '', False
            page.wait_for_timeout(3000)

            # Click BibTeX tab
            try:
                page.get_by_text("BibTeX", exact=True).click(timeout=5000)
            except Exception:
                browser.close()
                return '', False
            page.wait_for_timeout(2000)

            # Extract from textarea or pre
            bibtex = ''
            for tag in ['textarea', 'pre']:
                elems = page.locator(tag)
                for j in range(elems.count()):
                    txt = elems.nth(j).inner_text()
                    if '@' in txt:
                        bibtex = txt.strip()
                        break
                if bibtex:
                    break

            browser.close()
            return bibtex, bool(bibtex)
    except Exception:
        return '', False


# ===== Main fetch logic =====

def extract_doi_from_url(url: str) -> str:
    """Extract DOI from a doi.org URL."""
    if not url:
        return ''
    # https://doi.org/10.1109/RE.2024.00011 → 10.1109/RE.2024.00011
    m = re.search(r'doi\.org/(10\.\S+)', url)
    if m:
        return m.group(1).rstrip('/')
    return ''


def fetch_bibtex_for_doi(doi: str, use_ieee: bool = False, delay: float = 0.3) -> tuple:
    """
    Fetch BibTeX for a single DOI.
    Tries: IEEE (Playwright) → CrossRef → DBLP
    Returns (bibtex_str, source_str).
    """
    if not doi:
        return '', 'no_doi'

    # IEEE via Playwright (if enabled)
    if use_ieee:
        bib, ok = fetch_bibtex_from_ieee(doi)
        if ok:
            return bib, 'ieee'

    # CrossRef
    bib, ok = fetch_bibtex_from_crossref(doi)
    if ok:
        return bib, 'crossref'

    return '', 'not_found'


def load_papers_from_json(path: str) -> list:
    """Load papers from JSON file (output of search_dblp.py --json)."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


# ===== CLI =====

def main():
    parser = argparse.ArgumentParser(
        description='Fetch BibTeX for papers: IEEE/Playwright → CrossRef → DBLP fallback')
    parser.add_argument('input', nargs='*',
                        help='DOI URLs (e.g. https://doi.org/10.1109/RE.2024.11), '
                             'or JSON file from search_dblp.py (e.g. papers.json)')
    parser.add_argument('--file', '-f', help='File with DOI URLs (one per line) or JSON from search_dblp.py')
    parser.add_argument('--output', '-o', default=None, help='Output .bib file (default: stdout)')
    parser.add_argument('--ieee', action='store_true',
                        help='Use Playwright to fetch from IEEE Xplore (Cite This → BibTeX tab)')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='Delay between CrossRef requests (default: 0.3s)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show per-entry source')

    args = parser.parse_args()

    # Collect DOIs from all sources
    dois = []
    papers_info = []  # (doi, title) for verbose output

    # From positional args
    for item in args.input:
        if item.endswith('.json'):
            # Treat as JSON file
            papers = load_papers_from_json(item)
            for p in papers:
                doi = p.get('doi', '')
                if doi:
                    dois.append(('doi', doi))
                    papers_info.append((doi, p.get('title', '')))
        elif 'doi.org' in item:
            doi = extract_doi_from_url(item)
            dois.append(('doi', doi))
            papers_info.append((doi, ''))
        else:
            # Treat as DBLP key
            dois.append(('dblp', item))

    # From --file
    if args.file:
        if args.file.endswith('.json'):
            papers = load_papers_from_json(args.file)
            for p in papers:
                doi = p.get('doi', '')
                if doi:
                    dois.append(('doi', doi))
                    papers_info.append((doi, p.get('title', '')))
        else:
            with open(args.file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if 'doi.org' in line:
                        doi = extract_doi_from_url(line)
                        dois.append(('doi', doi))
                        papers_info.append((doi, ''))
                    else:
                        dois.append(('dblp', line))

    if not dois:
        parser.print_help()
        return

    # Deduplicate by (type, value)
    seen = set()
    unique = []
    for t, v in dois:
        key = (t, v)
        if key not in seen:
            seen.add(key)
            unique.append((t, v))
    dois = unique

    # Fetch BibTeX
    results = []
    stats = {'ieee': 0, 'crossref': 0, 'dblp': 0, 'failed': 0}

    for i, (dtype, dval) in enumerate(dois):
        if dtype == 'doi':
            bib, src = fetch_bibtex_for_doi(dval, use_ieee=args.ieee, delay=args.delay)
        else:
            bib, _ = fetch_bibtex_from_dblp(dval)
            src = 'dblp'
            if not bib:
                src = 'not_found'

        results.append(bib)
        stats[src] = stats.get(src, 0) + 1

        label = dval[:40]
        if args.verbose:
            status = '✓' if bib else '✗'
            title = ''
            for doi_, t_ in papers_info:
                if doi_ == dval and t_:
                    title = f'  # {t_[:60]}'
                    break
            print(f'[{i+1}/{len(dois)}] {status} {src}: {label}{title}', file=sys.stderr)
        else:
            status = '✓' if bib else '✗'
            print(f'[{i+1}/{len(dois)}] {status} {src}: {label}', file=sys.stderr)

        if args.delay > 0 and i < len(dois) - 1:
            time.sleep(args.delay)

    bibtex_output = '\n\n'.join(r for r in results if r)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(bibtex_output)
        total = len(dois)
        print(f'\nSaved {len(dois)} entries to {args.output} '
              f'(ieee={stats["ieee"]}, crossref={stats["crossref"]}, '
              f'dblp={stats["dblp"]}, failed={stats["failed"]})', file=sys.stderr)
    else:
        print(bibtex_output)

    if args.verbose:
        print(f'\n# Stats: ieee={stats["ieee"]}, crossref={stats["crossref"]}, '
              f'dblp={stats["dblp"]}, failed={stats["failed"]}', file=sys.stderr)


if __name__ == '__main__':
    main()
