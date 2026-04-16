#!/usr/bin/env python3
"""
Step 1: Search DBLP for papers by keyword.
Outputs: JSON list of papers with DOI URLs, suitable for piping to fetch_bibtex.py.

Usage:
    python3 search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025 --json
    python3 search_dblp.py "LLM requirements" --ccf SE --rank B --years 2020-2025 --json > papers.json
"""

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
import re
import time
from datetime import datetime

# CCF Venue lists
CCF_A_SE_CONFS = {'ICSE', 'FSE', 'ISSTA', 'PLDI', 'POPL', 'SOSP', 'OOPSLA', 'OSDI', 'FM'}
CCF_A_SE_JOURNALS = {'TOSEM', 'TSE', 'TOPLAS', 'TSC'}
CCF_B_SE_CONFS = {'RE', 'CAiSE', 'ECOOP', 'ETAPS', 'ICPC', 'ICFP', 'LCTES', 'MoDELS', 'CP',
                   'ICSOC', 'SANER', 'ICSME', 'VMCAI', 'ICWS', 'Middleware', 'SAS', 'ESEM', 'ISSRE', 'HotOS'}
CCF_B_SE_JOURNALS = {'ASE', 'ESE', 'IETS', 'IST', 'JFP', 'JSEP', 'RE', 'SCP', 'SoSyM', 'STVR', 'SPE',
                      'JOURNAL OF SOFTWARE EVOLUTION', 'JOURNAL OF SYSTEMS AND SOFTWARE'}
CCF_A_AI_CONFS = {'AAAI', 'NeurIPS', 'ACL', 'CVPR', 'ICCV', 'ICML', 'IJCAI', 'ECCV'}
CCF_A_AI_JOURNALS = {'AI', 'TPAMI', 'IJCV', 'JMLR'}
CCF_B_AI_CONFS = {'EMNLP', 'ECAI', 'ICRA', 'ICAPS', 'ICCBR', 'COLING', 'KR', 'UAI', 'AAMAS', 'PPSN', 'NAACL', 'COLT'}
CCF_B_AI_JOURNALS = {'AAMAS', 'CL', 'CVIU', 'DKE', 'EC', 'TAC', 'TASLP', 'TCYB', 'TEC', 'TFS', 'TNNLS',
                      'IJAR', 'JAIR', 'JAR', 'JSLHR', 'ML', 'NC', 'NN', 'PR', 'TACL'}
EXCLUDE_KEYWORDS = {'REMOTE', 'SMARTGREENS', 'VEHITS', 'IFM', 'NFM', 'TALN', 'RECITAL',
                     'ENASE', 'ITICSE', 'EQUITY', 'DIVERSITY', 'INCLUSION', 'FORMALISE', 'AI ETHICS', 'PANAFRICON'}

MULTI_TOKEN_VENUES = {
    'IEEE TRANSACTIONS ON PATTERN ANALYSIS AND MACHINE INTELLIGENCE': ('CCF-A AI', 'journal'),
    'IEEE TRANSACTIONS ON SOFTWARE ENGINEERING': ('CCF-A SE', 'journal'),
    'JOURNAL OF MACHINE LEARNING RESEARCH': ('CCF-A AI', 'journal'),
    'JOURNAL OF SOFTWARE EVOLUTION AND PROCESS': ('CCF-B SE', 'journal'),
    'JOURNAL OF SYSTEMS AND SOFTWARE': ('CCF-B SE', 'journal'),
    'IEEE TRANSACTIONS ON CYBERNETICS': ('CCF-B AI', 'journal'),
    'IEEE TRANSACTIONS ON FUZZY SYSTEMS': ('CCF-B AI', 'journal'),
    'IEEE TRANSACTIONS ON NEURAL NETWORKS AND LEARNING SYSTEMS': ('CCF-B AI', 'journal'),
    'IEEE TRANSACTIONS ON EVOLUTIONARY COMPUTATION': ('CCF-B AI', 'journal'),
    'IEEE TRANSACTIONS ON AFFECTIVE COMPUTING': ('CCF-B AI', 'journal'),
    'IEEE/ACM TRANSACTIONS ON AUDIO SPEECH AND LANGUAGE PROCESSING': ('CCF-B AI', 'journal'),
    'SOFTWARE AND SYSTEM MODELING': ('CCF-B SE', 'journal'),
    'SOFTWARE TESTING VERIFICATION AND RELIABILITY': ('CCF-B SE', 'journal'),
    'SOFTWARE-PRACTICE AND EXPERIENCE': ('CCF-B SE', 'journal'),
    'INTERNATIONAL JOURNAL OF APPROXIMATE REASONING': ('CCF-B AI', 'journal'),
    'JOURNAL OF AUTOMATED REASONING': ('CCF-B AI', 'journal'),
    'TRANSACTIONS OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS': ('CCF-B AI', 'journal'),
    'JOURNAL OF SPEECH LANGUAGE AND HEARING RESEARCH': ('CCF-B AI', 'journal'),
    'COMPUTER VISION AND IMAGE UNDERSTANDING': ('CCF-B AI', 'journal'),
    'PATTERN RECOGNITION': ('CCF-B AI', 'journal'),
}


def classify_venue(venue_upper: str) -> tuple:
    if any(ex in venue_upper for ex in EXCLUDE_KEYWORDS):
        return 'OTHER', ''
    for vname, result in sorted(MULTI_TOKEN_VENUES.items(), key=lambda x: -len(x[0])):
        if vname in venue_upper:
            return result
    tokens = set(venue_upper.split())
    if tokens & CCF_A_SE_CONFS: return 'CCF-A SE', 'conference'
    if tokens & CCF_A_SE_JOURNALS: return 'CCF-A SE', 'journal'
    if tokens & CCF_B_SE_CONFS: return 'CCF-B SE', 'conference'
    if tokens & CCF_B_SE_JOURNALS: return 'CCF-B SE', 'journal'
    if tokens & CCF_A_AI_CONFS: return 'CCF-A AI', 'conference'
    if tokens & CCF_A_AI_JOURNALS: return 'CCF-A AI', 'journal'
    if tokens & CCF_B_AI_CONFS: return 'CCF-B AI', 'conference'
    if tokens & CCF_B_AI_JOURNALS: return 'CCF-B AI', 'journal'
    return 'OTHER', ''


def extract_doi_from_ee(ee_url: str) -> str:
    """Extract DOI from a publisher URL (e.g. https://doi.org/10.1109/RE.2024.123)."""
    if not ee_url:
        return ''
    m = re.search(r'doi\.org/(10\.\d{4,}/[^\s]+)', ee_url)
    if m:
        return m.group(1).rstrip('/')
    return ''


def search_dblp_api(query: str, max_hits: int = 100) -> list:
    """Search DBLP API, return list of hit dicts."""
    encoded_q = urllib.parse.quote(query)
    r = subprocess.run(
        ['curl', '-s', f'https://dblp.org/search/publ/api?q={encoded_q}&format=json&h={max_hits}'],
        capture_output=True, timeout=30
    )
    try:
        data = json.loads(r.stdout)
        return data.get('result', {}).get('hits', {}).get('hit', [])
    except:
        return []


def fetch_doi_from_dblp_json(dblp_key: str, timeout: int = 15) -> str:
    """Fetch DOI from DBLP JSON API. Returns empty string if not found."""
    try:
        url = f'https://dblp.org/rec/{dblp_key}.json'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            doi = data.get('doi', '')
            if not doi:
                ext = data.get('externalids', {})
                doi = ext.get('DOI', '') if isinstance(ext, dict) else ''
            return doi
    except:
        return ''


def parse_paper(hit: dict) -> dict:
    info = hit['info']
    venue_val = info.get('venue', '')
    if isinstance(venue_val, list):
        venue_val = ' '.join(str(v) for v in venue_val)
    venue_upper = str(venue_val).upper()
    category, vtype = classify_venue(venue_upper)

    authors_raw = info.get('authors', {}).get('author', [])
    if not isinstance(authors_raw, list):
        authors_raw = [authors_raw]
    authors = [a.get('text', str(a)) if isinstance(a, dict) else str(a) for a in authors_raw]

    ee_url = info.get('ee', '')
    doi = extract_doi_from_ee(ee_url)

    return {
        'title': info.get('title', ''),
        'authors': authors,
        'authors_str': ', '.join(authors),
        'venue': info.get('venue', ''),
        'year': info.get('year', ''),
        'key': info.get('url', '').replace('https://dblp.org/rec/', ''),
        'dblp_url': info.get('url', ''),
        'ee_url': ee_url,
        'doi': doi,
        'category': category,
        'rank': category.split(' ')[0] if category else '',
        'type': vtype,
    }


def filter_papers(papers: list, args) -> list:
    filtered = []
    for p in papers:
        year = int(p.get('year') or 0)
        if args.year_from and year < args.year_from:
            continue
        if args.year_to and year > args.year_to:
            continue
        if args.rank and args.rank.upper() != 'ALL':
            if args.rank.upper() not in p.get('rank', ''):
                continue
        if args.ccf and args.ccf.upper() != 'ALL':
            ccf = args.ccf.upper()
            if ccf == 'SE' and 'SE' not in p.get('category', ''):
                continue
            if ccf == 'AI' and 'AI' not in p.get('category', ''):
                continue
        filtered.append(p)
    return filtered


def deduplicate(papers: list) -> list:
    seen = set()
    unique = []
    for p in papers:
        if p['key'] not in seen:
            seen.add(p['key'])
            unique.append(p)
    return unique


def enrich_missing_dois(papers: list, delay: float = 1.0) -> list:
    """Fill in missing DOIs using DBLP JSON API (rate-limited, use delay)."""
    enriched = []
    for p in papers:
        if p.get('doi'):
            enriched.append(p)
            continue
        doi = fetch_doi_from_dblp_json(p['key'])
        p = dict(p)
        p['doi'] = doi
        enriched.append(p)
        if delay > 0:
            time.sleep(delay)
    return enriched


def print_table(papers: list):
    if not papers:
        print("No papers found.")
        return
    rank_order = {'CCF-A SE': 0, 'CCF-A AI': 1, 'CCF-B SE': 2, 'CCF-B AI': 3, 'OTHER': 4}
    papers.sort(key=lambda p: (rank_order.get(p['category'], 4), p.get('year', ''), p.get('venue', '')))
    print(f"\n{'Rank':<10} {'Year':<6} {'Venue':<25} {'Title':<50} {'DOI':<30}")
    print("-" * 130)
    for p in papers:
        rank = p.get('category', 'OTHER')
        year = p.get('year', 'N/A')
        venue = p.get('venue', '')[:23]
        title = p.get('title', '')[:48]
        doi = p.get('doi', '')[:28]
        print(f"{rank:<10} {year:<6} {venue:<25} {title:<50} {doi:<30}")
    print(f"\nTotal: {len(papers)} papers")


def main():
    parser = argparse.ArgumentParser(description='Search DBLP: find papers by keyword, output JSON with DOI URLs')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--ccf', choices=['SE', 'AI', 'ALL'], default='ALL',
                        help='Filter by CCF category')
    parser.add_argument('--rank', choices=['A', 'B', 'ALL'], default='ALL',
                        help='Filter by CCF rank')
    parser.add_argument('--year-from', dest='year_from', type=int, default=None)
    parser.add_argument('--year-to', dest='year_to', type=int, default=None)
    parser.add_argument('--years', help='Year range, e.g. 2020-2025')
    parser.add_argument('--hits', type=int, default=100, help='Max DBLP hits (default: 100)')
    parser.add_argument('--json', action='store_true', help='Output JSON (for piping to fetch_bibtex.py)')
    parser.add_argument('--enrich-doi', action='store_true',
                        help='Also fetch missing DOIs from DBLP JSON API (slow, rate-limited)')
    parser.add_argument('--doi-delay', dest='doi_delay', type=float, default=1.0,
                        help='Delay between DBLP DOI requests (default: 1.0s)')
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()

    if args.years:
        try:
            args.year_from, args.year_to = map(int, args.years.split('-'))
        except:
            print("Error: --years should be YYYY-YYYY")
            sys.exit(1)

    if not args.year_from and not args.year_to:
        current_year = datetime.now().year
        args.year_from = current_year - 5
        args.year_to = current_year

    if args.verbose:
        print(f"Searching: '{args.query}'  CCF={args.ccf} {args.rank}  {args.year_from}-{args.year_to}",
              file=sys.stderr)

    hits = search_dblp_api(args.query, max_hits=args.hits)
    if args.verbose:
        print(f"DBLP returned {len(hits)} hits", file=sys.stderr)

    papers = [parse_paper(h) for h in hits]
    papers = filter_papers(papers, args)
    papers = deduplicate(papers)

    if args.enrich_doi:
        papers = enrich_missing_dois(papers, delay=args.doi_delay)

    if args.json:
        # Output JSON: each paper with doi_url field (https://doi.org/DOI)
        output = []
        for p in papers:
            output.append({
                'key': p['key'],
                'title': p['title'],
                'authors_str': p['authors_str'],
                'year': p['year'],
                'venue': p['venue'],
                'category': p['category'],
                'doi': p['doi'],
                'doi_url': f"https://doi.org/{p['doi']}" if p['doi'] else '',
                'dblp_url': p['dblp_url'],
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_table(papers)

    return papers


if __name__ == '__main__':
    main()
