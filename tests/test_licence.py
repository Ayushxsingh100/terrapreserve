"""pool/licence.py: SPDX detection from licence text and the E11 upstream-file check, with a fake network (D3 step 5).

No test here touches the network: ``get`` is a function that returns canned responses, and the clock and sleep
are fakes, so back-off and the one-request-per-second limit are checked exactly.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import licence  # noqa: E402

GRANT = (
    'Permission is hereby granted, free of charge, to any person obtaining a copy\n'
    'of this software and associated documentation files (the "Software"), to deal\n'
    'in the Software without restriction, including without limitation the rights\n'
    'to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n'
    'copies of the Software, and to permit persons to whom the Software is\n'
    'furnished to do so'
)
MIT = (
    "MIT License\n\nCopyright (c) 2020 Someone\n\n" + GRANT + ", subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all\n"
    "copies or substantial portions of the Software.\n\n"
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED.\n'
)
MIT0 = (
    "MIT No Attribution\n\nCopyright 2020 Someone\n\n" + GRANT + ".\n\n"
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED.\n'
)
BSD_HEAD = (
    "Copyright (c) 2020, Someone\nAll rights reserved.\n\n"
    "Redistribution and use in source and binary forms, with or without\n"
    "modification, are permitted provided that the following conditions are met:\n\n"
    "1. Redistributions of source code must retain the above copyright notice, this\n"
    "   list of conditions and the following disclaimer.\n\n"
    "2. Redistributions in binary form must reproduce the above copyright notice,\n"
    "   this list of conditions and the following disclaimer in the documentation\n"
    "   and/or other materials provided with the distribution.\n\n"
)
NEITHER = (
    "3. Neither the name of the copyright holder nor the names of its\n"
    "   contributors may be used to endorse or promote products derived from\n"
    "   this software without specific prior written permission.\n\n"
)
ADVERT = (
    "3. All advertising materials mentioning features or use of this software\n"
    "   must display the following acknowledgement.\n\n"
)
BSD_TAIL = 'THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS".\n'
BSD2 = "BSD 2-Clause License\n\n" + BSD_HEAD + BSD_TAIL
BSD3 = "BSD 3-Clause License\n\n" + BSD_HEAD + NEITHER + BSD_TAIL
BSD3_CLEAR = BSD3 + "NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS LICENSE.\n"
BSD4 = "BSD License\n\n" + BSD_HEAD + ADVERT + NEITHER + BSD_TAIL
ISC = (
    "ISC License\n\nCopyright (c) 2020, Someone\n\n"
    "Permission to use, copy, modify, and/or distribute this software for any\n"
    "purpose with or without fee is hereby granted, provided that the above\n"
    "copyright notice and this permission notice appear in all copies.\n"
)
ZERO_BSD = (
    "Zero-Clause BSD\n\nCopyright (c) 2020 Someone\n\n"
    "Permission to use, copy, modify, and/or distribute this software for\n"
    "any purpose with or without fee is hereby granted.\n"
)
UNLICENSE = "This is free and unencumbered software released into the public domain.\n\nAnyone is free to copy.\n"
CC0 = "Creative Commons Legal Code\n\nCC0 1.0 Universal\n\n    CREATIVE COMMONS CORPORATION IS NOT A LAW FIRM\n"
ZLIB = (
    "zlib License\n\n(C) 2020 Someone\n\n"
    "This software is provided 'as-is', without any express or implied\nwarranty.  In no event will the authors be held liable.\n\n"
    "1. The origin of this software must not be misrepresented; you must not\n   claim that you wrote the original software.\n"
)
BOOST = "Boost Software License - Version 1.0 - August 17th, 2003\n\nPermission is hereby granted, free of charge.\n"
GPL3 = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n"


def apache() -> str:
    return (REPO_ROOT / "LICENSES" / "Apache-2.0.txt").read_text(encoding="utf-8")


class TestDetect(unittest.TestCase):
    def test_each_permissive_licence_is_recognised(self) -> None:
        cases = {
            "MIT": MIT, "MIT-0": MIT0, "BSD-2-Clause": BSD2, "BSD-3-Clause": BSD3, "ISC": ISC, "0BSD": ZERO_BSD,
            "Unlicense": UNLICENSE, "CC0-1.0": CC0, "Zlib": ZLIB, "BSL-1.0": BOOST, "Apache-2.0": apache(),
        }
        for spdx, text in cases.items():
            with self.subTest(spdx=spdx):
                self.assertEqual(licence.detect_spdx(text), spdx)

    def test_whitespace_and_case_do_not_matter(self) -> None:
        self.assertEqual(licence.detect_spdx(MIT.upper().replace("\n", "\r\n  ")), "MIT")

    def test_close_relatives_are_told_apart(self) -> None:
        self.assertEqual(licence.detect_spdx(BSD3_CLEAR), "BSD-3-Clause-Clear")
        self.assertEqual(licence.detect_spdx(BSD4), "BSD-4-Clause")
        self.assertNotEqual(licence.detect_spdx(MIT0), "MIT")
        self.assertNotEqual(licence.detect_spdx(ZERO_BSD), "ISC")

    def test_unrecognised_or_copyleft_text_is_none(self) -> None:
        for text in ("", "all rights reserved", GPL3, "see the website"):
            with self.subTest(text=text[:20]):
                self.assertIsNone(licence.detect_spdx(text))


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class FakeNet:
    """``get(url)`` returns canned ``(status, body)`` pairs; a value that is an exception class is raised."""

    def __init__(self, responses: dict[str, list]) -> None:
        self.responses = {k: list(v) for k, v in responses.items()}
        self.calls: list[str] = []

    def get(self, url: str):
        self.calls.append(url)
        queue = self.responses.get(url) or [(404, b"")]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item("simulated")
        return item


SHA = "a" * 40


def url(name: str, repo: str = "o/r") -> str:
    return f"https://raw.githubusercontent.com/{repo}/{SHA}/{name}"


def check(net: FakeNet, fc: FakeClock, cache: Path | None, terrads: str | None = "MIT", **kw) -> licence.Check:
    limiter = licence.RateLimiter(clock=fc.clock, sleep=fc.sleep)
    return licence.check_repository(5, "o/r", SHA, terrads, get=net.get, limiter=limiter, sleep=fc.sleep,
                                    cache_dir=cache, **kw)


class TestFetch(unittest.TestCase):
    def test_names_and_order_are_those_of_the_work_package(self) -> None:
        self.assertEqual(licence.LICENCE_NAMES, ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING", "UNLICENSE"))

    def test_first_hit_wins_and_the_url_is_pinned_to_the_commit(self) -> None:
        net = FakeNet({url("LICENSE"): [(404, b"")], url("LICENSE.md"): [(200, MIT.encode())],
                       url("LICENSE.txt"): [(200, MIT.encode())]})
        got = check(net, FakeClock(), None)
        self.assertEqual(net.calls, [url("LICENSE"), url("LICENSE.md")])
        self.assertEqual((got.outcome, got.file_name, got.http_status, got.detected_spdx), ("found", "LICENSE.md", 200, "MIT"))
        self.assertEqual(got.bytes, len(MIT.encode()))

    def test_all_six_names_missing(self) -> None:
        net = FakeNet({})
        got = check(net, FakeClock(), None)
        self.assertEqual(len(net.calls), 6)
        self.assertEqual((got.outcome, got.file_name), ("missing", ""))

    def test_detected_spdx_that_differs_from_terraform_ds_is_a_mismatch(self) -> None:
        net = FakeNet({url("LICENSE"): [(200, BSD3.encode())]})
        got = check(net, FakeClock(), None, terrads="MIT")
        self.assertEqual((got.outcome, got.detected_spdx, got.terrads_spdx), ("mismatch", "BSD-3-Clause", "MIT"))

    def test_unrecognised_text_is_a_mismatch_with_no_detected_id(self) -> None:
        net = FakeNet({url("LICENSE"): [(200, b"all rights reserved")]})
        got = check(net, FakeClock(), None)
        self.assertEqual((got.outcome, got.detected_spdx), ("mismatch", ""))

    def test_comparison_ignores_case(self) -> None:
        net = FakeNet({url("LICENSE"): [(200, MIT.encode())]})
        self.assertEqual(check(net, FakeClock(), None, terrads="mit").outcome, "found")

    def test_a_licence_file_over_100_kb_is_not_accepted(self) -> None:
        net = FakeNet({url("LICENSE"): [(200, b"x" * (100 * 1024 + 1))]})
        got = check(net, FakeClock(), None)
        self.assertEqual(got.outcome, "error")
        self.assertIn("100 KB", got.detail)

    def test_back_off_then_success(self) -> None:
        net = FakeNet({url("LICENSE"): [OSError, (503, b""), (200, MIT.encode())]})
        fc = FakeClock()
        got = check(net, fc, None)
        self.assertEqual(got.outcome, "found")
        backoff = [s for s in fc.slept if s >= 2]
        self.assertEqual(backoff, [2, 4])

    def test_persistent_failure_is_recorded_as_error_not_invented(self) -> None:
        net = FakeNet({url(n): [(429, b"")] for n in licence.LICENCE_NAMES})
        fc = FakeClock()
        got = check(net, fc, None)
        self.assertEqual(got.outcome, "error")
        self.assertEqual([s for s in fc.slept if s >= 2][:3], [2, 4, 8])
        self.assertEqual(len(net.calls), 6 * licence.ATTEMPTS)

    def test_a_later_name_can_still_be_found_after_an_earlier_one_failed(self) -> None:
        net = FakeNet({url("LICENSE"): [(500, b"")], url("LICENSE.md"): [(200, MIT.encode())]})
        self.assertEqual(check(net, FakeClock(), None).outcome, "found")

    def test_requests_are_spaced_at_least_one_second_apart(self) -> None:
        net = FakeNet({})
        fc = FakeClock()
        times: list[float] = []
        original = net.get

        def timed(u: str):
            times.append(fc.now)
            return original(u)

        net.get = timed  # type: ignore[method-assign]
        check(net, fc, None)
        gaps = [b - a for a, b in zip(times, times[1:])]
        self.assertEqual(len(times), 6)
        self.assertTrue(all(g >= 1.0 - 1e-9 for g in gaps), gaps)

    def test_limiter_waits_only_for_what_is_left(self) -> None:
        fc = FakeClock()
        limiter = licence.RateLimiter(clock=fc.clock, sleep=fc.sleep)
        limiter.wait()
        fc.now += 0.25
        limiter.wait()
        self.assertEqual(fc.slept, [0.75])


class TestCacheAndCsv(unittest.TestCase):
    def test_second_call_for_a_repository_makes_no_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            net = FakeNet({url("LICENSE"): [(200, MIT.encode())]})
            first = check(net, FakeClock(), cache)
            calls = len(net.calls)
            second = check(net, FakeClock(), cache)
            self.assertEqual(len(net.calls), calls)
            self.assertEqual(first, second)
            self.assertEqual(licence.cached_text(cache, first), MIT.encode())

    def test_404s_are_cached_but_errors_are_retried(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            net = FakeNet({url(n): [(429, b"")] for n in licence.LICENCE_NAMES})
            self.assertEqual(check(net, FakeClock(), cache).outcome, "error")
            net2 = FakeNet({url("LICENSE"): [(200, MIT.encode())]})
            self.assertEqual(check(net2, FakeClock(), cache).outcome, "found")

    def test_known_rows_from_the_committed_csv_replace_the_network(self) -> None:
        net = FakeNet({url("LICENSE"): [(200, MIT.encode())]})
        known = {5: licence.Check(5, "o/r", SHA, "LICENSE", 200, 10, "ab" * 32, "MIT", "MIT", "found", "")}
        got = check(net, FakeClock(), None, known=known)
        self.assertEqual(net.calls, [])
        self.assertEqual(got.outcome, "found")

    def test_known_error_rows_are_not_trusted(self) -> None:
        net = FakeNet({url("LICENSE"): [(200, MIT.encode())]})
        known = {5: licence.Check(5, "o/r", SHA, "", 0, 0, "", "", "MIT", "error", "x")}
        self.assertEqual(check(net, FakeClock(), None, known=known).outcome, "found")
        self.assertTrue(net.calls)

    def test_csv_round_trip_is_lf_only_and_sorted(self) -> None:
        rows = [
            licence.Check(9, "o/b", SHA, "LICENSE", 200, 11, "cd" * 32, "MIT", "MIT", "found", ""),
            licence.Check(2, "o/a", SHA, "", 404, 0, "", "", "Apache-2.0", "missing", "all names 404"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "licence_checks.csv"
            licence.write_checks(path, rows)
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)
            back = licence.read_checks(path)
        self.assertEqual(list(back), [2, 9])
        self.assertEqual(back[9], rows[0])
        self.assertEqual(back[2], rows[1])


if __name__ == "__main__":
    unittest.main()
