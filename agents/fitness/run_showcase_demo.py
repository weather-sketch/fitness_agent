"""Unified showcase runner for Fitness Agent product demos."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
INTEGRATIONS_DIR = AGENT_ROOT / "integrations"
SHOWCASE_DATA_DIR = AGENT_ROOT / "demo_data" / "showcase"
SHOWCASE_DATA_LABEL = "agents/fitness/demo_data/showcase"
DEMO_ASSETS_DIR = AGENT_ROOT / "demo_assets" / "vision"

for path in (AGENT_ROOT, TOOLS_DIR, INTEGRATIONS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from handler import handle_fitness_message  # noqa: E402
from channel_adapter import handle_channel_message  # noqa: E402
from openclaw_adapter import handle_openclaw_event  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_recall  # noqa: E402
import fitness_state  # noqa: E402
import fitness_vision  # noqa: E402


FlowResult = dict[str, Any]
FLOW_ORDER = ["text", "lapse", "vision", "memory", "recall", "fallback", "channel", "openclaw"]
FLOW_ALIASES = {
    "all": FLOW_ORDER,
    "text": ["text", "lapse"],
    "vision": ["vision"],
    "memory": ["memory"],
    "recall": ["recall"],
    "fallback": ["fallback"],
    "channel": ["channel"],
    "openclaw": ["openclaw"],
}


def _print_block(title: str, body: str | list[str]) -> None:
    print(f"{title}:")
    if isinstance(body, list):
        for item in body:
            print(f"- {item}")
    else:
        print(body)
    print()


def _print_debug(payload: dict[str, Any]) -> None:
    print("Debug:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()


def set_demo_data_dir(data_dir: str | Path = SHOWCASE_DATA_DIR) -> Path:
    data_path = Path(data_dir)
    fitness_state.DATA_DIR = data_path
    return data_path


def reset_demo_user_state(data_root: str | Path = SHOWCASE_DATA_DIR) -> Path:
    """Reset isolated showcase state and bind Fitness state helpers to it."""
    data_path = Path(data_root)
    if data_path.exists():
        shutil.rmtree(data_path)
    data_path.mkdir(parents=True, exist_ok=True)
    set_demo_data_dir(data_path)
    return data_path


def _ensure_demo_user(user_id: str) -> None:
    for name in ["profile.json", "recall_state.json", "memory_candidates.json"]:
        fitness_state.save_json(
            fitness_state.get_user_data_dir(user_id) / name,
            copy.deepcopy(fitness_state.DEFAULTS[name]),
        )
    profile = fitness_state.get_profile(user_id=user_id)
    profile["metrics"]["daily_calorie_target"] = 1600
    profile["metrics"]["protein_target_g"] = 80
    fitness_state.save_json(fitness_state.get_user_data_dir(user_id) / "profile.json", profile)
    fitness_state.ensure_user_state(user_id=user_id)


def _latest_meal(user_id: str, date: str) -> dict[str, Any]:
    state = fitness_state.get_daily_state(user_id=user_id, date=date)
    meals = state.get("nutrition", {}).get("meals", []) or []
    return meals[-1] if meals else {}


def _result(
    flow_id: str,
    title: str,
    user_input: str,
    agent_reply: str,
    summary: list[str],
    highlight: str,
    debug: dict[str, Any] | None = None,
) -> FlowResult:
    return {
        "flow_id": flow_id,
        "title": title,
        "user_input": user_input,
        "agent_reply": agent_reply,
        "summary": summary,
        "product_highlight": highlight,
        "debug": debug or {},
    }


def run_training_food_plan_flow(user_id: str = "showcase_text_user") -> FlowResult:
    _ensure_demo_user(user_id)
    user_input = "今天晚上练臀，怎么吃？"
    handled = handle_fitness_message(user_input, user_id=user_id, channel="showcase")
    daily = fitness_state.get_daily_state(user_id=user_id)
    training = daily.get("training", {})
    return _result(
        "text",
        "Flow 1: Training Day Food Plan",
        user_input,
        handled["reply"],
        [
            f"handled: {str(handled['handled']).lower()}",
            f"intent: {handled['intent']}",
            f"day_type: {daily.get('day_type')}",
            f"planned_training: {training.get('type')}",
            f"training_time: {training.get('time')}",
        ],
        "把训练上下文纳入饮食建议，而不是只记录热量。",
        {"handler_result": handled, "daily_state": daily},
    )


def run_lapse_recovery_flow(user_id: str = "showcase_lapse_user") -> FlowResult:
    _ensure_demo_user(user_id)
    user_input = "我今天吃爆了，不想记了"
    handled = handle_fitness_message(user_input, user_id=user_id, channel="showcase")
    daily = fitness_state.get_daily_state(user_id=user_id)
    return _result(
        "lapse",
        "Flow 2: Lapse Recovery",
        user_input,
        handled["reply"],
        [
            f"handled: {str(handled['handled']).lower()}",
            f"intent: {handled['intent']}",
            f"lapse_risk: {daily.get('emotion', {}).get('lapse_risk')}",
            f"special_context: {daily.get('special_context', [])}",
        ],
        "健康管理中最重要的不是完美记录，而是偏离后能低压力接回来。",
        {"handler_result": handled, "daily_state": daily},
    )


def run_food_photo_flow(user_id: str = "showcase_vision_user", date: str = "2026-06-24") -> FlowResult:
    _ensure_demo_user(user_id)
    image_path = DEMO_ASSETS_DIR / "beef_noodle_demo.jpg"
    result = fitness_vision.log_meal_from_image(
        image_path,
        user_id=user_id,
        date=date,
        note="午餐",
        provider="manual",
        manual_food="牛肉面",
        manual_category="noodle",
        manual_confidence="medium",
    )
    image_result = result["image_result"]
    estimate = result["meal_estimate"]
    daily = result["daily_state"]
    meals = daily.get("nutrition", {}).get("meals", []) or []
    low, high = estimate["calorie_range_kcal"]
    return _result(
        "vision",
        "Flow 3: Food Photo Logging",
        "图片：beef_noodle_demo.jpg；manual_food=牛肉面",
        result["reply"],
        [
            f"provider: {image_result['provider']}",
            f"provider_status: {image_result['provider_status']}",
            f"fallback_used: {str(image_result['fallback_used']).lower()}",
            f"detected_food: {image_result['detected_food']}",
            f"calorie_range: {low}-{high} kcal",
            f"protein_estimate: {estimate['protein_estimate_g']}g",
            f"uncertainties: {'、'.join(estimate['uncertainties'])}",
            f"logged_date: {daily.get('date')}",
            f"meal_count_after: {len(meals)}",
            "state_field: nutrition.meals",
        ],
        "图片入口降低记录成本，但仍保留区间估算、置信度和用户纠错入口，不假装高精度。",
        {"vision_result": result, "latest_meal": _latest_meal(user_id, date)},
    )


def run_active_memory_flow(user_id: str = "showcase_memory_user") -> FlowResult:
    _ensure_demo_user(user_id)
    preference_input = "以后练前别推荐酸奶，我会胃不舒服。"
    candidate_result = handle_fitness_message(preference_input, user_id=user_id, channel="showcase")
    candidates = fitness_memory.list_memory_candidates(user_id=user_id)
    candidate = candidates[0]
    approved = fitness_memory.approve_memory_candidate(
        user_id,
        candidate["candidate_id"],
        review_note="Showcase approval: explicit pre-workout discomfort.",
    )
    plan_input = "今天晚上练臀，怎么吃？"
    plan_result = handle_fitness_message(plan_input, user_id=user_id, channel="showcase")
    active_preferences = plan_result["debug"].get("active_preferences_applied", [])
    reply_contains_yogurt = "酸奶" in plan_result["reply"]
    return _result(
        "memory",
        "Flow 4: Active Memory Changes Recommendation",
        f"{preference_input}\n{plan_input}",
        plan_result["reply"],
        [
            f"candidate_type: {candidate.get('type')}",
            f"candidate_key: {candidate.get('key')}",
            f"candidate_status_before_review: {candidate.get('status')}",
            f"approved_status: {approved.get('status')}",
            f"applied_to: {approved.get('applied_to')}",
            f"active_preferences_applied: {active_preferences}",
            f"reply_contains_yogurt: {str(reply_contains_yogurt).lower()}",
        ],
        "候选记忆不是自动写入长期记忆，而是经过确认后进入 active preference，并真实改变后续推荐行为。",
        {
            "candidate_result": candidate_result,
            "candidate": candidate,
            "approved": approved,
            "plan_result": plan_result,
        },
    )


def run_recall_flow(user_id: str = "showcase_recall_user") -> FlowResult:
    _ensure_demo_user(user_id)
    today = fitness_state.get_today_str()
    now = f"{today}T18:00:00"
    fitness_state.update_daily_state({
        "date": today,
        "day_type": "training_day",
        "training": {
            "planned": True,
            "type": "glutes",
            "time": "evening",
            "status": "planned",
            "post_workout_meal_status": "unknown",
        },
        "nutrition": {"meals": []},
    }, user_id=user_id, date=today)
    before = fitness_recall.detect_recall_opportunity(user_id=user_id, date=today, now=now)
    fitness_recall.set_recall_opt_in(user_id=user_id, enabled=True)
    after = fitness_recall.detect_recall_opportunity(user_id=user_id, date=today, now=now)
    return _result(
        "recall",
        "Flow 5: Opt-in Recall",
        "训练日傍晚还没有饮食记录",
        after["message"],
        [
            f"before_enabled: {str(before['enabled']).lower()}",
            f"before_should_send: {str(before['should_send']).lower()}",
            f"before_blocked_reason: {before['blocked_reason']}",
            f"after_enabled: {str(after['enabled']).lower()}",
            f"after_should_send: {str(after['should_send']).lower()}",
            f"after_blocked_reason: {after['blocked_reason']}",
            f"recall_type: {after['recall_type']}",
        ],
        "召回不是默认打扰，而是在用户 opt-in 后才建议发送，平衡陪伴感和边界感。",
        {"before": before, "after": after},
    )


def run_non_fitness_fallback_flow(user_id: str = "showcase_fallback_user") -> FlowResult:
    user_input = "帮我把明天的会议整理一下"
    before_exists = fitness_state.get_user_data_dir(user_id).exists()
    handled = handle_fitness_message(user_input, user_id=user_id, channel="showcase")
    after_exists = fitness_state.get_user_data_dir(user_id).exists()
    return _result(
        "fallback",
        "Flow 6: Non-fitness Fallback",
        user_input,
        "交还主 Agent 正常处理。",
        [
            f"handled: {str(handled['handled']).lower()}",
            f"intent: {handled['intent']}",
            "handoff: main_agent",
            f"user_state_existed_before: {str(before_exists).lower()}",
            f"user_state_exists_after: {str(after_exists).lower()}",
            "memory_candidates_added: 0",
        ],
        "垂直 Agent 只处理自己负责的健康管理场景，非 fitness 请求交还主 Agent，避免乱接任务。",
        {"handler_result": handled},
    )


def run_channel_adapter_flow() -> FlowResult:
    message = {
        "message_id": "showcase-channel-001",
        "channel": "wechat",
        "sender_id": "showcase_user",
        "conversation_id": "showcase-conv",
        "type": "text",
        "text": "今天晚上练臀，怎么吃？",
        "metadata": {},
    }
    response = handle_channel_message(message, date="2026-06-24")
    fallback_message = {
        **message,
        "message_id": "showcase-channel-002",
        "sender_id": "showcase_meeting_user",
        "text": "帮我把明天的会议整理一下",
    }
    fallback = handle_channel_message(fallback_message, date="2026-06-24")
    return _result(
        "channel",
        "Flow 7: Channel Adapter / OpenClaw-ready Message Router",
        "模拟微信消息：今天晚上练臀，怎么吃？",
        response["reply"],
        [
            f"channel: {response['channel']}",
            f"user_id: {response['user_id']}",
            f"message_type: {response['message_type']}",
            f"handled: {str(response['handled']).lower()}",
            f"handoff: {str(response['handoff']).lower()}",
            f"intent: {response['intent']}",
            f"fallback_handled: {str(fallback['handled']).lower()}",
            f"fallback_handoff: {str(fallback['handoff']).lower()}",
        ],
        "Channel Adapter 将微信/IM 消息抽象为统一 message schema；非 fitness 请求 handoff 给主 Agent。",
        {"fitness_response": response, "fallback_response": fallback},
    )


def run_openclaw_integration_flow() -> FlowResult:
    event = {
        "event_id": "showcase-openclaw-001",
        "source": "openclaw",
        "channel": "wechat",
        "sender_id": "showcase_openclaw_user",
        "conversation_id": "showcase-conv",
        "message": {
            "type": "text",
            "text": "今天晚上练臀，怎么吃？",
        },
        "date": "2026-06-24",
        "timestamp": "2026-06-24T20:00:00",
        "metadata": {},
    }
    response = handle_openclaw_event(event)
    fallback_event = {
        **event,
        "event_id": "showcase-openclaw-002",
        "sender_id": "showcase_openclaw_meeting_user",
        "message": {"type": "text", "text": "帮我把明天的会议整理一下"},
    }
    fallback = handle_openclaw_event(fallback_event)
    return _result(
        "openclaw",
        "Flow 8: OpenClaw Integration Scaffold",
        "模拟 OpenClaw runtime event：今天晚上练臀，怎么吃？",
        response["reply"]["text"] if response.get("reply") else "handoff to main_agent",
        [
            f"ok: {str(response['ok']).lower()}",
            f"handled: {str(response['handled']).lower()}",
            f"handoff: {str(response['handoff']).lower()}",
            f"agent: {response['agent']}",
            f"channel: {response['channel']}",
            f"conversation_id: {response['conversation_id']}",
            f"state_date: {response.get('state_summary', {}).get('date')}",
            "runtime_dispatcher_found: false",
            f"fallback_handled: {str(fallback['handled']).lower()}",
            f"fallback_handoff: {str(fallback['handoff']).lower()}",
            f"handoff_target: {fallback.get('handoff_payload', {}).get('target')}",
        ],
        "OpenClaw-ready scaffold: 当前 workspace 未发现真实 runtime dispatcher，本 demo 使用本地 OpenClaw-like events。",
        {"fitness_response": response, "fallback_response": fallback},
    )


FLOW_RUNNERS: dict[str, Callable[[], FlowResult]] = {
    "text": run_training_food_plan_flow,
    "lapse": run_lapse_recovery_flow,
    "vision": run_food_photo_flow,
    "memory": run_active_memory_flow,
    "recall": run_recall_flow,
    "fallback": run_non_fitness_fallback_flow,
    "channel": run_channel_adapter_flow,
    "openclaw": run_openclaw_integration_flow,
}


def run_showcase_flow(flow: str, reset_state: bool = True, data_root: str | Path = SHOWCASE_DATA_DIR) -> list[FlowResult]:
    if flow not in FLOW_ALIASES:
        raise ValueError(f"Unsupported showcase flow: {flow}")
    if reset_state:
        reset_demo_user_state(data_root)
    else:
        set_demo_data_dir(data_root)
    return [FLOW_RUNNERS[name]() for name in FLOW_ALIASES[flow]]


def print_flow_result(result: FlowResult, debug: bool = False) -> None:
    print(f"=== {result['title']} ===\n")
    _print_block("User input", result["user_input"])
    _print_block("Agent reply", result["agent_reply"])
    _print_block("Key state / provider summary", result["summary"])
    _print_block("Product highlight", result["product_highlight"])
    if debug:
        _print_debug(result.get("debug", {}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Fitness Agent showcase flows")
    parser.add_argument("--flow", default="all", choices=sorted(FLOW_ALIASES))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print("Fitness Agent v0.4 Showcase Demo")
    print(f"Demo state directory: {SHOWCASE_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.\n")

    results = run_showcase_flow(args.flow)
    for result in results:
        print_flow_result(result, debug=args.debug)


if __name__ == "__main__":
    main()
