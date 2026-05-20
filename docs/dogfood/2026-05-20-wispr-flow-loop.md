# Wispr Flow Dogfood Loop - 2026-05-20

## Scope

Issue: `#41`  
Goal: run one real owner capture through the full loop:
capture/import -> recipe run -> review -> markdown/Notion export -> run reopen -> resurfacing digest.

## Real capture used

- Source: owner-provided planning text from this session, entered through the
  Wispr Flow paste path in the Streamlit app.
- Capture ID: `cap-20260520T053352Z-c85b7592`
- Capture record: `/Users/kk/Code/spektorAI/.cache/captures/cap-20260520T053352Z-c85b7592/capture.json`
- Raw input: `/Users/kk/Code/spektorAI/.cache/captures/cap-20260520T053352Z-c85b7592/input.txt`

## Loop evidence

- Run ID: `20260520T053352Z-e5bb2f40`
- Run manifest: `/Users/kk/Code/spektorAI/.cache/runs/20260520T053352Z-e5bb2f40/manifest.json`
- Run stages dir: `/Users/kk/Code/spektorAI/.cache/runs/20260520T053352Z-e5bb2f40/stages/`
- Markdown export:
  `/Users/kk/Code/spektorAI/.cache/exports/2026-05-19-whisper-streamlining-voice-capture-into-actionable-workflows.md`
- Notion export:
  `https://notion.so/366c6f799a338120ae4bfcaca68ea895`
- Resurfacing digest:
  `/Users/kk/Code/spektorAI/.cache/digests/2026-05-19-resurfacing-digest.md`

## Commands run and observed outputs

1. `make test`  
   Output: `265 passed in 3.22s`
2. `make browser-e2e`  
   Output: `browser-e2e: OK`
3. `make browser-e2e-fresh`  
   Output: `browser-e2e-fresh: OK (run 20260520T053138Z-d21120a2)`
4. Local browser dogfood automation against live app + `.cache` artifacts  
   Output:  
   - `DOGFOOD_RUN_ID=20260520T053352Z-e5bb2f40`  
   - `DOGFOOD_CAPTURE_ID=cap-20260520T053352Z-c85b7592`  
   - `DOGFOOD_MARKDOWN_SAVED=True`  
   - `DOGFOOD_NOTION_SAVED=True`
5. `make digest`  
   Output: `/Users/kk/Code/spektorAI/.cache/digests/2026-05-19-resurfacing-digest.md`

## What worked

- Capture persisted with `source=wispr_flow` and linked run metadata.
- Recipe execution completed with full stage artifacts and scorecard.
- Review surface rendered with receipts + fact-check flags.
- Markdown export and Notion export both succeeded.
- Run reopen path worked and allowed downstream export retry.
- Digest generated and linked back to capture/run artifacts.

## Friction findings (real workflow pain)

1. Digest signal is noisy because smoke/demo captures are mixed into the same
   stream as real captures, making real-session recap quality worse.
2. Run manifest metadata keeps a stale capture status snapshot
   (`metadata.capture.status` remained `running`), while the capture record is
   actually `completed`.
3. Scorecard/handoff readiness evidence is stale after exports: the scorecard
   stage still reports "No export has been recorded yet" even when markdown and
   notion exports exist in the manifest.

## Simulation vs real workflow

- This run used real owner-authored text and real provider/notion credentials.
- Remaining realism gap: the text was pasted manually into the Wispr Flow tab
  rather than imported from a raw Wispr Flow export file.

## Follow-up issues created from this report

- `#45` Filter report-only digest to prioritize real captures over smoke/demo artifacts.
- `#46` Keep run manifest capture metadata in sync with capture lifecycle status.
- `#47` Refresh scorecard/handoff readiness after export events.
