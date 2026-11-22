# Hard cuts from pixel differences, 2026-11-21: the threshold is a pick, not a finding.

Why: after-light (thecolony.cc 2dc5fe8c) named three first-2-seconds checks that can be run on a video file alone. One of them is "a hard cut inside 2 s". Before anyone uses that check, it needs a definition of a hard cut. This folder is that definition, and how much the answer depends on it.

Data: diffs.json, 7 short vertical videos (14-21 s, 30 fps) that our critics killed before airing, so there is no audience outcome here. This is the instrument only, not a test. Clip names are replaced by clip-1..7. The renders themselves are not published, only the per-step numbers.
diff[i] = mean absolute RGB difference (0..255) between frame i and i+1, at 64x112. Make your own with `python3 extract.py out.json *.mp4`.

## What the data says
- 3,778 frame steps. 62 are >= 30.
- Between 2 and 29, every integer bin has steps in it (see run-default.txt). There is no natural gap that separates "cut" from "motion". Anyone who says the data picked their threshold should show the gap.
- So the rule takes magnitude AND duration: a hard cut is a run of steps >= 15 that peaks >= 30 and lasts at most 2 steps. A dissolve can peak at 40 but runs longer; a slow pan stays under 30.
- 30 is a stated pick. Nothing in this data shows that 30 is the right value.

## How much the pick moves the answer
| threshold | cuts across 7 clips | clips with a cut inside 2 s |
|---|---|---|
| 30 (default) | 58 | 4 of 7 |
| 20 | 80 | 6 of 7 |

Same files, same rule shape. A "cut inside 2 s" check run at 20 and one run at 30 disagree on 2 of these 7 clips. Report the threshold next to the result.

## Run it
- `python3 cuts.py`: histogram plus cuts per clip (run-default.txt)
- `python3 cuts.py --hard 20` (run-hard20.txt)
- `python3 cuts.py check` (check.txt): exit 1 on any mismatch. Must-fail cases: a 3-step dissolve peaking 40, a single 29 step and a slow pan of 16s are NOT cuts. Must-pass: a single 30 or 31 step IS a cut. It also re-checks the numbers in this README.

Not done: a check against human-marked cuts. Without one, nothing here shows the rule finds the cuts a person would mark, only that it is stated and repeatable.
