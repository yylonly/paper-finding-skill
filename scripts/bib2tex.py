#!/usr/bin/env python3
"""
Merge multiple .bib files into one and generate a LaTeX .tex file that cites them all.

Usage:
    python3 bib2tex.py refs1.bib refs2.bib -o combined
    python3 bib2tex.py *.bib --basename mypapers

Output:
    BASENAME.bib  — merged BibTeX file
    BASENAME.tex  — LaTeX file with \\cite{} for each entry, grouped by type/year
"""

import argparse
import os
import re
import sys


def parse_bib_entries(bib_text: str) -> list:
    """
    Parse a .bib file text into a list of (key, entry_text) tuples.
    Handles multi-line entries and nested braces.
    """
    entries = []
    i = 0
    n = len(bib_text)

    while i < n:
        # Find next @entry
        start = bib_text.find('@', i)
        if start == -1:
            break

        # Find the entry type (e.g. @inproceedings, @article)
        brace_start = bib_text.find('{', start)
        if brace_start == -1:
            i = start + 1
            continue

        entry_type = bib_text[start+1:brace_start].strip().lower()
        if entry_type not in ('comment', 'preamble', 'string'):
            # Find the matching closing brace using depth count
            depth = 0
            j = brace_start
            while j < n:
                if bib_text[j] == '{':
                    depth += 1
                elif bib_text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1

            entry_text = bib_text[start:j+1]

            # Extract citation key
            m = re.search(r'@\w+\{([^,\s]+)', entry_text)
            key = m.group(1) if m else f'unknown{start}'

            entries.append((key, entry_text))

        i = j + 1

    return entries


def merge_bib_files(bib_paths: list) -> tuple:
    """
    Merge multiple .bib files.
    Returns (merged_bib_text, entries) where entries = [(key, full_text)]
    """
    all_entries = []
    seen_keys = {}

    for path in bib_paths:
        if not os.path.exists(path):
            print(f'Warning: file not found: {path}', file=sys.stderr)
            continue

        with open(path) as f:
            text = f.read()

        entries = parse_bib_entries(text)

        for key, entry_text in entries:
            if key in seen_keys:
                print(f'Warning: duplicate key "{key}" — skipping second occurrence', file=sys.stderr)
                continue
            seen_keys[key] = True
            all_entries.append((key, entry_text))

    # Build merged .bib text
    merged = '\n\n'.join(e[1] for e in all_entries)
    return merged, all_entries


def generate_tex(entries: list, basename: str) -> str:
    """
    Generate a LaTeX .tex file with \\cite{} for each BibTeX entry.
    Groups entries by type (@inproceedings, @article, etc.) then sorts by year/key.
    """
    lines = []
    lines.append('%' + '=' * 60)
    lines.append(f'% Bibliography: {basename}')
    lines.append(f'% Generated: {__import__("datetime").datetime.now().strftime("%Y-%m-%d")}')
    lines.append(f'% Entries: {len(entries)}')
    lines.append('%' + '=' * 60)
    lines.append('')
    lines.append(r'\documentclass[12pt]{article}')
    lines.append(r'\usepackage[utf8]{inputenc}')
    lines.append(r'\usepackage{hyperref}')
    lines.append(r'\usepackage{cite}')
    lines.append(r'\bibliographystyle{IEEEtran}')
    lines.append(r'\bibliography{' + basename + r'}')  # no .bib extension
    lines.append('')
    lines.append(r'\begin{document}')
    lines.append('')
    lines.append('% References')
    lines.append('')

    # Group entries by type
    by_type = {}
    for key, entry_text in entries:
        m = re.search(r'@\w+\{', entry_text)
        etype = m.group()[1:-1] if m else 'unknown'
        by_type.setdefault(etype, []).append((key, entry_text))

    # Sort each type group by year (if present) then by key
    def sort_key(item):
        key, entry = item
        year_m = re.search(r'\byear\s*=\s*[{"]?(\d{4})', entry, re.IGNORECASE)
        year = year_m.group(1) if year_m else '0000'
        return (year, key)

    for etype in sorted(by_type.keys()):
        group = sorted(by_type[etype], key=sort_key)
        lines.append(f'% --- {etype} ---')
        lines.append('')
        for key, entry in group:
            # Extract title for comment
            title_m = re.search(r'\btitle\s*=\s*[{"]?([^@,\n]+)', entry, re.IGNORECASE)
            title = title_m.group(1).strip()[:80] if title_m else '(no title)'
            year_m = re.search(r'\byear\s*=\s*[{"]?(\d{4})', entry, re.IGNORECASE)
            year = year_m.group(1) if year_m else '????'

            lines.append(f'% {key}  ({year})')
            lines.append(f'%   {title}')
            lines.append(f'\\cite{{{key}}}')
            lines.append('')

    lines.append(r'\end{document}')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Merge .bib files and generate a LaTeX .tex with \\cite{} for each entry')
    parser.add_argument('bib_files', nargs='*',
                        help='.bib files to merge (e.g. refs1.bib refs2.bib)')
    parser.add_argument('--file', '-f', action='append',
                        help='Additional .bib files (can be specified multiple times, or use glob pattern)')
    parser.add_argument('--output', '-o', default=None,
                        help='Output directory (default: current dir)')
    parser.add_argument('--basename', default=None,
                        help='Base name for output files (default: derived from first input file)')

    args = parser.parse_args()

    # Collect all .bib file paths
    bib_paths = list(args.bib_files)
    if args.file:
        bib_paths.extend(args.file)

    if not bib_paths:
        parser.print_help()
        return

    # Resolve glob patterns and expand directories
    import glob
    resolved = []
    for p in bib_paths:
        if '*' in p or '?' in p:
            resolved.extend(glob.glob(p))
        elif os.path.isdir(p):
            for f in os.listdir(p):
                if f.endswith('.bib'):
                    resolved.append(os.path.join(p, f))
        else:
            resolved.append(p)

    bib_paths = [os.path.abspath(p) for p in resolved if os.path.exists(p)]
    bib_paths = sorted(set(bib_paths))  # deduplicate

    if not bib_paths:
        print('Error: no valid .bib files found', file=sys.stderr)
        sys.exit(1)

    # Determine basename
    if args.basename:
        basename = args.basename
    else:
        first = os.path.basename(bib_paths[0])
        basename = os.path.splitext(first)[0]

    output_dir = args.output or '.'

    # Merge
    print(f'Merging {len(bib_paths)} .bib files...', file=sys.stderr)
    merged_bib, entries = merge_bib_files(bib_paths)

    if not entries:
        print('Error: no BibTeX entries found in input files', file=sys.stderr)
        sys.exit(1)

    print(f'  -> {len(entries)} entries (deduplicated)', file=sys.stderr)

    # Save .bib
    os.makedirs(output_dir, exist_ok=True)
    bib_path = os.path.join(output_dir, basename + '.bib')
    with open(bib_path, 'w') as f:
        f.write(merged_bib)
    print(f'  BibTeX: {bib_path}', file=sys.stderr)

    # Generate .tex
    tex_content = generate_tex(entries, basename)
    tex_path = os.path.join(output_dir, basename + '.tex')
    with open(tex_path, 'w') as f:
        f.write(tex_content)
    print(f'  LaTeX:   {tex_path}', file=sys.stderr)

    print('')
    print(f'To use in your LaTeX document:')
    print(f'  \\input{{{basename}.tex}}')


if __name__ == '__main__':
    main()
