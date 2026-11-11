"""Regression checks for independently replayed Clopper–Pearson intervals."""
import math
import unittest

from scipy.stats import beta

from replay import same_beta_endpoint, same_statistics


class HistoricalIntervals(unittest.TestCase):
    def test_frozen_beta_endpoints(self):
        for probability, a, b, stored in ((1 - (1 - .975) / 2, 4, 21, .3523712243142352),
                                          (1 - .00625, 1, 12, .3448762640032966)):
            self.assertTrue(same_beta_endpoint(float(beta.ppf(probability, a, b)), stored))
        self.assertTrue(same_beta_endpoint(.35237122431423507, .3523712243142352))

    def test_boundaries_sign_and_step_limit(self):
        for boundary in (-1., 0., 1.):
            self.assertTrue(same_beta_endpoint(boundary, boundary))
            neighbor = math.nextafter(boundary, .5)
            self.assertFalse(same_beta_endpoint(neighbor, boundary))
            self.assertFalse(same_beta_endpoint(boundary, neighbor))
        self.assertFalse(same_beta_endpoint(math.ulp(0.), -math.ulp(0.)))
        x = .5
        for _ in range(3):
            x = math.nextafter(x, 0.)
        self.assertFalse(same_beta_endpoint(x, .5))
        self.assertFalse(same_beta_endpoint(float("nan"), .5))

    def test_other_fields_and_data_types_are_exact(self):
        paths = {("analysis", "ci")}
        ref = {"analysis": {"ci": [0., .3523712243142352], "count": 1, "effect": .5}}
        result = {"analysis": {"ci": [0., .35237122431423507], "count": 1, "effect": .5}}
        self.assertTrue(same_statistics(result, ref, paths))
        for key, bad in (("count", True), ("count", 1.), ("effect", math.nextafter(.5, 1.)),
                         ("ci", [0, .35237122431423507]), ("ci", [0., .35]), ("ci", [0.])):
            self.assertFalse(same_statistics({"analysis": {**result["analysis"], key: bad}}, ref, paths))
        self.assertFalse(same_statistics({"analysis": {"ci": result["analysis"]["ci"]}}, ref, paths))


if __name__ == "__main__":
    unittest.main()
