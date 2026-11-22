# Solar Straight Talk organic posting pipeline

Owned by the marketing chat (Mason, Nov 19 2026). Runs 3x/day as a scheduled task (about 9:40 AM, 4:40 PM, 9:40 PM HST).

## Files
- `specs/` one JSON per carousel (slides + caption). `renderer/render.py` turns a spec into 1080x1350 PNGs.
- `photos/` licensed photos used by specs (paths are relative to the repo root).
- `rendered/<post id>/` the PNGs actually posted. Buffer pulls them from `image_url_base` + path.
- `schedule.json` every post: date, time (HST), status, approval, hold, Buffer post ids.

## Approvals
Approval requests go to Mason through Instinct (a TASKS row with the slide images; Instinct texts him the images). Mason answers to Instinct or in the marketing chat; the chat writes his approval here directly.

## Status flow
`draft` -> `approved` (only with Mason's quoted words + date in `approved_by`) -> `queued` (in Buffer, ids recorded) -> `posted`.
A post with a non-empty `hold` is never queued, even if approved.

## Rules
- Nothing goes to Buffer unless `status` is `approved` and `hold` is empty.
- Organic posts only. No ads, no boosting, no spending, no replies or DMs.
- Every stat on a slide needs a source on its sources slide.
- Never say "unbiased" or "independent". Never imply affiliation with HECO or any agency.
- If an approved post's slides change after approval, set it back to `draft` and ask Mason again.
- **Reels are only made from carousels Mason already approved** (status `approved`, `queued` or `posted`). `reels/reel.py` refuses anything else; `--test` renders to /tmp only and is never posted or sent for approval. (Mason, Nov 22.)
- A Reel is its own post and needs its own approval from Mason before it goes to Buffer, even if its carousel was approved.

## Render
```
pip install playwright --break-system-packages
python3 renderer/render.py specs/week1/c01_5to9.json rendered/   # writes rendered/w1_c01_5to9/*.png
```
(uses /usr/bin/google-chrome)
