"""Portfolio demo for approved memory changing Fitness recommendations."""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = AGENT_ROOT / "tools"
DEMO_DATA_DIR = AGENT_ROOT / "demo_data"
DEMO_DATA_LABEL = "agents/fitness/demo_data"

for path in (AGENT_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from handler import handle_fitness_message  # noqa: E402
import fitness_memory  # noqa: E402
import fitness_state  # noqa: E402


def _print_block(title: str, body: str | list[str]) -> None:
    print(f"{title}:")
    if isinstance(body, list):
        for item in body:
            print(f"- {item}")
    else:
        print(body)
    print()


def _prepare_demo_data() -> None:
    if DEMO_DATA_DIR.exists():
        shutil.rmtree(DEMO_DATA_DIR)
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    fitness_state.DATA_DIR = DEMO_DATA_DIR
    for name in ["profile.json", "recall_state.json", "memory_candidates.json"]:
        fitness_state.save_json(
            fitness_state.get_user_data_dir("default") / name,
            copy.deepcopy(fitness_state.DEFAULTS[name]),
        )
    profile = fitness_state.get_profile(user_id="default")
    profile["metrics"]["daily_calorie_target"] = 1600
    profile["metrics"]["protein_target_g"] = 80
    fitness_state.save_json(fitness_state.get_user_data_dir("default") / "profile.json", profile)


def main() -> None:
    _prepare_demo_data()

    print("Fitness Agent v0.3 Active Memory Demo")
    print(f"Demo state directory: {DEMO_DATA_LABEL}")
    print("Real state under agents/fitness/data is not read or modified.\n")

    preference_text = "以后练前别推荐酸奶，我会胃不舒服。"
    _print_block("Step 1 User preference", preference_text)
    candidate_result = handle_fitness_message(preference_text, user_id="default", channel="demo")
    _print_block("Step 2 Handler reply", candidate_result["reply"])

    candidates = fitness_memory.list_memory_candidates(user_id="default")
    candidate = candidates[0]
    _print_block("Step 3 Candidate created", [
        f"candidate_id: {candidate['candidate_id']}",
        f"type: {candidate['type']}",
        f"key: {candidate['key']}",
        f"status: {candidate['status']}",
    ])

    approved = fitness_memory.approve_memory_candidate(
        "default",
        candidate["candidate_id"],
        review_note="User explicitly reported pre-workout discomfort.",
    )
    _print_block("Step 4 Approved candidate", [
        f"status: {approved['status']}",
        f"applied_to: {approved.get('applied_to')}",
    ])

    active = fitness_memory.get_active_preferences(user_id="default")
    _print_block("Step 5 Active preference", [
        f"food_avoidance keys: {[item['key'] for item in active['food_avoidance']]}",
    ])

    plan_text = "今天晚上练臀，怎么吃？"
    plan_result = handle_fitness_message(plan_text, user_id="default", channel="demo")
    _print_block("Step 6 User asks for plan", plan_text)
    _print_block("Step 7 Preference-aware reply", plan_result["reply"])
    _print_block("Step 8 Debug summary", [
        f"active_preferences_applied: {plan_result['debug'].get('active_preferences_applied')}",
        f"reply_contains_yogurt: {'酸奶' in plan_result['reply']}",
    ])

    _print_block(
        "Product highlight",
        "候选记忆被人工 approve 后写入 active preference，后续训练日推荐会避开用户明确不舒服的选项。",
    )


if __name__ == "__main__":
    main()
