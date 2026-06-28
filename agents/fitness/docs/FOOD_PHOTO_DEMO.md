# Food Photo Demo Adapter

## Product Goal

Food Photo Demo Adapter is a low-friction meal logging entry point. It lets a user start a meal log from a local food image, while keeping the output honest: rough calorie range, rough protein estimate, confidence, uncertainty factors, and a correction path.

This is not a high-precision food recognition system.

v0.4 Step 2 adds a replaceable provider adapter. The product contract stays the same:

```text
image -> structured food analysis -> calorie range -> confidence -> uncertainty -> user confirmation -> daily meal log
```

## Input And Output

Input:

```text
local image path
optional user note
```

Output:

```json
{
  "provider": "demo",
  "provider_status": "ok",
  "fallback_used": false,
  "detected_food": "牛肉面",
  "meal_category": "noodle",
  "confidence": "medium",
  "estimated_components": ["面", "牛肉", "汤"],
  "uncertainties": ["份量大小", "是否喝完汤", "是否有额外小菜"],
  "provider_notes": []
}
```

Meal estimate:

```json
{
  "meal_text": "牛肉面",
  "calorie_range_kcal": [600, 850],
  "protein_estimate_g": 25,
  "confidence": "medium",
  "default_logged_kcal": 725
}
```

## Uncertainty Handling

The adapter never claims exact grams or exact calories. User-visible copy always includes:

- calorie range;
- rough protein estimate;
- confidence;
- uncertainty factors;
- a correction path, such as portion size, soup, sugar, milk, sauces, or extra side dishes.

## Difference From General Image Recognition

Current implementation is a demo-friendly adapter:

- It checks that a local image path exists.
- It keeps the deterministic `demo` provider for local examples.
- It supports a `manual` provider for structured walkthroughs without an API key.
- It exposes a `vision_api` provider contract, but does not call external APIs by default.
- It supports `auto` fallback when `vision_api` is unavailable.
- It maps the coarse result into existing Fitness meal estimate logic.
- It writes into the existing daily meal state only when explicitly called in `log` mode.

It does not do:

- image segmentation;
- weight estimation;
- multi-label nutrition decomposition;
- medical nutrition advice;
- external food database lookup;
- default real vision provider calls.

## State Integration

`log_meal_from_image(...)` writes into the same daily nutrition state used by text meal logs:

```text
agents/fitness/data/users/<user_id>/daily/YYYY-MM-DD.json
```

Meal logs from images include:

```json
{
  "source": "image",
  "vision_confidence": "medium",
  "vision_uncertainties": []
}
```

Food images do not create memory candidates and do not become long-term preferences.

## CLI

Analyze only:

```bash
python3 agents/fitness/tools/fitness_vision_cli.py analyze \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --provider demo
```

Manual provider:

```bash
python3 agents/fitness/tools/fitness_vision_cli.py analyze \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --provider manual \
  --manual-food "牛肉面" \
  --manual-category noodle \
  --manual-confidence medium
```

Auto provider with fallback:

```bash
python3 agents/fitness/tools/fitness_vision_cli.py analyze \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --provider auto
```

Analyze and log:

```bash
rm -rf agents/fitness/data/users/v04_vision_check

python3 agents/fitness/tools/fitness_vision_cli.py log \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --user v04_vision_check \
  --note "午餐" \
  --date 2026-06-24 \
  --provider manual \
  --manual-food "牛肉面" \
  --manual-category noodle \
  --manual-confidence medium
```

Use `--debug` to inspect structured output.

CLI output includes:

```text
Provider: demo/manual/vision_api
Provider status: ok/fallback/unavailable/error
Fallback used: true/false
```

`--date` selects the exact daily state file. If omitted, the state layer uses `get_today_str()` at command execution time.

The canonical meal log field is:

```python
state["nutrition"]["meals"]
```

There is no top-level `state["meal_logs"]` field.

Focused check:

```bash
python3 - <<'PY'
from agents.fitness.tools.fitness_state import get_daily_state

state = get_daily_state(user_id="v04_vision_check", date="2026-06-24")
meals = state.get("nutrition", {}).get("meals", [])

print("date:", state.get("date"))
print("meal_count:", len(meals))
print("latest_meal:", meals[-1] if meals else None)
PY
```

Remove the throwaway acceptance user after checking:

```bash
rm -rf agents/fitness/data/users/v04_vision_check
```

## Demo

```bash
python3 agents/fitness/run_vision_demo.py
python3 agents/fitness/run_vision_provider_demo.py
python3 agents/fitness/run_showcase_demo.py --flow vision
```

The demo writes only under:

```text
agents/fitness/demo_data/vision/
agents/fitness/demo_data/vision_provider/
agents/fitness/demo_data/showcase/
```

## Vision Provider Contract

The adapter currently supports:

- `demo`: stable local fixture recognition by filename/note hints;
- `manual`: admin/user supplied structured food description;
- `vision_api`: placeholder interface, unavailable unless a future safe wrapper is added;
- `auto`: attempts `vision_api`, then falls back to `demo` or the configured fallback provider.

`vision_api` checks configuration such as `FITNESS_VISION_API_KEY` and `FITNESS_VISION_API_ENDPOINT`, but this version does not perform network calls.

The product principle should remain the same: uncertainty is explicit, correction is easy, and no image result becomes long-term memory by default.
