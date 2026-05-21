"""Seed a small presentation pack so cold-start demos have real content.

The Streamlit captures inbox and Runs dialog are empty on a fresh clone. Running
this script writes deterministic demo captures and run artifacts under
`.cache/`, which the app picks up on next launch.

Safe to run repeatedly: existing records with the seed IDs are overwritten.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from whisperforge_core import captures, handoffs, run_artifacts, songforge

ARTICLE_CAPTURE_ID = "cap-20260519T170000Z-demo0001"
ARTICLE_RUN_ID = "20260519T170015Z-demo0001"
CAPTURE_ID = ARTICLE_CAPTURE_ID
RUN_ID = ARTICLE_RUN_ID
CREATED_AT = "2026-05-19T17:00:00Z"
RUN_CREATED_AT = "2026-05-19T17:00:15Z"
RUN_COMPLETED_AT = "2026-05-19T17:10:00Z"

SONGFORGE_CAPTURE_ID = "cap-20260519T170400Z-demo0002"
SONGFORGE_RUN_ID = "20260519T170415Z-demo0002"
SONGFORGE_CREATED_AT = "2026-05-19T17:04:00Z"
SONGFORGE_RUN_CREATED_AT = "2026-05-19T17:04:15Z"
SONGFORGE_COMPLETED_AT = "2026-05-19T17:06:30Z"

PARTIAL_CAPTURE_ID = "cap-20260519T170800Z-demo0003"
PARTIAL_RUN_ID = "20260519T170815Z-demo0003"
PARTIAL_CREATED_AT = "2026-05-19T17:08:00Z"
PARTIAL_RUN_CREATED_AT = "2026-05-19T17:08:15Z"
PARTIAL_FAILED_AT = "2026-05-19T17:09:10Z"

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

SONGFORGE_TRANSCRIPT = """\
Wispr Flow note for SongForge. The phrase that keeps coming back is bring the
signal back. Not as a slogan, as a practice. People make these tiny beautiful
things in the margins of community events and then the useful parts disappear
into chat logs, camera rolls, and half-finished docs. The song should feel like
walking home after an event with your pockets full of names, promises, and
little sparks of responsibility.

The chorus is not about fame. It is about remembering out loud. It should be
warm, a little haunted, and still practical. Something you could play before a
community showcase without making everyone cringe. Keep it original. No
soundalikes. No borrowed hooks. The source is enough.
"""

SONGFORGE_KB = {
    "voice.md": (
        "Keep the voice intimate, warm, direct, and source-grounded. Prefer "
        "community language, practical tenderness, and original phrasing over "
        "borrowed style references."
    )
}

SONGFORGE_SCORECARD = {
    "verdict_label": "ready",
    "average_score": 84,
    "claim_flags": 0,
    "source_grounded": True,
    "notes": "Source-linked creative pack with originality guardrails.",
}

PARTIAL_TRANSCRIPT = """\
Quick capture before the workshop starts. I need a three-part recap of the
knowledge-base governance idea: what counts as canonical context, what should
be quarantined, and how agents should warn before using stale files.
"""

PARTIAL_ERROR = "Demo fixture: stopped before composition so reviewers can see a failed run."


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _seed_capture(
    *,
    capture_id: str,
    run_id: str,
    created_at: str,
    updated_at: str,
    filename: str,
    title: str,
    text: str,
    status: str,
    demo_role: str,
    topics: list[str],
) -> dict:
    cap_dir = captures.capture_dir(capture_id)
    cap_dir.mkdir(parents=True, exist_ok=True)
    input_file = cap_dir / "input.txt"
    input_file.write_text(text, encoding="utf-8")

    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    excerpt = text.strip()[:320]

    record = {
        "capture_id": capture_id,
        "created_at": created_at,
        "filename": filename,
        "input_path": str(input_file),
        "metadata": {
            "created_by": "demo_seed",
            "demo_role": demo_role,
            "topics": topics,
        },
        "run_ids": [run_id],
        "source": "wispr_flow",
        "status": status,
        "text_excerpt": excerpt,
        "text_sha256": text_sha,
        "title": title,
        "updated_at": updated_at,
    }
    _write_json(captures.record_path(capture_id), record)
    return record


def seed_capture() -> dict:
    return _seed_capture(
        capture_id=ARTICLE_CAPTURE_ID,
        run_id=ARTICLE_RUN_ID,
        created_at=CREATED_AT,
        updated_at=RUN_COMPLETED_AT,
        filename="wispr-flow-20260519-100000-bcai-cohort-debrief.txt",
        title="BC + AI cohort debrief: ship the deadline, not the curriculum",
        text=TRANSCRIPT,
        status="completed",
        demo_role="article_handoff",
        topics=["bcai", "cohort", "futureproof"],
    )


def _write_stage(run_id: str, stage: str, payload: dict, updated_at: str) -> dict:
    stage_path = run_artifacts.run_dir(run_id) / "stages" / f"{stage}.json"
    _write_json(stage_path, {
        "artifact_schema_version": run_artifacts.ARTIFACT_SCHEMA_VERSION,
        "run_id": run_id,
        "stage": stage,
        "updated_at": updated_at,
        "payload": payload,
    })
    return {"stage": stage, "path": str(stage_path), "updated_at": updated_at}


def _capture_manifest(capture_record: dict) -> dict:
    return {
        "capture_id": capture_record["capture_id"],
        "source": capture_record["source"],
        "title": capture_record["title"],
        "filename": capture_record["filename"],
        "status": capture_record["status"],
        "input_path": capture_record["input_path"],
        "text_sha256": capture_record["text_sha256"],
        "text_excerpt": capture_record["text_excerpt"],
    }


def _base_metadata(
    capture_record: dict,
    *,
    recipe_id: str,
    recipe_name: str,
    settings: dict,
) -> dict:
    return {
        "mode": "paste",
        "source": "wispr_flow",
        "filename": capture_record["filename"],
        "capture": _capture_manifest(capture_record),
        "recipe": {
            "recipe_id": recipe_id,
            "name": recipe_name,
        },
        "selected_user": "kris",
        "provider": "anthropic",
        "model": "claude-opus-4-5",
        "settings": settings,
    }


def seed_run(capture_record: dict) -> dict:
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

    handoff_draft = handoffs.build_issue_draft(
        title="Handoff: tighten the week-two public demo cadence",
        source_text=ARTICLE,
        source_kind="article",
        source_title="Stop Pretending the Curriculum Is the Product",
        recipe={"recipe_name": "Article with receipts"},
        scorecard=SCORECARD,
    )
    handoff_path = (
        run_artifacts.run_dir(ARTICLE_RUN_ID)
        / "handoffs"
        / "tighten-week-two-public-demo-cadence.md"
    )
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        f"# {handoff_draft.title}\n\n{handoff_draft.body}",
        encoding="utf-8",
    )

    stages = [
        _write_stage(
            ARTICLE_RUN_ID,
            "transcription",
            {"text": TRANSCRIPT, "segments": [], "source": "wispr_flow"},
            RUN_CREATED_AT,
        ),
        _write_stage(ARTICLE_RUN_ID, "scorecard", SCORECARD, RUN_COMPLETED_AT),
        _write_stage(ARTICLE_RUN_ID, "session_output", session_payload, RUN_COMPLETED_AT),
        _write_stage(
            ARTICLE_RUN_ID,
            "handoff_draft",
            {**handoff_draft.to_dict(), "path": str(handoff_path)},
            RUN_COMPLETED_AT,
        ),
    ]

    manifest = {
        "artifact_schema_version": run_artifacts.ARTIFACT_SCHEMA_VERSION,
        "created_at": RUN_CREATED_AT,
        "current_stage": "handoff_draft",
        "exports": [{
            "kind": "handoff_draft",
            "value": str(handoff_path),
            "updated_at": RUN_COMPLETED_AT,
        }],
        "metadata": _base_metadata(
            capture_record,
            recipe_id="article_with_receipts",
            recipe_name="Article with receipts",
            settings={
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
        ),
        "run_id": ARTICLE_RUN_ID,
        "stages": stages,
        "status": "completed",
        "updated_at": RUN_COMPLETED_AT,
    }
    _write_json(run_artifacts.manifest_path(ARTICLE_RUN_ID), manifest)
    return manifest


def seed_songforge_capture() -> dict:
    return _seed_capture(
        capture_id=SONGFORGE_CAPTURE_ID,
        run_id=SONGFORGE_RUN_ID,
        created_at=SONGFORGE_CREATED_AT,
        updated_at=SONGFORGE_COMPLETED_AT,
        filename="wispr-flow-20260519-100400-songforge-community-signal.txt",
        title="SongForge note: bring the signal back",
        text=SONGFORGE_TRANSCRIPT,
        status="completed",
        demo_role="songforge",
        topics=["songforge", "community", "creative"],
    )


def seed_songforge_run(capture_record: dict) -> dict:
    pack = songforge.build_pack(
        SONGFORGE_TRANSCRIPT,
        SONGFORGE_KB,
        title="Bring the Signal Back",
    )
    markdown = songforge.render_markdown(pack)
    session_payload = {
        "wisdom": "Bring the signal back before useful community moments disappear.",
        "outline": "1. Source phrase\n2. Emotional arc\n3. Lyric draft\n4. Prompt pack",
        "social_content": "",
        "image_prompts": "",
        "article": markdown,
        "chapters": [],
        "fact_check_flags": [],
        "generated_images": [],
        "article_compare": None,
        "compare_label": None,
        "persona_articles": [],
        "songforge": pack,
        "scorecard_summary": SONGFORGE_SCORECARD,
    }
    stages = [
        _write_stage(
            SONGFORGE_RUN_ID,
            "transcription",
            {"text": SONGFORGE_TRANSCRIPT, "segments": [], "source": "wispr_flow"},
            SONGFORGE_RUN_CREATED_AT,
        ),
        _write_stage(SONGFORGE_RUN_ID, "scorecard", SONGFORGE_SCORECARD, SONGFORGE_COMPLETED_AT),
        _write_stage(SONGFORGE_RUN_ID, "session_output", session_payload, SONGFORGE_COMPLETED_AT),
    ]
    manifest = {
        "artifact_schema_version": run_artifacts.ARTIFACT_SCHEMA_VERSION,
        "created_at": SONGFORGE_RUN_CREATED_AT,
        "current_stage": "session_output",
        "exports": [],
        "metadata": _base_metadata(
            capture_record,
            recipe_id="songforge",
            recipe_name="SongForge creative pack",
            settings={
                "cleanup": False,
                "chapters": False,
                "agentic": False,
                "fact_check": False,
                "images": False,
                "rag_mode": "auto",
                "compare_provider": None,
                "compare_model": None,
                "personas": [],
            },
        ),
        "run_id": SONGFORGE_RUN_ID,
        "stages": stages,
        "status": "completed",
        "updated_at": SONGFORGE_COMPLETED_AT,
    }
    _write_json(run_artifacts.manifest_path(SONGFORGE_RUN_ID), manifest)
    return manifest


def seed_partial_capture() -> dict:
    return _seed_capture(
        capture_id=PARTIAL_CAPTURE_ID,
        run_id=PARTIAL_RUN_ID,
        created_at=PARTIAL_CREATED_AT,
        updated_at=PARTIAL_FAILED_AT,
        filename="wispr-flow-20260519-100800-kb-governance-partial.txt",
        title="Partial run: KB governance recap",
        text=PARTIAL_TRANSCRIPT,
        status="failed",
        demo_role="partial_failed",
        topics=["kb governance", "agent safety"],
    )


def seed_partial_run(capture_record: dict) -> dict:
    stages = [
        _write_stage(
            PARTIAL_RUN_ID,
            "transcription",
            {"text": PARTIAL_TRANSCRIPT, "segments": [], "source": "wispr_flow"},
            PARTIAL_RUN_CREATED_AT,
        ),
        _write_stage(
            PARTIAL_RUN_ID,
            "error",
            {"message": PARTIAL_ERROR, "stage_idx": 3},
            PARTIAL_FAILED_AT,
        ),
    ]
    manifest = {
        "artifact_schema_version": run_artifacts.ARTIFACT_SCHEMA_VERSION,
        "created_at": PARTIAL_RUN_CREATED_AT,
        "current_stage": "error",
        "error": PARTIAL_ERROR,
        "exports": [],
        "metadata": _base_metadata(
            capture_record,
            recipe_id="article_with_receipts",
            recipe_name="Article with receipts",
            settings={
                "cleanup": True,
                "chapters": False,
                "agentic": False,
                "fact_check": True,
                "images": False,
                "rag_mode": "auto",
                "compare_provider": None,
                "compare_model": None,
                "personas": [],
            },
        ),
        "run_id": PARTIAL_RUN_ID,
        "stages": stages,
        "status": "failed",
        "updated_at": PARTIAL_FAILED_AT,
    }
    _write_json(run_artifacts.manifest_path(PARTIAL_RUN_ID), manifest)
    return manifest


def main() -> None:
    partial_capture = seed_partial_capture()
    seed_partial_run(partial_capture)
    songforge_capture = seed_songforge_capture()
    seed_songforge_run(songforge_capture)
    article_capture = seed_capture()
    seed_run(article_capture)
    print("Seeded demo fixture pack:")
    print(f"- article/handoff capture: {captures.record_path(ARTICLE_CAPTURE_ID)}")
    print(f"- article/handoff run:     {run_artifacts.manifest_path(ARTICLE_RUN_ID)}")
    print(f"- SongForge capture:       {captures.record_path(SONGFORGE_CAPTURE_ID)}")
    print(f"- SongForge run:           {run_artifacts.manifest_path(SONGFORGE_RUN_ID)}")
    print(f"- partial/failed capture:  {captures.record_path(PARTIAL_CAPTURE_ID)}")
    print(f"- partial/failed run:      {run_artifacts.manifest_path(PARTIAL_RUN_ID)}")


if __name__ == "__main__":
    main()
