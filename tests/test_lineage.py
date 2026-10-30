"""pool/lineage.py: repository lineages (D3-07, E10), on synthetic modules with hand-derived similarities.

Construction used throughout: a module is a list of lines ``attr_<tag>_<i> = "val_<tag>_<i>"``. Each line is
3 tokens (identifier, ``=``, string), so N lines give 3N tokens and 3N-4 five-token shingles. Two modules that
differ in the last k of N lines share the shingles that lie wholly inside the first N-k lines:
    shared = 3(N-k) - 4,  each module has 3k shingles of its own,  J = shared / (shared + 6k).
By hand: N=100, k=10 -> 266/326 = 0.816 (joined); N=100, k=17 -> 245/347 = 0.706 (not joined).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import lineage  # noqa: E402


def lines(tag: str, rng) -> str:
    return "".join(f'attr_{tag}_{i} = "val_{tag}_{i}"\n' for i in rng)


def mod(module_id: int, repo_id: int, files: dict[str, str]) -> lineage.ModuleInput:
    return lineage.ModuleInput(module_id, repo_id, files)


def one(module_id: int, repo_id: int, text: str) -> lineage.ModuleInput:
    return mod(module_id, repo_id, {"main.tf": text})


def result_for(*modules, **kw) -> lineage.LineageResult:
    return lineage.build_lineages(list(modules), **kw)


BASE = lines("a", range(100))


class TestHandDerivedSimilarity(unittest.TestCase):
    def shingles(self, text: str) -> set[int]:
        return lineage.module_shingles({"main.tf": text})

    def test_shingle_count_matches_the_hand_count(self) -> None:
        self.assertEqual(len(self.shingles(BASE)), 296)

    def test_ten_of_a_hundred_lines_replaced_is_0_816(self) -> None:
        other = lines("a", range(90)) + lines("x", range(10))
        self.assertAlmostEqual(lineage.exact_jaccard(self.shingles(BASE), self.shingles(other)), 266 / 326)

    def test_seventeen_replaced_is_0_706(self) -> None:
        other = lines("a", range(83)) + lines("x", range(17))
        self.assertAlmostEqual(lineage.exact_jaccard(self.shingles(BASE), self.shingles(other)), 245 / 347)

    def test_threshold_is_inclusive_at_exactly_0_8(self) -> None:
        a, b = set(range(9)), set(range(1, 10))  # 8 shared of 10 in the union
        self.assertEqual(lineage.exact_jaccard(a, b), 0.8)
        self.assertTrue(lineage.similar(a, b))
        self.assertFalse(lineage.similar(set(range(10)), set(range(2, 12))))  # 8 of 12

    def test_empty_sets_are_never_similar(self) -> None:
        self.assertFalse(lineage.similar(set(), set()))


class TestRuleA(unittest.TestCase):
    def test_modules_of_one_repository_share_a_lineage_whatever_they_contain(self) -> None:
        got = result_for(one(1, 5, lines("p", range(100))), one(2, 5, lines("q", range(100))))
        self.assertEqual(got.lineage_of[1], got.lineage_of[2])
        self.assertEqual(got.lineage_of[1], "lin-000000000005")


class TestRuleB(unittest.TestCase):
    def test_identical_text_in_two_repositories(self) -> None:
        got = result_for(one(1, 9, BASE), one(2, 4, BASE))
        self.assertEqual(got.lineage_of[1], got.lineage_of[2])
        self.assertEqual(got.lineage_of[1], "lin-000000000004")  # the smallest repository id

    def test_comments_and_whitespace_do_not_matter(self) -> None:
        noisy = "# a comment\n" + BASE.replace(" = ", "   =   ").replace("\n", " // trailing\n\n") + "/* end */\n"
        a, b = {"main.tf": BASE}, {"main.tf": noisy}
        self.assertEqual(lineage.module_hash(a), lineage.module_hash(b))
        got = result_for(mod(1, 9, a), mod(2, 4, b))
        self.assertEqual(got.lineage_of[1], got.lineage_of[2])

    def test_file_names_and_order_do_not_matter(self) -> None:
        a = {"a.tf": lines("p", range(30)), "b.tf": lines("q", range(30))}
        b = {"zz.tf": lines("q", range(30)), "yy.tf": lines("p", range(30))}
        self.assertEqual(lineage.module_hash(a), lineage.module_hash(b))

    def test_a_changed_token_changes_the_hash(self) -> None:
        self.assertNotEqual(lineage.module_hash({"m.tf": BASE}), lineage.module_hash({"m.tf": BASE.replace("val_a_3", "val_a_X")}))

    def test_heredoc_body_is_part_of_the_text(self) -> None:
        a = {"m.tf": 'x = <<EOT\none\nEOT\n'}
        b = {"m.tf": 'x = <<EOT\ntwo\nEOT\n'}
        self.assertNotEqual(lineage.module_hash(a), lineage.module_hash(b))


class TestRuleC(unittest.TestCase):
    F1, F2, F3, F4, F5 = (lines(t, range(100)) for t in "uvwxy")

    def test_half_of_the_files_shared_joins(self) -> None:
        a = mod(1, 1, {"a.tf": self.F1, "b.tf": self.F2})
        b = mod(2, 2, {"x.tf": self.F1, "y.tf": self.F3})
        got = result_for(a, b)
        self.assertEqual(got.lineage_of[1], got.lineage_of[2])
        self.assertEqual(got.merges["c"], 1)  # and not by rule d: their shingle Jaccard is 296/888

    def test_one_of_three_files_shared_does_not_join(self) -> None:
        a = mod(1, 1, {"a.tf": self.F1, "b.tf": self.F2, "c.tf": self.F4})
        b = mod(2, 2, {"x.tf": self.F1, "y.tf": self.F3, "z.tf": self.F5})
        got = result_for(a, b)
        self.assertNotEqual(got.lineage_of[1], got.lineage_of[2])

    def test_rule_needs_two_files_in_each_module(self) -> None:
        a = mod(1, 1, {"a.tf": self.F1})
        b = mod(2, 2, {"x.tf": self.F1, "y.tf": self.F3})
        got = result_for(a, b)  # shingle Jaccard is 296/592 = 0.5
        self.assertNotEqual(got.lineage_of[1], got.lineage_of[2])

    BOILER = 'provider "aws" {\n  region = "us-east-1"\n}\n'  # 7 tokens

    def test_trivial_shared_files_do_not_join_by_default(self) -> None:
        """User decision, 30 Oct 2026: rule c counts a file as shared only from 30 normalised tokens up."""
        a = mod(1, 1, {"provider.tf": self.BOILER, "main.tf": self.F1})
        b = mod(2, 2, {"provider.tf": self.BOILER, "main.tf": self.F3})
        got = result_for(a, b)
        self.assertNotEqual(got.lineage_of[1], got.lineage_of[2])
        self.assertEqual(lineage.FILE_TOKEN_FLOOR, 30)

    def test_floor_zero_is_the_rule_as_originally_written(self) -> None:
        a = mod(1, 1, {"provider.tf": self.BOILER, "main.tf": self.F1})
        b = mod(2, 2, {"provider.tf": self.BOILER, "main.tf": self.F3})
        as_written = result_for(a, b, min_shared_tokens=0)
        self.assertEqual(as_written.lineage_of[1], as_written.lineage_of[2])

    def test_a_shared_file_of_exactly_30_tokens_counts_29_does_not(self) -> None:
        thirty = lines("t", range(10))  # 3 tokens a line
        twenty_nine = lines("t", range(9)) + "attr_t_9 =\n"  # 27 + identifier + "="
        self.assertEqual(len(lineage.normalised_tokens(thirty)), 30)
        self.assertEqual(len(lineage.normalised_tokens(twenty_nine)), 29)
        for text, joined in ((thirty, True), (twenty_nine, False)):
            with self.subTest(tokens=len(lineage.normalised_tokens(text))):
                a = mod(1, 1, {"s.tf": text, "m.tf": self.F1})
                b = mod(2, 2, {"s.tf": text, "m.tf": self.F3})
                got = result_for(a, b)
                self.assertEqual(got.lineage_of[1] == got.lineage_of[2], joined)



class TestRuleD(unittest.TestCase):
    def test_renaming_one_variable_still_joins(self) -> None:
        # 5 tokens per line, 496 windows; name_3 occurs in 4 lines (i = 3, 28, 53, 78), changing 4 x 5 = 20 windows:
        # J = (496 - 20) / (496 + 20) = 476 / 516 = 0.92
        text = "".join(f"attr_a_{i} = var.name_{i % 25}\n" for i in range(100))
        renamed = text.replace("name_3\n", "other_3\n")
        self.assertNotEqual(lineage.module_hash({"m.tf": text}), lineage.module_hash({"m.tf": renamed}))
        self.assertAlmostEqual(
            lineage.exact_jaccard(lineage.module_shingles({"m.tf": text}), lineage.module_shingles({"m.tf": renamed})),
            476 / 516,
        )
        got = result_for(one(1, 7, text), one(2, 3, renamed))
        self.assertEqual(got.lineage_of[1], got.lineage_of[2])
        self.assertEqual(got.merges["d"], 1)

    def test_eighty_percent_similar_joins(self) -> None:
        got = result_for(one(1, 7, BASE), one(2, 3, lines("a", range(90)) + lines("x", range(10))))
        self.assertEqual(got.lineage_of[1], got.lineage_of[2])

    def test_seventy_percent_similar_does_not_join(self) -> None:
        got = result_for(one(1, 7, BASE), one(2, 3, lines("a", range(83)) + lines("x", range(17))))
        self.assertNotEqual(got.lineage_of[1], got.lineage_of[2])

    def test_unrelated_modules_stay_apart(self) -> None:
        got = result_for(one(1, 7, lines("p", range(100))), one(2, 3, lines("q", range(100))))
        self.assertEqual(got.lineage_of[1], "lin-000000000007")
        self.assertEqual(got.lineage_of[2], "lin-000000000003")

    def test_minhash_false_positive_is_stopped_by_the_exact_check(self) -> None:
        """The 70 percent pair is proposed by the banding (a false positive) and rejected by exact Jaccard."""
        a = BASE
        b = lines("a", range(83)) + lines("x", range(17))
        sig_a = lineage.signature(lineage.module_shingles({"m.tf": a}))
        sig_b = lineage.signature(lineage.module_shingles({"m.tf": b}))
        proposed = lineage.band_candidates({1: sig_a, 2: sig_b})
        self.assertIn((1, 2), proposed)  # precondition: the banding does propose it
        self.assertFalse(lineage.similar(lineage.module_shingles({"m.tf": a}), lineage.module_shingles({"m.tf": b})))
        got = result_for(one(1, 7, a), one(2, 3, b))
        self.assertNotEqual(got.lineage_of[1], got.lineage_of[2])


class TestChain(unittest.TestCase):
    P, Q, R, P2, R2 = (lines("p", range(15)), lines("q", range(170)), lines("r", range(15)),
                       lines("p2", range(15)), lines("r2", range(15)))

    def test_hand_derived_similarities(self) -> None:
        a, b, c = (lineage.module_shingles({"m.tf": t}) for t in (
            self.P + self.Q + self.R, self.P + self.Q + self.R2, self.P2 + self.Q + self.R2))
        self.assertAlmostEqual(lineage.exact_jaccard(a, b), 551 / 641)
        self.assertAlmostEqual(lineage.exact_jaccard(b, c), 551 / 641)
        self.assertAlmostEqual(lineage.exact_jaccard(a, c), 506 / 686)

    def test_a_similar_to_b_similar_to_c_is_one_lineage_although_a_and_c_differ(self) -> None:
        got = result_for(one(1, 30, self.P + self.Q + self.R), one(2, 20, self.P + self.Q + self.R2),
                         one(3, 10, self.P2 + self.Q + self.R2))
        self.assertEqual({got.lineage_of[i] for i in (1, 2, 3)}, {"lin-000000000010"})

    def test_input_order_does_not_change_the_result(self) -> None:
        ms = [one(1, 30, self.P + self.Q + self.R), one(2, 20, self.P + self.Q + self.R2),
              one(3, 10, self.P2 + self.Q + self.R2)]
        self.assertEqual(result_for(*ms).lineage_of, result_for(*reversed(ms)).lineage_of)


class TestIdsStatsDeterminism(unittest.TestCase):
    def test_id_format_is_lin_and_twelve_digits(self) -> None:
        self.assertEqual(lineage.lineage_id(42), "lin-000000000042")
        self.assertEqual(lineage.lineage_id(123456789012), "lin-123456789012")

    def test_same_seed_same_signature_different_seed_different(self) -> None:
        s = lineage.module_shingles({"m.tf": BASE})
        self.assertEqual(lineage.signature(s, seed=5), lineage.signature(s, seed=5))
        self.assertNotEqual(lineage.signature(s, seed=5), lineage.signature(s, seed=6))
        self.assertEqual(len(lineage.signature(s)), 64)

    def test_runs_are_repeatable(self) -> None:
        ms = [one(1, 7, BASE), one(2, 3, lines("a", range(90)) + lines("x", range(10))), one(3, 1, lines("z", range(50)))]
        self.assertEqual(result_for(*ms).lineage_of, result_for(*ms).lineage_of)

    def test_members_stats_and_cross_repository_counts(self) -> None:
        got = result_for(one(1, 7, BASE), one(2, 3, lines("a", range(90)) + lines("x", range(10))),
                         one(3, 3, lines("z", range(50))), one(4, 8, lines("w", range(50))))
        self.assertEqual(got.members["lin-000000000003"], [1, 2, 3])
        self.assertEqual(got.members["lin-000000000008"], [4])
        self.assertEqual(got.stats["lineages"], 2)
        self.assertEqual(got.stats["modules"], 4)
        self.assertEqual(got.stats["largest_lineage_modules"], 3)
        self.assertEqual(got.stats["largest_lineage_repositories"], 2)
        self.assertEqual(got.stats["multi_repository_lineages"], 1)
        self.assertEqual(got.stats["repositories_merged_by_content"], 2)  # repos 7 and 3 joined by content alone

    def test_modules_of_one_repository_are_not_counted_as_merged_by_content(self) -> None:
        got = result_for(one(1, 7, lines("p", range(50))), one(2, 7, lines("q", range(50))))
        self.assertEqual(got.stats["repositories_merged_by_content"], 0)
        self.assertEqual(got.stats["multi_repository_lineages"], 0)


class TestOneHostPerLineage(unittest.TestCase):
    def test_smallest_module_id_is_kept_per_lineage(self) -> None:
        lineage_of = {5: "lin-A", 3: "lin-A", 9: "lin-B", 4: "lin-A", 7: "lin-C"}
        keep, dropped = lineage.one_per_lineage([5, 3, 9, 4, 7], lineage_of)
        self.assertEqual(keep, [3, 7, 9])
        self.assertEqual(dropped, {4: 3, 5: 3})

    def test_no_two_kept_share_a_lineage(self) -> None:
        lineage_of = {i: f"lin-{i % 3}" for i in range(30)}
        keep, _ = lineage.one_per_lineage(list(range(30)), lineage_of)
        self.assertEqual(len({lineage_of[i] for i in keep}), len(keep))


if __name__ == "__main__":
    unittest.main()
