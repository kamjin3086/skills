# Palworld Source Policy

Use sources by topic. Prefer fresh, official, structured, and directly relevant pages.

## Source Priority

### 1. Official / Version Truth

Use for patch notes, current version, official changes, bug fixes, events, platform notes, and server/API behavior.

- Steam News Hub: `https://store.steampowered.com/news/app/1623730`
- Official changelog posts, e.g. Steam news article pages under `store.steampowered.com/news/app/1623730/view/...`
- Steam Community all news: `https://steamcommunity.com/app/1623730/allnews/`
- Pocketpair official site/social channels when relevant.
- SteamDB patch notes for build/update tracking: `https://steamdb.info/app/1623730/patchnotes/`

Rule: if official and third-party sources differ about a patch, prefer official.

### 2. Structured Databases

Use for Pal facts, items, recipes, skills, breeding, and searchable game data.

- PalDB / Palworld database pages when available.
- Palworld.gg database and tools: `https://palworld.gg/`
- Wiki.gg pages for explanatory context: `https://palworld.wiki.gg/`

Rule: for exact numeric values, prefer structured database tables over prose guides.

### 3. Maps / Location Data

Use for coordinates, spawn points, resources, eggs, dungeons, bosses, fast travel, chests, and route planning.

- TH.GL Palworld interactive maps: `https://palworld.th.gl/`
- Palworld.gg map: `https://palworld.gg/map`
- Map-specific pages such as `https://palworld.th.gl/maps/...`

Rule: never invent coordinates. If the source only gives an area, report an area, not precise coordinates.

### 4. Guides / Community Experience

Use for practical recommendations, builds, passives, base layouts, route choices, and subjective “best” questions.

- Wiki.gg guide/mechanics pages.
- Palworld.gg guides/tools.
- Steam guides, Reddit, YouTube, Bilibili, Game8, or similar guide sites only as secondary support.

Rule: label community/guide material as advice or experience, not game-file fact.

## Freshness Checks

For current-version questions:

1. Search official Steam/Pocketpair first.
2. Check publication or “last updated” date when visible.
3. If a map/database page shows an update date, include it.
4. If the user asks “now/current/latest/today”, browse even if you think you know.

## Freshness Risk Levels

- **High risk**: patch changes, newly added Pals/items/areas, map resources, event content, server/API behavior, meta recommendations. Always browse.
- **Medium risk**: drops, recipes, breeding routes, exact spawn areas. Browse unless a recent trusted source/tool result is available.
- **Low risk**: basic old Pal identity, broad mechanics, terminology. Still cite if the user asks for accuracy.

## Reliability Labels

Use these labels internally and reflect them when useful:

- **官方**: Steam/Pocketpair. Best for what changed, not always complete for exact values.
- **结构化数据**: PalDB, Palworld.gg database, wiki tables, calculators. Best for exact values.
- **地图数据**: interactive maps. Best for location claims if recently updated.
- **百科说明**: wiki prose. Good for mechanics and context.
- **社区经验**: Reddit, Steam guides, videos, forums. Good for tactics and preferences, weak for facts.

## Search Query Patterns

Use targeted searches instead of broad web searches:

```text
site:store.steampowered.com/news/app/1623730 Palworld [topic]
site:steamdb.info/app/1623730/patchnotes Palworld [version/topic]
site:palworld.wiki.gg [Pal/item/mechanic]
site:palworld.gg [Pal/item/map/topic]
site:palworld.th.gl [Pal/resource/location]
```

For Chinese user questions, search both Chinese and English names when possible. If only a Chinese name is given, use a database/wiki page to confirm the English/internal name before searching map or guide sources.

## Citation Style

Use short source bullets:

```text
来源：
- Steam 官方更新：...（发布日期/版本）
- Palworld.gg：...（查询时间）
- TH.GL 地图：...（地图更新时间如可见）
```

Avoid long quotes. Paraphrase unless a short exact wording is necessary.

## Bad Source Handling

Avoid relying on:

- AI-generated SEO pages with no data tables or update dates.
- Pages that do not indicate game version for version-sensitive claims.
- Copied wiki mirrors when the original wiki/database is reachable.
- Old videos/posts for exact current-version recommendations unless explicitly historical.

If only weak sources are available, state that the answer is provisional.
