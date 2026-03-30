#!/usr/bin/env python3
"""
Fetch BibTeX entries from DBLP by DBLP key or from a list of keys.

Usage:
    python3 fetch_bibtex.py conf/icse/Pan024
    python3 fetch_bibtex.py conf/icse/Pan024 conf/icse/ChangGY23 conf/icse/MashkoorLE21
    python3 fetch_bibtex.py --file keys.txt
    python3 fetch_bibtex.py --search "requirements validation" --venue ICSE --year 2024
"""

import argparse
import subprocess
import sys
import urllib.parse
import json


def fetch_bibtex(dblp_key: str, raw: bool = False) -> str:
    """Fetch BibTeX for a single DBLP key. Returns empty string on failure."""
    url = f'https://dblp.org/rec/bib/{dblp_key}.bib'
    r = subprocess.run(['curl', '-sL', url], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace') if isinstance(r.stdout, bytes) else r.stdout


def fetch_json(dblp_key: str) -> dict:
    """Fetch DBLP JSON for a single key. Returns empty dict on failure."""
    url = f'https://dblp.org/rec/{dblp_key}.json'
    r = subprocess.run(['curl', '-s', url], capture_output=True)
    try:
        return json.loads(r.stdout)
    except:
        return {}


def get_page_count(dblp_key: str) -> tuple:
    """Get page range for a paper. Returns (start_page, end_page, total_pages)."""
    data = fetch_json(dblp_key)
    try:
        result = data.get('result', {})
        data_obj = result.get('data', {})
        if isinstance(data_obj, dict):
            pages_str = data_obj.get('pages', '') or data_obj.get('page', '')
            if pages_str:
                if '-' in str(pages_str):
                    parts = str(pages_str).split('-')
                    start = int(parts[0])
                    end = int(parts[1])
                    return start, end, end - start + 1
                else:
                    return int(pages_str), int(pages_str), 1
    except:
        pass
    return None, None, None


def search_and_fetch_bibtex(query: str, venue: str = None, year: str = None, max_results: int = 10) -> list:
    """Search DBLP and fetch BibTeX for top results."""
    q = query
    if venue:
        q = f"venue:{venue} {q}"
    if year:
        q = f"{q} year:{year}"

    encoded_q = urllib.parse.quote(q)
    r = subprocess.run(
        ['curl', '-s', f'https://dblp.org/search/publ/api?q={encoded_q}&format=json&h={max_results}'],
        capture_output=True
    )
    try:
        data = json.loads(r.stdout)
        hits = data.get('result', {}).get('hits', {}).get('hit', [])
        results = []
        for hit in hits:
            key = hit['info'].get('url', '').replace('https://dblp.org/rec/', '')
            bib = fetch_bibtex(key, raw=True)
            results.append({'key': key, 'bib': bib, 'info': hit['info']})
        return results
    except:
        return []


def main():
    parser = argparse.ArgumentParser(description='Fetch BibTeX from DBLP')
    parser.add_argument('keys', nargs='*', help='DBLP keys to fetch')
    parser.add_argument('--file', '-f', help='File containing DBLP keys (one per line)')
    parser.add_argument('--search', '-s', help='Search query to find keys first')
    parser.add_argument('--venue', help='Restrict search to venue')
    parser.add_argument('--year', type=int, help='Restrict search to year')
    parser.add_argument('--raw', action='store_true', help='Raw BibTeX without cleanup')
    parser.add_argument('--pages', action='store_true', help='Also show page count')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    keys = list(args.keys)

    if args.file:
        with open(args.file) as f:
            keys.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])

    if args.search:
        results = search_and_fetch_bibtex(args.search, venue=args.venue, year=str(args.year) if args.year else None)
        for res in results:
            print(f"# {res['key']}")
            print(res['bib'])
        return

    if not keys:
        parser.print_help()
        return

    output = []
    for key in keys:
        key = key.strip()
        if not key:
            continue

        bib = fetch_bibtex(key, raw=args.raw)

        if args.pages:
            start, end, total = get_page_count(key)
            if total:
                print(f"# {key}: pages {start}-{end} ({total} pages)", file=sys.stderr)

        output.append(f"# {key}")
        output.append(bib)

    result = '\n'.join(output)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(result)
        print(f"Saved {len(keys)} entries to {args.output}")
    else:
        print(result)


if __name__ == '__main__':
    main()
