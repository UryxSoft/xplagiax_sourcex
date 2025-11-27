# tests/unit/test_html_cleaner.py
import pytest
from app.utils.html_cleaner import (
    HTMLCleaner,
    clean_html,
    strip_html,
    extract_text_from_html,
    is_safe_html,
    sanitize_for_display
)


class TestHTMLCleaner:
    """Test suite for HTMLCleaner"""
    
    def test_strip_basic_tags(self):
        """Test stripping basic HTML tags"""
        result = strip_html("<p>Hello <b>World</b></p>")
        assert result == "Hello World"
    
    def test_remove_script_tags(self):
        """Test removal of dangerous script tags"""
        result = clean_html("<p>Safe</p><script>alert('xss')</script>")
        assert "alert" not in result
        assert "Safe" in result
    
    def test_remove_dangerous_attributes(self):
        """Test removal of dangerous attributes"""
        result = clean_html('<a href="#" onclick="alert()">Link</a>')
        assert "onclick" not in result
    
    def test_decode_entities(self):
        """Test HTML entity decoding"""
        result = clean_html("&lt;Hello&gt; &amp; &quot;World&quot;")
        assert result == '<Hello> & "World"'
    
    def test_preserve_safe_tags(self):
        """Test preserving safe tags when allowed"""
        cleaner = HTMLCleaner(allow_safe_tags=True)
        result = cleaner.clean("<p>Hello <b>World</b></p>")
        assert "<p>" in result
        assert "<b>" in result
    
    def test_extract_text_complex_html(self):
        """Test extracting text from complex HTML"""
        html = """
        <div>
            <h1>Title</h1>
            <p>Paragraph 1</p>
            <p>Paragraph 2</p>
        </div>
        """
        result = extract_text_from_html(html)
        assert "Title" in result
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result
    
    def test_is_safe_html_with_script(self):
        """Test detection of unsafe HTML"""
        assert not is_safe_html("<script>alert('xss')</script>")
    
    def test_is_safe_html_with_safe_tags(self):
        """Test detection of safe HTML"""
        assert is_safe_html("<p>Hello <b>World</b></p>")
    
    def test_contains_html(self):
        """Test HTML detection"""
        cleaner = HTMLCleaner()
        assert cleaner.contains_html("<p>Hello</p>")
        assert not cleaner.contains_html("Plain text")
    
    def test_extract_links(self):
        """Test link extraction"""
        cleaner = HTMLCleaner()
        html = '<a href="http://example.com">Example</a>'
        links = cleaner.extract_links(html)
        
        assert len(links) == 1
        assert links[0]['url'] == "http://example.com"
        assert links[0]['text'] == "Example"
    
    def test_truncate_html(self):
        """Test HTML truncation"""
        cleaner = HTMLCleaner()
        html = "<p>This is a very long text that should be truncated</p>"
        result = cleaner.truncate_html(html, max_length=20)
        
        assert len(extract_text_from_html(result)) <= 24  # 20 + "..."
    
    def test_clean_whitespace(self):
        """Test whitespace normalization"""
        result = clean_html("Hello    World\n\n\nMultiple   spaces")
        assert "    " not in result
        assert "Hello World" in result
    
    def test_sanitize_for_display(self):
        """Test sanitization for display"""
        result = sanitize_for_display(
            "<p>Safe text</p><script>alert('xss')</script>"
        )
        assert "<p>" in result
        assert "script" not in result.lower()