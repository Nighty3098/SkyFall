import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTextBrowser

from src.ui.output_formatter import render_html, set_output
from src.ui.rich_output_browser import RichOutputBrowser, is_rich_output_widget

_app = QApplication.instance() or QApplication([])


class RichOutputTest(unittest.TestCase):
    def test_render_html_escapes_values_and_marks_errors(self):
        html = render_html(
            "Scan result\n  host: <example.test>\n  ! Connection failed",
            theme="dark",
        )

        self.assertIn("&lt;example.test&gt;", html)
        self.assertIn("Connection failed", html)
        self.assertIn("#E5484D", html)
        self.assertIn("font-size:10pt", html)
        self.assertNotIn("font-size:12pt", html)
        self.assertIn("version", render_html("  version: TLSv1.3", theme="dark"))
        self.assertIn("&nbsp;&nbsp;", render_html("  version: TLSv1.3", theme="dark"))
        self.assertNotIn("padding-bottom:10px", html)
        self.assertNotIn("border-bottom:1px solid", html)
        self.assertNotIn("<example.test>", html)

    def test_set_output_keeps_readable_text_in_browser(self):
        browser = QTextBrowser()
        set_output(browser, "TLS result\n  issuer: Example CA")

        self.assertIn("TLS result", browser.toPlainText())
        self.assertIn("issuer", browser.toPlainText())
        self.assertIn("Example CA", browser.toPlainText())

    def test_empty_output_stays_empty(self):
        browser = QTextBrowser()
        set_output(browser, "")

        self.assertEqual(browser.toPlainText(), "")

    def test_fixed_width_tables_keep_column_alignment(self):
        table = "SSID       SECURITY\n────       ────────\nCafe       WPA2"
        html = render_html(table)

        self.assertIn("<pre", html)
        self.assertIn("SSID       SECURITY", html)
        self.assertIn("Cafe       WPA2", html)

    def test_blank_lines_remain_between_result_records(self):
        text = "Showing 2 records\n\n1. First camera\n   Stream: url\n\n2. Second"
        html = render_html(text)

        self.assertEqual(html.count('height:8px'), 2)

    def test_rich_browser_formats_plain_and_appended_output(self):
        browser = RichOutputBrowser()
        source = "TLS\n  version: TLSv1.3"
        set_output(browser, source)
        self.assertIn("TLS", browser.toPlainText())
        self.assertIn("TLSv1.3", browser.toPlainText())
        self.assertEqual(browser.toPlainText(), source)
        self.assertIn("background-color:#161616", browser.toHtml())

        browser.appendPlainText("  cipher: AES-128")
        self.assertEqual(browser.toPlainText(), f"{source}\n  cipher: AES-128")

    def test_only_output_plain_text_widgets_are_replaced(self):
        self.assertTrue(is_rich_output_widget("QPlainTextEdit", "socialDebug"))
        self.assertTrue(is_rich_output_widget("QPlainTextEdit", "cameraInfoText"))
        self.assertFalse(is_rich_output_widget("QPlainTextEdit", "proxyListEdit"))
        self.assertFalse(is_rich_output_widget("QPlainTextEdit", "nodeContentEdit"))
        self.assertFalse(is_rich_output_widget("QTextEdit", "socialDebug"))
        self.assertTrue(is_rich_output_widget("QTextBrowser", "serverTlsDebug"))
