#!/usr/bin/env python3
"""
Generate a literature review report (md + bibtex) from DBLP search results.

Usage:
    python3 generate_report.py "requirements validation" --ccf SE --rank A --years 2021-2025
    python3 generate_report.py "AI requirements engineering" --ccf ALL --rank A --years 2023-2025
    python3 generate_report.py "deep learning testing" --output ~/papers
"""

import argparse
import subprocess
import json
import urllib.parse
import sys
import os
import re
import time
from datetime import datetime


# ===== CCF Venue Lists =====

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


def classify_venue(venue_upper):
    if any(ex in venue_upper for ex in EXCLUDE_KEYWORDS):
        return 'OTHER', ''
    tokens = set(venue_upper.split())
    if tokens & CCF_A_SE_CONFS:
        return 'CCF-A SE', 'conference'
    if tokens & CCF_A_SE_JOURNALS:
        return 'CCF-A SE', 'journal'
    if tokens & CCF_B_SE_CONFS:
        return 'CCF-B SE', 'conference'
    if tokens & CCF_B_SE_JOURNALS:
        return 'CCF-B SE', 'journal'
    if tokens & CCF_A_AI_CONFS:
        return 'CCF-A AI', 'conference'
    if tokens & CCF_A_AI_JOURNALS:
        return 'CCF-A AI', 'journal'
    if tokens & CCF_B_AI_CONFS:
        return 'CCF-B AI', 'conference'
    if tokens & CCF_B_AI_JOURNALS:
        return 'CCF-B AI', 'journal'
    return 'OTHER', ''


def fetch_bibtex(dblp_key):
    url = 'https://dblp.org/rec/bib/' + dblp_key + '.bib'
    r = subprocess.run(['curl', '-sL', url], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace') if isinstance(r.stdout, bytes) else r.stdout


def search_dblp(query, max_hits=100):
    encoded_q = urllib.parse.quote(query)
    r = subprocess.run(
        ['curl', '-s', 'https://dblp.org/search/publ/api?q=' + encoded_q + '&format=json&h=' + str(max_hits)],
        capture_output=True)
    try:
        data = json.loads(r.stdout)
        return data.get('result', {}).get('hits', {}).get('hit', [])
    except:
        return []


def parse_paper(hit):
    info = hit['info']
    venue_upper = info.get('venue', '').upper()
    category, vtype = classify_venue(venue_upper)
    authors_raw = info.get('authors', {}).get('author', [])
    if not isinstance(authors_raw, list):
        authors_raw = [authors_raw]
    authors = []
    for a in authors_raw:
        if isinstance(a, dict):
            authors.append(a.get('text', str(a)))
        else:
            authors.append(str(a))
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


def filter_papers(papers, args):
    filtered = []
    for p in papers:
        year = int(p.get('year') or 0)
        if args.year_from and year < args.year_from:
            continue
        if args.year_to and year > args.year_to:
            continue
        if args.rank:
            if args.rank.upper() not in p.get('rank', ''):
                continue
        if args.ccf:
            ccf = args.ccf.upper()
            if ccf == 'SE' and 'SE' not in p.get('category', ''):
                continue
            if ccf == 'AI' and 'AI' not in p.get('category', ''):
                continue
        filtered.append(p)
    return filtered


def deduplicate(papers):
    seen = set()
    unique = []
    for p in papers:
        if p['key'] not in seen:
            seen.add(p['key'])
            unique.append(p)
    return unique


def format_author_initials(name):
    parts = name.split()
    if len(parts) >= 2:
        last = parts[-1]
        if re.match(r'^\d{4}$', last):
            if len(parts) >= 3:
                initials = ' '.join(p[0] + '.' for p in parts[:-2])
                return initials + ' ' + parts[-2]
            return parts[0][0] + '. ' + last
        initials = ' '.join(p[0] + '.' for p in parts[:-1])
        return initials + ' ' + parts[-1]
    return name


def sentence_case(title):
    if not title:
        return title
    return title[0].upper() + title[1:].lower()


def short_venue(venue, year):
    v = venue.upper()
    if 'SOFTWARE ENGINEERING' in v and 'INTERNATIONAL CONFERENCE' in v:
        return 'IEEE/ACM Int. Conf. Software Engineering (ICSE)'
    if 'IEEE TRANSACTIONS ON SOFTWARE ENGINEERING' in v:
        return 'IEEE Trans. Software Engineering'
    if 'IEEE TRANSACTIONS ON PATTERN ANALYSIS' in v:
        return 'IEEE Trans. Pattern Analysis and Machine Intelligence'
    if 'JOURNAL OF MACHINE LEARNING' in v:
        return 'J. Machine Learning Research'
    if 'ARTIFICIAL INTELLIGENCE' in v and len(v) < 30:
        return 'Artificial Intelligence'
    if 'NEURAL INFORMATION PROCESSING' in v:
        return 'NeurIPS'
    if 'AAAI' in v:
        return 'AAAI'
    if 'ASSOCIATION COMPUTATIONAL LINGUISTICS' in v:
        return 'ACL'
    if 'COMPUTER VISION AND PATTERN' in v:
        return 'CVPR'
    return venue


def ieee_format(paper):
    authors = paper['authors']
    year = paper['year']
    title = paper['title']
    venue = paper['venue']
    venue_short = short_venue(venue, year)

    if len(authors) == 1:
        author_str = format_author_initials(authors[0])
    elif len(authors) == 2:
        author_str = format_author_initials(authors[0]) + ' and ' + format_author_initials(authors[1])
    else:
        author_str = ', '.join(format_author_initials(a) for a in authors[:-1]) + ', and ' + format_author_initials(authors[-1])

    title_sc = sentence_case(title)
    return author_str + ', "' + title_sc + '," in *' + venue_short + '*, ' + year + '.'


def generate_md(papers, topic, args, full_bibtex):
    today = datetime.now().strftime('%Y-%m-%d')

    rank_order = {'CCF-A SE': 0, 'CCF-A AI': 1, 'CCF-B SE': 2, 'CCF-B AI': 3, 'OTHER': 4}
    papers_sorted = sorted(papers, key=lambda p: (rank_order.get(p['category'], 4), p.get('year', ''), p.get('venue', '')))

    lines = []
    lines.append('# Literature Review: ' + topic)
    lines.append('')
    scope = (args.ccf or 'ALL') + ' / ' + (args.rank or 'ALL')
    lines.append('> Generated: ' + today + '  |  Topic: "' + topic + '"  |  Scope: ' + scope + '  |  Year: ' + str(args.year_from) + '--' + str(args.year_to) + '  |  Papers: ' + str(len(papers)))
    lines.append('')

    groups = {}
    for p in papers_sorted:
        cat = p.get('category', 'OTHER')
        groups.setdefault(cat, []).append(p)

    for cat in ['CCF-A SE', 'CCF-A AI', 'CCF-B SE', 'CCF-B AI']:
        if cat not in groups:
            continue
        lines.append('## ' + cat + ' Papers')
        lines.append('')
        for i, p in enumerate(groups[cat], 1):
            lines.append('**[' + str(i) + ']** ' + p['title'])
            dblp_url = 'https://dblp.org/rec/' + p['key']
            lines.append('> ' + p['authors_str'] + ' -- *' + p['venue'] + '*, ' + p['year'] + ' -- [`' + p['key'] + '`](' + dblp_url + ')')
            lines.append('')
        lines.append('')

    lines.append('## References (IEEE Format)')
    lines.append('')
    for i, p in enumerate(papers_sorted, 1):
        lines.append('**[' + str(i) + ']** ' + ieee_format(p))
    lines.append('')

    lines.append('## BibTeX')
    lines.append('')
    lines.append('```bibtex')
    lines.append(full_bibtex.strip())
    lines.append('```')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate literature review report from DBLP')
    parser.add_argument('topic', help='Research topic / search query')
    parser.add_argument('--ccf', choices=['SE', 'AI', 'ALL'], default='ALL', help='CCF category')
    parser.add_argument('--rank', choices=['A', 'B', 'ALL'], default='ALL', help='CCF rank')
    parser.add_argument('--year-from', dest='year_from', type=int, default=None, help='Start year')
    parser.add_argument('--year-to', dest='year_to', type=int, default=None, help='End year')
    parser.add_argument('--years', help='Year range, e.g. 2021-2025')
    parser.add_argument('--hits', type=int, default=100, help='Max DBLP hits per query')
    parser.add_argument('--output', '-o', default=None, help='Output directory (default: current dir)')
    parser.add_argument('--basename', default=None, help='Base filename without extension')

    args = parser.parse_args()

    if args.years:
        try:
            parts = args.years.split('-')
            args.year_from = int(parts[0])
            args.year_to = int(parts[1])
        except:
            print('Error: --years should be format YYYY-YYYY')
            sys.exit(1)
    if not args.year_from and not args.year_to:
        current_year = datetime.now().year
        args.year_from = current_year - 5
        args.year_to = current_year

    print('Searching DBLP for: "' + args.topic + '" ...', file=sys.stderr)
    hits = search_dblp(args.topic, max_hits=args.hits)
    print('  -> ' + str(len(hits)) + ' raw hits', file=sys.stderr)

    papers = [parse_paper(h) for h in hits]
    papers = filter_papers(papers, args)
    papers = deduplicate(papers)
    print('  -> ' + str(len(papers)) + ' papers after filtering', file=sys.stderr)

    if not papers:
        print('No papers found. Try a broader query.')
        sys.exit(0)

    print('Fetching BibTeX (with polite delay)...', file=sys.stderr)
    bibtex_entries = []
    for i, p in enumerate(papers):
        if i > 0:
            time.sleep(1.5)  # polite delay between requests
        bib = fetch_bibtex(p['key'])
        bib = bib.strip() if bib else ''
        if bib and bib.startswith('@'):
            bibtex_entries.append(bib)
            print('  fetched: ' + p['key'], file=sys.stderr)
        else:
            bibtex_entries.append('% BibTeX not available for ' + p['key'] + ' (rate limited or not found)')
            print('  skipped: ' + p['key'], file=sys.stderr)
    full_bibtex = '\n\n'.join(bibtex_entries)

    safe_topic = re.sub(r'[^\w\s-]', '', args.topic)[:50].strip().replace(' ', '-')
    base = args.basename or ('literature-review-' + safe_topic)
    output_dir = args.output or '.'

    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, base + '.md')
    bib_path = os.path.join(output_dir, base + '.bib')

    md_content = generate_md(papers, args.topic, args, full_bibtex)

    with open(md_path, 'w') as f:
        f.write(md_content)

    with open(bib_path, 'w') as f:
        f.write(full_bibtex)

    print('')
    print('Saved:')
    print('  Report: ' + md_path)
    print('  BibTeX: ' + bib_path)


if __name__ == '__main__':
    main()
