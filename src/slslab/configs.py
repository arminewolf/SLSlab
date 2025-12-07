from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).parents[2]
DATA_DIR = ROOT_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"


@dataclass(slots=True, frozen=True)
class InputConfig:
    is_master: bool = True
    is_extobj: bool = False
    is_sophisticated: bool = True
    is_fcfs: bool = False
    # Topology
    n_locks: int = 2
    n_segments: int = n_locks + 1
    chambers_per_lock: int = 2  # 1 or 2; second chamber set to 0 if 1

    # Segment geometry (m)
    segment_length_m_range: tuple[int, int] = (12000, 30000)

    # Ships (cm)
    ship_count: int = 6
    ship_distribution_range: tuple[int, int] = (
        50,
        50,
    )  # Other typical distributions over both sides: 30,70 / 70, 30
    ship_length_cm_range: tuple[int, int] = (7000, 11000)  # 70-110 m
    ship_width_cm_range: tuple[int, int] = (950, 1700)  # 9.5-17.0 m

    # Chambers (usable dims in centimeters)
    chamber_length_cm_range: tuple[int, int] = (9000, 14000)
    chamber_width_cm_range: tuple[int, int] = (1100, 2400)
    auto_scale_chambers: bool = (
        True  # ensure each ship fits into at least one chamber per lock
    )

    # Lock operations (minutes)
    fill_time_range: tuple[int, int] = (8, 14)
    empty_time_range: tuple[int, int] = (8, 14)

    # Segment transit durations (minutes)
    speed_up_range: tuple[int, int] = (8, 12)
    speed_down_range: tuple[int, int] = (15, 20)
    duration_factor: int = 2

    # Misc
    buffer_time_min: int = 3
    security_distance_cm: int = 200
    eta_range: tuple[int, int] = (
        5,
        10,
    )  # now the range is the INTERVAL range of the ships entering from the same side
    delay_weight: int = 1000
    wait_weight: int = 10
    seed: int = 42
    out: str = "data-generated.json"


@dataclass(slots=True, frozen=True)
class OutputConfig:
    is_master: bool
    is_sophisticated: bool
    is_fcfs: bool
    is_extobj: bool
    is_latex: bool
    is_json: bool
    raw_max_horizon: int
    raw_buffer_time: int
    raw_security_distance: int
    locations: list[str]
    segments: list[str]
    raw_left_positions: list[int]
    raw_right_positions: list[int]
    locks: list[str]
    num_of_chambers: int
    max_num_of_lockings: int
    raw_lengths_of_chambers: list[list[int]]
    raw_widths_of_chambers: list[list[int]]
    raw_times_for_filling: list[list[int]]
    raw_times_for_emptying: list[list[int]]
    ships: list[str]
    directions: list[int]
    raw_lengths_of_ships: list[int]
    raw_widths_of_ships: list[int]
    raw_durations_for_entering: list[list[int]]
    raw_durations_for_leaving: list[list[int]]
    raw_etas: list[int]
    eta_range: tuple[int, int]
    raw_min_durs: list[list[int]]
    raw_max_durs: list[list[int]]
    max_delay_weight: int
    max_waiting_time_weight: int
    ship_distribution_range: tuple[int, int]
    ship_length_cm_range: tuple[int, int]
    ship_width_cm_range: tuple[int, int]
    seed: int
