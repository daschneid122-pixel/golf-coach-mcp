"""
golf-coach-mcp
==============

A stateless MCP server that turns the host LLM (Claude, etc.) into a golf coach.

Tools are organized into four areas:
  1. Swing analysis  — rubrics + ball-flight diagnosis
  2. Practice & drills — structured plans, drill library, warm-ups
  3. Round stats — aggregate a list of rounds into useful numbers
  4. Course strategy — club selection (wind / lie / elevation adjusted) + risk-tiered shot plans

Run with:  python server.py        (stdio transport, default)
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("golf-coach")


# ---------------------------------------------------------------------------
# 1. Swing analysis
# ---------------------------------------------------------------------------

_SWING_CHECKPOINTS: dict[str, list[dict[str, str]]] = {
    "address": [
        {"checkpoint": "Stance width", "good": "Driver: outside shoulders. Iron: shoulder-width. Wedge: narrower.", "fault": "Too wide restricts rotation; too narrow loses balance."},
        {"checkpoint": "Posture", "good": "Hinge from hips, neutral spine, arms hanging under shoulders.", "fault": "C-posture (slouched) or S-posture (over-arched) limits rotation."},
        {"checkpoint": "Ball position", "good": "Driver: inside lead heel. Mid-iron: center. Wedge: slightly back.", "fault": "Too far forward = thin / weak right miss. Too far back = fat / push."},
        {"checkpoint": "Grip pressure", "good": "3-4 out of 10. Hands work as a unit.", "fault": "Death grip kills tempo and clubhead speed."},
    ],
    "takeaway": [
        {"checkpoint": "First 18 inches", "good": "Club, hands, arms, chest move together. Clubhead outside hands at 9 o'clock, shaft parallel to target line.", "fault": "Hands inside / club rolling open = stuck behind, blocks and hooks."},
        {"checkpoint": "Lead arm", "good": "Connected to chest, no early lift.", "fault": "Lead arm separating from chest pushes the club inside."},
    ],
    "top": [
        {"checkpoint": "Shoulder turn", "good": "~90° lead-shoulder turn under chin (irons), even more for driver.", "fault": "Short turn reduces width and power; over-turn collapses lead arm."},
        {"checkpoint": "Wrist position", "good": "Lead wrist flat or slightly bowed.", "fault": "Cupped lead wrist = open face = slice."},
        {"checkpoint": "Weight", "good": "~70-80% on lead-side instep (driver) / similar (iron with stable lower body).", "fault": "Reverse pivot (weight stays forward) destroys sequence."},
    ],
    "transition": [
        {"checkpoint": "Sequence", "good": "Lower body initiates: lead hip clears, then torso, arms, club.", "fault": "Arms-first (casting) sheds lag and adds loft."},
        {"checkpoint": "Pressure shift", "good": "Pressure into lead foot before arms drop.", "fault": "Hanging back = thin/fat strikes and high right miss."},
    ],
    "impact": [
        {"checkpoint": "Shaft lean", "good": "Iron: hands ahead of ball, shaft leaning toward target. Driver: shaft slightly back, hitting up.", "fault": "Flipping (hands behind) loses compression."},
        {"checkpoint": "Hip clearance", "good": "Lead hip cleared 30-45° open at impact.", "fault": "Stalled hips = arm flip + pulls/blocks."},
        {"checkpoint": "Head", "good": "Behind the ball at impact (especially driver).", "fault": "Head moves forward past ball = thin, weak strikes."},
    ],
    "follow_through": [
        {"checkpoint": "Finish balance", "good": "Full rotation to target, belt buckle to target, weight 95% on lead foot, can hold finish 3 seconds.", "fault": "Falling back / off-balance signals sequence problem earlier in swing."},
        {"checkpoint": "Arm extension", "good": "Both arms extend toward target post-impact before folding.", "fault": "Chicken-wing lead arm = open face + loss of speed."},
    ],
}


@mcp.tool()
def swing_rubric(
    club: Literal["driver", "iron", "wedge", "putter"] = "iron",
    view: Literal["down-the-line", "face-on", "either"] = "down-the-line",
    handedness: Literal["right", "left"] = "right",
) -> dict[str, Any]:
    """
    Return a structured checkpoint rubric for evaluating a golf swing.

    Use this BEFORE looking at a swing video/image: each checkpoint tells you
    what 'good' looks like and the common fault, so visual analysis stays
    grounded instead of hand-wavy.

    Args:
        club: Club category being analyzed (driver / iron / wedge / putter).
        view: Camera angle (DTL emphasizes plane and path; face-on emphasizes
            ball position, weight shift, shaft lean).
        handedness: Right or left handed.

    Returns:
        A dict with `phases` (address → finish), each containing checkpoints
        with what to look for, what good looks like, and the common fault.
    """
    if club == "putter":
        return {
            "club": club,
            "view": view,
            "handedness": handedness,
            "phases": {
                "setup": [
                    {"checkpoint": "Eyes", "good": "Eyes directly over the ball (or just inside).", "fault": "Eyes outside the ball pulls putts."},
                    {"checkpoint": "Shoulders", "good": "Shoulders parallel to start line.", "fault": "Open shoulders = pull; closed = push."},
                ],
                "stroke": [
                    {"checkpoint": "Tempo", "good": "Backstroke and through-stroke equal length and time (~2:1 time ratio of through:back is common but consistency matters most).", "fault": "Decel through impact = short / pulled putts."},
                    {"checkpoint": "Face", "good": "Face square to start line at impact (start-line dispersion < 1°).", "fault": "Face is ~83% of where the ball starts; tiny rotation = big miss."},
                ],
            },
            "scoring_guidance": "Grade each checkpoint A/B/C with a one-sentence reason and ONE prioritized fix.",
        }
    return {
        "club": club,
        "view": view,
        "handedness": handedness,
        "phases": _SWING_CHECKPOINTS,
        "scoring_guidance": (
            "For each phase, grade the most visible checkpoint A/B/C with a one-line reason. "
            "End with the SINGLE highest-leverage fix — most amateur swings only need one change at a time."
        ),
    }


_BALL_FLIGHT_DIAGNOSIS: dict[str, dict[str, Any]] = {
    "slice": {
        "pattern": "Starts left of target, curves hard right (RH golfer).",
        "primary_causes": [
            "Clubface open to path at impact (the dominant cause).",
            "Out-to-in swing path amplifies the curve.",
            "Weak grip (hands rotated toward target).",
        ],
        "fixes": [
            "Strengthen grip: rotate both hands away from target until you see 2-3 knuckles on lead hand.",
            "Feel the clubface release: practice swings where toe passes heel through impact.",
            "Path drill: place a headcover just outside the ball — swing to miss it (forces in-to-out).",
        ],
    },
    "hook": {
        "pattern": "Starts right of target, curves hard left (RH).",
        "primary_causes": [
            "Clubface closed to path at impact.",
            "Excessively in-to-out path.",
            "Strong grip + active hands through impact.",
        ],
        "fixes": [
            "Weaken the grip slightly (1 knuckle on lead hand visible at address).",
            "Quiet the hands: feel the chest rotating the club through impact, not the wrists.",
            "Path drill: align toe-line right of target, swing along that line — feel a slight 'fade' release.",
        ],
    },
    "push": {
        "pattern": "Starts right and stays right with little curve (RH).",
        "primary_causes": [
            "Path is to the right and face matches it.",
            "Body stalled, arms swinging out without rotation.",
            "Ball position too far back.",
        ],
        "fixes": [
            "Move ball position forward slightly (mid-iron: center).",
            "Drill: feel lead hip clearing aggressively before arms drop.",
            "Check alignment — most pushes are aim issues in disguise.",
        ],
    },
    "pull": {
        "pattern": "Starts left and stays left with little curve (RH).",
        "primary_causes": [
            "Path left of target with face matching it (over-the-top).",
            "Shoulders open at impact.",
            "Ball position too far forward.",
        ],
        "fixes": [
            "Closed-shoulder drill: at address, drop trail shoulder and feel a slight closed alignment.",
            "Tempo: 80% effort to allow lower body to lead.",
            "Move ball back ~1 ball.",
        ],
    },
    "fat": {
        "pattern": "Club hits ground behind ball; weak, short shot.",
        "primary_causes": [
            "Low point is behind the ball — usually weight hanging on trail side at impact.",
            "Early extension or casting from the top.",
            "Ball position too forward for the lie.",
        ],
        "fixes": [
            "Towel drill: place a towel 4 inches behind the ball — clip ball without touching towel.",
            "Pressure drill: at impact feel 80% pressure in lead foot.",
            "Check ball position — if uphill lie, play ball back of normal.",
        ],
    },
    "thin": {
        "pattern": "Strike on the bottom edge — low, hot, sometimes 'screamer'.",
        "primary_causes": [
            "Low point is in front of the ball or you're lifting up through impact.",
            "Trying to 'help' the ball into the air.",
            "Ball position too far back with steep angle of attack.",
        ],
        "fixes": [
            "Trust the loft — feel like you hit DOWN on the ball, divot AFTER ball.",
            "Maintain posture: feel chest covering ball through impact.",
            "Tee drill: tee ball low and brush the tee.",
        ],
    },
    "shank": {
        "pattern": "Strike on the hosel; ball rockets right (RH).",
        "primary_causes": [
            "Club moving outward (away from body) through impact.",
            "Weight on toes / leaning forward.",
            "Anxiety + standing too close at address.",
        ],
        "fixes": [
            "Two-ball drill: place a second ball just outside the target ball — strike inner ball without touching outer.",
            "Stand a half-inch farther from ball; weight in heels.",
            "Slow rehearsal swings — 50% speed for 5 swings before next ball.",
        ],
    },
    "topped": {
        "pattern": "Ball squirts low along the ground.",
        "primary_causes": [
            "Lifting up through impact (loss of posture).",
            "Reverse pivot — weight ending on trail foot.",
            "Ball too far back combined with a sweepy attack.",
        ],
        "fixes": [
            "Maintain spine angle: 'belt buckle stays low' through impact.",
            "Weight forward at finish — full balanced finish.",
            "Practice from a low tee for irons to groove descending strike.",
        ],
    },
    "low_weak": {
        "pattern": "Low trajectory, weak distance — 'knuckleball'.",
        "primary_causes": [
            "De-lofting through flip release that adds dynamic loft variability.",
            "Glancing impact (off-center toward heel/toe).",
            "Slow clubhead speed at impact (deceleration).",
        ],
        "fixes": [
            "Impact bag work: drive into bag with shaft leaning forward, lead wrist flat.",
            "Tempo metronome: 3:1 backswing to downswing, smooth transition.",
            "Foot-spray on face — find true center contact before chasing distance.",
        ],
    },
}


@mcp.tool()
def diagnose_ball_flight(
    pattern: Literal["slice", "hook", "push", "pull", "fat", "thin", "shank", "topped", "low_weak"],
    handedness: Literal["right", "left"] = "right",
    club: Literal["driver", "iron", "wedge"] = "iron",
) -> dict[str, Any]:
    """
    Map a ball-flight pattern to its likely root causes and prioritized fixes.

    Args:
        pattern: The dominant miss pattern (slice, hook, push, pull, fat,
            thin, shank, topped, low_weak).
        handedness: Right or left handed (descriptions are written for RH;
            LH gets directions flipped).
        club: Helps tailor fixes — driver tendencies differ from irons.

    Returns:
        A dict with `pattern`, `description`, `primary_causes`, and a
        prioritized `fixes` list (try the first fix first).
    """
    diag = _BALL_FLIGHT_DIAGNOSIS[pattern]
    note = ""
    if handedness == "left":
        note = "Note: directions in this diagnosis are written for a right-hander. Flip 'right' and 'left' for your perspective."
    if club == "driver" and pattern in ("fat", "thin"):
        note = (note + " ").strip() + "Driver fat/thin usually trace back to ball position and tee height — start there."
    return {
        "pattern": pattern,
        "club": club,
        "handedness": handedness,
        "description": diag["pattern"],
        "primary_causes": diag["primary_causes"],
        "fixes_in_order": diag["fixes"],
        "coaching_note": note or "Start with fix #1 for ~50 reps before adding the next. One change at a time.",
    }


# ---------------------------------------------------------------------------
# 2. Practice plans + drill library
# ---------------------------------------------------------------------------

_DRILL_LIBRARY: list[dict[str, Any]] = [
    {
        "name": "Alignment Stick Gate",
        "fault": ["slice", "hook", "path"],
        "skill": "all",
        "equipment": ["2 alignment sticks"],
        "setup": "Place two sticks on the ground forming a V pointing slightly right of target (RH). Ball at the apex.",
        "execute": "Swing along the inside line, exit along the outside line. 20 reps.",
        "success": "Consistent path through the gate without clipping sticks.",
    },
    {
        "name": "Towel Behind Ball",
        "fault": ["fat", "low point"],
        "skill": "all",
        "equipment": ["small towel"],
        "setup": "Place a folded towel 4 inches behind the ball on a flat lie.",
        "execute": "Hit 15 balls without touching the towel — divot must start AFTER the ball.",
        "success": "10 of 15 strikes leave the towel undisturbed.",
    },
    {
        "name": "Step-Through Driver",
        "fault": ["weight shift", "thin", "topped"],
        "skill": "intermediate+",
        "equipment": ["driver", "tee"],
        "setup": "At address feet together, ball off lead heel.",
        "execute": "Step lead foot toward target as you start the downswing — finish balanced.",
        "success": "Full balanced finish on lead leg, square strike, no fall-back.",
    },
    {
        "name": "Pump Drill",
        "fault": ["over the top", "casting"],
        "skill": "all",
        "equipment": ["any iron"],
        "setup": "Take backswing to top.",
        "execute": "Pump down to halfway 3 times, feeling lower body lead — then swing through.",
        "success": "Sense of arms 'falling' as hips clear; club drops into slot.",
    },
    {
        "name": "Knee-Height Finish",
        "fault": ["chunked wedges", "decel"],
        "skill": "all",
        "equipment": ["wedge"],
        "setup": "30-yard pitch shot, normal setup.",
        "execute": "Backswing to waist height, follow-through to KNEE height matching backswing length.",
        "success": "Pitch lands within 5 yards of target consistently. Builds tempo + commit.",
    },
    {
        "name": "Gate Putting Drill",
        "fault": ["face", "start line"],
        "skill": "all",
        "equipment": ["2 tees"],
        "setup": "Place two tees on ground 1.5 inches apart, just wider than the putter head, 6 feet from a hole.",
        "execute": "Putt 10 balls through the gate without touching tees.",
        "success": "8/10 through clean and holed; trains square face at impact.",
    },
    {
        "name": "9-Ball Window",
        "fault": ["shot shaping", "control"],
        "skill": "advanced",
        "equipment": ["range balls"],
        "setup": "Pick a target. Mentally divide into 9 windows: low/mid/high × draw/straight/fade.",
        "execute": "Hit one ball into each window in sequence with the same club.",
        "success": "Hitting at least 6 of 9 windows on demand — true face/path control.",
    },
    {
        "name": "Slow-Motion Sequence",
        "fault": ["sequencing", "tempo"],
        "skill": "all",
        "equipment": ["any club"],
        "setup": "Empty range bay or mat.",
        "execute": "10 swings at 50% speed, exaggerating lower-body-leads-arms feel. Then 5 at 75%, then 5 at full.",
        "success": "Strike improves and you feel hips clear before arms — re-grooves sequence.",
    },
    {
        "name": "One-Arm Wedge",
        "fault": ["release", "hand action"],
        "skill": "intermediate+",
        "equipment": ["wedge"],
        "setup": "Lead hand only on club, ball teed slightly.",
        "execute": "10 chip-length swings using just the lead arm, focus on rotating chest through.",
        "success": "Crisp contact teaches body-led release, kills the flip.",
    },
    {
        "name": "Ladder Putting",
        "fault": ["distance control"],
        "skill": "all",
        "equipment": ["6 balls"],
        "setup": "On a flat green. No target — just distance.",
        "execute": "Putt 1: 10 ft. Putt 2: 20 ft past 1. Putt 3: 10 ft past 2. Continue alternating ladder.",
        "success": "Each putt within 3 ft of intended distance — pure pace calibration.",
    },
]


@mcp.tool()
def drill_library(
    fault: str | None = None,
    equipment: list[str] | None = None,
    skill: Literal["beginner", "intermediate", "advanced", "all"] = "all",
) -> dict[str, Any]:
    """
    Search the drill library by fault, available equipment, and skill level.

    Args:
        fault: Optional fault keyword (slice, hook, fat, casting, etc.).
            Substring match against drill fault tags.
        equipment: Optional list of equipment the player has. Drills are
            returned only if their requirements are a subset of what's available.
            If omitted, equipment isn't filtered.
        skill: Filter by skill level. 'all' returns drills for any level.

    Returns:
        A dict with `count` and `drills`, each drill containing setup,
        execution, and success criteria.
    """
    have = {e.lower() for e in equipment} if equipment else None
    out = []
    for d in _DRILL_LIBRARY:
        if fault and not any(fault.lower() in f.lower() for f in d["fault"]):
            continue
        if skill != "all" and d["skill"] not in (skill, "all", "intermediate+"):
            continue
        if have is not None:
            need = {e.lower() for e in d["equipment"]}
            generic = {"any club", "any iron", "range balls"}
            need_real = need - generic
            if need_real and not need_real.issubset(have):
                continue
        out.append(d)
    return {"count": len(out), "drills": out}


@mcp.tool()
def practice_plan(
    time_minutes: int = 60,
    skill_level: Literal["beginner", "intermediate", "advanced"] = "intermediate",
    focus_areas: list[str] | None = None,
    facility: Literal["range_only", "range_and_short_game", "full_facility"] = "range_and_short_game",
) -> dict[str, Any]:
    """
    Generate a structured, time-boxed practice plan.

    Args:
        time_minutes: Total minutes available (15-180).
        skill_level: Beginner / intermediate / advanced.
        focus_areas: Optional list like ['driver', 'wedges', 'putting'].
            If omitted, plan is balanced (data-backed allocation: ~65% short game).
        facility: What the player can practice at.

    Returns:
        A dict with `total_minutes` and a list of `blocks`, each with name,
        minutes, intent, and concrete reps/structure.
    """
    t = max(15, min(int(time_minutes), 180))
    foci = [f.lower() for f in (focus_areas or [])]

    if facility == "range_only":
        alloc = {"warmup": 0.10, "full_swing": 0.65, "wedges": 0.20, "skill_challenge": 0.05}
    elif facility == "range_and_short_game":
        alloc = {"warmup": 0.10, "full_swing": 0.30, "wedges_chipping": 0.25, "putting": 0.25, "skill_challenge": 0.10}
    else:
        alloc = {"warmup": 0.10, "putting": 0.25, "chipping": 0.20, "wedges": 0.15, "full_swing": 0.20, "bunker": 0.05, "skill_challenge": 0.05}

    if foci:
        boost = 0.15
        weight_to_pull = boost / max(1, len([k for k in alloc if k != "warmup"]))
        for k in list(alloc.keys()):
            if k == "warmup":
                continue
            alloc[k] = max(0.05, alloc[k] - weight_to_pull)
        for f in foci:
            for key in alloc:
                if f in key:
                    alloc[key] = alloc.get(key, 0.0) + boost
                    break

    total_w = sum(alloc.values())
    minutes = {k: round(t * v / total_w) for k, v in alloc.items()}
    drift = t - sum(minutes.values())
    if drift:
        biggest = max(minutes, key=lambda k: minutes[k])
        minutes[biggest] += drift

    block_recipes = {
        "warmup": "Dynamic stretch (arm swings, hip openers, torso rotations) → 10 putts to feel pace → 10 wedges at 50% effort.",
        "putting": "Ladder drill (4 distances) → Gate drill from 6ft × 10 putts → 3 lag putts from 30ft to a small circle.",
        "chipping": "Land-spot drill: 3 different lies, pick a landing spot, hit 5 from each. Goal: 12/15 inside 6ft.",
        "wedges": "50/75/100 yd targets, 5 balls each, alternating. Track shots inside 15 ft.",
        "wedges_chipping": "Half wedges (40-80yd) × 10 → greenside chips 5 lies × 3.",
        "full_swing": "Block: 8B / 7I / 6I (5 each, alignment sticks). Random: alternate 7I, hybrid, driver — pre-shot routine every ball.",
        "bunker": "10 splash shots to a target (open face, hit sand 2 inches behind ball). Then 5 longer 30-40yd bunker shots.",
        "skill_challenge": "Score-based test: 9-shot drill, par-18 chipping game, or string of 5 made 6-footers — track and beat your number.",
    }

    blocks: list[dict[str, Any]] = []
    for key, m in minutes.items():
        if m <= 0:
            continue
        blocks.append({
            "name": key.replace("_", " ").title(),
            "minutes": m,
            "intent": block_recipes.get(key, "Focused work."),
        })

    skill_note = {
        "beginner": "Stay block-style — same club / same shot until quality is consistent before changing.",
        "intermediate": "End every session with 10 minutes of RANDOM practice (different club every shot) to bridge to the course.",
        "advanced": "Most blocks should be random + with consequences (game / score). Pure block work is for technical changes only.",
    }[skill_level]

    return {
        "total_minutes": t,
        "skill_level": skill_level,
        "facility": facility,
        "focus_areas": foci or "balanced",
        "blocks": blocks,
        "coaching_note": skill_note,
    }


@mcp.tool()
def pre_round_warmup(time_minutes: int = 30) -> dict[str, Any]:
    """
    A pre-round warmup routine. The goal is RHYTHM and CONFIDENCE, not technique.

    Args:
        time_minutes: 15, 30, or 45 — anything else is bucketed to nearest.

    Returns:
        A dict with timed steps from putting → short game → range → 1st-tee routine.
    """
    if time_minutes <= 20:
        bucket = 15
    elif time_minutes <= 37:
        bucket = 30
    else:
        bucket = 45

    plans = {
        15: [
            {"minutes": 5, "step": "Putting", "do": "10 putts at 6ft (build confidence). 5 lag putts to a tee 30ft away."},
            {"minutes": 5, "step": "Range", "do": "5 wedges at 50% → 5 mid-irons → 3 driver. NO swing thoughts."},
            {"minutes": 5, "step": "Short game", "do": "5 chips to a target. Then 3 putts from 4ft."},
        ],
        30: [
            {"minutes": 5, "step": "Putting (pace)", "do": "Ladder drill: putts at 10/20/30/40 ft."},
            {"minutes": 5, "step": "Putting (line)", "do": "10 putts from 4-6 ft. Last 5 must be made in a row."},
            {"minutes": 8, "step": "Range", "do": "5 wedges, 5 mid-iron, 5 long-iron/hybrid, 5 driver — full pre-shot routine each ball."},
            {"minutes": 7, "step": "Short game", "do": "5 chips × 3 different lies. 3 bunker shots."},
            {"minutes": 5, "step": "1st-tee rehearsal", "do": "Visualize 1st tee shot 3 times, hit 3 balls with that exact shot in mind."},
        ],
        45: [
            {"minutes": 5, "step": "Putting (pace)", "do": "Ladder drill 10/20/30/40 ft × 2 sets."},
            {"minutes": 8, "step": "Putting (line)", "do": "Gate drill from 4-8 ft. Finish with 5 in a row from 4 ft."},
            {"minutes": 12, "step": "Range", "do": "Wedge → 9I → 7I → 5I → hybrid → driver (3-5 each), pre-shot routine every ball. Last 3 driver = exact 1st-tee shot."},
            {"minutes": 10, "step": "Short game", "do": "Chip 5 from tight lie, 5 from rough. 5 bunker splashes. 5 pitches 30-50 yds."},
            {"minutes": 5, "step": "Putting (close)", "do": "10 putts from 3-5 ft to walk off feeling perfect."},
            {"minutes": 5, "step": "Mental", "do": "Walk to 1st tee. Breathe. Visualize round. Commit to game plan."},
        ],
    }

    return {
        "total_minutes": bucket,
        "principle": "Warm up to PLAY, not to PRACTICE. No technical work in the last 30 minutes before tee time.",
        "steps": plans[bucket],
    }


# ---------------------------------------------------------------------------
# 3. Round stats — given holes-played JSON, compute aggregates
# ---------------------------------------------------------------------------


def _score_round(holes: list[dict[str, Any]]) -> dict[str, Any]:
    """Internal: compute stats for a single round (no decorator)."""
    if not holes:
        return {"error": "No holes provided."}

    total = sum(h["score"] for h in holes)
    par_total = sum(h["par"] for h in holes)

    fwy_attempts = [h for h in holes if h["par"] != 3 and "fairway_hit" in h]
    fwy_pct = round(100 * sum(1 for h in fwy_attempts if h["fairway_hit"]) / len(fwy_attempts), 1) if fwy_attempts else None

    gir_holes = [h for h in holes if "gir" in h]
    gir_pct = round(100 * sum(1 for h in gir_holes if h["gir"]) / len(gir_holes), 1) if gir_holes else None

    putts_holes = [h for h in holes if "putts" in h]
    total_putts = sum(h["putts"] for h in putts_holes) if putts_holes else None

    gir_putts = [h for h in holes if h.get("gir") and "putts" in h]
    putts_per_gir = round(sum(h["putts"] for h in gir_putts) / len(gir_putts), 2) if gir_putts else None

    scrambling = [h for h in holes if "gir" in h and h["gir"] is False and h["score"] <= h["par"]]
    scrambling_chances = [h for h in holes if h.get("gir") is False]
    scrambling_pct = round(100 * len(scrambling) / len(scrambling_chances), 1) if scrambling_chances else None

    by_par: dict[int, list[int]] = {3: [], 4: [], 5: []}
    for h in holes:
        if h["par"] in by_par:
            by_par[h["par"]].append(h["score"] - h["par"])
    par_avg = {f"par_{p}_avg_vs_par": round(sum(v) / len(v), 2) for p, v in by_par.items() if v}

    takeaways: list[str] = []
    if fwy_pct is not None and fwy_pct < 50:
        takeaways.append(f"Driver was the bottleneck — {fwy_pct}% fairways. Strokes-gained for amateurs scales fastest with off-the-tee accuracy.")
    if gir_pct is not None and gir_pct < 30:
        takeaways.append(f"Approach play needs work — {gir_pct}% GIR. Consider practicing 100-150yd wedges; that's where amateur shots get bled.")
    if putts_per_gir is not None and putts_per_gir > 2.0:
        takeaways.append(f"Putts per GIR is {putts_per_gir} — pace control on lag putts is the fastest fix.")
    if scrambling_pct is not None and scrambling_pct < 30 and scrambling_chances:
        takeaways.append(f"Scrambling {scrambling_pct}% — short game is leaking strokes. Even 50% scrambling is a 4-shot improvement over 30%.")
    if not takeaways:
        takeaways.append("Solid balanced round. Pick the LOWEST stat above and target that area in next 2 practice sessions.")

    return {
        "holes_played": len(holes),
        "total_score": total,
        "par_total": par_total,
        "vs_par": total - par_total,
        "fairways_pct": fwy_pct,
        "gir_pct": gir_pct,
        "total_putts": total_putts,
        "putts_per_gir": putts_per_gir,
        "scrambling_pct": scrambling_pct,
        **par_avg,
        "takeaways": takeaways,
    }


@mcp.tool()
def score_round(holes: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute stats for a single round.

    Args:
        holes: A list of hole dicts. Each hole supports:
            - par (int, required)
            - score (int, required)
            - fairway_hit (bool, optional — irrelevant for par 3s)
            - gir (bool, optional — green in regulation)
            - putts (int, optional)

    Returns:
        Aggregate stats: total, vs par, fairways%, GIR%, putts/round,
        putts/GIR, scrambling%, par-3/4/5 averages, and quick takeaways.
    """
    return _score_round(holes)


@mcp.tool()
def round_stats(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate stats across multiple rounds.

    Args:
        rounds: A list of rounds. Each round is a dict with optional
            metadata (`date`, `course`) and a required `holes` list (same
            shape as `score_round`).

    Returns:
        Aggregate stats across all rounds plus a per-round summary and
        trend (last-3 vs first-3 if available).
    """
    if not rounds:
        return {"error": "No rounds provided."}

    per_round = []
    for r in rounds:
        s = _score_round(r["holes"])
        per_round.append({
            "date": r.get("date"),
            "course": r.get("course"),
            **{k: s[k] for k in ("vs_par", "fairways_pct", "gir_pct", "total_putts", "scrambling_pct") if k in s},
        })

    def avg(key: str) -> float | None:
        vals = [r[key] for r in per_round if r.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    trend = None
    if len(per_round) >= 6:
        first3 = per_round[:3]
        last3 = per_round[-3:]
        def avg_subset(rs: list[dict[str, Any]], key: str) -> float | None:
            vals = [r[key] for r in rs if r.get(key) is not None]
            return round(sum(vals) / len(vals), 1) if vals else None
        trend = {
            "vs_par_first_3_avg": avg_subset(first3, "vs_par"),
            "vs_par_last_3_avg": avg_subset(last3, "vs_par"),
            "delta": (avg_subset(last3, "vs_par") - avg_subset(first3, "vs_par"))
                     if avg_subset(first3, "vs_par") is not None and avg_subset(last3, "vs_par") is not None
                     else None,
        }

    return {
        "rounds_played": len(rounds),
        "averages": {
            "vs_par": avg("vs_par"),
            "fairways_pct": avg("fairways_pct"),
            "gir_pct": avg("gir_pct"),
            "total_putts": avg("total_putts"),
            "scrambling_pct": avg("scrambling_pct"),
        },
        "trend_last_3_vs_first_3": trend,
        "per_round": per_round,
    }


# ---------------------------------------------------------------------------
# 4. Course strategy — club selection + shot strategy
# ---------------------------------------------------------------------------

# Player default carry distances (yards) — sensible mid-handicap defaults.
_DEFAULT_DISTANCES: dict[str, int] = {
    "LW": 70, "SW": 90, "GW": 105, "PW": 120,
    "9I": 130, "8I": 140, "7I": 150, "6I": 160,
    "5I": 170, "4H": 180, "3H": 195, "5W": 210, "3W": 225, "Driver": 250,
}

_CLUB_ORDER = ["LW", "SW", "GW", "PW", "9I", "8I", "7I", "6I", "5I", "4H", "3H", "5W", "3W", "Driver"]


@mcp.tool()
def recommend_club(
    distance_yards: float,
    lie: Literal["tee", "fairway", "light_rough", "heavy_rough", "fairway_bunker", "wet"] = "fairway",
    wind_mph: float = 0,
    wind_direction: Literal["headwind", "tailwind", "crosswind", "none"] = "none",
    elevation_change_ft: float = 0,
    temperature_f: float = 70,
    player_distances: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Recommend a club given conditions and the player's known carry distances.

    Adjustments (industry rules of thumb):
      - Headwind: +1.5 yds per 1 mph effective played distance
      - Tailwind: -1.0 yds per 1 mph
      - Elevation: +1 yd per 1 ft uphill, -1 yd per 1 ft downhill (rough; non-linear past ±50ft)
      - Temperature: ball flies ~2 yds shorter per 10°F below 70°F (denser air)
      - Lie: rough costs ~5-15%, fairway bunker plays one club longer, wet adds ~5%

    Args:
        distance_yards: Raw distance to the target.
        lie: Surface the ball is sitting on.
        wind_mph: Wind speed in mph.
        wind_direction: Headwind, tailwind, crosswind (no distance effect), or none.
        elevation_change_ft: Positive = uphill, negative = downhill.
        temperature_f: Ambient temperature in °F.
        player_distances: Dict of club → carry yards. Falls back to mid-handicap
            defaults if omitted.

    Returns:
        A dict with the adjusted "playing distance", recommended primary club,
        a one-up / one-down option, and the reasoning behind each adjustment.
    """
    dists = {**_DEFAULT_DISTANCES, **(player_distances or {})}

    reasoning: list[str] = []
    played = float(distance_yards)
    reasoning.append(f"Raw distance: {distance_yards:.0f} yds.")

    if wind_direction == "headwind" and wind_mph:
        adj = 1.5 * wind_mph
        played += adj
        reasoning.append(f"+{adj:.0f} yds for {wind_mph} mph headwind.")
    elif wind_direction == "tailwind" and wind_mph:
        adj = 1.0 * wind_mph
        played -= adj
        reasoning.append(f"-{adj:.0f} yds for {wind_mph} mph tailwind.")
    elif wind_direction == "crosswind":
        reasoning.append(f"{wind_mph} mph crosswind: minimal distance effect, but aim adjustment needed.")

    if elevation_change_ft:
        adj = elevation_change_ft
        played += adj
        sign = "+" if adj > 0 else ""
        reasoning.append(f"{sign}{adj:.0f} yds for {elevation_change_ft:+.0f} ft elevation.")

    if temperature_f != 70:
        temp_adj = (70 - temperature_f) * 0.2
        played += temp_adj
        if abs(temp_adj) >= 1:
            sign = "+" if temp_adj > 0 else ""
            reasoning.append(f"{sign}{temp_adj:.1f} yds for temp ({temperature_f:.0f}°F vs 70°F baseline).")

    lie_factor = {
        "tee": 1.0,
        "fairway": 1.0,
        "light_rough": 1.05,   # plays ~5% longer
        "heavy_rough": 1.15,   # ~15% longer + flier risk
        "fairway_bunker": 1.0, # play one MORE club but full carry distance
        "wet": 1.05,
    }.get(lie, 1.0)
    if lie_factor != 1.0:
        before = played
        played = played * lie_factor
        reasoning.append(f"Lie ({lie}) plays ~{(lie_factor - 1) * 100:.0f}% longer: {before:.0f} → {played:.0f} yds.")

    bunker_warning = None
    if lie == "fairway_bunker":
        bunker_warning = "Fairway bunker: take 1 more club than the math suggests, choke down ½ inch, swing 80%."

    primary = None
    primary_gap = float("inf")
    for c in _CLUB_ORDER:
        if c not in dists:
            continue
        gap = abs(dists[c] - played)
        if gap < primary_gap:
            primary_gap = gap
            primary = c

    primary_idx = _CLUB_ORDER.index(primary) if primary else 0
    one_up = _CLUB_ORDER[primary_idx + 1] if primary_idx + 1 < len(_CLUB_ORDER) and _CLUB_ORDER[primary_idx + 1] in dists else None
    one_down = _CLUB_ORDER[primary_idx - 1] if primary_idx - 1 >= 0 and _CLUB_ORDER[primary_idx - 1] in dists else None

    return {
        "raw_distance_yds": distance_yards,
        "playing_distance_yds": round(played, 1),
        "primary_club": primary,
        "primary_carry_yds": dists.get(primary) if primary else None,
        "one_more_club": one_up,
        "one_less_club": one_down,
        "reasoning": reasoning,
        "warnings": [bunker_warning] if bunker_warning else [],
        "rule_of_thumb": "If the playing distance is between two clubs, take the longer one and swing smooth — amateurs miss short ~2x more often than long.",
    }


@mcp.tool()
def shot_strategy(
    par: int,
    distance_to_pin_yds: float,
    lie: Literal["tee", "fairway", "light_rough", "heavy_rough", "fairway_bunker", "trees", "wet"] = "fairway",
    hazards: list[str] | None = None,
    pin_position: Literal["front", "middle", "back", "tucked"] = "middle",
    score_situation: Literal["even", "need_birdie", "protecting_lead"] = "even",
    player_skill: Literal["beginner", "intermediate", "advanced"] = "intermediate",
) -> dict[str, Any]:
    """
    Risk-tiered shot strategy: conservative / standard / aggressive options.

    Args:
        par: Hole par (3, 4, or 5).
        distance_to_pin_yds: Distance to the pin from current position.
        lie: Where the ball is sitting.
        hazards: List of hazards in play, e.g. ["water_right", "OB_left", "front_bunker"].
        pin_position: Where the flag is on the green.
        score_situation: Affects risk weighting.
        player_skill: Affects expected execution probability.

    Returns:
        Three options (conservative / standard / aggressive) with the shot,
        target, expected outcome, and probability that scales with skill.
    """
    hazards = hazards or []

    has_short_hazard = any(h in hazards for h in ("water_short", "front_bunker", "OB_short"))
    is_tucked = pin_position == "tucked"

    skill_multiplier = {"beginner": 0.7, "intermediate": 1.0, "advanced": 1.25}[player_skill]

    options: list[dict[str, Any]] = []

    if lie == "trees":
        options.append({
            "tier": "conservative",
            "shot": "Punch out sideways to fairway with 7-iron at 70%.",
            "target": "Widest part of fairway, leaving a full wedge in.",
            "expected_outcome": "Safe bogey or par save in play.",
            "exec_probability": round(0.85 * skill_multiplier, 2),
            "rationale": "From trees, accept the half-shot loss. The hero shot through a 2-yard gap costs you 1.5 strokes on average.",
        })
        options.append({
            "tier": "standard",
            "shot": "Low runner with 5-iron threading the gap.",
            "target": "Wide miss area short of green.",
            "expected_outcome": "Advance ~150 yds, leaves chip-and-putt for par.",
            "exec_probability": round(0.45 * skill_multiplier, 2),
            "rationale": "Only attempt if the gap is genuinely 5+ yds wide and ground is firm enough to run.",
        })
        return {"par": par, "lie": lie, "options": options, "guidance": "Trees: pick the conservative option unless gap is unmistakable."}

    if par == 3:
        options.append({
            "tier": "conservative",
            "shot": "Club up one, aim for the FAT of the green (center).",
            "target": "Center of green, 30 ft from any edge.",
            "expected_outcome": "On in regulation, two-putt par likely.",
            "exec_probability": round(0.65 * skill_multiplier, 2),
            "rationale": "Par 3s are scored on GIR. Center pin = lowest variance.",
        })
        if is_tucked:
            options.append({
                "tier": "standard",
                "shot": "Aim 15-20 ft to the safe side of the pin.",
                "target": "Safe side of pin, accept long putt.",
                "expected_outcome": "GIR with a 15-25 ft birdie putt.",
                "exec_probability": round(0.50 * skill_multiplier, 2),
                "rationale": "Tucked pin: short-side leave costs 0.5+ strokes vs middle.",
            })
        options.append({
            "tier": "aggressive",
            "shot": "Pin-seeker, full club exact yardage.",
            "target": "5-10 ft of pin.",
            "expected_outcome": "Birdie chance — but short-side miss likely.",
            "exec_probability": round(0.20 * skill_multiplier, 2),
            "rationale": "Only worth it if pin is on a generous side and you NEED a birdie.",
        })

    elif par == 4:
        if lie == "tee":
            if "OB_left" in hazards or "OB_right" in hazards or "water_left" in hazards or "water_right" in hazards:
                options.append({
                    "tier": "conservative",
                    "shot": "3-wood or hybrid into the wide part of the fairway.",
                    "target": "Center fairway, accept ~20 yds shorter.",
                    "expected_outcome": "Fairway, longer approach but no penalty risk.",
                    "exec_probability": round(0.70 * skill_multiplier, 2),
                    "rationale": "OB / water doubles your expected score on the hole. Trade 20 yards for 100% safety.",
                })
            options.append({
                "tier": "standard",
                "shot": "Driver to fat side of fairway.",
                "target": "Aim away from biggest miss-pattern hazard.",
                "expected_outcome": "Fairway with full short-iron approach.",
                "exec_probability": round(0.55 * skill_multiplier, 2),
                "rationale": "Default for most par 4s. Accuracy beats distance for amateurs.",
            })
            options.append({
                "tier": "aggressive",
                "shot": "Driver maxed at the corner / over hazard.",
                "target": "Tightest line that opens the hole.",
                "expected_outcome": "Wedge in if struck — penalty if missed.",
                "exec_probability": round(0.30 * skill_multiplier, 2),
                "rationale": "Only attempt if you NEED the birdie and miss-side is recoverable.",
            })
        else:
            options.append({
                "tier": "conservative",
                "shot": f"Lay-up to your favorite full wedge yardage (~100yd).",
                "target": "Fairway with comfortable wedge in.",
                "expected_outcome": "Bogey worst, par likely with decent wedge.",
                "exec_probability": round(0.75 * skill_multiplier, 2),
                "rationale": "Especially from rough/trees: leave yourself the yardage you PRACTICE.",
            })
            options.append({
                "tier": "standard",
                "shot": f"Approach to fat of green ({distance_to_pin_yds:.0f} yds, center target).",
                "target": "Center of green.",
                "expected_outcome": "GIR with two-putt par.",
                "exec_probability": round(0.45 * skill_multiplier, 2),
                "rationale": "GIR > flag hunting at every skill level under tour pro.",
            })
            if not has_short_hazard and not is_tucked:
                options.append({
                    "tier": "aggressive",
                    "shot": "Attack the pin directly.",
                    "target": "Within 10 ft.",
                    "expected_outcome": "Birdie chance, but short-side miss in play.",
                    "exec_probability": round(0.25 * skill_multiplier, 2),
                    "rationale": "Only if there's no front-side trouble AND the pin isn't tucked.",
                })

    else:  # par 5
        options.append({
            "tier": "conservative",
            "shot": "3 shots to the green: drive → mid-iron lay-up → full wedge in.",
            "target": "Lay-up to your favorite wedge yardage.",
            "expected_outcome": "Par with chance at birdie via wedge.",
            "exec_probability": round(0.78 * skill_multiplier, 2),
            "rationale": "For amateurs, the 'lay-up to your number' par 5 strategy beats going-for-it on average.",
        })
        if distance_to_pin_yds < 240:
            options.append({
                "tier": "standard",
                "shot": "3-wood / hybrid going for the green in 2.",
                "target": "Front edge / fat of green.",
                "expected_outcome": "Eagle putt OR up-and-down for birdie.",
                "exec_probability": round(0.40 * skill_multiplier, 2),
                "rationale": "Worth the attempt if the front is open and miss-area is grass (not water/OB).",
            })
        if has_short_hazard:
            options.append({
                "tier": "aggressive",
                "shot": "Carry the hazard with long club.",
                "target": "Past trouble, on or near green.",
                "expected_outcome": "Eagle look or in the water.",
                "exec_probability": round(0.20 * skill_multiplier, 2),
                "rationale": "Only if you NEED an eagle/birdie. Otherwise the EV is negative.",
            })

    if score_situation == "need_birdie":
        recommendation = options[-1] if len(options) >= 2 else options[0]
        bias = "Need-birdie bias: take the most aggressive sensible option."
    elif score_situation == "protecting_lead":
        recommendation = options[0]
        bias = "Protect-lead bias: conservative is mandatory. Make par, make them beat you."
    else:
        recommendation = options[len(options) // 2] if len(options) >= 3 else options[0]
        bias = "Even bias: standard option unless the aggressive line has unusually high probability."

    return {
        "par": par,
        "distance_to_pin_yds": distance_to_pin_yds,
        "lie": lie,
        "pin_position": pin_position,
        "options": options,
        "recommended": recommendation["tier"],
        "score_situation_bias": bias,
        "core_principle": "Decide BEFORE the shot. Commit fully. The worst score comes from a shot played between two ideas.",
    }


# ---------------------------------------------------------------------------
# Prompts — quick-start canned conversations
# ---------------------------------------------------------------------------

@mcp.prompt()
def coach_my_swing() -> str:
    """Kick off a swing-coaching conversation."""
    return (
        "I want a swing lesson. Here's what to do:\n"
        "1. Ask me to share a video or photo of my swing (down-the-line and/or face-on).\n"
        "2. Call `swing_rubric` to load the right checkpoints for the club + view.\n"
        "3. Grade each checkpoint A/B/C with one short reason.\n"
        "4. End with the SINGLE highest-leverage fix and a drill from `drill_library` that targets it.\n"
        "Keep it under 250 words. Be specific, not generic."
    )


@mcp.prompt()
def plan_my_practice(time_minutes: int = 60) -> str:
    """Build a personalized practice plan."""
    return (
        f"I have {time_minutes} minutes to practice. Before generating a plan:\n"
        "1. Ask my skill level (beginner/intermediate/advanced) if I haven't said.\n"
        "2. Ask what's leaking strokes lately (driver, irons, wedges, putting).\n"
        "3. Ask my facility (range only / range + short game / full).\n"
        "Then call `practice_plan` and present the time-blocks with a short coaching note at the end."
    )


@mcp.prompt()
def help_me_score() -> str:
    """Per-shot help during a round."""
    return (
        "I'm on the course and need shot help. For each shot I describe, do this:\n"
        "1. Ask any missing info: distance, lie, wind, elevation, hazards, pin position.\n"
        "2. Call `recommend_club` for the math.\n"
        "3. Call `shot_strategy` for the risk tiers.\n"
        "4. Give me ONE recommendation with a one-sentence reason. Don't paralyze me — pick a side."
    )


def main() -> None:
    """Entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
