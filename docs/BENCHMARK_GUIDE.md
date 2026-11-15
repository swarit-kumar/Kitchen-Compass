# Phase 1 development benchmark review

The 15 cases in `data/benchmark/dev_cases.jsonl` use the v2 development
split. Each case has three fixed candidate options, so the two reviewers can
grade exactly the same options. Grades and annotator IDs are blank.
The v1 prompts and their split are in `data/benchmark/archive/v1/`.

Vibhu and Swarit should independently review the same 10 flagged cases in
`data/benchmark/review_vibhu.md` and `data/benchmark/review_swarit.md`.
Keep the two files separate until both reviews are complete. Look up the
full ingredients and cooking steps in `data/processed/recipes.jsonl`. Use
`data/processed/ingredients.jsonl` to check ingredient components. Some
options deliberately violate an exclusion to test the rubric.

| Grade | Pantry recipe | Substitution or joint plan |
|---|---|---|
| 0 | Unsuitable or violates a constraint | Unsuitable or violates a constraint |
| 1 | Possible with substantial additions | Plausible with caveats |
| 2 | Practical match | Suitable for the role and recipe context |

Record a grade, short reason, and evidence type for each option. A proposed
alternative based on your judgment uses `plausibility_judgment`. If a source
specifically documents the alternative in a relevant context, record the URL
or filename, exact location, and a short paraphrase. The generated recipe
source identifies the context. A hard constraint violation always receives
0. Explain every nonzero substitution grade.

Once both sheets are filled, compare the grades and compute exact agreement
as matching option grades divided by the number of jointly graded options.
Keep both original sheets and document reconciled labels in the benchmark.
These are development cases. Keep test labels separate from feature, model,
and rule decisions.
