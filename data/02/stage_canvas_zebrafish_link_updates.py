"""Stage a link-only update for every question in Canvas quiz 175982.

Default mode is read-only: it validates all questions and writes a review
plan.  Canvas is changed only when this script is run with ``--apply``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DATA_DIRECTORY = Path(__file__).resolve().parent
QUIZ_ID = 175982
PLAN_FILE = DATA_DIRECTORY / "staged_canvas_zebrafish_link_updates.json"
LABEL = "Download the data (right click, save as)"

PAIR = re.compile(
    r"\[?\s*<a\b(?=[^>]*href=[\"']https://canvaswizards\.org\.uk/dataspell/zebrafish/(\d{3})[\"'])[^>]*>.*?</a>\s*\]?\s*\|\s*"
    r"<a\b(?=[^>]*href=[\"'](https://raw\.githubusercontent\.com/rtreharne/qs/main/data/02/zebrafish_(\d{3})\.csv)[\"'])[^>]*>.*?</a>",
    flags=re.IGNORECASE | re.DOTALL,
)


def settings() -> dict[str, str]:
    for directory in (DATA_DIRECTORY, *DATA_DIRECTORY.parents):
        env_file = directory / ".env"
        if env_file.is_file():
            break
    else:
        raise FileNotFoundError("No parent .env file found")
    values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    missing = {"CANVAS_API_URL", "CANVAS_API_TOKEN", "COURSE_ID"} - values.keys()
    if missing:
        raise ValueError(f"Missing .env values: {', '.join(sorted(missing))}")
    return values


class Canvas:
    def __init__(self, config: dict[str, str]) -> None:
        root = config["CANVAS_API_URL"].rstrip("/")
        self.root = root if root.endswith("/api/v1") else f"{root}/api/v1"
        self.course_id = config["COURSE_ID"]
        self.headers = {"Authorization": f"Bearer {config['CANVAS_API_TOKEN']}"}

    def get_json(self, url: str) -> tuple[object, str]:
        request = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response), response.headers.get("Link", "")

    def questions(self) -> list[dict[str, object]]:
        url: str | None = f"{self.root}/courses/{self.course_id}/quizzes/{QUIZ_ID}/questions?per_page=100"
        result: list[dict[str, object]] = []
        while url:
            page, links = self.get_json(url)
            result.extend(page)  # type: ignore[arg-type]
            next_links = [item for item in links.split(",") if 'rel="next"' in item]
            url = re.search(r"<([^>]+)>", next_links[0]).group(1) if next_links else None
        return result

    def question(self, question_id: int) -> dict[str, object]:
        question, _ = self.get_json(
            f"{self.root}/courses/{self.course_id}/quizzes/{QUIZ_ID}/questions/{question_id}"
        )
        return question  # type: ignore[return-value]

    def update(self, question: dict[str, object], text: str) -> None:
        """Update text while re-sending the existing numerical-answer fields."""
        fields: dict[str, object] = {
            "question[question_name]": question["question_name"],
            "question[question_type]": question["question_type"],
            "question[question_text]": text,
            "question[points_possible]": question["points_possible"],
        }
        if question.get("quiz_group_id") is not None:
            fields["question[quiz_group_id]"] = question["quiz_group_id"]
        for field in ("correct_comments", "incorrect_comments", "neutral_comments", "text_after_answers"):
            if question.get(field) is not None:
                fields[f"question[{field}]"] = question[field]

        answers = question.get("answers")
        if not isinstance(answers, list) or len(answers) != 1:
            raise ValueError(f"Question {question['id']} does not have one numerical answer")
        answer = answers[0]
        if not isinstance(answer, dict) or answer.get("numerical_answer_type") != "exact_answer":
            raise ValueError(f"Question {question['id']} is not an exact numerical question")
        prefix = "question[answers][0]"
        fields.update(
            {
                f"{prefix}[id]": answer["id"],
                f"{prefix}[answer_text]": answer["text"],
                f"{prefix}[answer_weight]": answer["weight"],
                f"{prefix}[numerical_answer_type]": answer["numerical_answer_type"],
                f"{prefix}[answer_exact]": answer["exact"],
                f"{prefix}[answer_error_margin]": answer["margin"],
            }
        )
        request = urllib.request.Request(
            f"{self.root}/courses/{self.course_id}/quizzes/{QUIZ_ID}/questions/{question['id']}",
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded"},
            method="PUT",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            json.load(response)


def transformed(text: str) -> tuple[str, int, str]:
    matches = list(PAIR.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one broken/backup link pair; found {len(matches)}")
    match = matches[0]
    canvas_id, backup_url, backup_id = match.groups()
    if canvas_id != backup_id:
        raise ValueError(f"Mismatched data links: {canvas_id} and {backup_id}")
    replacement = f'<a target="_blank" href="{backup_url}">{LABEL}</a>'
    result = text[: match.start()] + replacement + text[match.end() :]
    if "canvaswizards.org.uk/dataspell/zebrafish/" in result or result.count(LABEL) != 1:
        raise ValueError("Link transformation validation failed")
    return result, int(canvas_id), match.group(0)


def group_name(question: dict[str, object]) -> str:
    return "Q4" if "repeat your zebrafish experiment" in str(question["question_text"]).lower() else "Q3"


def is_confirmed_update(text: str, dataset_id: int) -> bool:
    """Check the intended link semantics without relying on HTML whitespace."""
    if "canvaswizards.org.uk/dataspell/zebrafish/" in text:
        return False
    backup_url = (
        "https://raw.githubusercontent.com/rtreharne/qs/main/data/02/"
        f"zebrafish_{dataset_id}.csv"
    )
    anchors = re.findall(
        r'<a\b(?=[^>]*href=["\']([^"\']+)["\'])[^>]*>(.*?)</a>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    matching = [label for href, label in anchors if href == backup_url]
    return len(matching) == 1 and re.sub(r"<[^>]+>", "", matching[0]).strip() == LABEL


def make_plan(questions: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[int, str]]:
    plan: list[dict[str, object]] = []
    replacements: dict[int, str] = {}
    for question in questions:
        old_text = str(question["question_text"])
        question_id = int(question["id"])
        try:
            new_text, dataset_id, old_fragment = transformed(old_text)
        except ValueError:
            # An interrupted run may already have completed this question.
            existing = re.search(r"zebrafish_(\d{3})\.csv", old_text)
            if existing and is_confirmed_update(old_text, int(existing.group(1))):
                continue
            raise
        replacements[question_id] = new_text
        plan.append(
            {
                "canvas_question_id": question_id,
                "question_name": question["question_name"],
                "group": group_name(question),
                "dataset_id": dataset_id,
                "old_html_sha256": hashlib.sha256(old_text.encode()).hexdigest(),
                "new_html_sha256": hashlib.sha256(new_text.encode()).hexdigest(),
                "removed_fragment": re.sub(r"\s+", " ", old_fragment).strip(),
            }
        )
    if len(questions) != 201:
        raise ValueError(f"Expected 201 quiz variants; found {len(questions)}")
    return plan, replacements


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="perform Canvas PUT requests")
    arguments = parser.parse_args()

    canvas = Canvas(settings())
    current_questions = canvas.questions()
    plan, replacements = make_plan(current_questions)
    PLAN_FILE.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    counts = {group: sum(item["group"] == group for item in plan) for group in ("Q3", "Q4")}
    print(f"Validated and staged {len(plan)} link updates: {counts['Q3']} Q3 and {counts['Q4']} Q4.")
    print(f"Review plan: {PLAN_FILE}")
    if not arguments.apply:
        print("Dry run only: no Canvas changes were made.")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_file = DATA_DIRECTORY / f"canvas_zebrafish_link_update_audit_{timestamp}.json"
    audit = {"status": "in_progress", "updates": []}
    audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    try:
        for question in current_questions:
            question_id = int(question["id"])
            if question_id not in replacements:
                continue
            old_answer = dict(question["answers"][0])
            audit_update = {"question_id": question_id, "old_question_text": question["question_text"], "new_question_text": replacements[question_id]}
            audit["updates"].append(audit_update)
            audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
            canvas.update(question, replacements[question_id])
            confirmed = canvas.question(question_id)
            confirmed_text = str(confirmed["question_text"])
            confirmed_answer = confirmed["answers"][0]
            answer_fields = ("id", "text", "weight", "numerical_answer_type", "exact", "margin")
            if (
                not is_confirmed_update(confirmed_text, next(item["dataset_id"] for item in plan if item["canvas_question_id"] == question_id))
                or any(str(confirmed_answer[field]) != str(old_answer[field]) for field in answer_fields)
            ):
                raise RuntimeError(f"Canvas did not confirm link update for question {question_id}")
            audit_update["verified"] = True
            audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    except Exception:
        audit["status"] = "incomplete"
        audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        raise
    audit["status"] = "complete"
    audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Applied and verified {len(plan)} link updates. Audit: {audit_file}")


if __name__ == "__main__":
    main()
