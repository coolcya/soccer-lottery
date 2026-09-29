import unittest

import fetch_titan007_odds as odds


class HandicapSettlementTests(unittest.TestCase):
    def test_home_gives_one_goal(self):
        self.assertEqual(odds.settle_handicap_result(2, 0, -1), "胜")
        self.assertEqual(odds.settle_handicap_result(1, 0, -1), "平")
        self.assertEqual(odds.settle_handicap_result(0, 0, -1), "负")

    def test_home_receives_three_goals(self):
        self.assertEqual(odds.settle_handicap_result(0, 2, 3), "胜")
        self.assertEqual(odds.settle_handicap_result(0, 3, 3), "平")
        self.assertEqual(odds.settle_handicap_result(0, 4, 3), "负")

    def test_rule_text_matches_examples(self):
        give_one = odds.handicap_settlement_rule(-1)["rules"]
        receive_three = odds.handicap_settlement_rule(3)["rules"]
        self.assertEqual(give_one["胜"], "主队得分减去客队得分大于1")
        self.assertEqual(give_one["平"], "主队得分减去客队得分等于1")
        self.assertEqual(give_one["负"], "主队得分减去客队得分小于1")
        self.assertEqual(receive_three["胜"], "客队得分减去主队得分小于3")
        self.assertEqual(receive_three["平"], "客队得分减去主队得分等于3")
        self.assertEqual(receive_three["负"], "客队得分减去主队得分大于3")


class SourceBoundaryTests(unittest.TestCase):
    def test_approved_host_is_accepted(self):
        url = odds.ensure_titan_url("/Handle/JcSp.aspx?spid=1")
        self.assertEqual(url, "https://cp.titan007.com/Handle/JcSp.aspx?spid=1")

    def test_other_odds_host_is_rejected(self):
        with self.assertRaises(ValueError):
            odds.ensure_titan_url("https://cp.zgzcw.com/lottery/example")


class HistoryParserTests(unittest.TestCase):
    def test_history_is_returned_oldest_first(self):
        html = """
        <table>
          <tr><td>2.10</td><td>3.30</td><td>3.00</td><td>09-28 18:00</td></tr>
          <tr><td>2.00</td><td>3.40</td><td>3.20</td><td>09-28 12:00</td></tr>
        </table>
        """
        records = odds.parse_history_records(html)
        self.assertEqual([record["home"] for record in records], [2.0, 2.1])
        self.assertEqual([record["sequence"] for record in records], [1, 2])


if __name__ == "__main__":
    unittest.main()
