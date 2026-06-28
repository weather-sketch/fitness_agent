# Demo Playground

## Purpose

Fitness Agent v0.4 Step 3 adds a unified showcase runner and a local playground. This is demo packaging, not a new core Agent capability.

The goal is to make the prototype easy to record, screenshot, and explain:

```text
Fitness Agent is not a calorie tracker and not a prompt-only chatbot.
It uses state management, candidate memory, active preference, provider adapter,
and opt-in recall to turn health management into a sustainable Agent workflow.
```

## One-command Showcase

```bash
python3 agents/fitness/run_showcase_demo.py
```

Default flow is `all`.

## Per-flow Showcase

```bash
python3 agents/fitness/run_showcase_demo.py --flow all
python3 agents/fitness/run_showcase_demo.py --flow text
python3 agents/fitness/run_showcase_demo.py --flow vision
python3 agents/fitness/run_showcase_demo.py --flow memory
python3 agents/fitness/run_showcase_demo.py --flow recall
python3 agents/fitness/run_showcase_demo.py --flow fallback
python3 agents/fitness/run_showcase_demo.py --flow channel
python3 agents/fitness/run_showcase_demo.py --flow openclaw
```

Use `--debug` only when you need the full structured result:

```bash
python3 agents/fitness/run_showcase_demo.py --flow memory --debug
```

## Showcase Flows

1. Training day food plan: `今天晚上练臀，怎么吃？`
2. Lapse recovery: `我今天吃爆了，不想记了`
3. Food photo logging: manual provider logs beef noodle into `nutrition.meals`
4. Active memory: approve `avoid_yogurt_pre_workout`, then later plan avoids yogurt
5. Opt-in recall: `should_send=false` before opt-in, `should_send=true` after opt-in
6. Non-fitness fallback: meeting request returns `handled=false`
7. Channel adapter: simulated WeChat message routes through `handle_channel_message(...)`
8. OpenClaw scaffold: simulated runtime event routes through `handle_openclaw_event(...)`

This is an OpenClaw-ready scaffold. No real runtime dispatcher was found in this workspace, so this demo uses local OpenClaw-like events.

Each flow prints:

```text
User input
Agent reply
Key state / provider summary
Product highlight
```

## Local Interactive Playground

```bash
python3 agents/fitness/playground.py
```

Menu:

```text
Fitness Agent Playground

请选择一个 demo:
1. 训练日怎么吃
2. 吃超后怎么接回节奏
3. 图片记录一餐
4. 记忆生效：不推荐酸奶
5. opt-in recall 建议
6. non-fitness fallback
7. 自由输入
8. 模拟微信/IM 消息入口
9. 模拟 OpenClaw runtime event
0. 退出
```

Free input uses the existing `handle_fitness_message(...)` entry point. It does not add new intents.

## Demo State Isolation

Showcase runner writes only to:

```text
agents/fitness/demo_data/showcase/
```

Playground writes only to:

```text
agents/fitness/demo_data/playground/
```

Both scripts print that real state under `agents/fitness/data/` is not read or modified. They do not use `agents/fitness/data/users/default` by default.

## Recommended Recording Order

```text
1. 训练日饮食建议
2. 图片记录牛肉面
3. 模拟微信/IM 消息入口
4. 模拟 OpenClaw runtime event
5. 不推荐酸奶的记忆生效
6. 吃超后的低压力恢复
7. opt-in recall
8. non-fitness fallback
```

## Portfolio Narrative

The strongest product story is the combination of:

- text routing for training/nutrition context;
- low-pressure lapse recovery;
- image-to-meal logging with confidence and uncertainty;
- candidate memory review before long-term preference writes;
- active preferences that change later recommendations;
- opt-in recall that respects user boundaries;
- OpenClaw-ready channel adapter contract;
- OpenClaw integration scaffold with reply/handoff payloads;
- non-fitness fallback to avoid vertical-agent overreach.

## Boundaries

Do not describe this as:

- high-precision food recognition;
- exact calorie calculation;
- automatic health diagnosis;
- medical advice;
- scheduler or proactive push integration;
- real WeChat/OpenClaw channel dispatcher integration.
- real OpenClaw runtime binding.

Current status: local showcase, playground, channel adapter simulator, and OpenClaw integration scaffold only.
