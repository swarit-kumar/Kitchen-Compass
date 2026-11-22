\# KitchenCompass — Service Contract Examples



These examples document the existing Pydantic contracts in `kitchencompass/schemas.py`.



They are schema examples, not claims about exact runtime responses from every service function.



\## 1. Constraints



```python

from kitchencompass.schemas import Constraints



constraints = Constraints(

&#x20;   pantry\_ids=\["ing\_tomato", "ing\_onion"],

&#x20;   excluded\_ids=\["ing\_peanut"],

&#x20;   pantry\_only=True,

&#x20;   max\_replacements=3,

)

```



Fields:



\- `pantry\_ids`: ingredients available to the user.

\- `excluded\_ids`: ingredients that must not be used.

\- `pantry\_only`: restrict candidates to pantry ingredients.

\- `max\_replacements`: maximum replacement count, from 1 to 3.



\## 2. Successful result



```python

from kitchencompass.schemas import Result



result = Result(

&#x20;   status="OK",

&#x20;   items=\[{"example": "Illustrative result item"}],

&#x20;   schema\_version="1.0",

)

```



`items` contains dictionaries. The exact item structure depends on the service workflow.



\## 3. Missing input



```python

result = Result(status="NEEDS\_INPUT")

```



Used when additional user input is required.



\## 4. Unsupported input



```python

result = Result(status="UNSUPPORTED\_INPUT")

```



Used when the supplied input is unsupported.



\## 5. Unresolved exclusion



```python

result = Result(status="UNRESOLVED\_EXCLUSION")

```



Used when an exclusion cannot be resolved.



\## 6. No feasible result



```python

result = Result(status="NO\_FEASIBLE\_RESULT")

```



Used when the request has no feasible result.



\## 7. Joint planner interface



The Phase 4 implementation currently exposes these functions in `kitchencompass/adapt.py`:



\- `generate\_candidate\_lists(...)`

\- `generate\_joint\_plans(...)`

\- `generate\_independent\_baseline(...)`

\- `validate\_plan(...)`



These functions currently return planner data and validation dictionaries, not the public `Result` contract.



A public joint-adaptation endpoint in `service.py` is not yet implemented.



\## Important distinction



The `Result` schema describes the existing service response contract. The Phase 4 joint planner is a separate module-level implementation. These interfaces should not be presented as integrated until a service wrapper is implemented and tested.



