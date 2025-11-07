##!/usr/bin/env python3
"""
Simplified configurable JSON data generator for Shipping and Lock Scheduling.

Configurable via CLI:
- --locks, --chambers-per-lock
- --ship-count, --ship-length-range, --ship-width-range
- --chamber-length-range, --chamber-width-range
- --tmin-range, --tmax-range
- --fill-time-range, --empty-time-range
- --segment-length-range, --buffer-time, --security-distance, --eta-range, --seed

Outputs a JSON instance with the fields expected by the input schema.
Validation is intentionally omitted.
"""

import json
import random
import argparse
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


@dataclass
class Config:
    # Topology
    n_locks: int = 2
    n_segments: int = n_locks + 1
    chambers_per_lock: int = 2  # 1 or 2; second chamber set to 0 if 1

    # Segment geometry (m)
    segment_length_m_range: Tuple[int, int] = (12000, 30000)

    # Ships (cm)
    ship_count: int = 6
    ship_distribution_range: tuple[int, int] = (50, 50) # other typical distributions over both sides: 30,70 / 70, 30
    ship_length_cm_range: Tuple[int, int] = (7000, 11000)  # 70-110 m
    ship_width_cm_range: Tuple[int, int] = (950, 1700)  # 9.5-17.0 m

    # Chambers (usable dims in centimeters)
    chamber_length_cm_range: Tuple[int, int] = (9000, 14000)
    chamber_width_cm_range: Tuple[int, int] = (1100, 2400)
    auto_scale_chambers: bool = (
        True  # ensure each ship fits into at least one chamber per lock
    )

    # Lock operations (minutes)
    fill_time_range: Tuple[int, int] = (8, 14)
    empty_time_range: Tuple[int, int] = (8, 14)

    # Segment transit durations (minutes)
    speed_up_range: Tuple[int, int] = (8, 12)
    speed_down_range: Tuple[int, int] = (15, 20)
    duration_factor: int = 2

    # Misc
    buffer_time_min: int = 3
    security_distance_cm: int = 200
    eta_range: Tuple[int, int] = (0, 180)
    delay_weight: int = 1000
    wait_weight: int = 10
    seed: int = 42
    out: str = "gpt5-data-generated.json"


def enum(items: List[str]) -> List[Dict[str, str]]:
    return [{"e": s} for s in items]


def sample_range(rng: Tuple[int, int]) -> int:
    lo, hi = rng
    return random.randint(lo, hi)


def index_range(rng: tuple[int, int], num: int) -> int:
    lh, rh = rng
    return int(round((lh * num) / (lh + rh)))


def factor_range(rng: Tuple[int, int]) -> float:
    lo, hi = rng
    return lo + (hi - lo) * (1.0 - random.random())


def generate_instance(cfg: Config) -> Dict[str, Any]:
    assert cfg.n_locks >= 1, "Need at least one lock"
    assert cfg.ship_count >= 1, "Need at least one ship"
    assert cfg.chambers_per_lock >= 1, "Need at least one chamber"

    n_segments = cfg.n_locks + 1

    random.seed(cfg.seed)

    # Names
    locations = ["S", "T"]
    locks_names = [f"LOCK-{i+1}" for i in range(cfg.n_locks)]
    segments_names = [f"SEG-{i+1}" for i in range(n_segments)]
    ships_names = [f"SHIP-{i+1}" for i in range(cfg.ship_count)]

    # Ship sizes (cm)
    ship_lengths_cm = [
        sample_range(cfg.ship_length_cm_range) for _ in range(cfg.ship_count)
    ]
    ship_widths_cm = [
        sample_range(cfg.ship_width_cm_range) for _ in range(cfg.ship_count)
    ]

    # Chambers per lock (m);
    lock_lengths = []
    raw_lengths_of_chambers, raw_widths_of_chambers = [], []
    raw_times_for_filling, raw_times_for_emptying = [], []
    for _ in range(cfg.n_locks):
        max_length = 0
        lengths, widths = [], []
        fillings, emptyings = [], []
        for _ in range(cfg.chambers_per_lock):
            c_len = sample_range(cfg.chamber_length_cm_range)
            c_w = sample_range(cfg.chamber_width_cm_range)
            f = sample_range(cfg.fill_time_range)
            e = sample_range(cfg.empty_time_range)
            lengths.append(c_len)
            widths.append(c_w)
            fillings.append(f)
            emptyings.append(e)
            if c_len > max_length:
                max_length = c_len
        raw_lengths_of_chambers.append(lengths)
        raw_widths_of_chambers.append(widths)
        raw_times_for_filling.append(fillings)
        raw_times_for_emptying.append(emptyings)
        lock_lengths.append(max_length)
    lock_lengths.append(0)

    # Ensure each ship fits in at least one chamber of each lock (scale chamber 1 if needed)
    if cfg.auto_scale_chambers:
        for li in range(cfg.n_locks):
            for ch in range(cfg.chambers_per_lock):
                usable_len_cm = raw_lengths_of_chambers[li][ch]
                usable_w_cm = raw_widths_of_chambers[li][ch]
                for s in range(cfg.ship_count):
                    if (
                        ship_lengths_cm[s] + cfg.security_distance_cm
                        > usable_len_cm
                    ):
                        raw_lengths_of_chambers[li][ch] = (
                            ship_lengths_cm[s] + cfg.security_distance_cm
                        )
                        usable_len_cm = raw_lengths_of_chambers[li][ch]
                        if lock_lengths[li] < raw_lengths_of_chambers[li][ch]:
                            lock_lengths[li] = raw_lengths_of_chambers[li][ch]
                    if ship_widths_cm[s] > usable_w_cm:
                        raw_widths_of_chambers[li][ch] = ship_widths_cm[s]
                        usable_w_cm = raw_widths_of_chambers[li][ch]

    # Segment positions (contiguous)
    left_positions, right_positions = [], []
    pos = 0
    for p in range(n_segments):
        seg_len = sample_range(cfg.segment_length_m_range)
        left_positions.append(pos)
        right_positions.append(pos + seg_len)
        pos += seg_len + int(round(lock_lengths[p] / 100, 0))

    # Directions alternate: 1 (down) / -1 (up)
    # directions = [1 if i % 2 == 0 else -1 for i in range(cfg.ship_count)]

    directions = [
        1 if i < index_range(cfg.ship_distribution_range, cfg.ship_count) else -1
        for i in range(cfg.ship_count)
    ]

    # ETAs
    # raw_etas = [sample_range(cfg.eta_range) for _ in range(cfg.ship_count)]

    raw_etas = []
    lh = 0
    rh = 0
    for s in range(cfg.ship_count):
        if s < index_range(cfg.ship_distribution_range, cfg.ship_count):
            raw_etas.append(lh)
            lh = lh + sample_range(cfg.eta_range)
        else:
            raw_etas.append(rh)
            rh = rh + sample_range(cfg.eta_range)

    # Enter/leave times per ship per lock (simple size-based heuristic)
    def enter_leave_time(length_cm: int, width_cm: int) -> Tuple[int, int]:
        base = 2
        add_len = max(0, length_cm // 4000)  # +1 per ~40m
        add_w = max(0, width_cm // 800)  # +1 per ~8m
        return base + add_len + add_w, base + add_len

    raw_durs_entering, raw_durs_leaving = [], []
    for s in range(cfg.ship_count):
        e_row, l_row = [], []
        e_base, l_base = enter_leave_time(
            ship_lengths_cm[s], ship_widths_cm[s]
        )
        for _ in range(cfg.n_locks):
            e_row.append(e_base + random.randint(0, 1))
            l_row.append(l_base + random.randint(0, 1))
        raw_durs_entering.append(e_row)
        raw_durs_leaving.append(l_row)

    # Segment transit durations per ship (tmin/tmax ranges)
    raw_min_durs, raw_max_durs = [], []
    for s in range(cfg.ship_count):
        min_row, max_row = [], []
        for p in range(n_segments):
            if directions[s] == 1:
                t_min = int(
                    round(
                        60.0
                        * (right_positions[p] - left_positions[p])
                        / (1000.0 * factor_range(cfg.speed_up_range)),
                        0,
                    )
                )
            else:  # directions[s] == -1:
                t_min = int(
                    round(
                        60.0
                        * (right_positions[p] - left_positions[p])
                        / (1000.0 * factor_range(cfg.speed_down_range)),
                        0,
                    )
                )
            t_max = cfg.duration_factor * t_min
            min_row.append(t_min)
            max_row.append(t_max)
        raw_min_durs.append(min_row)
        raw_max_durs.append(max_row)

    # Horizon (rough but safe)
    # longest_route_max = max((sum(row) for row in raw_max_durs), default=0)
    # max_fill = max((max(row) for row in raw_times_for_filling), default=0)
    # max_empty = max((max(row) for row in raw_times_for_emptying), default=0)
    # max_enter = max((max(row) for row in raw_durs_entering), default=0)
    # max_leave = max((max(row) for row in raw_durs_leaving), default=0)
    # per_lock_overhead = (
    #     max_fill + max_empty + max_enter + max_leave + 2 * cfg.buffer_time_min
    # )
    # horizon = max(raw_etas) + longest_route_max + cfg.n_locks * per_lock_overhead + 120
    horizon = 1440  # 24 hours
    # Assemble instance
    instance = {
        "isMaster": False,
        "isSophisticated": True,
        "isFCFS": False,
        "isExtObj": False,
        "isLaTeX": False,
        "isJSON": True,
        "rawMaxHorizon": int(horizon),
        "rawBufferTime": int(cfg.buffer_time_min),
        "rawSecurityDistance": int(cfg.security_distance_cm),
        "locations": enum(locations),
        "segments": enum(segments_names),
        "rawLeftPositions": left_positions,
        "rawRightPositions": right_positions,
        "locks": enum(locks_names),
        "numOfChambers": int(cfg.chambers_per_lock),
        "maxNumOfLockings": max(1, cfg.ship_count + 5),
        "rawLengthsOfChambers": raw_lengths_of_chambers,
        "rawWidthsOfChambers": raw_widths_of_chambers,
        "rawTimesForFilling": raw_times_for_filling,
        "rawTimesForEmptying": raw_times_for_emptying,
        "ships": enum(ships_names),
        "directions": directions,
        "rawLengthsOfShips": ship_lengths_cm,
        "rawWidthsOfShips": ship_widths_cm,
        "rawDurationsForEntering": raw_durs_entering,
        "rawDurationsForLeaving": raw_durs_leaving,
        "rawEtas": raw_etas,
        "rawMinDurs": raw_min_durs,
        "rawMaxDurs": raw_max_durs,
        "maxDelayWeight": 1000,
        "maxWaitingTimeWeight": 1,
    }
    return instance


def parse_args() -> Config:
    p = argparse.ArgumentParser(description="Simplified generator for shipping and lock scheduling JSON instances")
    p.add_argument("--locks", type=int, default=2)
    p.add_argument("--chambers-per-lock", type=int, default=2)
    p.add_argument("--segment-length-range", nargs=2, type=int, default=(12000, 30000))
    p.add_argument("--ship-count", type=int, default=6)
    p.add_argument("--ship-distribution-range", nargs=2, type=int, default=(50, 50))
    p.add_argument("--ship-length-range", nargs=2, type=int, default=(7000, 11000))
    p.add_argument("--ship-width-range", nargs=2, type=int, default=(950, 1700))
    p.add_argument("--chamber-length-range", nargs=2, type=int, default=(9000, 14000))
    p.add_argument("--chamber-width-range", nargs=2, type=int, default=(1100, 2400))

    p.add_argument(
        "--no-auto-scale-chambers",
        action="store_true",
        help="disable auto scaling to fit ships",
    )

    p.add_argument("--fill-time-range", nargs=2, type=int, default=(8, 14))
    p.add_argument("--empty-time-range", nargs=2, type=int, default=(8, 14))

    p.add_argument("--speed-up-range", nargs=2, type=int, default=(8, 12))
    p.add_argument("--speed-down-range", nargs=2, type=int, default=(15, 20))
    p.add_argument("--duration-factor", type=int, default=2)

    p.add_argument("--buffer-time", type=int, default=3)
    p.add_argument("--security-distance", type=int, default=200)
    p.add_argument("--eta-range", nargs=2, type=int, default=(3, 10))
    p.add_argument("--delay-weight", type=int, default=42)
    p.add_argument("--wait-weight", type=int, default=42)

    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=str, default="gpt5-generated-input.json")

    args = p.parse_args()
    return Config(
        n_locks=args.locks,
        chambers_per_lock=args.chambers_per_lock,
        segment_length_m_range=tuple[int, int](args.segment_length_range),
        ship_count=args.ship_count,
        ship_distribution_range=args.ship_distribution_range,
        ship_length_cm_range=tuple[int, int](args.ship_length_range),
        ship_width_cm_range=tuple[int, int](args.ship_width_range),
        chamber_length_cm_range=tuple[int, int](args.chamber_length_range),
        chamber_width_cm_range=tuple[int, int](args.chamber_width_range),
        auto_scale_chambers=not args.no_auto_scale_chambers,
        fill_time_range=tuple[int, int](args.fill_time_range),
        empty_time_range=tuple[int, int](args.empty_time_range),
        speed_up_range=tuple[int, int](args.speed_up_range),
        speed_down_range=tuple[int, int](args.speed_down_range),
        duration_factor=args.duration_factor,
        buffer_time_min=args.buffer_time,
        security_distance_cm=args.security_distance,
        eta_range=tuple[int, int](args.eta_range),
        delay_weight=args.delay_weight,
        wait_weight=args.wait_weight,
        seed=args.seed,
        out=args.out,
    )


def main():
    cfg = parse_args()
    instance = generate_instance(cfg)
    # print(json.dumps(instance, indent=2))
    with open(cfg.out, "w", encoding="utf-8") as json_file:
        # Use json.dump() to write the data to the file
        # ensure_ascii=False ensures non-ASCII characters are written directly
        json.dump(instance, json_file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
