"""Create the GitHub labels, milestones, issues and Project board described by docs/plan/backlog.yaml.

Idempotent: anything that already exists (matched by name, title or the ``[ID]`` title prefix) is left
alone, so the script is safe to rerun after adding items to the backlog. It never edits or closes
issues; the plan docs stay the source of truth for criteria, the issues for work status.

    uv run --with pyyaml python tools/plan_sync.py --dry-run
    uv run --with pyyaml python tools/plan_sync.py --project "Music Engineering"

Needs the GitHub CLI, logged in with the ``project`` scope (``gh auth login -s project``).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "plan"
PLAN_DOCS = ["prd.md", "dod.md", "scorecard.md", "sourcing.md", "alignment.md"]
SCORE_FIELDS = ["Score EN", "Score LT", "Score (any)", "Quality Q", "Evidence E"]


def gh(*args, input_text=None, check=True):
    result = subprocess.run(["gh", *args], input=input_text, capture_output=True, text=True, encoding="utf-8")
    if check and result.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def slug(heading):
    text = re.sub(r"[^\w\s-]", "", heading.lower())
    return re.sub(r"\s+", "-", text.strip())


def clean(cell):
    return re.sub(r"[*`]", "", cell).strip()


def parse_tables():
    """Index every plan-table row by its first cell's ID (``FR-1 Ingest`` -> ``FR-1``) and full text."""
    rows = {}
    for name in PLAN_DOCS:
        heading, lines = "", (PLAN / name).read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            is_table = line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*-{3}", lines[i + 1])
            if is_table:
                header = [clean(c) for c in line.strip("|").split("|")]
                i += 2
                while i < len(lines) and lines[i].startswith("|"):
                    cells = [c.strip() for c in lines[i].strip("|").split("|")]
                    row = dict(zip(header, cells), _doc=name, _anchor=slug(heading))
                    first = clean(cells[0])
                    rows.setdefault(first, []).append(row)
                    rows.setdefault(first.split(" ")[0], []).append(row)
                    i += 1
                continue
            i += 1
    return rows


def pick(rows, key, column):
    for row in rows.get(key, []):
        if column in row and row[column]:
            return row
    return None


def build_issue(item, rows, milestones):
    iid = item["id"]
    ui = re.match(r"^[UVRM]\d+$", iid)
    kind = "user-action" if ui else item.get("type", "task")
    sections, title, priority, agreement = [], item.get("title"), item.get("priority"), None

    if kind == "requirement":
        req = pick(rows, iid, "Requirement")
        done = pick(rows, iid, "Done when")
        title = title or clean(req["Stage"])
        sections.append(f"**Requirement** ([PRD](../blob/main/docs/plan/{req['_doc']}#{req['_anchor']}))\n\n{req['Requirement']}")
        if done:
            sections.append(f"**Done when** ([DoD](../blob/main/docs/plan/{done['_doc']}#{done['_anchor']}))\n\n- [ ] {done['Done when']}\n\n**Evidence:** {done['Evidence']}")
    elif kind == "family":
        fam = pick(rows, item["family"], "How it's transcribed")
        title = title or f"{item['family']} transcription and notation"
        how = fam["How it's transcribed"]
        sections.append(
            f"**How it's transcribed:** {how}\n\n"
            f"**What the user sees:** {fam['What the user sees']}\n\n"
            f"**Done when** ([DoD](../blob/main/docs/plan/{fam['_doc']}#{fam['_anchor']}))\n\n- [ ] {fam['Done when (proposed)']}"
        )
    elif ui:
        row = pick(rows, iid, "Done when")
        action = row.get("The user can…") or row.get("Can…")
        title = title or clean(action)
        who = f" · **Who:** {row['Who']}" if row.get("Who") else ""
        priority = priority or clean(row.get("Priority", "")).lower() or None
        agreement = clean(row.get("Status", "")).lower() or None
        sections.append(
            f"**The user can:** {action}{who}\n\n"
            f"**Done when** ([plan](../blob/main/docs/plan/{row['_doc']}#{row['_anchor']}))\n\n- [ ] {row['Done when']}\n\n"
            "Accepted by a recorded walkthrough on two songs per language (DoD walkthrough rules)."
        )
    else:
        if item.get("body"):
            sections.append(item["body"])
        if item.get("doc"):
            sections.append(f"**Plan:** [docs/plan/{item['doc']}](../blob/main/docs/plan/{item['doc']})")
        if kind == "decision":
            sections.append("Close this issue with a link to the ADR or plan PR that records the decision.")

    langs = item.get("langs", [])
    if kind in ("requirement", "family", "user-action"):
        scope = " and ".join(l.upper() for l in langs) if langs else "any language"
        sections.append(f"**Scorecard:** scored for {scope}; done at 100. Every-change checklist in the [DoD](../blob/main/docs/plan/dod.md#every-change) applies.")

    labels = [f"type:{kind}", f"area:{item['area']}"] + [f"lang:{l}" for l in langs]
    if priority:
        labels.append(f"priority:{priority}")
    if agreement:
        labels.append(f"agreement:{agreement}")
    gate = milestones[int(item["gate"][1])]["title"]
    return {"id": iid, "title": f"[{iid}] {title}", "body": "\n\n".join(sections), "labels": labels,
            "milestone": gate, "skip": agreement == "cut"}


def ensure_labels(repo, labels, dry):
    existing = {l["name"] for l in json.loads(gh("label", "list", "-R", repo, "--limit", "200", "--json", "name"))}
    for name, spec in labels.items():
        if name in existing:
            continue
        print(f"label    + {name}")
        if not dry:
            gh("label", "create", name, "-R", repo, "--color", spec["color"], "--description", spec.get("description", ""))


def ensure_milestones(repo, milestones, dry):
    existing = {m["title"] for m in json.loads(gh("api", f"repos/{repo}/milestones?state=all&per_page=100"))}
    for m in milestones:
        if m["title"] in existing:
            continue
        print(f"milestone+ {m['title']}")
        if not dry:
            gh("api", f"repos/{repo}/milestones", "-f", f"title={m['title']}", "-f", f"description={m['description']}")


def ensure_issues(repo, issues, dry):
    existing = json.loads(gh("issue", "list", "-R", repo, "--state", "all", "--limit", "1000", "--json", "number,title"))
    by_id = {m.group(1): i["number"] for i in existing if (m := re.match(r"^\[([^\]]+)\]", i["title"]))}
    for issue in issues:
        if issue["skip"] or issue["id"] in by_id:
            continue
        print(f"issue    + {issue['title']}  ({issue['milestone']}; {', '.join(issue['labels'])})")
        if dry:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(issue["body"])
        args = ["issue", "create", "-R", repo, "--title", issue["title"], "--body-file", f.name, "--milestone", issue["milestone"]]
        for label in issue["labels"]:
            args += ["--label", label]
        url = gh(*args).strip()
        by_id[issue["id"]] = int(url.rsplit("/", 1)[1])
        Path(f.name).unlink()
    return by_id


def ensure_project(repo, title, by_id, dry):
    owner = repo.split("/")[0]
    projects = json.loads(gh("project", "list", "--owner", owner, "--format", "json"))["projects"]
    project = next((p for p in projects if p["title"] == title), None)
    if project is None:
        print(f"project  + {title}")
        if dry:
            return
        project = json.loads(gh("project", "create", "--owner", owner, "--title", title, "--format", "json"))
        gh("project", "link", str(project["number"]), "--owner", owner, "--repo", repo)
    number = str(project["number"])
    fields = {f["name"] for f in json.loads(gh("project", "field-list", number, "--owner", owner, "--format", "json"))["fields"]}
    for name in SCORE_FIELDS:
        if name not in fields:
            print(f"field    + {name}")
            if not dry:
                gh("project", "field-create", number, "--owner", owner, "--name", name, "--data-type", "NUMBER")
    items = json.loads(gh("project", "item-list", number, "--owner", owner, "--limit", "1000", "--format", "json"))["items"]
    on_board = {i["content"].get("number") for i in items if i.get("content")}
    for iid, num in sorted(by_id.items(), key=lambda kv: kv[1]):
        if num in on_board:
            continue
        print(f"board    + #{num} [{iid}]")
        if not dry:
            gh("project", "item-add", number, "--owner", owner, "--url", f"https://github.com/{repo}/issues/{num}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="Kausiukas/music_engineering")
    parser.add_argument("--project", help="GitHub Project title to create/fill (owner-level Project v2)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be created")
    parser.add_argument("--offline", action="store_true", help="only check the backlog resolves against the plan (no gh)")
    args = parser.parse_args()

    backlog = yaml.safe_load((PLAN / "backlog.yaml").read_text(encoding="utf-8"))
    rows = parse_tables()
    issues, missing = [], []
    for item in backlog["items"]:
        try:
            issues.append(build_issue(item, rows, backlog["milestones"]))
        except (KeyError, TypeError) as exc:
            missing.append(f"{item['id']}: no matching plan row ({exc})")
    if missing:
        raise SystemExit("Backlog items without a plan row:\n" + "\n".join(missing))

    if args.offline:
        for issue in issues:
            print(f"ok {issue['title']}{'  [cut]' if issue['skip'] else ''}")
        print(f"{len(issues)} backlog items resolve against the plan")
        return
    ensure_labels(args.repo, backlog["labels"], args.dry_run)
    ensure_milestones(args.repo, backlog["milestones"], args.dry_run)
    by_id = ensure_issues(args.repo, issues, args.dry_run)
    if not args.dry_run:
        (PLAN / "issues.json").write_text(json.dumps(dict(sorted(by_id.items())), indent=2) + "\n", encoding="utf-8")
    if args.project:
        ensure_project(args.repo, args.project, by_id, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
