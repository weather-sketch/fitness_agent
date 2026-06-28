# WeChat Manual Test Guide

## Premise

The current workspace does not expose a real WeChat runtime binding point, OpenClaw dispatcher, WeChat SDK callback, or plugin manifest for Fitness Agent.

This test depends on OpenClaw main Agent skill routing. The expected path is:

```text
WeChat message
  -> OpenClaw main Agent
  -> skills/fitness-coach/SKILL.md guidance
  -> agents.fitness.channel_adapter.handle_channel_message(...)
  -> user-facing reply or main-Agent handoff
```

Current best path to real WeChat testing is skill-guided routing, not direct runtime binding, because no dispatcher/callback API is exposed in this workspace.

No explicit skill reload command was found in this workspace. If WeChat routing does not change after editing the skill, restart/reload OpenClaw using the runtime UI or the method provided by OpenClaw.

## Local Preflight

Run these before testing in WeChat:

```bash
python3 agents/fitness/tools/fitness_wechat_routing_check.py
python3 agents/fitness/tools/fitness_binding_check.py
python3 -m unittest discover -s agents/fitness/tests
```

## Test Steps

In WeChat, send these messages to OpenClaw one by one:

```text
今天晚上练臀，怎么吃？
我今天吃爆了，不想记了
以后练前别推荐酸奶，我会胃不舒服
今天晚上练臀，怎么吃？
/recall on
/recall status
帮我把明天的会议整理一下
```

If image messages are supported, send a food photo with this caption:

```text
午餐
```

## Expected Results

- Training-day question: returns practical pre-workout and post-workout food guidance.
- Lapse recovery: returns low-pressure recovery guidance and does not suggest punishment or restriction.
- Yogurt preference: creates a Fitness memory candidate.
- Second training-day question: if the preference has been approved, the reply should avoid yogurt; if it has not been approved, yogurt may still appear.
- `/recall on`: enables Fitness recall suggestions for that channel user.
- `/recall status`: returns enabled status.
- Meeting request: should not be forced into Fitness; it should hand off to the main Agent.
- Image: if the runtime can provide a local image path, it should go through the Food Photo Adapter. If the runtime cannot provide an image path, the main Agent should ask the user for a text description instead of pretending image analysis happened.

## If Fitness Does Not Trigger

如果没有触发 Fitness, record:

```text
1. 用户原始输入
2. 主 Agent 原始回复
3. 是否提到了 fitness-coach skill
4. 是否调用了任何 tool
5. 是否出现 error
```

Then check:

- Adjust `skills/fitness-coach/SKILL.md` trigger wording.
- Confirm whether OpenClaw currently enabled the `fitness-coach` skill.
- Confirm whether the skill needs registration, refresh, reload, or a runtime restart.
- If no reload command is available, restart/reload OpenClaw using the runtime UI or the method provided by OpenClaw.

Do not claim this as real WeChat SDK integration. This is a manual test for skill-guided routing through the OpenClaw main Agent.

## Proactive Recall And Delivery Note

Fitness Agent v0.5 can create proactive recall outbox items after opt-in and can use safety-gated OpenClaw outbound delivery.

Current path:

```text
recall opportunity -> outbox pending item -> openclaw message send -> openclaw-weixin
```

This is not a direct WeChat SDK integration. Scheduled proactive recall uses local launchd/cron only to trigger:

```text
fitness_recall_worker.py scheduled-run
```

No launchd or cron job is installed automatically.

Use `python3 agents/fitness/tools/fitness_recall_worker.py run-once ... --dry-run` or `scheduled-run ... --dry-run` for local verification. Do not describe outbox pending items as sent messages.

OpenClaw message delivery can be tested with `fitness_delivery_cli.py` and `openclaw_message` mode, but it defaults to dry-run. Real sending requires configuring exact-case `target=<user@im.wechat>` and `account_id`, then passing `--send --confirm-send`.

Important: `@im.wechat` targets are case-sensitive. Use the exact target from OpenClaw inbound metadata, for example `DemoUserAbC123@im.wechat`; do not lowercase it. Lowercase targets can return a core messageId while the WeChat client receives nothing.

See `OPENCLAW_MESSAGE_DELIVERY.md` and `SCHEDULED_PROACTIVE_RECALL.md`.
