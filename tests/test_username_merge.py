"""Unit tests for :mod:`src.modules.username_merge`."""

import unittest

from src.modules.username_merge import (
    CONFIRMED_MARK,
    UNCONFIRMED_MARK,
    canonical_site,
    canonical_url,
    merge_sources,
    report,
    render_report,
)
from src.controllers.username_search_controller import UsernameController
from src.ui.output_formatter import render


def sherlock(site, url, status="Claimed"):
    return {"site": site, "url_user": url, "status": status}


def maigret(site, url, status="Claimed", ids=None):
    entry = {"site": site, "url_user": url, "status": status}
    if ids:
        entry["ids"] = ids
    return entry


class CanonicalTest(unittest.TestCase):
    def test_canonical_url(self):
        self.assertEqual(
            canonical_url("https://www.GitHub.com/user/"), "github.com/user"
        )
        self.assertEqual(canonical_url("http://github.com/user"), "github.com/user")
        self.assertEqual(
            canonical_url("https://m.reddit.com/u/x?tab=1"), "reddit.com/u/x"
        )
        self.assertEqual(canonical_url(""), "")
        self.assertEqual(canonical_url(None), "")

    def test_canonical_site(self):
        self.assertEqual(canonical_site("GitHub"), "github")
        self.assertEqual(canonical_site("git-hub!"), "github")
        self.assertEqual(canonical_site(None), "")


class MergeTest(unittest.TestCase):
    def test_confirmed_by_url_across_normalisation(self):
        left = [sherlock("GitHub", "https://www.github.com/alice/")]
        right = [maigret("github", "http://github.com/alice", ids={"uid": "1"})]
        confirmed, sh_only, mg_only = merge_sources(left, right)
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(sh_only, [])
        self.assertEqual(mg_only, [])

    def test_confirmed_by_site_name_fallback(self):
        left = [sherlock("GitHub", "")]
        right = [maigret("github", "https://github.com/alice")]
        confirmed, sh_only, mg_only = merge_sources(left, right)
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(sh_only, [])
        self.assertEqual(mg_only, [])

    def test_unconfirmed_split(self):
        left = [sherlock("GitHub", "https://github.com/alice")]
        right = [maigret("GitLab", "https://gitlab.com/alice")]
        confirmed, sh_only, mg_only = merge_sources(left, right)
        self.assertEqual(confirmed, [])
        self.assertEqual([e["site"] for e in sh_only], ["GitHub"])
        self.assertEqual([e["site"] for e in mg_only], ["GitLab"])

    def test_no_double_matching(self):
        left = [
            sherlock("GitHub", "https://github.com/alice"),
            sherlock("GitHub", "https://github.com/alice"),
        ]
        right = [maigret("github", "https://github.com/alice")]
        confirmed, sh_only, mg_only = merge_sources(left, right)
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(len(sh_only), 1)
        self.assertEqual(mg_only, [])

    def test_empty_inputs(self):
        self.assertEqual(merge_sources(None, None), ([], [], []))

    def test_does_not_mutate_inputs(self):
        left = [sherlock("GitHub", "https://github.com/alice")]
        right = [maigret("github", "https://github.com/alice")]
        merge_sources(left, right)
        self.assertEqual(left[0]["site"], "GitHub")


class RenderTest(unittest.TestCase):
    def _report(self):
        left = [
            sherlock("GitHub", "https://github.com/alice"),
            sherlock("Reddit", "https://reddit.com/user/alice"),
        ]
        right = [
            maigret("github", "https://github.com/alice", ids={"uid": "42"}),
            maigret("GitLab", "https://gitlab.com/alice"),
        ]
        return render_report("alice", *merge_sources(left, right))

    def test_confirmed_listed_first(self):
        text = self._report()
        self.assertIn("Username OSINT: alice", text)
        self.assertIn(f"{CONFIRMED_MARK} confirmed 1", text)
        self.assertLess(text.index(CONFIRMED_MARK), text.index("Unconfirmed"))
        self.assertLess(text.index("GitHub"), text.index("Unconfirmed"))
        self.assertLess(text.index("Unconfirmed"), text.index("GitLab"))
        self.assertLess(text.index("Unconfirmed"), text.index("Reddit"))

    def test_marks_and_sections(self):
        text = self._report()
        self.assertIn("Confirmed by both engines", text)
        self.assertIn("[ Sherlock only ]", text)
        self.assertIn("[ Maigret only ]", text)
        self.assertIn("Sherlock: Claimed", text)
        self.assertIn("Maigret: Claimed", text)
        self.assertIn("uid=42", text)
        self.assertIn(UNCONFIRMED_MARK, text)

    def test_no_confirmed(self):
        text = render_report(
            "bob",
            [],
            [sherlock("Reddit", "https://reddit.com/user/bob")],
            [],
        )
        self.assertIn("No account was confirmed", text)

    def test_structured_report_renders_found_accounts(self):
        confirmed, sherlock_only, maigret_only = merge_sources(
            [sherlock("GitHub", "https://github.com/alice")],
            [maigret("github", "https://github.com/alice", ids={"uid": "42"})],
        )

        text = render(
            report("alice", confirmed, sherlock_only, maigret_only),
            title="Username OSINT: alice",
        )

        self.assertIn("Username OSINT: alice", text)
        self.assertIn("GitHub", text)
        self.assertIn("https://github.com/alice", text)
        self.assertIn("Claimed", text)
        self.assertIn("42", text)


class UsernameControllerTest(unittest.IsolatedAsyncioTestCase):
    async def test_maigret_error_is_included_in_final_debug_output(self):
        class Widget:
            def __init__(self):
                self.text = ""

            def setPlainText(self, text):
                self.text = text

            def setValue(self, _value):
                pass

            def setRange(self, _minimum, _maximum):
                pass

        class Ui:
            usernameResultsDebug = Widget()
            usernameSearchProgress = Widget()

        class Maigret:
            async def search_and_report_structured(self, _username, on_progress=None):
                return {"error": "Maigret unavailable"}, []

        class Sherlock:
            async def acheck(self, _username, proxy=None, on_progress=None):
                return []

        ui = Ui()
        controller = UsernameController(ui, Sherlock(), Maigret())
        await controller.start_searching("alice")

        self.assertIn("Maigret error", ui.usernameResultsDebug.text)
        self.assertIn("Maigret unavailable", ui.usernameResultsDebug.text)


if __name__ == "__main__":
    unittest.main()
