\# KitchenCompass — Phase 4: Joint Ingredient Adaptation



\## Objective



Phase 4 extends single-ingredient substitution into joint multi-target ingredient adaptation.



The planner evaluates candidate replacement combinations and selects a valid plan using individual substitution quality and pair compatibility.



\## Implementation



Main implementation: `kitchencompass/adapt.py`



Functions:



\- `validate\_targets`: validates requested replacement targets.

\- `generate\_candidate\_lists`: generates eligible candidates for each target.

\- `target\_role\_context`: obtains recipe-role context.

\- `pair\_compatibility\_score`: evaluates compatibility between replacement pairs.

\- `score\_joint\_plan`: calculates the joint-plan score.

\- `generate\_joint\_plans`: enumerates and ranks candidate combinations.

\- `generate\_independent\_baseline`: selects individually highest-scoring candidates for comparison.

\- `validate\_plan`: independently validates a completed plan.



\## Planning constraints



\- Maximum targets: 3.

\- Maximum candidates per target: 5.

\- Maximum combinations: 125.

\- Replacement IDs must be distinct.

\- Target ingredients cannot be selected as replacements.

\- Excluded ingredients and pantry restrictions must be respected.

\- Every requested target must be replaced exactly once.



\## Joint scoring



For multiple replacements:



`Plan score = 0.8 × Q + 0.2 × J`



Where:



\- Q is the mean individual substitution score.

\- J is the mean pair-compatibility score.



For a single replacement, the individual score is used.



Pair compatibility is a computational proxy, not a guarantee of culinary suitability.



\## Independent baseline



The baseline selects the individually highest-scoring eligible candidate for each target.



It does not silently repair duplicate replacement IDs or incompatible pairs. Violations are reported.



\## Development output



File: `results/development\_joint\_plans.json`



The generated development output contains four eligible two-target cases:



\- `dev\_v2\_09`: cauliflower and grated coconut.

\- `dev\_v2\_10`: small pasta and celery.

\- `dev\_v2\_10`: small pasta and canned tomato.

\- `dev\_v2\_10`: small pasta and cooked chickpea.



All four cases produced two joint plans, with both plans passing the independent validator.



The independent baselines were invalid in all four cases.



\## Tests



The complete test suite passed:



`99 passed in 7.82s`



The development JSON output was also parsed successfully using Python's JSON tool.



\## Evidence limitations



All generated development cases remain `pending\_review`.



Candidate scores and pair compatibility are software outputs. They must not be interpreted as manually verified culinary recommendations.



Synthetic test fixtures are software-validation fixtures and are not culinary evidence.



\## Service integration status



The existing public service functions are:



\- `recommend\_recipes`

\- `recommend\_for\_pantry`

\- `rank\_substitutes`



The Phase 4 joint planner is currently implemented as an internal module API in `adapt.py`. A public joint-adaptation endpoint in `service.py` is not claimed by this phase documentation.



\## Phase 4 completion status



Core joint-planning implementation, independent validation, development output generation, and regression tests are complete.



Documentation and manifest updates are being finalized.



