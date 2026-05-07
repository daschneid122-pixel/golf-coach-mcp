"""Smoke test — exercises every tool with realistic inputs."""
import asyncio
import json
import server


async def main():
    print('=== swing_rubric ===')
    _, r = await server.mcp.call_tool('swing_rubric', {'club': 'iron', 'view': 'down-the-line'})
    print('phases:', list(r['phases'].keys()))

    print('\n=== diagnose_ball_flight (slice) ===')
    _, r = await server.mcp.call_tool('diagnose_ball_flight', {'pattern': 'slice'})
    print('top fix:', r['fixes_in_order'][0])

    print('\n=== drill_library (fault=slice) ===')
    _, r = await server.mcp.call_tool('drill_library', {'fault': 'slice', 'equipment': ['2 alignment sticks']})
    print('count:', r['count'], '| first:', r['drills'][0]['name'] if r['drills'] else None)

    print('\n=== practice_plan (60 min, focus=putting) ===')
    _, r = await server.mcp.call_tool('practice_plan', {'time_minutes': 60, 'focus_areas': ['putting']})
    print('total:', r['total_minutes'], '| blocks:', [(b['name'], b['minutes']) for b in r['blocks']])

    print('\n=== pre_round_warmup (30) ===')
    _, r = await server.mcp.call_tool('pre_round_warmup', {'time_minutes': 30})
    print('steps:', [s['step'] for s in r['steps']])

    print('\n=== score_round ===')
    holes = [
        {'par': 4, 'score': 5, 'fairway_hit': True, 'gir': False, 'putts': 2},
        {'par': 3, 'score': 3, 'gir': True, 'putts': 2},
        {'par': 5, 'score': 7, 'fairway_hit': False, 'gir': False, 'putts': 3},
        {'par': 4, 'score': 4, 'fairway_hit': True, 'gir': True, 'putts': 2},
    ]
    _, r = await server.mcp.call_tool('score_round', {'holes': holes})
    summary = {k: v for k, v in r.items() if k != 'takeaways'}
    print(json.dumps(summary, indent=2))

    print('\n=== round_stats (2 rounds) ===')
    _, r = await server.mcp.call_tool('round_stats', {'rounds': [{'date': '2026-04-20', 'holes': holes}, {'date': '2026-04-26', 'holes': holes}]})
    print('averages:', r['averages'])

    print('\n=== recommend_club (165yd, 10mph headwind, +20ft, 60F) ===')
    _, r = await server.mcp.call_tool('recommend_club', {
        'distance_yards': 165, 'wind_mph': 10, 'wind_direction': 'headwind',
        'elevation_change_ft': 20, 'temperature_f': 60, 'lie': 'fairway'
    })
    print('playing_dist:', r['playing_distance_yds'], '| club:', r['primary_club'])
    print('reasoning:')
    for line in r['reasoning']:
        print('  -', line)

    print('\n=== shot_strategy (par 4 tee, OB right) ===')
    _, r = await server.mcp.call_tool('shot_strategy', {
        'par': 4, 'distance_to_pin_yds': 390, 'lie': 'tee',
        'hazards': ['OB_right'], 'pin_position': 'middle', 'player_skill': 'intermediate'
    })
    print('options:', [(o['tier'], o['exec_probability']) for o in r['options']])
    print('recommended:', r['recommended'])

    print('\n=== shot_strategy (par 3, tucked pin, need_birdie) ===')
    _, r = await server.mcp.call_tool('shot_strategy', {
        'par': 3, 'distance_to_pin_yds': 165, 'lie': 'tee',
        'pin_position': 'tucked', 'score_situation': 'need_birdie', 'player_skill': 'advanced'
    })
    print('options:', [(o['tier'], o['exec_probability']) for o in r['options']])
    print('recommended:', r['recommended'])

    print('\nALL TOOLS OK.')


asyncio.run(main())
