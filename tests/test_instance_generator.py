import unittest

from slslab import *


class TestInstanceGenerator(unittest.TestCase):
    def setUp(self):
        self.input_config = InputConfig(
            n_locks=2,
            chambers_per_lock=2,
            ship_count=3,
            seed=123,
        )
        self.generator = InstanceGenerator(self.input_config)


    def test_ship_lengths_within_range(self):
        lengths = self.generator._create_ship_length_cm_range()
        lo, hi = self.input_config.ship_length_cm_range

        self.assertEqual(len(lengths), self.input_config.ship_count)
        for length in lengths:
            self.assertGreaterEqual(length, lo)
            self.assertLessEqual(length, hi)

    def test_generate_chambers_shape(self):
        chambers = self.generator._generate_chambers()

        self.assertEqual(len(chambers.lengths), self.input_config.n_locks)
        self.assertEqual(len(chambers.lock_lengths), self.input_config.n_locks + 1)

        for lock in chambers.lengths:
            self.assertEqual(len(lock), self.input_config.chambers_per_lock)

    def test_scale_chambers_fits_ships(self):
        chambers = self.generator._generate_chambers()

        ship_lengths = [20000] * self.input_config.ship_count
        ship_widths = [5000] * self.input_config.ship_count

        self.generator._scale_chambers_for_ships(
            chambers, ship_lengths, ship_widths
        )

        for l in range(self.input_config.n_locks):
            for c in range(self.input_config.chambers_per_lock):
                self.assertGreaterEqual(
                    chambers.lengths[l][c],
                    ship_lengths[0] + self.input_config.security_distance_cm,
                )
                self.assertGreaterEqual(
                    chambers.widths[l][c],
                    ship_widths[0],
                )

    def test_segments_are_contiguous(self):
        chambers = self.generator._generate_chambers()
        left, right = self.generator._generate_segments(chambers.lock_lengths)

        for index in range(1, len(left)):
            self.assertGreater(left[index], right[index - 1])

    def test_generate_directions_split(self):
        directions = self.generator._generate_directions()
        split = self.generator._index_range(
            self.input_config.ship_distribution_range,
            self.input_config.ship_count,
        )

        self.assertEqual(directions.count(1), split)
        self.assertEqual(directions.count(-1), self.input_config.ship_count - split)

    def test_etas_monotonic_per_side(self):
        etas = self.generator._generate_etas()
        split = self.generator._index_range(self.input_config.ship_distribution_range, self.input_config.ship_count)

        self.assertEqual(etas[:split], sorted(etas[:split]))
        self.assertEqual(etas[split:], sorted(etas[split:]))

    def test_segment_duration_bounds(self):
        chambers = self.generator._generate_chambers()
        left, right = self.generator._generate_segments(chambers.lock_lengths)
        directions = self.generator._generate_directions()

        min_durs, max_durs = self.generator._generate_segment_durations(
            left, right, directions
        )

        for s in range(self.input_config.ship_count):
            for p in range(len(min_durs[s])):
                self.assertGreater(min_durs[s][p], 0)
                self.assertGreaterEqual(
                    max_durs[s][p],
                    min_durs[s][p],
                )

    def test_horizon_is_fixed(self):
        chambers = self.generator._generate_chambers()
        enter = [[1] * self.input_config.n_locks] * self.input_config.ship_count
        leave = [[1] * self.input_config.n_locks] * self.input_config.ship_count
        max_durs = [[10] * (self.input_config.n_locks + 1)]

        horizon = self.generator._compute_horizon(max_durs, chambers, enter, leave)

        self.assertEqual(horizon, 1440)

    def test_same_seed_produces_same_output(self):
        gen1 = InstanceGenerator(self.input_config)
        gen2 = InstanceGenerator(self.input_config)

        self.assertEqual(
            gen1.output_config.raw_lengths_of_ships,
            gen2.output_config.raw_lengths_of_ships,
        )


if __name__ == "__main__":
    unittest.main()