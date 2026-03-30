#!/usr/bin/env python3
"""
Comprehensive DBLP paper search with CCF venue filtering.

Usage:
    python3 search_dblp.py "requirements validation" --ccf SE --rank A --years 2021-2025
    python3 search_dblp.py "deep learning testing" --ccf AI --rank B --years 2020-2025
"""

import argparse
import json
import subprocess
import sys
import urllib.parse
from datetime import datetime

# CCF Venue lists (from official CCF category lists)
# Software Engineering / System Software / Programming Languages
CCF_A_SE_CONFS = {'ICSE', 'FSE', 'ISSTA', 'PLDI', 'POPL', 'SOSP', 'OOPSLA', 'OSDI', 'FM'}
CCF_A_SE_JOURNALS = {'TOSEM', 'TSE', 'TOPLAS', 'TSC'}  # IEEE TPAMI is AI

# CCF-B SE (conferences and journals)
CCF_B_SE_CONFS = {'RE', 'CAiSE', 'ECOOP', 'ETAPS', 'ICPC', 'ICFP', 'LCTES', 'MoDELS', 'CP',
                   'ICSOC', 'SANER', 'ICSME', 'VMCAI', 'ICWS', 'Middleware', 'SAS', 'ESEM', 'ISSRE', 'HotOS'}
CCF_B_SE_JOURNALS = {'ASE', 'ESE', 'IETS', 'IST', 'JFP', 'JSEP', 'RE', 'SCP', 'SoSyM', 'STVR', 'SPE',
                       'JOURNAL OF SOFTWARE EVOLUTION', 'JOURNAL OF SYSTEMS AND SOFTWARE'}

# CCF-A AI
CCF_A_AI_CONFS = {'AAAI', 'NeurIPS', 'ACL', 'CVPR', 'ICCV', 'ICML', 'IJCAI', 'ECCV'}
CCF_A_AI_JOURNALS = {'AI', 'TPAMI', 'IJCV', 'JMLR'}

# CCF-B AI
CCF_B_AI_CONFS = {'EMNLP', 'ECAI', 'ICRA', 'ICAPS', 'ICCBR', 'COLING', 'KR', 'UAI', 'AAMAS', 'PPSN', 'NAACL', 'COLT'}
CCF_B_AI_JOURNALS = {'AAMAS', 'CL', 'CVIU', 'DKE', 'EC', 'TAC', 'TASLP', 'TCYB', 'TEC', 'TFS', 'TNNLS',
                      'IJAR', 'JAIR', 'JAR', 'JSLHR', 'ML', 'NC', 'NN', 'PR', 'TACL'}

# Exclude false positives from venue matching
EXCLUDE_KEYWORDS = {'REMOTE', 'SMARTGREENS', 'VEHITS', 'IFM', 'NFM', 'TALN', 'RECITAL',
                     'ENASE', 'ITICSE', 'EQUITY', 'DIVERSITY', 'INCLUSION', 'FORMALISE',
                     'AI ETHICS', 'PANAFRICON'}  # AI ETHICS contains AI but isn't a CCF venue

# Multi-token venues (match full name, not substring)
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

ALL_CCF_VENUES = (CCF_A_SE_CONFS | CCF_B_SE_CONFS | CCF_A_SE_JOURNALS | CCF_B_SE_JOURNALS |
                   CCF_A_AI_CONFS | CCF_B_AI_CONFS | CCF_A_AI_JOURNALS | CCF_B_AI_JOURNALS)


def classify_venue(venue_upper: str) -> tuple:
    """Classify a venue into (category, rank). Returns ('OTHER', '') if not CCF."""
    # Check false positives
    if any(ex in venue_upper for ex in EXCLUDE_KEYWORDS):
        return 'OTHER', ''

    # Check multi-token venues first (longest match wins)
    for vname, result in sorted(MULTI_TOKEN_VENUES.items(), key=lambda x: -len(x[0])):
        if vname in venue_upper:
            return result

    # Split into tokens and check
    tokens = set(venue_upper.split())

    # CCF-A SE - exact token match
    match = tokens & CCF_A_SE_CONFS
    if match:
        return 'CCF-A SE', 'conference'
    match = tokens & CCF_A_SE_JOURNALS
    if match:
        return 'CCF-A SE', 'journal'

    # CCF-B SE - exact token match
    match = tokens & CCF_B_SE_CONFS
    if match:
        return 'CCF-B SE', 'conference'
    match = tokens & CCF_B_SE_JOURNALS
    if match:
        return 'CCF-B SE', 'journal'

    # CCF-A AI - exact token match (NeurIPS needs special handling)
    match = tokens & CCF_A_AI_CONFS
    if match:
        return 'CCF-A AI', 'conference'
    match = tokens & CCF_A_AI_JOURNALS
    if match:
        return 'CCF-A AI', 'journal'

    # CCF-B AI - exact token match
    match = tokens & CCF_B_AI_CONFS
    if match:
        return 'CCF-B AI', 'conference'
    match = tokens & CCF_B_AI_JOURNALS
    if match:
        return 'CCF-B AI', 'journal'

    return 'OTHER', ''


def search_dblp(query: str, max_hits: int = 100) -> list:
    """Search DBLP API and return list of paper dicts."""
    encoded_q = urllib.parse.quote(query)
    r = subprocess.run(
        ['curl', '-s', f'https://dblp.org/search/publ/api?q={encoded_q}&format=json&h={max_hits}'],
        capture_output=True
    )
    try:
        data = json.loads(r.stdout)
        return data.get('result', {}).get('hits', {}).get('hit', [])
    except:
        return []


def search_venue_prefix(venue: str, query: str, max_hits: int = 20) -> list:
    """Search DBLP with venue:prefix query for targeted venue search."""
    encoded_q = urllib.parse.quote(f"venue:{venue} {query}")
    r = subprocess.run(
        ['curl', '-s', f'https://dblp.org/search/publ/api?q={encoded_q}&format=json&h={max_hits}'],
        capture_output=True
    )
    try:
        data = json.loads(r.stdout)
        return data.get('result', {}).get('hits', {}).get('hit', [])
    except:
        return []


def parse_paper(hit: dict) -> dict:
    """Parse a DBLP hit into a normalized paper dict."""
    info = hit['info']
    venue_upper = info.get('venue', '').upper()
    category, vtype = classify_venue(venue_upper)

    authors_raw = info.get('authors', {}).get('author', [])
    if not isinstance(authors_raw, list):
        authors_raw = [authors_raw]
    authors = [a.get('text', str(a)) if isinstance(a, dict) else str(a) for a in authors_raw]

    return {
        'title': info.get('title', ''),
        'authors': authors,
        'authors_str': ', '.join(authors),
        'venue': info.get('venue', ''),
        'year': info.get('year', ''),
        'key': info.get('url', '').replace('https://dblp.org/rec/', ''),
        'dblp_url': info.get('url', ''),
        'category': category,
        'rank': category.split(' ')[0] if category else '',
        'type': vtype,
    }


def filter_papers(papers: list, args) -> list:
    """Filter papers by year range, CCF rank, CCF category."""
    filtered = []
    for p in papers:
        # Year filter
        year = int(p.get('year') or 0)
        if args.year_from and year < args.year_from:
            continue
        if args.year_to and year > args.year_to:
            continue

        # CCF rank filter
        if args.rank:
            rank = p.get('rank', '')
            if args.rank.upper() not in rank:
                continue

        # CCF category filter
        if args.ccf:
            ccf = args.ccf.upper()
            if ccf == 'SE' and 'SE' not in p.get('category', ''):
                continue
            if ccf == 'AI' and 'AI' not in p.get('category', ''):
                continue

        # Page count filter (approximate - caller should verify)
        # Page count filter - caller should filter after fetching page counts
        pass

        filtered.append(p)

    return filtered


def deduplicate(papers: list) -> list:
    """Deduplicate by DBLP key."""
    seen = set()
    unique = []
    for p in papers:
        if p['key'] not in seen:
            seen.add(p['key'])
            unique.append(p)
    return unique


def print_results(papers: list, verbose: bool = False):
    """Print papers in table format."""
    if not papers:
        print("No papers found matching criteria.")
        return

    # Sort by rank, year, venue
    rank_order = {'CCF-A SE': 0, 'CCF-A AI': 1, 'CCF-B SE': 2, 'CCF-B AI': 3, 'OTHER': 4}
    papers.sort(key=lambda p: (rank_order.get(p['category'], 4), p.get('year', ''), p.get('venue', '')))

    print(f"\n{'Rank':<10} {'Year':<6} {'Venue':<25} {'Title':<50} {'Authors':<30} {'DBLP Key'}")
    print("-" * 150)

    for p in papers:
        rank = p.get('category', 'OTHER')
        year = p.get('year', 'N/A')
        venue = p.get('venue', '')[:23]
        title = p.get('title', '')[:48]
        authors = p.get('authors_str', '')[:28]
        key = p.get('key', '')

        print(f"{rank:<10} {year:<6} {venue:<25} {title:<50} {authors:<30} {key}")

    print(f"\nTotal: {len(papers)} papers")


def main():
    parser = argparse.ArgumentParser(description='Search DBLP with CCF venue filtering')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--ccf', choices=['SE', 'AI', 'ALL'], default='ALL',
                        help='Filter by CCF category: SE (Software Engineering), AI (Artificial Intelligence), or ALL')
    parser.add_argument('--rank', choices=['A', 'B', 'ALL'], default='ALL',
                        help='Filter by CCF rank: A, B, or ALL')
    parser.add_argument('--year-from', '--year_from', type=int, default=None,
                        help='Filter papers from this year onward')
    parser.add_argument('--year-to', '--year_to', type=int, default=None,
                        help='Filter papers up to this year')
    parser.add_argument('--years', default=None,
                        help='Year range, e.g. 2020-2025')
    parser.add_argument('--hits', type=int, default=100,
                        help='Max results per query (default: 100)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show extra debug info')
    parser.add_argument('--json', action='store_true',
                        help='Output raw JSON')

    args = parser.parse_args()

    # Parse year range
    if args.years:
        try:
            args.year_from, args.year_to = map(int, args.years.split('-'))
        except:
            print("Error: --years should be in format YYYY-YYYY")
            sys.exit(1)

    # Default: last 5 years
    if not args.year_from and not args.year_to:
        current_year = datetime.now().year
        args.year_from = current_year - 5
        args.year_to = current_year

    if args.verbose:
        print(f"Searching DBLP for: '{args.query}'")
        print(f"Filters: CCF={args.ccf}, Rank={args.rank}, Years={args.year_from}-{args.year_to}")

    # Search DBLP
    hits = search_dblp(args.query, max_hits=args.hits)

    if args.verbose:
        print(f"DBLP returned {len(hits)} raw hits")

    # Parse and classify
    papers = []
    for hit in hits:
        p = parse_paper(hit)
        papers.append(p)

    # Filter
    filtered = filter_papers(papers, args)
    filtered = deduplicate(filtered)

    if args.json:
        print(json.dumps(filtered, indent=2))
    else:
        print_results(filtered, verbose=args.verbose)

    return filtered


if __name__ == '__main__':
    main()
