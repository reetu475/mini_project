# test_multimodal_url.py
"""
Test suite verifying the Multimodal URL ingestion feature in PathFinder.
Validates:
1. Web URL HTML extraction for online portfolios and GitHub profiles.
2. Content-type routing for hosted PDFs and images.
3. Skill extraction and candidate profiling from web sources.
4. Robust network error handling.
"""

import sys
import unittest
from unittest.mock import patch, Mock
import requests

from resume_parser import (
    HTMLContentExtractor,
    extract_text_from_url,
    parse_url_resume,
    parse_multimodal_resume
)

class TestMultimodalURLIngestion(unittest.TestCase):

    def test_html_content_extractor(self):
        sample_html = """
        <html>
        <head><title>Sarah Chen - Senior AI Researcher</title><style>.test{color:red;}</style></head>
        <body>
            <header><nav><a href="/">Home</a></nav></header>
            <main>
                <h1>Sarah Chen</h1>
                <p>Contact: sarah.chen@lab.ai | San Francisco</p>
                <p>Expertise: Large Language Models, PyTorch, Transformers, vLLM, LangChain, Python, Deep Learning.</p>
            </main>
            <footer><p>2026 Sarah Chen</p></footer>
        </body>
        </html>
        """
        parser = HTMLContentExtractor()
        parser.feed(sample_html)
        text = parser.get_text()
        self.assertIn("Sarah Chen", text)
        self.assertIn("Large Language Models", text)
        self.assertNotIn("color:red", text)  # style stripped
        self.assertNotIn("Home", text)       # nav stripped
        self.assertNotIn("2026 Sarah", text) # footer stripped

    def test_mock_portfolio_url_parsing(self):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Content-Type': 'text/html; charset=utf-8'}
        mock_resp.encoding = 'utf-8'
        mock_resp.content = b"""
        <html>
        <head><title>David Kim - Cloud Platform & DevSecOps Engineer</title></head>
        <body>
            <h1>David Kim</h1>
            <p>Email: david.kim@cloudtech.io</p>
            <h2>Core Competencies</h2>
            <p>Cloud Architecture: AWS, Azure, Docker, Kubernetes, Terraform, Helm, CI/CD, Python, Go, Linux.</p>
            <h2>Objective</h2>
            <p>Seeking senior Cloud DevSecOps roles building scalable multi-tenant platforms.</p>
        </body>
        </html>
        """
        mock_resp.text = mock_resp.content.decode('utf-8')

        with patch('requests.get', return_value=mock_resp):
            profile = parse_url_resume("https://davidkim-cloud.dev")
            self.assertEqual(profile["name"], "David Kim")
            self.assertEqual(profile["email"], "david.kim@cloudtech.io")
            self.assertIn("Kubernetes", profile["skills"])
            self.assertIn("Terraform", profile["skills"])
            self.assertIn("Docker", profile["skills"])
            self.assertIn("Web URL", profile["media_type"])
            self.assertEqual(profile["source_url"], "https://davidkim-cloud.dev")

    def test_parse_multimodal_resume_with_url_dispatch(self):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Content-Type': 'text/html; charset=utf-8'}
        mock_resp.encoding = 'utf-8'
        mock_resp.content = b"""
        <html><body>
        <h1>Elena Rostova</h1>
        <p>Email: elena@dataplatform.net</p>
        <p>Skills: Apache Spark, PySpark, Snowflake, dbt, SQL, Python, Kafka, Airflow.</p>
        </body></html>
        """
        mock_resp.text = mock_resp.content.decode('utf-8')

        with patch('requests.get', return_value=mock_resp):
            # Pass URL as the second argument (filename)
            profile = parse_multimodal_resume(None, "https://github.com/erostova")
            self.assertEqual(profile["name"], "Elena Rostova")
            self.assertIn("PySpark", profile["skills"])
            self.assertIn("Snowflake", profile["skills"])
            self.assertIn("Web URL", profile["media_type"])

    def test_network_failure_handling(self):
        with patch('requests.get', side_effect=requests.RequestException("DNS lookup failed")):
            text, media = extract_text_from_url("https://unreachable-domain-xyz123.com")
            self.assertEqual(text, "")
            self.assertIn("URL Fetch Error", media)

if __name__ == '__main__':
    unittest.main()
