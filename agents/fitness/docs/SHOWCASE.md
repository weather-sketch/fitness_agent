# Fitness Agent Showcase

## 项目一句话

一个基于 OpenClaw 工作流设计的 Fitness 垂直 Agent 原型，将热量记录扩展为训练、饮食、恢复、候选记忆、个性化建议和低成本图片记录入口。

## 核心 Demo Flows

1. 训练日饮食规划。
2. 饮食记录与动态调整。
3. 练后恢复建议。
4. 吃爆后的 lapse recovery。
5. 周度轻量复盘。
6. memory candidate review。
7. active memory 改变后续推荐。
8. opt-in recall suggestion。
9. food photo logging demo。
10. channel adapter / OpenClaw-ready message router。
11. OpenClaw integration scaffold。

## 一键 Showcase Runner

v0.4 Step 3 新增统一展示入口，把分散 demo 串成适合录屏、截图和面试讲解的固定流程：

```bash
python3 agents/fitness/run_showcase_demo.py
python3 agents/fitness/run_showcase_demo.py --flow vision
python3 agents/fitness/run_showcase_demo.py --flow memory
python3 agents/fitness/run_showcase_demo.py --flow recall
python3 agents/fitness/run_showcase_demo.py --flow channel
python3 agents/fitness/run_showcase_demo.py --flow openclaw
```

默认 `--flow all` 会展示：

```text
训练日饮食建议
吃超后的低压力恢复
图片记录牛肉面
不推荐酸奶的 active memory 闭环
opt-in recall 建议
non-fitness fallback
模拟微信/IM 消息入口
模拟 OpenClaw runtime event
```

输出只保留用户输入、Agent 回复、关键状态摘要和产品亮点；完整结构只在 `--debug` 下展示。

本地可交互入口：

```bash
python3 agents/fitness/playground.py
```

Showcase 和 playground 都默认写入 `agents/fitness/demo_data/` 下的隔离目录，不读写真实 `agents/fitness/data/users/default`。

## Channel Adapter

v0.4 Step 4 新增 Channel Adapter，让 Fitness Agent 具备接入真实对话入口前的 adapter contract：

```text
IM / WeChat message
  -> normalize channel message
  -> resolve channel + sender_id to Fitness user_id
  -> route text / image / command
  -> return channel-safe reply
  -> non-fitness handoff to main agent
```

示例：

```bash
python3 agents/fitness/run_channel_demo.py
python3 agents/fitness/tools/fitness_channel_cli.py text \
  --text "今天晚上练臀，怎么吃？" \
  --channel wechat \
  --sender demo_user
```

当前是 OpenClaw-ready channel adapter，不是真实微信接入；不调用微信 SDK，不发送真实消息。

## OpenClaw Integration Scaffold

v0.4 Step 5 新增 OpenClaw Integration Scaffold，把 runtime event 形态包装到上一层：

```text
OpenClaw runtime event
  -> normalize_openclaw_event(...)
  -> channel_adapter.handle_channel_message(...)
  -> format_openclaw_response(...)
  -> reply 或 handoff_payload
```

示例：

```bash
python3 agents/fitness/run_openclaw_integration_demo.py
python3 agents/fitness/tools/fitness_openclaw_cli.py text \
  --text "今天晚上练臀，怎么吃？" \
  --channel wechat \
  --sender demo_user \
  --conversation conv_demo
```

当前是 integration scaffold，不是真实 OpenClaw runtime binding；真实接入时，需要把 runtime event 适配到 `handle_openclaw_event(...)`。

## Food Photo Logging Demo

v0.4 Step 1 新增 Food Photo Demo Adapter，Step 2 扩展为可替换 Vision Provider Adapter，用来展示更低成本的 meal logging 入口：

```text
本地食物图片
  -> demo/manual/auto provider
  -> 统一结构化 food analysis
  -> 热量区间 + 蛋白质粗估
  -> 置信度 + 不确定因素
  -> 用户确认/纠错入口
  -> 写入当日 meal log
```

示例：

```text
牛肉面图片
  -> 牛肉面 / 面食类
  -> 600-850 kcal
  -> 蛋白约 25g
  -> 置信度中
  -> 不确定：面量、是否喝汤、是否有额外配菜
```

核心价值不是“高精度视觉识别”，而是“让用户先低成本开始记录，并保留修正入口”。

Provider 边界：

- `demo` 保证作品集和测试稳定；
- `manual` 支持无 API key 的真实图片录屏；
- `vision_api` 是可替换接口占位，不默认调用外部 API；
- `auto` 在 `vision_api` 不可用时明确 fallback，不把失败伪装成成功。

## 最亮的产品闭环

```text
用户说：“以后练前别推荐酸奶，我会胃不舒服”
  -> 系统生成 safety_boundary candidate
  -> candidate 去重并累积 evidence_count
  -> admin approve
  -> 写入 active preference
  -> 用户再问：“今天晚上练臀，怎么吃”
  -> 推荐中自动避开酸奶
```

这证明记忆不是静态存储，而是真的影响 Agent 后续行为。

## 边界

- 不做医疗建议。
- 不默认主动提醒。
- recall 必须 opt-in。
- sensitive memory 不自动 approve。
- non-fitness 输入 fallback。
- 不把单次饮食乱记成长期偏好。
- Food Photo 当前是可替换 provider adapter，不是高精度视觉识别系统。
- Channel Adapter 当前是本地 message router contract，不是真实微信/OpenClaw runtime binding。
- OpenClaw Integration 当前是 scaffold，不调用真实 runtime，也不发送消息。
- 不接真实 OpenClaw / 微信 channel dispatcher。
- 不接 scheduler / cron。
- 不接外部 API、复杂营养数据库、图片分割、数据库或可穿戴设备数据。
