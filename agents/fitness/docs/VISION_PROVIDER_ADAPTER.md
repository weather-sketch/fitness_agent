# Vision Provider Adapter

## Purpose

Fitness Agent v0.4 Step 2 turns the food-photo demo into a replaceable provider adapter. The goal is not high-precision food recognition. The goal is a stable product contract:

```text
image
  -> structured food analysis
  -> rough calorie range / protein estimate
  -> confidence and uncertainty
  -> user confirmation or correction
  -> existing daily meal log
```

## Providers

Supported provider names:

- `demo`: deterministic local provider based on filename and note hints. It keeps demos and tests stable.
- `manual`: structured manual input for real-image walkthroughs when no API key is available.
- `vision_api`: placeholder contract for a future real provider. It does not call external APIs in this version.
- `auto`: tries `vision_api`; if unavailable or errored, falls back to `demo` or another configured fallback provider.

## Unified Schema

Every provider returns the same shape:

```python
{
  "provider": "demo",
  "provider_status": "ok",
  "fallback_used": False,
  "fallback_provider": None,
  "requested_provider": "demo",
  "detected_food": "牛肉面",
  "meal_category": "noodle",
  "confidence": "medium",
  "estimated_components": ["面", "牛肉", "汤"],
  "uncertainties": ["份量大小", "是否喝完汤", "是否有额外小菜"],
  "raw_caption": "demo adapter: noodle bowl with beef-like topping",
  "provider_notes": [],
  "image_path": "agents/fitness/demo_assets/vision/beef_noodle_demo.jpg"
}
```

`provider_status` values:

- `ok`: selected provider returned a usable result.
- `fallback`: requested provider was unavailable or errored, and fallback produced the result.
- `unavailable`: provider is not configured or not implemented.
- `error`: provider raised an unexpected error.

## Fallback Rules

`vision_api` is unavailable when `FITNESS_VISION_API_KEY` or `FITNESS_VISION_API_ENDPOINT` is missing. Even when both variables exist, this version still returns unavailable because network calls are intentionally disabled until a safe wrapper is added.

`auto` always attempts the `vision_api` contract first. If it cannot produce an `ok` result, the adapter falls back to the configured fallback provider, defaulting to `demo`. Fallback is explicit:

```python
{
  "provider": "demo",
  "provider_status": "fallback",
  "fallback_used": True,
  "requested_provider": "auto"
}
```

Provider failures should not crash the main flow. They become `provider_status="error"` and then fallback if possible.

## CLI Examples

Demo provider:

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

Log with explicit date:

```bash
python3 agents/fitness/tools/fitness_vision_cli.py log \
  --image agents/fitness/demo_assets/vision/beef_noodle_demo.jpg \
  --user v04_provider_check \
  --date 2026-06-24 \
  --provider manual \
  --manual-food "牛肉面" \
  --manual-category noodle \
  --manual-confidence medium \
  --note "午餐"
```

The canonical state field is:

```python
state["nutrition"]["meals"]
```

There is no top-level `meal_logs` field.

## Demo

```bash
python3 agents/fitness/run_vision_provider_demo.py
python3 agents/fitness/run_showcase_demo.py --flow vision
```

The demo writes only to:

```text
agents/fitness/demo_data/vision_provider/
agents/fitness/demo_data/showcase/
```

## Boundaries

- No default external API calls.
- No hard-coded secrets.
- No food weight estimation.
- No image segmentation.
- No nutrition database lookup.
- No memory candidate creation from image logs.
- No OpenClaw dispatcher or WeChat channel integration.

## Future Real Provider

To add a real provider later, implement a safe wrapper behind `analyze_food_image_vision_api(...)`, keep tests mocked, and preserve the same schema. The product output should remain conservative and correction-friendly rather than claiming exact calories.
