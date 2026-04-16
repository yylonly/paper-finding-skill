#!/usr/bin/env python3
"""
Filter papers by abstract relevance to a topic using Semantic Scholar API.
Takes a JSON file from search_dblp.py --json and filters out irrelevant papers.

Usage:
    python3 filter_by_abstract.py papers.json "requirements validation" -o filtered.json
    python3 filter_by_abstract.py papers.json "AI for design" -o relevant.json -v

Pipeline:
    search_dblp.py --json  →  filter_by_abstract.py  →  fetch_bibtex.py  →  bib2tex.py
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse


def search_semantic_scholar(query: str, year_from: int = None, year_to: int = None,
                             max_results: int = 20, retries: int = 3) -> dict:
    """
    Search Semantic Scholar API by query, return paper metadata including abstract.
    Returns a dict keyed by title (lowercase) for fast lookup.
    Retries on 429 rate-limit errors.
    """
    params = {
        'query': query,
        'limit': max_results,
        'fields': 'title,abstract,year,venue',
    }
    url = 'https://api.semanticscholar.org/graph/v1/paper/search?' + urllib.parse.urlencode(params)

    for attempt in range(retries):
        req = urllib.request.Request(url, headers={'User-Agent': 'paper-finding-skill/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                papers = {}
                for p in data.get('data', []):
                    title_key = p.get('title', '').lower().strip()
                    if title_key:
                        papers[title_key] = p
                return papers
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = (attempt + 1) * 2
                print(f'  Semantic Scholar rate limit, retrying in {wait}s...', file=sys.stderr)
                time.sleep(wait)
                continue
            print(f'Semantic Scholar API error: {e}', file=sys.stderr)
            return {}
        except Exception as e:
            print(f'Semantic Scholar API error: {e}', file=sys.stderr)
            return {}
    return {}


def title_words(title: str) -> set:
    stopwords = {'a', 'an', 'the', 'for', 'with', 'and', 'or', 'of', 'in', 'on', 'to', 'by',
                 'using', 'via', 'through', 'from', 'into', 'toward', 'towards'}
    return set(title.lower().split()) - stopwords


def title_similarity(paper_title: str, query: str) -> float:
    """
    Keyword overlap score between paper title and query terms.
    Returns 0.0 (no overlap) to 1.0 (all query terms in title).
    """
    t_words = title_words(paper_title)
    q_words = title_words(query)
    if not q_words:
        return 0.0
    overlap = len(t_words & q_words)
    return overlap / len(q_words)


def is_relevant(paper_title: str, paper_abstract: str, query: str,
                min_overlap: float = 0.15) -> tuple:
    """
    Determine if a paper is relevant to the query based on title + abstract.

    Returns (relevant: bool, reason: str)
    """
    title_lower = paper_title.lower()
    abstract_lower = (paper_abstract or '').lower()
    q_words = title_words(query)

    if not q_words:
        return True, 'no query terms'

    t_words = title_words(paper_title)
    a_words = set(abstract_lower.split())
    title_overlap = len(t_words & q_words) / len(q_words) if q_words else 0
    abstract_overlap = len((q_words) & a_words) / len(q_words) if q_words else 0

    # High title overlap — definitely relevant
    if title_overlap >= 0.4:
        return True, f'title overlap {title_overlap:.0%} >= 40%'

    # Moderate abstract overlap — accept
    if abstract_overlap >= min_overlap:
        return True, f'{abstract_overlap:.0%} of query terms in abstract >= {min_overlap:.0%} threshold'

    # Some title overlap but no abstract match — be lenient, accept if overlap > 0
    if title_overlap > 0:
        return True, f'some title overlap ({title_overlap:.0%}), accepting'

    return False, f'title overlap={title_overlap:.0%}, abstract overlap={abstract_overlap:.0%}'


def load_papers(path: str) -> list:
    """Load papers from JSON file (list format from search_dblp.py --json)."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def main():
    parser = argparse.ArgumentParser(
        description='Filter papers by abstract relevance using Semantic Scholar API')
    parser.add_argument('input', help='JSON file from search_dblp.py --json')
    parser.add_argument('topic', help='Research topic to filter relevance against')
    parser.add_argument('--output', '-o', help='Output JSON file (default: stdout)')
    parser.add_argument('--min-overlap', dest='min_overlap', type=float, default=0.15,
                        help='Min fraction of query terms in abstract to accept (default: 0.15)')
    parser.add_argument('--scholar-delay', dest='scholar_delay', type=float, default=0.5,
                        help='Delay between Semantic Scholar requests (default: 0.5s)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show per-paper relevance decision')

    args = parser.parse_args()

    papers = load_papers(args.input)
    if not papers:
        print('No papers found in input file.', file=sys.stderr)
        sys.exit(0)

    print(f'Loaded {len(papers)} papers from {args.input}', file=sys.stderr)
    print(f'Filtering by relevance to: "{args.topic}"', file=sys.stderr)

    # Fetch abstracts from Semantic Scholar
    print('Fetching abstracts from Semantic Scholar...', file=sys.stderr)
    scholar_papers = search_semantic_scholar(args.topic, max_results=len(papers) * 2)
    found_count = sum(1 for p in papers if p.get('title', '').lower().strip() in scholar_papers)
    print(f'  -> found {found_count}/{len(papers)} papers in Semantic Scholar', file=sys.stderr)

    relevant = []
    dropped = []

    for p in papers:
        title = p.get('title', '')
        title_key = title.lower().strip()
        abstract = scholar_papers.get(title_key, {}).get('abstract', '') if title_key in scholar_papers else ''

        is_rel, reason = is_relevant(title, abstract, args.topic, args.min_overlap)

        if args.verbose:
            mark = 'KEEP' if is_rel else 'DROP'
            short = title[:65]
            print(f'  [{mark}] {short}  ({reason})', file=sys.stderr)

        if is_rel:
            p['abstract'] = abstract
            relevant.append(p)
        else:
            dropped.append({'paper': p, 'reason': reason})

        time.sleep(args.scholar_delay)

    print(f'\nKept: {len(relevant)}/{len(papers)} papers', file=sys.stderr)
    if dropped:
        for d in dropped:
            short = d['paper']['title'][:60]
            print(f'  DROP: {short}  ({d["reason"]})', file=sys.stderr)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(relevant, f, indent=2, ensure_ascii=False)
        print(f'Saved {len(relevant)} papers to {args.output}', file=sys.stderr)
    else:
        print(json.dumps(relevant, indent=2, ensure_ascii=False))

    return relevant


if __name__ == '__main__':
    main()
