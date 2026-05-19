"""Seed a capture + completed run so cold-start demos have inbox content.

The Streamlit captures inbox and Runs dialog are empty on a fresh clone, which
is the gap called out in `docs/PRESENTATION-RUNBOOK-2026-05-19.md` section 5
item 4. Running this script writes one deterministic capture and one completed
run artifact under `.cache/`, which the app picks up on next launch.

Safe to run repeatedly: existing records with the seed IDs are overwritten.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from whisperforge_core import captures, run_artifacts

CAPTURE_ID = "cap-20260519T170000Z-demo0001"
RUN_ID = "20260519T170015Z-demo0001"
CREATED_AT = "2026-05-19T17:00:00Z"
RUN_CREATED_AT = "2026-05-19T17:00:15Z"
RUN_COMPLETED_AT = "2026-05-19T17:02:42Z"

TRANSCRIPT = """\
Okay so here's what's actually happening with BC plus AI right now. We're three
cohorts deep into the certification program and the pattern that keeps showing
up is that the students who ship something publicly inside the first two weeks
are the ones who are still building six months later. The ones who try to learn
everything before they ship — they churn. Every time. So we're going to stop
pretending that the curriculum is the product. The curriculum is the excuse.
The product is the deadline and the audience.

Second thing. The Futureproof Festival pitch that went out last week landed
better than I expected. Three of the five sponsors we cold-emailed actually
booked discovery calls. The one that's most likely to close is the credit
union — they want to be in front of the small-business AI track because their
loan officers are getting AI questions from clients and they have zero answers.
That's a real pain. We can write that pitch as a workshop track and they'll
sponsor the whole thing. Send Britney the workshop outline by end of week.

Third thing. The coaching cohort feedback from the May cycle is in and the
single biggest complaint is that the weekly office hours run too long and
don't have enough structure. People show up, someone asks a vague question,
and forty-five minutes evaporate into general chat. We need a hard agenda. Two
case study slots, one open Q and A, one demo. Fifty minutes flat. If you
didn't sign up for a case study slot you can come but you can't talk for more
than two minutes. That sounds harsh but the people who are paying for this
need the time to be useful, not social.

Fourth thing. The ecosystem map is still our best leverage and we keep
underinvesting in it. Every time I talk to a partner — Mozilla, the city,
SDECB — they ask me who else is doing AI work in BC and I send them the map.
And then they hire someone off the map. The map is doing the work of three
business development people and it lives on a Notion page that I update by
hand once a month. We have to give it a real owner and a real cadence. Not
me. Not on top of everything else. A real owner.

Fifth. Stop using the word ecosystem in external copy. It tested badly with
the credit union and it tests badly with everyone outside our bubble. Use
network. Use community. Use the names of the actual people in the room. The
word ecosystem makes us sound like a conference panel.

Okay last thing. We're shipping the Futureproof Festival site by June first.
Real domain. Real schedule. Real sponsor logos. No more placeholder copy. If
the schedule isn't locked we publish a thirty percent confirmed version and
update it weekly. Done is better than perfect and a public schedule is what
makes the rest of the program book itself. The site is the forcing function.

That's it. Send me back the three things you're going to actually do this
week, not five, not seven, three. And tell me which one you're most worried
about, because that's the one we should talk about first.
"""

ARTICLE = """\
# Stop Pretending the Curriculum Is the Product

After three cohorts of the BC + AI certification program, one pattern is
impossible to ignore: the students who publish something — anything — within
their first two weeks are the ones still building six months later. The
students who try to learn everything before they ship are the ones who quit.

This is not a curriculum problem. It is a deadline-and-audience problem.

The curriculum is the excuse to start. The product is the public commitment
to finish. If your program does not force a public ship inside the first two
weeks, you are running a study group, not a transformation.

## What we are changing

1. Every cohort now has a public demo day at the end of week two. Not
   polished. Not finished. Public.
2. Office hours go from open-ended chat to a fifty-minute agenda: two case
   study slots, one open Q and A, one live demo.
3. The Futureproof Festival site ships June first with a thirty percent
   confirmed schedule. A public schedule is the forcing function that makes
   the rest of the program book itself.

## What we are killing

The word ecosystem. It tested badly with sponsors and it tests badly with
everyone outside the room. Use network. Use community. Use the names of the
people who are actually doing the work.

## The point

The students who ship are the students who stay. Build the deadline. Build
the audience. The curriculum will take care of itself.
"""

SOCIAL_POSTS = """\
LinkedIn:
After three cohorts of BC + AI, one pattern keeps repeating: students who
ship something public in the first two weeks are still building six months
later. The ones who wait to learn it all? Gone.

The curriculum is not the product. The deadline is the product. The audience
is the product.

Next cohort, every student demos publicly on day fourteen. Not polished.
Public.

---

Twitter / X:
The curriculum is the excuse. The deadline is the product.

Three cohorts in: students who ship publicly in week two are still building
in month six. Students who try to learn it all first are gone by month two.

We stopped pretending and added a public demo on day fourteen. No exceptions.
"""

IMAGE_PROMPTS = """\
1. A bright, uncluttered workshop scene: a small group of adult learners in
   a modern Vancouver co-working space, one of them presenting a laptop
   screen with simple wireframes visible. Natural daylight, no stock-photo
   smiles. Documentary feel.

2. A clean white wall with three large sticky notes in primary colors. Each
   sticky note has a single bold phrase handwritten on it: "Ship in 14 days",
   "Public demo", "Audience first". Slight shadow under each sticky note.

3. A flat-design illustration of a calendar grid with day fourteen circled
   in red marker. A small rocket icon sits on the circled date. Muted teal
   and warm orange palette. No people.
"""

CHAPTERS = [
    {"title": "Three cohorts of pattern", "start_seconds": 0},
    {"title": "Festival pitch landed", "start_seconds": 75},
    {"title": "Office hours need structure", "start_seconds": 145},
    {"title": "The ecosystem map owns itself", "start_seconds": 215},
    {"title": "Stop saying ecosystem", "start_seconds": 285},
    {"title": "June 1 site ship date", "start_seconds": 330},
]

WISDOM = (
    "The curriculum is the excuse to start. The deadline and the audience are "
    "what carry students across the finish line. Build the forcing function "
    "before you build the content."
)

OUTLINE = """\
- Three cohorts of evidence: shippers stay, learners-only churn
- Festival sponsor pitch outcomes: 3 of 5 booked discovery calls
- Office hours redesign: 50-minute fixed agenda
- Ecosystem map needs a dedicated owner
- Kill the word "ecosystem" in external copy
- Futureproof Festival site ships June 1
"""

SCORECARD = {
    "verdict_label": "ship",
    "average_score": 88,
    "claim_flags": 0,
    "source_grounded": True,
    "notes": "Strong first-person evidence; no unverifiable claims.",
}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def seed_capture() -> dict:
    cap_dir = captures.capture_dir(CAPTURE_ID)
    cap_dir.mkdir(parents=True, exist_ok=True)
    input_file = cap_dir / "input.txt"
    input_file.write_text(TRANSCRIPT, encoding="utf-8")

    text_sha = hashlib.sha256(TRANSCRIPT.encode("utf-8")).hexdigest()
    excerpt = TRANSCRIPT.strip()[:320]

    record = {
        "capture_id": CAPTURE_ID,
        "created_at": CREATED_AT,
        "filename": "wispr-flow-20260519-100000-bcai-cohort-debrief.txt",
        "input_path": str(input_file),
        "metadata": {"created_by": "demo_seed"},
        "run_ids": [RUN_ID],
        "source": "wispr_flow",
        "status": "completed",
        "text_excerpt": excerpt,
        "text_sha256": text_sha,
        "title": "BC + AI cohort debrief: ship the deadline, not the curriculum",
        "updated_at": RUN_COMPLETED_AT,
    }
    _write_json(captures.record_path(CAPTURE_ID), record)
    return record


def seed_run(capture_record: dict) -> dict:
    run_root = run_artifacts.run_dir(RUN_ID)
    stages_dir = run_root / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)

    session_payload = {
        "wisdom": WISDOM,
        "outline": OUTLINE,
        "social_content": SOCIAL_POSTS,
        "image_prompts": IMAGE_PROMPTS,
        "article": ARTICLE,
        "chapters": CHAPTERS,
        "fact_check_flags": [],
        "generated_images": [],
        "article_compare": None,
        "compare_label": None,
        "persona_articles": [],
        "songforge": {},
        "scorecard_summary": SCORECARD,
    }

    session_path = stages_dir / "session_output.json"
    _write_json(session_path, {
        "run_id": RUN_ID,
        "stage": "session_output",
        "updated_at": RUN_COMPLETED_AT,
        "payload": session_payload,
    })

    scorecard_path = stages_dir / "scorecard.json"
    _write_json(scorecard_path, {
        "run_id": RUN_ID,
        "stage": "scorecard",
        "updated_at": RUN_COMPLETED_AT,
        "payload": SCORECARD,
    })

    transcription_path = stages_dir / "transcription.json"
    _write_json(transcription_path, {
        "run_id": RUN_ID,
        "stage": "transcription",
        "updated_at": RUN_CREATED_AT,
        "payload": {"text": TRANSCRIPT, "segments": []},
    })

    manifest = {
        "created_at": RUN_CREATED_AT,
        "current_stage": "session_output",
        "exports": [],
        "metadata": {
            "mode": "paste",
            "source": "wispr_flow",
            "filename": capture_record["filename"],
            "capture": {
                "capture_id": CAPTURE_ID,
                "source": "wispr_flow",
                "title": capture_record["title"],
                "filename": capture_record["filename"],
                "status": "completed",
                "input_path": capture_record["input_path"],
                "text_sha256": capture_record["text_sha256"],
                "text_excerpt": capture_record["text_excerpt"],
            },
            "recipe": {
                "recipe_id": "default-article",
                "name": "Article + Social + Images",
            },
            "selected_user": "kris",
            "provider": "anthropic",
            "model": "claude-opus-4-5",
            "settings": {
                "cleanup": True,
                "chapters": True,
                "agentic": False,
                "fact_check": True,
                "images": True,
                "rag_mode": "auto",
                "compare_provider": None,
                "compare_model": None,
                "personas": [],
            },
        },
        "run_id": RUN_ID,
        "stages": [
            {"stage": "transcription", "path": str(transcription_path), "updated_at": RUN_CREATED_AT},
            {"stage": "scorecard", "path": str(scorecard_path), "updated_at": RUN_COMPLETED_AT},
            {"stage": "session_output", "path": str(session_path), "updated_at": RUN_COMPLETED_AT},
        ],
        "status": "completed",
        "updated_at": RUN_COMPLETED_AT,
    }
    _write_json(run_artifacts.manifest_path(RUN_ID), manifest)
    return manifest


def main() -> None:
    capture_record = seed_capture()
    seed_run(capture_record)
    print(f"Seeded capture: {captures.record_path(CAPTURE_ID)}")
    print(f"Seeded run:     {run_artifacts.manifest_path(RUN_ID)}")


if __name__ == "__main__":
    main()
