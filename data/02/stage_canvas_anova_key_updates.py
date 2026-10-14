"""Stage (or, only when explicitly requested, apply) Q4 ANOVA key updates.

The default mode is read-only.  It verifies the Canvas mapping and writes a
JSON review plan; no Canvas request that changes state can occur unless
``--apply`` is passed as well.

Examples:
    python3 qs/data/02/stage_canvas_anova_key_updates.py
    python3 qs/data/02/stage_canvas_anova_key_updates.py --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


DATA_DIRECTORY = Path(__file__).resolve().parent
QUIZ_ID = 175982
FIRST_DATASET = 200
LAST_DATASET = 299
# This key was corrected manually before this script was staged.
MANUALLY_CORRECTED = {287}
PLAN_FILE = DATA_DIRECTORY / "staged_canvas_anova_key_updates.json"


def load_environment() -> dict[str, str]:
    """Load the Canvas settings without printing their values."""
    for directory in (DATA_DIRECTORY, *DATA_DIRECTORY.parents):
        environment_file = directory / ".env"
        if environment_file.is_file():
            break
    else:
        raise FileNotFoundError("Could not find a .env file in a parent directory")

    settings: dict[str, str] = {}
    for raw_line in environment_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip().strip('"').strip("'")

    required = {"CANVAS_API_URL", "CANVAS_API_TOKEN", "COURSE_ID"}
    missing = required - settings.keys()
    if missing:
        raise ValueError(f"Missing .env settings: {', '.join(sorted(missing))}")
    return settings


def anova_f_statistic(csv_file: Path) -> float:
    """Calculate the conventional one-way ANOVA F statistic."""
    groups: dict[str, list[float]] = defaultdict(list)
    with csv_file.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["length_micron"].strip():
                groups[row["conc_pc"]].append(float(row["length_micron"]))

    values = [value for group in groups.values() for value in group]
    group_count = len(groups)
    grand_mean = sum(values) / len(values)
    between_ss = sum(
        len(group) * (sum(group) / len(group) - grand_mean) ** 2
        for group in groups.values()
    )
    within_ss = sum(
        sum((value - sum(group) / len(group)) ** 2 for value in group)
        for group in groups.values()
    )
    return (between_ss / (group_count - 1)) / (
        within_ss / (len(values) - group_count)
    )


class CanvasClient:
    def __init__(self, settings: dict[str, str]) -> None:
        api_root = settings["CANVAS_API_URL"].rstrip("/")
        self.api_root = (
            api_root if api_root.endswith("/api/v1") else f"{api_root}/api/v1"
        )
        self.course_id = settings["COURSE_ID"]
        self.headers = {"Authorization": f"Bearer {settings['CANVAS_API_TOKEN']}"}

    def get_json(self, url: str) -> tuple[object, str]:
        request = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response), response.headers.get("Link", "")

    def get_all_questions(self) -> list[dict[str, object]]:
        url: str | None = (
            f"{self.api_root}/courses/{self.course_id}/quizzes/{QUIZ_ID}/questions?per_page=100"
        )
        questions: list[dict[str, object]] = []
        while url:
            page, link_header = self.get_json(url)
            questions.extend(page)  # type: ignore[arg-type]
            url = self._next_page_url(link_header)
        return questions

    @staticmethod
    def _next_page_url(link_header: str) -> str | None:
        for link in link_header.split(","):
            if 'rel="next"' in link:
                return link[link.find("<") + 1 : link.find(">")]
        return None

    def update_answer(self, question_id: int, answer: dict[str, object]) -> dict[str, object]:
        """Submit one answer update.  This is called only with ``--apply``."""
        answer_index = "question[answers][0]"
        fields = {
            f"{answer_index}[id]": answer["id"],
            # Canvas returns ``text`` and ``weight`` but accepts the documented
            # request names ``answer_text`` and ``answer_weight``.
            f"{answer_index}[answer_text]": answer["text"],
            f"{answer_index}[answer_weight]": answer["weight"],
            f"{answer_index}[numerical_answer_type]": answer["numerical_answer_type"],
            # The numerical-question parser consumes these request names,
            # rather than its response names (``exact`` and ``margin``).
            f"{answer_index}[answer_exact]": answer["exact"],
            f"{answer_index}[answer_error_margin]": answer["margin"],
        }
        request = urllib.request.Request(
            f"{self.api_root}/courses/{self.course_id}/quizzes/{QUIZ_ID}/questions/{question_id}",
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded"},
            method="PUT",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def get_question(self, question_id: int) -> dict[str, object]:
        question, _ = self.get_json(
            f"{self.api_root}/courses/{self.course_id}/quizzes/{QUIZ_ID}/questions/{question_id}"
        )
        return question  # type: ignore[return-value]


def question_number(question: dict[str, object]) -> int:
    match = re.search(r"(\d+)$", str(question["question_name"]))
    if match is None:
        raise ValueError(f"Unexpected question name: {question['question_name']!r}")
    return int(match.group(1))


def build_plan(questions: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build updates after validating that Canvas points to the intended CSV."""
    q4_questions = {
        question_number(question): question
        for question in questions
        if "repeat your zebrafish experiment" in str(question["question_text"]).lower()
    }
    expected_numbers = set(range(FIRST_DATASET, LAST_DATASET + 1))
    missing = expected_numbers - q4_questions.keys()
    if missing:
        raise ValueError(f"Missing Q4 variants: {sorted(missing)}")

    plan: list[dict[str, object]] = []
    for number in sorted(expected_numbers - MANUALLY_CORRECTED):
        question = q4_questions[number]
        expected_link = f"zebrafish/{number}"
        if expected_link not in str(question["question_text"]):
            raise ValueError(
                f"Question #{number} does not link to its matching dataset ({expected_link})"
            )

        answers = question.get("answers")
        if not isinstance(answers, list) or len(answers) != 1:
            raise ValueError(f"Question #{number} does not have exactly one numerical answer")
        answer = answers[0]
        if not isinstance(answer, dict) or answer.get("numerical_answer_type") != "exact_answer":
            raise ValueError(f"Question #{number} is not an exact numerical-answer question")

        expected_f = round(
            anova_f_statistic(DATA_DIRECTORY / f"zebrafish_{number}.csv"), 2
        )
        current_f = float(answer["exact"])
        if current_f == expected_f:
            continue

        updated_answer = dict(answer)
        updated_answer["exact"] = f"{expected_f:.2f}"
        plan.append(
            {
                "dataset_id": number,
                "canvas_question_id": question["id"],
                "canvas_answer_id": answer["id"],
                "previous_f_statistic": f"{current_f:.2f}",
                "replacement_f_statistic": f"{expected_f:.2f}",
                "request_fields": updated_answer,
            }
        )
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="submit the staged updates to Canvas (omitted by default)",
    )
    arguments = parser.parse_args()

    canvas = CanvasClient(load_environment())
    plan = build_plan(canvas.get_all_questions())
    PLAN_FILE.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    print(f"Staged {len(plan)} Canvas answer-key updates in {PLAN_FILE}")
    for update in plan:
        print(
            "Question #{dataset_id}: {previous_f_statistic} -> {replacement_f_statistic}".format(
                **update
            )
        )

    if not arguments.apply:
        print("Dry run only: no Canvas changes were made.")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_file = DATA_DIRECTORY / f"canvas_anova_key_update_audit_{timestamp}.json"
    audit = {
        "quiz_id": QUIZ_ID,
        "applied_at_utc": timestamp,
        "status": "in_progress",
        "updates": [dict(update) for update in plan],
    }
    # Write the full pre-change snapshot before the first Canvas mutation.
    audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    try:
        for audit_update in audit["updates"]:
            canvas.update_answer(
                int(audit_update["canvas_question_id"]),
                dict(audit_update["request_fields"]),
            )
            confirmed_question = canvas.get_question(int(audit_update["canvas_question_id"]))
            new_answer = confirmed_question["answers"][0]
            confirmed_f = float(new_answer["exact"])
            if confirmed_f != float(audit_update["replacement_f_statistic"]):
                raise RuntimeError(
                    f"Canvas did not confirm Question #{audit_update['dataset_id']}"
                )
            audit_update["canvas_confirmed_f_statistic"] = f"{confirmed_f:.2f}"
            audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    except Exception:
        audit["status"] = "incomplete"
        audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        raise

    audit["status"] = "complete"
    audit_file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Applied and verified {len(plan)} Canvas answer-key updates.")
    print(f"Audit log: {audit_file}")


if __name__ == "__main__":
    main()
