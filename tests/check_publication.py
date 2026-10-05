#!/usr/bin/env python3
"""Check that what is about to be published holds no personal data and no password.

    python tests/check_publication.py                  the commits not yet on GitHub (origin/master..HEAD)
    python tests/check_publication.py <range>          another range of commits, e.g. origin/master..v0.10

For every commit of the range, it looks at:
  - its author and committer e-mail addresses: only no-reply addresses may be published;
  - its message;
  - every text file of the published tree.
It reports any e-mail address (except the public ones listed below), any local path
revealing a user folder, the real eMule password (EMULE_PASSWORD, if set), and every
term of tests/private_terms.txt: a local file, ignored by git, one term per line, for
what must stay private but cannot be written in this published script (names of
private machines, of sites, a real name...). Findings never show a private value.
Exit code 1 when something is found. Python standard library only.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRIVATE_TERMS = os.path.join(HERE, 'private_terms.txt')

EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
# public addresses that may be published
ALLOWED_EMAILS = re.compile(r'(?i)(?:@users\.noreply\.github\.com|^noreply@github\.com|^noreply@anthropic\.com'
                            r'|^medleymind@gmail\.com|@example\.(?:com|org))$')
# noreply@github.com: committer of the commits made on the GitHub web site
# medleymind@gmail.com: in the LGPL notice of the embedded GM_config library
LOCAL_PATH = re.compile(r'(?i)\b[a-z]:[\\/](?:users|documents and settings)[\\/][^\\/\s]+'
                        r'|/(?:users|home)/[\w.-]+|/[a-z]/users/[\w.-]+')
BINARY = ('.png', '.jpg', '.jpeg', '.gif', '.ico')


def git(*args):
    return subprocess.check_output(['git', '-C', ROOT, *args]).decode('utf-8', 'replace')


def private_terms():
    """The private terms, from tests/private_terms.txt and EMULE_PASSWORD: never shown."""
    terms = []
    if os.path.exists(PRIVATE_TERMS):
        with open(PRIVATE_TERMS, encoding='utf-8') as f:
            terms = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    labels = [f'private term #{i}' for i in range(1, len(terms) + 1)]
    if os.environ.get('EMULE_PASSWORD'):
        terms.append(os.environ['EMULE_PASSWORD'])
        labels.append('the real eMule password')
    return list(zip(terms, labels))


def masked_email(address):
    user, domain = address.split('@', 1)
    return f'{user[:2]}***@{domain}'


def scan_text(text, where, terms, findings):
    for number, line in enumerate(text.splitlines(), 1):
        place = f'{where}:{number}' if number else where
        for address in EMAIL.findall(line):
            if not ALLOWED_EMAILS.search(address):
                findings.append((place, 'e-mail address', masked_email(address)))
        for path in LOCAL_PATH.findall(line):
            findings.append((place, 'local user folder', path[:40]))
        lowered = line.lower()
        for term, label in terms:
            if term.lower() in lowered:
                findings.append((place, label, ''))


def check(commit_range):
    terms = private_terms()
    commits = git('rev-list', commit_range).split()
    findings = []
    for commit in commits:
        short = commit[:7]
        for role, fmt in (('author', '%ae'), ('committer', '%ce')):
            address = git('show', '-s', f'--format={fmt}', commit).strip()
            if not ALLOWED_EMAILS.search(address):
                findings.append((f'commit {short}', f'{role} e-mail address', masked_email(address)))
        scan_text(git('show', '-s', '--format=%B', commit), f'commit {short} message', terms, findings)
        for name in git('ls-tree', '-r', '--name-only', commit).split('\n'):
            if name and not name.lower().endswith(BINARY):
                scan_text(git('show', f'{commit}:{name}'), f'{short} {name}', terms, findings)
    return commits, terms, sorted(set(findings))


def main():
    commit_range = sys.argv[1] if len(sys.argv) > 1 else 'origin/master..HEAD'
    commits, terms, findings = check(commit_range)
    print(f'{len(commits)} commit(s) checked ({commit_range}), {len(terms)} private term(s)'
          + ('' if os.path.exists(PRIVATE_TERMS) else f' — no {os.path.relpath(PRIVATE_TERMS, ROOT)} file'))
    for place, kind, value in findings:
        print(f'  {place:<40} {kind}' + (f': {value}' if value else ''))
    print('nothing personal found' if not findings else f'{len(findings)} finding(s): do not publish as is')
    sys.exit(1 if findings else 0)


if __name__ == '__main__':
    main()
