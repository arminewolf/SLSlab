import random
from typing import Any
from dataclasses import dataclass

from .configs import InputConfig, OutputConfig

@dataclass(slots=True)
class Chambers:
    lock_lengths: list[int]
    lengths: list[list[int]]
    widths: list[list[int]]
    fill_times: list[list[int]]
    empty_times: list[list[int]]


class InstanceGenerator:
    def __init__(self, input_config: InputConfig):
        self.input_config = input_config
        self.output_config = self.generate_output_config()

    @staticmethod
    def _enum(items: list[str]) -> list[dict[str, str]]:
        return [{"e": s} for s in items]

    @staticmethod
    def _sample_range(rng: tuple[int, int]) -> int:
        lo, hi = rng
        return random.randint(lo, hi)

    @staticmethod
    def _index_range(rng: tuple[int, int], num: int) -> int:
        lh, rh = rng
        return int(round((lh * num) / (lh + rh)))

    @staticmethod
    def _factor_range(rng: tuple[int, int]) -> float:
        lo, hi = rng
        return lo + (hi - lo) * (1.0 - random.random())

    # Enter/leave times per ship per lock (simple size-based heuristic)
    @staticmethod
    def _enter_leave_time(length_cm: int, width_cm: int) -> tuple[int, int]:
        base = 2
        add_len = max(0, length_cm // 4000)  # +1 per ~40m
        add_w = max(0, width_cm // 800)  # +1 per ~8m
        return base + add_len + add_w, base + add_len

    def return_instance(self) -> dict[str, Any]:
        return self.output_config.to_instance()
    
    def _create_ship_length_cm_range(self):
        return [self._sample_range(self.input_config.ship_length_cm_range) for _ in range(self.input_config.ship_count)]

    def _create_ship_width_cm_range(self):
        return [self._sample_range(self.input_config.ship_width_cm_range) for _ in range(self.input_config.ship_count)]

    def _generate_chambers(self) -> Chambers:
        cfg = self.input_config

        lock_lengths = []
        lengths_all, widths_all = [], []
        fills_all, empties_all = [], []

        for _ in range(cfg.n_locks):
            lengths, widths, fills, empties = [], [], [], []

            for _ in range(cfg.chambers_per_lock):
                lengths.append(self._sample_range(cfg.chamber_length_cm_range))
                widths.append(self._sample_range(cfg.chamber_width_cm_range))
                fills.append(self._sample_range(cfg.fill_time_range))
                empties.append(self._sample_range(cfg.empty_time_range))

            lengths_all.append(lengths)
            widths_all.append(widths)
            fills_all.append(fills)
            empties_all.append(empties)
            lock_lengths.append(max(lengths))

        lock_lengths.append(0)

        return Chambers(
            lock_lengths=lock_lengths,
            lengths=lengths_all,
            widths=widths_all,
            fill_times=fills_all,
            empty_times=empties_all,
        )
    
    def _scale_chambers_for_ships(self, chambers: Chambers, ship_lengths: list[int], ship_widths: list[int]) -> None:
        cfg = self.input_config

        for li in range(cfg.n_locks):
            for ch in range(cfg.chambers_per_lock):
                for s in range(cfg.ship_count):
                    required_len = ship_lengths[s] + cfg.security_distance_cm
                    if required_len > chambers.lengths[li][ch]:
                        chambers.lengths[li][ch] = required_len
                        chambers.lock_lengths[li] = max(
                            chambers.lock_lengths[li],
                            required_len,
                        )

                    if ship_widths[s] > chambers.widths[li][ch]:
                        chambers.widths[li][ch] = ship_widths[s]

    def _generate_segments(self, lock_lengths: list[int]) -> tuple[list[int], list[int]]:
        cfg = self.input_config
        left, right = [], []
        pos = 0

        for p in range(cfg.n_locks + 1):
            seg_len = self._sample_range(cfg.segment_length_m_range)
            left.append(pos)
            right.append(pos + seg_len)
            pos += seg_len + int(round(lock_lengths[p] / 100))

        return left, right
    
    def _generate_directions(self) -> list[int]:
        cfg = self.input_config
        split = self._index_range(cfg.ship_distribution_range, cfg.ship_count)
        return [1 if i < split else -1 for i in range(cfg.ship_count)]

    def _generate_etas(self) -> list[int]:
        cfg = self.input_config
        split = self._index_range(cfg.ship_distribution_range, cfg.ship_count)

        etas = []
        lh = rh = 0

        for i in range(cfg.ship_count):
            if i < split:
                etas.append(lh)
                lh += self._sample_range(cfg.eta_range)
            else:
                etas.append(rh)
                rh += self._sample_range(cfg.eta_range)

        return etas
    
    def _generate_enter_leave_durations(self, ship_lengths: list[int], ship_widths: list[int]) -> tuple[list[list[int]], list[list[int]]]:
        cfg = self.input_config
        entering, leaving = [], []
        for s in range(cfg.ship_count):
            e_base, l_base = self._enter_leave_time(ship_lengths[s], ship_widths[s])
            entering.append([e_base + random.randint(0, 1) for _ in range(cfg.n_locks)])
            leaving.append([l_base + random.randint(0, 1) for _ in range(cfg.n_locks)])

        return entering, leaving

    def _generate_segment_durations(self, left_positions: list[int], right_positions: list[int], directions: list[int]) -> tuple[list[list[int]], list[list[int]]]:
        cfg = self.input_config
        n_segments = cfg.n_locks + 1

        min_durs, max_durs = [], []

        for s in range(cfg.ship_count):
            min_row, max_row = [], []

            speed_range = (cfg.speed_up_range if directions[s] == 1 else cfg.speed_down_range)

            for p in range(n_segments):
                length_m = right_positions[p] - left_positions[p]
                t_min = int(round(60.0 * length_m / (1000.0 * self._factor_range(speed_range))))
                min_row.append(t_min)
                max_row.append(cfg.duration_factor * t_min)

            min_durs.append(min_row)
            max_durs.append(max_row)

        return min_durs, max_durs
    
    def _compute_horizon(self, raw_max_durs: list[list[int]], chambers: Chambers, raw_durs_entering: list[list[int]], raw_durs_leaving: list[list[int]]) -> int:
        cfg = self.input_config

        longest_route_max = max((sum(row) for row in raw_max_durs), default=0)
        max_fill = max((max(row) for row in chambers.fill_times), default=0)
        max_empty = max((max(row) for row in chambers.empty_times), default=0)
        max_enter = max((max(row) for row in raw_durs_entering), default=0)
        max_leave = max((max(row) for row in raw_durs_leaving), default=0)

        per_lock_overhead = (
            max_fill
            + max_empty
            + max_enter
            + max_leave
            + 2 * cfg.buffer_time_min
        )
        # return max(raw_etas) + longest_route_max + cfg.n_locks * per_lock_overhead + 120
        # Keep your fixed horizon for now
        return 1440
    
    def generate_output_config(self) -> OutputConfig:
        assert self.input_config.n_locks >= 1, "Need at least one lock"
        assert self.input_config.ship_count >= 1, "Need at least one ship"
        assert self.input_config.chambers_per_lock >= 1, "Need at least one chamber"

        n_segments = self.input_config.n_locks + 1

        random.seed(self.input_config.seed)

        # Names
        locations = ["S", "T"]
        locks_names = [f"LOCK-{i+1}" for i in range(self.input_config.n_locks)]
        segments_names = [f"SEG-{i+1}" for i in range(n_segments)]
        ships_names = [f"SHIP-{i+1}" for i in range(self.input_config.ship_count)]

        # Ship sizes (cm)
        ship_lengths_cm = self._create_ship_length_cm_range()
        ship_widths_cm = self._create_ship_width_cm_range()

        # Chambers per lock (cm);
        chambers = self._generate_chambers()

        # Ensure each ship fits in at least one chamber of each lock (scale chamber 1 if needed)
        if self.input_config.auto_scale_chambers:
            self._scale_chambers_for_ships(chambers, ship_lengths_cm, ship_widths_cm)

        # Segment positions (contiguous)
        left_positions, right_positions = self._generate_segments(chambers.lock_lengths)

        # Directions alternate: 1 (down) / -1 (up)
        directions = self._generate_directions()

        # ETAs
        raw_etas = self._generate_etas()

        # Enter/leave durations per ship per lock
        raw_durs_entering, raw_durs_leaving = self._generate_enter_leave_durations(ship_lengths_cm, ship_widths_cm)

        # Segment transit durations per ship (tmin/tmax ranges)
        raw_min_durs, raw_max_durs = self._generate_segment_durations(left_positions, right_positions, directions)  

        # Horizon (rough but safe)
        horizon = self._compute_horizon(raw_max_durs, chambers, raw_durs_entering, raw_durs_leaving)
        
        # Assemble instance
        return OutputConfig(
            is_master=self.input_config.is_master,
            is_sophisticated=self.input_config.is_sophisticated,
            is_fcfs=self.input_config.is_fcfs,
            is_extobj=self.input_config.is_extobj,
            is_latex=False,
            is_json=True,
            raw_max_horizon=int(horizon),
            raw_buffer_time=int(self.input_config.buffer_time_min),
            raw_security_distance=int(self.input_config.security_distance_cm),
            locations=self._enum(locations),
            segments=self._enum(segments_names),
            raw_left_positions=left_positions,
            raw_right_positions=right_positions,
            locks=self._enum(locks_names),
            num_of_chambers=int(self.input_config.chambers_per_lock),
            max_num_of_lockings=max(1, self.input_config.ship_count + 5),
            raw_lengths_of_chambers=chambers.lengths,
            raw_widths_of_chambers=chambers.widths,
            raw_times_for_filling=chambers.fill_times,
            raw_times_for_emptying=chambers.empty_times,
            ships=self._enum(ships_names),
            directions=directions,
            raw_lengths_of_ships=ship_lengths_cm,
            raw_widths_of_ships=ship_widths_cm,
            raw_durations_for_entering=raw_durs_entering,
            raw_durations_for_leaving=raw_durs_leaving,
            raw_etas=raw_etas,
            eta_range=self.input_config.eta_range,
            raw_min_durs=raw_min_durs,
            raw_max_durs=raw_max_durs,
            max_delay_weight=1000,
            max_waiting_time_weight=10,
            ship_distribution_range=self.input_config.ship_distribution_range,
            ship_length_cm_range=self.input_config.ship_length_cm_range,
            ship_width_cm_range=self.input_config.ship_width_cm_range,
            seed=self.input_config.seed,
        )
