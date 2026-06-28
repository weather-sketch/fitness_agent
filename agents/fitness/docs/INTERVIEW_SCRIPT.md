# Fitness Agent v0.1 Interview Script

## Two-Minute Version

I built a v0.1 Fitness Agent as a vertical sub-agent inside OpenClaw. The motivation was that a simple calorie skill is too narrow: when someone asks "I am training glutes tonight, what should I eat?", the right answer depends on training timing, intensity, recovery, protein, and the risk of falling off logging after overeating.

So I split the system into clear layers. The skill file is only the workflow instruction layer. A rule-based router detects fitness intent. A handler is the single message entry point for OpenClaw-style messages. The actual behavior lives in deterministic tools, and state lives in local JSON files for profile, daily state, cycle state, recall state, and memory candidates.

The main demo has five flows: training-day nutrition planning, meal logging with dynamic adjustment, post-workout meal advice, lapse recovery after overeating, and a lightweight weekly review. There is also a routed demo that shows which messages are handled and which get handed back to the main agent.

The product design point I care about most is that it is not a prompt-only wellness chatbot. It has state, tools, routing, tests, and safety boundaries. It also avoids shame-based feedback: if the user says they ate too much and do not want to log, the agent shifts to recovery mode instead of asking for perfect tracking.

For v0.1, I deliberately did not add scheduler, external APIs, image recognition, or real channel routing. The next step would be a minimal OpenClaw channel binding that calls the handler and falls back when `handled=False`, then integration tests before adding proactive recall.

## Thirty-Second Version

Fitness Agent is a local OpenClaw sub-agent for training-aware nutrition and recovery. It is more than calorie logging: it tracks training context, meal state, recovery, lapse recovery, and weekly review. I built deterministic tools, local JSON state, a router, a unified handler, demos, and tests. v0.1 is intentionally scoped: no scheduler, no external API, no image recognition. The value is a clear vertical-agent architecture that can be safely routed from the main agent later.

## Follow-Up: Why Not Just Use One Skill?

A skill is good for instructions, but it should not become the state store or business-logic engine. If all behavior lived in the skill prompt, state updates would be harder to test and easy to drift. Here the skill only explains the workflow. Routing, state updates, and replies go through deterministic Python tools, which makes the behavior inspectable and testable.

## Follow-Up: OpenClaw Already Has Memory/State. What Is The Design Value?

OpenClaw memory and state are useful platform capabilities, but the Fitness Agent still needs a domain-specific state model. Daily training context, calorie budget, protein gap, lapse risk, recovery need, and weekly review counters are not generic memory entries. The value is deciding what belongs in short-term state, what might become a memory candidate, and what should wait for future recall scheduling.

## Follow-Up: How Would You Evaluate Whether This Agent Is Effective?

For v0.1, I would evaluate correctness and safety first: routing accuracy on common messages, whether state changes match the intent, whether replies avoid unsafe or shaming language, and whether unknown inputs are handed off. For later versions, I would look at user-level behavior: logging continuity, recovery after over-budget days, training-day meal preparedness, and whether weekly reviews lead to one actionable next-week focus.

## Follow-Up: How Would You Productize This Next?

I would start with the smallest channel integration: main Agent routes fitness-domain messages to `handle_fitness_message(...)`, sends the reply, and falls back on `handled=False`. Then I would add integration tests, a simple user/channel mapping, and only after that consider opt-in scheduler-based recall. External APIs or image recognition should come later, after the local state and safety behavior are stable.
