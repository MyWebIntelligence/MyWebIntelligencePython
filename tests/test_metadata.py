"""
Test metadata extraction functionality
"""
import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from mwi.core import extract_metadata, get_title, get_description, get_keywords


class TestMetadataExtraction(unittest.TestCase):
    """Test the metadata extraction functions"""

    def setUp(self):
        """Set up test data"""
        self.html_standard = """
        <html>
            <head>
                <title>Standard Title</title>
                <meta name="description" content="Standard description">
                <meta name="keywords" content="standard, keywords">
            </head>
            <body>Test content</body>
        </html>
        """
        
        self.html_opengraph = """
        <html>
            <head>
                <title>Basic Title</title>
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG description">
                <meta property="og:keywords" content="og, keywords">
            </head>
            <body>Test content</body>
        </html>
        """
        
        self.html_twitter = """
        <html>
            <head>
                <title>Basic Title</title>
                <meta name="twitter:title" content="Twitter Title">
                <meta name="twitter:description" content="Twitter description">
                <meta name="twitter:keywords" content="twitter, keywords">
            </head>
            <body>Test content</body>
        </html>
        """
        
        self.html_schema = """
        <html>
            <head>
                <title>Basic Title</title>
                <meta itemprop="title" content="Schema Title">
                <meta itemprop="description" content="Schema description">
            </head>
            <body>Test content</body>
        </html>
        """
        
        self.html_mixed = """
        <html>
            <head>
                <title>Basic Title</title>
                <meta name="description" content="Standard description">
                <meta property="og:title" content="OG Title">
                <meta name="twitter:description" content="Twitter description">
            </head>
            <body>Test content</body>
        </html>
        """

    def test_get_title_standard(self):
        """Test getting title from standard HTML"""
        soup = BeautifulSoup(self.html_standard, 'html.parser')
        self.assertEqual(get_title(soup), "Standard Title")
        
    def test_get_title_opengraph(self):
        """Test getting title from Open Graph"""
        soup = BeautifulSoup(self.html_opengraph, 'html.parser')
        self.assertEqual(get_title(soup), "OG Title")
        
    def test_get_title_twitter(self):
        """Test getting title from Twitter Cards"""
        soup = BeautifulSoup(self.html_twitter, 'html.parser')
        self.assertEqual(get_title(soup), "Twitter Title")
        
    def test_get_title_schema(self):
        """Test getting title from Schema.org"""
        soup = BeautifulSoup(self.html_schema, 'html.parser')
        self.assertEqual(get_title(soup), "Schema Title")
        
    def test_get_description_standard(self):
        """Test getting description from standard HTML"""
        soup = BeautifulSoup(self.html_standard, 'html.parser')
        self.assertEqual(get_description(soup), "Standard description")
        
    def test_get_description_opengraph(self):
        """Test getting description from Open Graph"""
        soup = BeautifulSoup(self.html_opengraph, 'html.parser')
        self.assertEqual(get_description(soup), "OG description")
        
    def test_get_description_twitter(self):
        """Test getting description from Twitter Cards"""
        soup = BeautifulSoup(self.html_twitter, 'html.parser')
        self.assertEqual(get_description(soup), "Twitter description")
        
    def test_get_description_schema(self):
        """Test getting description from Schema.org"""
        soup = BeautifulSoup(self.html_schema, 'html.parser')
        self.assertEqual(get_description(soup), "Schema description")
        
    def test_get_keywords_standard(self):
        """Test getting keywords from standard HTML"""
        soup = BeautifulSoup(self.html_standard, 'html.parser')
        self.assertEqual(get_keywords(soup), "standard, keywords")
        
    def test_get_keywords_opengraph(self):
        """Test getting keywords from Open Graph"""
        soup = BeautifulSoup(self.html_opengraph, 'html.parser')
        self.assertEqual(get_keywords(soup), "og, keywords")
        
    def test_get_keywords_twitter(self):
        """Test getting keywords from Twitter Cards"""
        soup = BeautifulSoup(self.html_twitter, 'html.parser')
        self.assertEqual(get_keywords(soup), "twitter, keywords")
        
    def test_extract_metadata_fallback_chain(self):
        """Test the fallback chain in extract_metadata"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = self.html_mixed
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            metadata = extract_metadata('https://example.com')
            
            # Should get OG title (priority over standard)
            self.assertEqual(metadata['title'], "OG Title")
            # Should get standard description (first in chain)
            self.assertEqual(metadata['description'], "Standard description")
            # Keywords should be None (not present in mixed HTML)
            self.assertIsNone(metadata['keywords'])
            
    def test_extract_metadata_error_handling(self):
        """Test error handling in extract_metadata"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Test error")
            
            metadata = extract_metadata('https://example.com')
            
            # All fields should be None on error
            self.assertIsNone(metadata['title'])
            self.assertIsNone(metadata['description'])
            self.assertIsNone(metadata['keywords'])


if __name__ == '__main__':
    unittest.main()
