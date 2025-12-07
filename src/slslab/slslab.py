import random
from typing import Any

from .configs import InputConfig, OutputConfig


class InstanceGenerator:
    def __init__(self, input_config: InputConfig):
        self.input_config = input_config
        self.output_config = self.generate_output_config()

    def _enum(self, items: list[str]) -> list[dict[str, str]]:
        return [{"e": s} for s in items]

    def _sample_range(self, rng: tuple[int, int]) -> int:
        lo, hi = rng
        return random.randint(lo, hi)

    def _index_range(self, rng: tuple[int, int], num: int) -> int:
        lh, rh = rng
        return int(round((lh * num) / (lh + rh)))

    def _factor_range(self, rng: tuple[int, int]) -> float:
        lo, hi = rng
        return lo + (hi - lo) * (1.0 - random.random())

    # Enter/leave times per ship per lock (simple size-based heuristic)
    def _enter_leave_time(
        self, length_cm: int, width_cm: int
    ) -> tuple[int, int]:
        base = 2
        add_len = max(0, length_cm // 4000)  # +1 per ~40m
        add_w = max(0, width_cm // 800)  # +1 per ~8m
        return base + add_len + add_w, base + add_len

    def generate_output_config(self) -> OutputConfig:
        assert self.input_config.n_locks >= 1, "Need at least one lock"
        assert self.input_config.ship_count >= 1, "Need at least one ship"
        assert (
            self.input_config.chambers_per_lock >= 1
        ), "Need at least one chamber"

        n_segments = self.input_config.n_locks + 1

        random.seed(self.input_config.seed)

        # Names
        locations = ["S", "T"]
        locks_names = [f"LOCK-{i+1}" for i in range(self.input_config.n_locks)]
        segments_names = [f"SEG-{i+1}" for i in range(n_segments)]
        ships_names = [
            f"SHIP-{i+1}" for i in range(self.input_config.ship_count)
        ]

        # Ship sizes (cm)
        ship_lengths_cm = [
            self._sample_range(self.input_config.ship_length_cm_range)
            for _ in range(self.input_config.ship_count)
        ]
        ship_widths_cm = [
            self._sample_range(self.input_config.ship_width_cm_range)
            for _ in range(self.input_config.ship_count)
        ]

        # Chambers per lock (cm);
        lock_lengths = []
        raw_lengths_of_chambers, raw_widths_of_chambers = [], []
        raw_times_for_filling, raw_times_for_emptying = [], []
        for _ in range(self.input_config.n_locks):
            max_length = 0
            lengths, widths = [], []
            fillings, emptyings = [], []
            for _ in range(self.input_config.chambers_per_lock):
                c_len = self._sample_range(
                    self.input_config.chamber_length_cm_range
                )
                c_w = self._sample_range(
                    self.input_config.chamber_width_cm_range
                )
                f = self._sample_range(self.input_config.fill_time_range)
                e = self._sample_range(self.input_config.empty_time_range)
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
        if self.input_config.auto_scale_chambers:
            for li in range(self.input_config.n_locks):
                for ch in range(self.input_config.chambers_per_lock):
                    usable_len_cm = raw_lengths_of_chambers[li][ch]
                    usable_w_cm = raw_widths_of_chambers[li][ch]
                    for s in range(self.input_config.ship_count):
                        if (
                            ship_lengths_cm[s]
                            + self.input_config.security_distance_cm
                            > usable_len_cm
                        ):
                            raw_lengths_of_chambers[li][ch] = (
                                ship_lengths_cm[s]
                                + self.input_config.security_distance_cm
                            )
                            usable_len_cm = raw_lengths_of_chambers[li][ch]
                            if (
                                lock_lengths[li]
                                < raw_lengths_of_chambers[li][ch]
                            ):
                                lock_lengths[li] = raw_lengths_of_chambers[li][
                                    ch
                                ]
                        if ship_widths_cm[s] > usable_w_cm:
                            raw_widths_of_chambers[li][ch] = ship_widths_cm[s]
                            usable_w_cm = raw_widths_of_chambers[li][ch]

        # Segment positions (contiguous)
        left_positions, right_positions = [], []
        pos = 0
        for p in range(n_segments):
            seg_len = self._sample_range(
                self.input_config.segment_length_m_range
            )
            left_positions.append(pos)
            right_positions.append(pos + seg_len)
            pos += seg_len + int(round(lock_lengths[p] / 100, 0))

        # Directions alternate: 1 (down) / -1 (up)
        directions = [
            (
                1
                if i
                < self._index_range(
                    self.input_config.ship_distribution_range,
                    self.input_config.ship_count,
                )
                else -1
            )
            for i in range(self.input_config.ship_count)
        ]

        # ETAs
        raw_etas = []
        lh = 0
        rh = 0
        for s in range(self.input_config.ship_count):
            if s < self._index_range(
                self.input_config.ship_distribution_range,
                self.input_config.ship_count,
            ):
                raw_etas.append(lh)
                lh = lh + self._sample_range(self.input_config.eta_range)
            else:
                raw_etas.append(rh)
                rh = rh + self._sample_range(self.input_config.eta_range)

        raw_durs_entering, raw_durs_leaving = [], []
        for s in range(self.input_config.ship_count):
            e_row, l_row = [], []
            e_base, l_base = self._enter_leave_time(
                ship_lengths_cm[s], ship_widths_cm[s]
            )
            for _ in range(self.input_config.n_locks):
                e_row.append(e_base + random.randint(0, 1))
                l_row.append(l_base + random.randint(0, 1))
            raw_durs_entering.append(e_row)
            raw_durs_leaving.append(l_row)

        # Segment transit durations per ship (tmin/tmax ranges)
        raw_min_durs, raw_max_durs = [], []
        for s in range(self.input_config.ship_count):
            min_row, max_row = [], []
            for p in range(n_segments):
                if directions[s] == 1:
                    t_min = int(
                        round(
                            60.0
                            * (right_positions[p] - left_positions[p])
                            / (
                                1000.0
                                * self._factor_range(
                                    self.input_config.speed_up_range
                                )
                            ),
                            0,
                        )
                    )
                else:  # directions[s] == -1:
                    t_min = int(
                        round(
                            60.0
                            * (right_positions[p] - left_positions[p])
                            / (
                                1000.0
                                * self._factor_range(
                                    self.input_config.speed_down_range
                                )
                            ),
                            0,
                        )
                    )
                t_max = self.input_config.duration_factor * t_min
                min_row.append(t_min)
                max_row.append(t_max)
            raw_min_durs.append(min_row)
            raw_max_durs.append(max_row)

        # Horizon (rough but safe)
        longest_route_max = max((sum(row) for row in raw_max_durs), default=0)
        max_fill = max((max(row) for row in raw_times_for_filling), default=0)
        max_empty = max(
            (max(row) for row in raw_times_for_emptying), default=0
        )
        max_enter = max((max(row) for row in raw_durs_entering), default=0)
        max_leave = max((max(row) for row in raw_durs_leaving), default=0)
        per_lock_overhead = (
            max_fill
            + max_empty
            + max_enter
            + max_leave
            + 2 * self.input_config.buffer_time_min
        )
        # horizon = max(raw_etas) + longest_route_max + cfg.n_locks * per_lock_overhead + 120
        horizon = 1440  # 24 hours
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
            raw_lengths_of_chambers=raw_lengths_of_chambers,
            raw_widths_of_chambers=raw_widths_of_chambers,
            raw_times_for_filling=raw_times_for_filling,
            raw_times_for_emptying=raw_times_for_emptying,
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

    def return_instance(self) -> dict[str, Any]:
        # Assemble instance
        instance = {
            "isMaster": self.output_config.is_master,
            "isSophisticated": self.output_config.is_sophisticated,
            "isFCFS": self.output_config.is_fcfs,
            "isExtObj": self.output_config.is_extobj,
            "isLaTeX": self.output_config.is_latex,
            "isJSON": self.output_config.is_json,
            "rawMaxHorizon": self.output_config.raw_max_horizon,
            "rawBufferTime": self.output_config.raw_buffer_time,
            "rawSecurityDistance": self.output_config.raw_security_distance,
            "locations": self.output_config.locations,
            "segments": self.output_config.segments,
            "rawLeftPositions": self.output_config.raw_left_positions,
            "rawRightPositions": self.output_config.raw_right_positions,
            "locks": self.output_config.locks,
            "numOfChambers": self.output_config.num_of_chambers,
            "maxNumOfLockings": self.output_config.max_num_of_lockings,
            "rawLengthsOfChambers": self.output_config.raw_lengths_of_chambers,
            "rawWidthsOfChambers": self.output_config.raw_widths_of_chambers,
            "rawTimesForFilling": self.output_config.raw_times_for_filling,
            "rawTimesForEmptying": self.output_config.raw_times_for_emptying,
            "ships": self.output_config.ships,
            "directions": self.output_config.directions,
            "rawLengthsOfShips": self.output_config.raw_lengths_of_ships,
            "rawWidthsOfShips": self.output_config.raw_widths_of_ships,
            "rawDurationsForEntering": self.output_config.raw_durations_for_entering,
            "rawDurationsForLeaving": self.output_config.raw_durations_for_leaving,
            "rawEtas": self.output_config.raw_etas,
            "etaRange": self.output_config.eta_range,
            "rawMinDurs": self.output_config.raw_min_durs,
            "rawMaxDurs": self.output_config.raw_max_durs,
            "maxDelayWeight": self.output_config.max_delay_weight,
            "maxWaitingTimeWeight": self.output_config.max_waiting_time_weight,
            "shipDistributionRange": self.output_config.ship_distribution_range,
            "shipLengthCMRange": self.output_config.ship_length_cm_range,
            "shipWidthCMRange": self.output_config.ship_width_cm_range,
            "seed": self.output_config.seed,
        }
        return instance

