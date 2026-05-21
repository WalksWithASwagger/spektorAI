"""Review tab: evidence, run story, scorecards, and handoff drafts."""

from __future__ import annotations

import hashlib
import os
from typing import Optional

import streamlit as st

from whisperforge_core import captures as captures_mod
from whisperforge_core import composition_review as review_mod
from whisperforge_core import handoff_router as handoff_router_mod
from whisperforge_core import handoffs as handoffs_mod
from whisperforge_core import run_artifacts
from whisperforge_core import run_story as run_story_mod
from whisperforge_core import scorecards as scorecards_mod


def render() -> None:
    s = st.session_state
    summary = _review_summary_from_state(s)
    scorecard = scorecard_summary_from_state(s)
    s.scorecard_summary = scorecard
    left, right = st.columns([2, 1])
    with left:
        with st.container(border=True):
            st.markdown("### Draft")
            if s.article:
                st.markdown(s.article)
            else:
                st.info("No article draft generated yet.")
        if s.article_critique:
            with st.expander("Revision notes", expanded=True):
                st.markdown(s.article_critique)
        if s.get("article_compare"):
            with st.expander(
                f"Compare · {s.get('compare_label', 'alternate')}", expanded=False,
            ):
                st.markdown(s.article_compare)
        for pa in s.get("persona_articles") or []:
            with st.expander(f"Persona · {pa.get('name', 'Persona')}", expanded=False):
                st.markdown(pa.get("text") or "")

    with right:
        st.markdown("### Evidence")
        c1, c2 = st.columns(2)
        c1.metric("Sources", summary["source_count"])
        c2.metric("Flags", summary["claim_flag_count"])
        retrieval = summary.get("retrieval") or {}
        st.caption(
            f"Retrieval hits: {retrieval.get('hits', 0)} · "
            f"Voice anchors: {len(retrieval.get('voice_anchors') or [])}"
        )
        _scorecard_panel(scorecard)
        _run_story_panel(s)
        if summary["sources"]:
            st.markdown("**Receipts**")
            for source in summary["sources"]:
                st.markdown(f"- {source}")
        if summary["quotes"]:
            st.markdown("**Quotes / excerpts**")
            for item in summary["quotes"]:
                st.markdown(f"- **{item['label']}** — {item['quote']}")
        if summary["claim_flags"]:
            st.markdown("**Claim flags**")
            for flag in summary["claim_flags"]:
                st.warning(f"{flag.get('claim', '')}\n\n{flag.get('issue', '')}")
        elif s.get("fact_check_ran"):
            st.success("No claim flags.")
    _handoff_panel()


def scorecard_summary_from_state(
    s,
    *,
    source_receipts: Optional[list[dict]] = None,
    exports: Optional[list[dict]] = None,
) -> dict:
    transcript = s.get("cleaned_transcript") or s.get("transcription") or ""
    receipts = (
        list(source_receipts)
        if source_receipts is not None
        else _scorecard_source_receipts_from_state(s, transcript)
    )
    if exports is None:
        try:
            exports = run_artifacts.load_manifest(s.get("run_id") or "").get("exports", [])
        except Exception:
            exports = []
    return scorecards_mod.build_summary(
        article=s.get("article") or "",
        transcript=transcript,
        wisdom=s.get("wisdom") or "",
        outline=s.get("outline") or "",
        social_content=s.get("social_content") or "",
        image_prompts=s.get("image_prompts") or "",
        chapters=s.get("chapters") or [],
        source_receipts=receipts,
        retrieval_inspector=s.get("retrieval_inspector"),
        fact_check_flags=s.get("fact_check_flags") or [],
        fact_check_ran=bool(s.get("fact_check_ran")),
        recipe=s.get("active_recipe") or {},
        recipe_effective_settings=s.get("recipe_effective_settings") or {},
        songforge=s.get("songforge") or {},
        exports=exports or [],
    )


def _scorecard_panel(scorecard: dict) -> None:
    st.markdown("**Scorecard**")
    st.metric("Verdict", scorecards_mod.compact_verdict(scorecard))
    st.caption("Advisory only; saves are not blocked.")
    with st.expander("Scorecard details", expanded=False):
        for dimension in scorecard.get("dimensions", []):
            score = int(dimension.get("score", 0))
            st.progress(
                score / 100,
                text=(
                    f"{dimension.get('label', 'Dimension')}: "
                    f"{score}/100 · {dimension.get('status', 'review')}"
                ),
            )
            notes = dimension.get("notes") or []
            if notes:
                st.caption(notes[0])


def _run_story_panel(s) -> None:
    run_id = s.get("run_id")
    if not run_id:
        return
    try:
        manifest = run_artifacts.load_manifest(run_id)
    except Exception:
        return
    if not manifest:
        return

    story = run_story_mod.build_run_story(
        manifest,
        capture_metadata=captures_mod.run_metadata(s.get("capture_id")),
    )
    if not story:
        return

    st.markdown("**Run story**")
    st.caption(f"Run `{manifest.get('run_id') or run_id}`")
    for step in story:
        status = str(step.get("status") or "unknown").replace("_", " ")
        detail = step.get("detail") or ""
        st.markdown(f"- **{step.get('label', 'Step')}** · `{status}`  \n  {detail}")


def _review_summary_from_state(s) -> dict:
    transcript = s.get("cleaned_transcript") or s.get("transcription") or ""
    receipts = []
    recipe_meta = s.get("recipe_effective_settings")
    if recipe_meta:
        receipts.append({
            "source": "Recipe",
            "name": recipe_meta.get("recipe_name"),
            "excerpt": ", ".join(recipe_meta.get("output_sections") or []),
        })
    capture_meta = captures_mod.run_metadata(s.get("capture_id"))
    if capture_meta:
        receipts.append({
            "source": "Capture",
            "title": capture_meta.get("title"),
            "excerpt": capture_meta.get("text_excerpt"),
        })
    if transcript:
        receipts.append({
            "source": "Transcript",
            "sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "excerpt": transcript[:240],
        })
    retrieval_inspector = s.get("retrieval_inspector")
    if retrieval_inspector:
        stages = retrieval_inspector.get("stages") or {}
        receipts.append({
            "source": "Knowledge retrieval",
            "excerpt": f"{sum(len(hits) for hits in stages.values())} retrieved KB hits",
        })
    return review_mod.build_summary(
        source_receipts=receipts,
        retrieval_inspector=retrieval_inspector,
        fact_check_flags=s.get("fact_check_flags") or [],
        article_critique=s.get("article_critique"),
        article_compare=s.get("article_compare"),
        persona_articles=s.get("persona_articles") or [],
        chapters=s.get("chapters") or [],
    )


def _scorecard_source_receipts_from_state(s, transcript: str) -> list[dict]:
    receipts = []
    recipe_meta = s.get("recipe_effective_settings")
    if recipe_meta:
        receipts.append({
            "source": "Recipe",
            "name": recipe_meta.get("recipe_name"),
        })
    capture_meta = captures_mod.run_metadata(s.get("capture_id"))
    if capture_meta:
        receipts.append({
            "source": "Capture",
            "title": capture_meta.get("title"),
        })
    if transcript:
        receipts.append({
            "source": "Transcript",
            "excerpt": transcript[:240],
        })
    retrieval_inspector = s.get("retrieval_inspector")
    if retrieval_inspector:
        stages = retrieval_inspector.get("stages") or {}
        receipts.append({
            "source": "Knowledge retrieval",
            "hits": sum(len(hits) for hits in stages.values()),
        })
    return receipts


def _handoff_panel() -> None:
    s = st.session_state
    sources = _handoff_sources(s)
    if not sources:
        return
    with st.expander("Agent handoff draft", expanded=False):
        st.caption(
            "Preview a draft, then approve to create the actual GitHub or "
            "Linear issue. Dry-run is the default when external config is missing."
        )
        labels = [item["label"] for item in sources]
        selected = st.selectbox("Draft from", labels, key="handoff_source_select")
        source = next(item for item in sources if item["label"] == selected)
        default_title = f"Handoff: {source['title']}"
        title = st.text_input("Issue title", value=default_title, key="handoff_title")
        if st.button("Generate dry-run draft", use_container_width=True, key="generate_handoff_draft"):
            scorecard = s.get("scorecard_summary") or scorecard_summary_from_state(s)
            draft = handoffs_mod.build_issue_draft(
                title=title,
                source_text=source["text"],
                source_kind=source["kind"],
                source_title=source["title"],
                recipe=s.get("recipe_effective_settings") or {},
                scorecard=scorecard,
            )
            path = None
            if s.get("run_id"):
                path = handoffs_mod.persist_draft(s.run_id, draft)
            s.handoff_draft_preview = {
                "title": draft.title,
                "body": draft.body,
                "path": str(path) if path else None,
            }
            st.toast("Handoff draft generated.", icon=":material/draft:")
            st.rerun()

        preview = s.get("handoff_draft_preview")
        if preview:
            if preview.get("path"):
                st.caption(f"Saved to `{preview['path']}`")
            else:
                st.caption("Preview only; start a run to persist the draft under run artifacts.")
            st.text_area("Preview", preview.get("body") or "", height=420, key="handoff_preview_body")
            _approval_panel(preview)


def _approval_panel(preview: dict) -> None:
    s = st.session_state
    st.markdown("---")
    st.markdown("**Approve and create**")

    available = handoff_router_mod.routing_available()
    target_options = ["GitHub", "Linear", "Follow-up queue"]
    target = st.radio(
        "Target",
        target_options,
        horizontal=True,
        key="handoff_target_select",
    )

    destination = ""
    labels_raw = ""
    if target == "GitHub":
        default_repo = os.getenv("WHISPERFORGE_HANDOFF_GITHUB_REPO", "")
        destination = st.text_input(
            "Repo (owner/name)", value=default_repo, key="handoff_github_repo",
        )
        labels_raw = st.text_input(
            "Labels (comma-separated)",
            value="agent:ready,handoff",
            key="handoff_github_labels",
        )
        status_line = (
            "Ready to create live issues via `gh`."
            if available["github"]
            else "Dry-run only - install `gh` and set WHISPERFORGE_HANDOFF_GITHUB_REPO to enable live creation."
        )
        st.caption(status_line)
    elif target == "Linear":
        default_team = os.getenv("WHISPERFORGE_HANDOFF_LINEAR_TEAM_ID", "")
        destination = st.text_input(
            "Linear team ID", value=default_team, key="handoff_linear_team",
        )
        labels_raw = st.text_input(
            "Label IDs (comma-separated UUIDs, optional)",
            value="",
            key="handoff_linear_labels",
        )
        status_line = (
            "Ready to create live issues via Linear API."
            if available["linear"]
            else "Dry-run only - set LINEAR_API_KEY and WHISPERFORGE_HANDOFF_LINEAR_TEAM_ID to enable live creation."
        )
        st.caption(status_line)
    else:
        default_queue = os.getenv("WHISPERFORGE_HANDOFF_FOLLOWUP_QUEUE_PATH", "")
        destination = st.text_input(
            "Queue path (jsonl)",
            value=default_queue,
            key="handoff_followup_queue_path",
        )
        status_line = (
            "Ready to append approved follow-ups to the local queue file."
            if available["followup_queue"]
            else "Dry-run only - set WHISPERFORGE_HANDOFF_FOLLOWUP_QUEUE_PATH to enable queue writes."
        )
        st.caption(status_line)

    body_text = preview.get("body") or ""
    title_text = preview.get("title") or ""
    draft_key = hashlib.sha256(
        f"{target}|{title_text}|{body_text[:500]}".encode("utf-8")
    ).hexdigest()[:16]
    s.setdefault("handoff_created", {})
    already = s["handoff_created"].get(draft_key)
    if already:
        if already.get("url"):
            st.success(f"Already created: [{already['url']}]({already['url']})")
        elif already.get("dry_run"):
            st.info("Dry-run already executed for this draft this session.")

    if st.button("Approve and create", type="primary", use_container_width=True, key="approve_handoff"):
        labels = [s.strip() for s in (labels_raw or "").split(",") if s.strip()]
        with st.spinner(f"Submitting to {target}..."):
            if target == "GitHub":
                result = handoff_router_mod.create_github_issue(
                    repo=destination,
                    title=title_text,
                    body=body_text,
                    labels=labels,
                )
            elif target == "Linear":
                result = handoff_router_mod.create_linear_issue(
                    team_id=destination,
                    title=title_text,
                    description=body_text,
                    label_ids=labels,
                )
            else:
                result = handoff_router_mod.create_followup_queue_item(
                    queue_path=destination,
                    title=title_text,
                    body=body_text,
                )
        s["handoff_created"][draft_key] = {
            "url": result.url,
            "target": result.target,
            "dry_run": result.dry_run,
            "error": result.error,
        }
        if result.success and result.url:
            st.toast("Handoff issue created.", icon=":material/check_circle:")
            st.rerun()
        elif result.dry_run:
            st.toast("Dry-run only - no external issue created.", icon=":material/draft:")
            if result.error:
                st.info(result.error)
            st.rerun()
        else:
            st.error(result.error or "Handoff creation failed.")


def _handoff_sources(s) -> list[dict[str, str]]:
    transcript = s.get("cleaned_transcript") or s.get("transcription") or ""
    capture_meta = captures_mod.run_metadata(s.get("capture_id"))
    sources = []
    if s.get("article"):
        sources.append({"label": "Article", "kind": "selected output", "title": "Article", "text": s.article})
    if s.get("wisdom"):
        sources.append({"label": "Wisdom", "kind": "selected output", "title": "Wisdom", "text": s.wisdom})
    if s.get("outline"):
        sources.append({"label": "Outline", "kind": "selected output", "title": "Outline", "text": s.outline})
    if s.get("social_content"):
        sources.append({"label": "Social", "kind": "selected output", "title": "Social", "text": s.social_content})
    if s.get("songforge"):
        sources.append({"label": "SongForge", "kind": "selected output", "title": "SongForge", "text": s.article})
    if transcript:
        sources.append({"label": "Transcript", "kind": "transcript", "title": "Transcript", "text": transcript})
    if capture_meta:
        capture_text = captures_mod.read_capture_text(capture_meta["capture_id"])
        if capture_text:
            sources.append({
                "label": "Capture",
                "kind": "capture",
                "title": capture_meta.get("title") or "Capture",
                "text": capture_text,
            })
    return sources
