# golf-coach-mcp

A stateless MCP server that turns Claude (or any MCP-aware client) into a golf coach.

It covers the four areas you'd want from a real coach:

1. **Swing analysis** — checkpoint rubrics + ball-flight diagnosis
2. **Practice & drills** — time-boxed plans, a drill library, pre-round warm-ups
3. **Round stats** — aggregate hole-by-hole data into the numbers that actually matter
4. **Course strategy** — wind/elevation/lie-adjusted club selection and risk-tiered shot plans

It has no database and stores nothing. Every tool is a pure function of its inputs, so the host LLM keeps round history in context (or you pass it in).

## Install

```bash
cd golf-coach-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Smoke test:

```bash
python -c "import server; print('tools:', [t.name for t in server.mcp._tool_manager.list_tools()])"
```

## Run

The server speaks MCP over stdio. You don't run it standalone — the client launches it.

### Claude Desktop / Cowork

Add to `claude_desktop_config.json` (macOS path: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "golf-coach": {
      "command": "python",
      "args": ["/absolute/path/to/golf-coach-mcp/server.py"]
    }
  }
}
```

If you're using a venv, point `command` at that venv's python:

```json
"command": "/absolute/path/to/golf-coach-mcp/.venv/bin/python"
```

Restart Claude Desktop. You should see `golf-coach` listed in the MCP tools menu.

### Claude Code

```bash
claude mcp add golf-coach -- /absolute/path/to/golf-coach-mcp/.venv/bin/python /absolute/path/to/golf-coach-mcp/server.py
```

## Tools

| Tool | What it does |
|---|---|
| `swing_rubric` | Returns a checkpoint rubric (address → finish) for the LLM to grade a video/image against. |
| `diagnose_ball_flight` | Maps a miss pattern (slice, hook, fat, shank…) to root causes + ordered fixes. |
| `practice_plan` | Generates a time-boxed plan weighted toward your focus areas + facility. |
| `drill_library` | Search drills by fault keyword, equipment available, and skill level. |
| `pre_round_warmup` | A 15/30/45-minute warmup routine. |
| `score_round` | Computes stats for a single round (vs par, fairways%, GIR%, putts, scrambling, par-3/4/5 averages). |
| `round_stats` | Aggregates many rounds + last-3-vs-first-3 trend. |
| `recommend_club` | Adjusted playing distance from raw distance + wind + elevation + temperature + lie, then picks the club. |
| `shot_strategy` | Conservative / standard / aggressive options with skill-scaled execution probabilities. |

## Prompts

The server registers three prompts the client can surface as quick actions:

- `coach_my_swing` — kick off a swing lesson workflow
- `plan_my_practice` — gather context then call `practice_plan`
- `help_me_score` — on-course per-shot help loop

## Round JSON shape

`score_round` and `round_stats` expect rounds shaped like this:

```json
{
  "date": "2026-04-26",
  "course": "Bethpage Black",
  "holes": [
    {"par": 4, "score": 5, "fairway_hit": true,  "gir": false, "putts": 2},
    {"par": 3, "score": 3,                       "gir": true,  "putts": 2},
    {"par": 5, "score": 6, "fairway_hit": false, "gir": false, "putts": 2}
  ]
}
```

Missing fields are skipped — `score` and `par` are the only required ones.

## Adjustments used by `recommend_club`

Industry rule-of-thumb numbers — feel free to tune:

- Headwind: +1.5 yds per 1 mph
- Tailwind: −1.0 yds per 1 mph
- Elevation: ±1 yd per 1 ft (rough; non-linear past ±50 ft)
- Temperature: ~2 yds shorter per 10°F below 70°F
- Light rough: ~+5% played distance
- Heavy rough: ~+15% played distance
- Wet conditions: ~+5%
- Fairway bunker: take 1 club extra, choke down, swing 80%

## Customizing your distances

Pass your own carry numbers into `recommend_club`:

```json
{
  "distance_yards": 165,
  "wind_mph": 10,
  "wind_direction": "headwind",
  "player_distances": {"7I": 155, "6I": 165, "5I": 175}
}
```

If you don't, the tool uses sensible mid-handicap defaults.

## Extending

The drill library, club-selection rules, and shot-strategy logic are all plain Python data + functions in `server.py`. Add a new drill by appending to `_DRILL_LIBRARY`. Add a new fault to `_BALL_FLIGHT_DIAGNOSIS`. Tune the wind constants directly in `recommend_club`.
