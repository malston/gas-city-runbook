#!/usr/bin/env python3
"""Check relative links and #anchors in the runbook's Markdown files.

Use it after moving, renaming or retitling a doc. It reads every *.md file in
the repo (skipping .git and .remember), resolves each relative link against the
linking file, and checks that the target exists. For links with a #fragment
into a Markdown file, it checks the fragment matches a heading slug the way
GitHub builds them. External http(s) links are not fetched.

Usage: scripts/check-links.py [-h]

Exit status:
  0  every relative link resolves
  1  one or more broken links; each is printed as file:line: link (reason)
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP = {".git", ".remember"}
LINK = re.compile(r"\]\(([^)\s]+)\)")


def slug(heading):
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(path):
    text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    return {slug(m) for m in re.findall(r"^#+\s+(.*)$", text, flags=re.M)}


def main():
    if len(sys.argv) > 1:
        print(__doc__.strip())
        return 0 if sys.argv[1] in ("-h", "--help") else 1
    broken = []
    files = [p for p in ROOT.rglob("*.md") if not SKIP & set(p.relative_to(ROOT).parts)]
    for md in sorted(files):
        in_code = False
        for n, line in enumerate(md.read_text().splitlines(), 1):
            if line.startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            for target in LINK.findall(line):
                if re.match(r"[a-z]+:", target):
                    continue
                path, _, frag = target.partition("#")
                dest = (md.parent / path).resolve() if path else md
                where = f"{md.relative_to(ROOT)}:{n}: {target}"
                if not dest.exists():
                    broken.append(f"{where} (no such file)")
                elif frag and dest.suffix == ".md" and frag not in anchors(dest):
                    broken.append(f"{where} (no heading #{frag})")
    for b in broken:
        print(b)
    print(f"{len(files)} files checked, {len(broken)} broken links", file=sys.stderr)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
