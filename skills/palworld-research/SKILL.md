---
name: palworld-research
description: Answer Palworld questions with up-to-date sourced research. Use for Palworld guide, Pal facts, item, breeding, map/location, patch, build/version, recommendation, and gameplay questions where accuracy, source quality, and current-version awareness matter.
---

# Palworld Research

Use this skill to answer Palworld questions with current sources, clear uncertainty, and practical gameplay reasoning.

## Core Rule

Do not answer precise Palworld facts from memory. For names, stats, work suitability, drops, recipes, locations, spawn points, patch changes, or current-version recommendations, search or query an appropriate source first unless the user explicitly asks for offline brainstorming.

The skill's main value is not stored knowledge. It is source routing, evidence discipline, and practical answer framing.

## Fast Workflow

1. Classify the question:
   - **Version/patch**: update notes, nerfs/buffs, new content.
   - **Paldex facts**: Pal stats, work suitability, elements, skills, drops.
   - **Map/location**: spawn points, resources, bosses, dungeons, eggs, fast travel.
   - **Items/recipes/tech**: crafting, material sources, technology unlocks.
   - **Breeding/calculation**: breeding outcomes, parents, calculators.
   - **Gameplay advice**: base setup, party choice, passives, leveling, route planning.
2. Use the source policy in [references/sources.md](references/sources.md).
3. Decide whether browsing is required:
   - Browse for latest/current/version/map/location/recommendation questions.
   - Browse for any exact fact you are not already verifying with a trusted tool result.
   - Do not browse only when the user explicitly asks for offline reasoning or brainstorming.
4. Prefer structured pages/databases for exact values; use guide/community sources only for recommendations or explanations.
5. Cross-check if the answer affects decisions, uses newly updated content, or sources disagree.
6. Answer with a compact structure:
   - **结论**
   - **依据**
   - **不确定/需确认** when applicable
   - **来源** with links and version/date signals

## Evidence Standards

- Exact numbers require a source or tool result.
- Map coordinates/locations require an interactive map, database page, or explicit source page.
- Patch/version claims require official Steam/Pocketpair source when available.
- Recommendations must distinguish:
  - **事实**: sourced data.
  - **推断**: reasoned from data.
  - **经验**: guide/community consensus.
- If sources conflict, state the conflict and which source is preferred.
- If data may be outdated, say so and include the lookup date.
- Do not turn a weak source into a strong claim. If only guide/community evidence is available, label it as recommendation.
- Do not over-answer. If the user asks a small factual question, keep the answer small and cite only necessary sources.

## Source Count Guidance

- Simple fact: 1 good structured source is enough; 2 if current-version risk is high.
- Version/patch: official source first, plus database/wiki only if explaining resulting data.
- Map/location: 1 map source plus 1 database/wiki page when identifying the entity.
- Recommendation: at least 1 structured data source plus 1 guide/community/official context source when possible.
- Conflict: cite both conflicting sources and choose conservatively.

## Useful Response Patterns

For direct factual questions:

```text
结论：...

依据：
- ...

来源：
- ...
```

For recommendations:

```text
结论：...

为什么：
- 数据事实：...
- 玩法推断：...
- 可选替代：...

不确定/需确认：...
来源：...
```

For location/map questions:

```text
结论：...

位置/路线：
- ...

注意：
- 地图数据更新时间：...
- 如果来源没有精确坐标，不能编坐标。
```

For source conflicts:

```text
结论：暂时采用 ...，但置信度为中/低。

冲突：
- 来源 A 显示 ...
- 来源 B 显示 ...

采用理由：...
建议：如果这会影响路线/培养决策，进游戏或查看地图站再确认一次。
来源：...
```

## Refusal / Limitation Behavior

Say you cannot confirm when:

- no source gives the requested exact value;
- a map source gives only a rough area but the user asks for exact coordinates;
- a guide recommendation is version-sensitive and no recent source is available;
- the question depends on the user's save file, mod list, server settings, or custom difficulty.

Offer a useful next step instead of stopping, such as asking for level/base location/available Pals or giving a source-backed partial answer.

## When To Read References

- Read [references/sources.md](references/sources.md) before selecting sources or citing pages.
- Read [references/question-types.md](references/question-types.md) when the question mixes multiple types, such as “35级建矿场推荐哪些帕鲁”.
- Read [references/examples.md](references/examples.md) when calibrating answer style or when the user asks a practical recommendation question.
