"""
HTML Cleaner - Advanced HTML sanitization and text extraction

Provides secure HTML cleaning with multiple strategies:
- Strip all HTML tags
- Allow specific safe tags
- Extract plain text while preserving structure
- Remove dangerous attributes and scripts
- Decode HTML entities
"""
import re
import html
import logging
from typing import Optional, Set, List
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class HTMLStripper(HTMLParser):
    """
    Custom HTML parser that strips all tags and extracts text
    
    More robust than regex for complex HTML
    """
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text_parts = []
    
    def handle_data(self, data):
        """Handle text data between tags"""
        self.text_parts.append(data)
    
    def handle_entityref(self, name):
        """Handle HTML entities like &amp; &lt; etc."""
        try:
            char = html.unescape(f'&{name};')
            self.text_parts.append(char)
        except Exception:
            pass
    
    def handle_charref(self, name):
        """Handle numeric character references like &#123;"""
        try:
            if name.startswith('x'):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
            self.text_parts.append(char)
        except Exception:
            pass
    
    def get_text(self) -> str:
        """Get extracted text"""
        return ''.join(self.text_parts)


class HTMLCleaner:
    """
    Advanced HTML cleaning and sanitization
    
    Features:
    - XSS prevention
    - Script injection removal
    - Safe tag whitelisting
    - Attribute sanitization
    - Entity decoding
    """
    
    # Dangerous tags that should always be removed
    DANGEROUS_TAGS = {
        'script', 'style', 'iframe', 'object', 'embed',
        'applet', 'link', 'meta', 'base', 'form'
    }
    
    # Safe tags that can be allowed in whitelisting mode
    SAFE_TAGS = {
        'p', 'br', 'strong', 'em', 'b', 'i', 'u',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'blockquote', 'pre', 'code', 'span', 'div'
    }
    
    # Dangerous attributes
    DANGEROUS_ATTRIBUTES = {
        'onclick', 'onload', 'onerror', 'onmouseover',
        'onmouseout', 'onfocus', 'onblur', 'onchange',
        'onsubmit', 'onkeydown', 'onkeyup', 'onkeypress'
    }
    
    # Safe attributes (only for whitelisted tags)
    SAFE_ATTRIBUTES = {
        'class', 'id', 'title', 'alt', 'href', 'src'
    }
    
    def __init__(self, allow_safe_tags: bool = False):
        """
        Initialize HTML cleaner
        
        Args:
            allow_safe_tags: If True, keep safe HTML tags. If False, strip all.
        """
        self.allow_safe_tags = allow_safe_tags
    
    # ==================== MAIN CLEANING METHODS ====================
    
    def clean(self, text: str, preserve_structure: bool = False) -> str:
        """
        Clean HTML from text
        
        Args:
            text: Input text with potential HTML
            preserve_structure: If True, replace tags with whitespace
        
        Returns:
            Cleaned text
        
        Examples:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.clean("<p>Hello <b>World</b></p>")
            'Hello World'
            >>> cleaner.clean("<script>alert('xss')</script>Safe text")
            'Safe text'
        """
        if not text:
            return ""
        
        # 1. Remove dangerous tags first
        text = self._remove_dangerous_tags(text)
        
        # 2. Remove comments
        text = self._remove_comments(text)
        
        # 3. Strip or sanitize tags
        if self.allow_safe_tags:
            text = self._sanitize_tags(text)
        else:
            text = self._strip_all_tags(text, preserve_structure)
        
        # 4. Decode HTML entities
        text = self._decode_entities(text)
        
        # 5. Clean whitespace
        text = self._clean_whitespace(text)
        
        return text.strip()
    
    def strip_all_tags(self, text: str) -> str:
        """
        Strip all HTML tags from text
        
        Args:
            text: Input text
        
        Returns:
            Text without HTML tags
        
        Examples:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.strip_all_tags("<p>Hello <b>World</b></p>")
            'Hello World'
        """
        return self.clean(text, preserve_structure=False)
    
    def extract_text(self, html: str) -> str:
        """
        Extract plain text from HTML using parser
        
        More robust than regex for complex HTML
        
        Args:
            html: HTML content
        
        Returns:
            Extracted plain text
        
        Examples:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.extract_text("<div><p>Hello</p><p>World</p></div>")
            'HelloWorld'
        """
        if not html:
            return ""
        
        # Remove dangerous content first
        html = self._remove_dangerous_tags(html)
        html = self._remove_comments(html)
        
        # Use parser to extract text
        try:
            stripper = HTMLStripper()
            stripper.feed(html)
            text = stripper.get_text()
            
            # Clean whitespace
            text = self._clean_whitespace(text)
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            # Fallback to regex
            return self._strip_all_tags(html, preserve_structure=False)
    
    # ==================== DANGEROUS CONTENT REMOVAL ====================
    
    def _remove_dangerous_tags(self, text: str) -> str:
        """
        Remove dangerous tags that could contain malicious code
        
        Args:
            text: Input text
        
        Returns:
            Text with dangerous tags removed
        """
        for tag in self.DANGEROUS_TAGS:
            # Remove opening and closing tags with any attributes
            pattern = re.compile(
                f'<{tag}[^>]*?>.*?</{tag}>',
                re.DOTALL | re.IGNORECASE
            )
            text = pattern.sub('', text)
            
            # Remove self-closing tags
            pattern = re.compile(
                f'<{tag}[^>]*?/>',
                re.IGNORECASE
            )
            text = pattern.sub('', text)
        
        return text
    
    def _remove_comments(self, text: str) -> str:
        """
        Remove HTML comments
        
        Args:
            text: Input text
        
        Returns:
            Text without HTML comments
        """
        # Remove <!-- ... --> comments
        return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    def _remove_dangerous_attributes(self, text: str) -> str:
        """
        Remove dangerous attributes like onclick, onload, etc.
        
        Args:
            text: Input text
        
        Returns:
            Text with dangerous attributes removed
        """
        for attr in self.DANGEROUS_ATTRIBUTES:
            # Remove attribute="value" or attribute='value'
            pattern = re.compile(
                f'{attr}\\s*=\\s*["\'][^"\']*["\']',
                re.IGNORECASE
            )
            text = pattern.sub('', text)
        
        return text
    
    # ==================== TAG HANDLING ====================
    
    def _strip_all_tags(self, text: str, preserve_structure: bool = False) -> str:
        """
        Strip all HTML tags
        
        Args:
            text: Input text
            preserve_structure: If True, replace tags with space
        
        Returns:
            Text without tags
        """
        if preserve_structure:
            # Replace tags with space to preserve word boundaries
            text = re.sub(r'<[^>]+>', ' ', text)
        else:
            # Remove tags completely
            text = re.sub(r'<[^>]+>', '', text)
        
        return text
    
    def _sanitize_tags(self, text: str) -> str:
        """
        Keep only safe tags, remove others
        
        Args:
            text: Input text
        
        Returns:
            Text with only safe tags
        """
        # Remove dangerous attributes from all tags
        text = self._remove_dangerous_attributes(text)
        
        # Find all tags
        def replace_tag(match):
            tag_content = match.group(0)
            
            # Extract tag name
            tag_name_match = re.match(r'</?(\w+)', tag_content)
            if not tag_name_match:
                return ''
            
            tag_name = tag_name_match.group(1).lower()
            
            # If tag is safe, keep it (with sanitized attributes)
            if tag_name in self.SAFE_TAGS:
                return tag_content
            
            # Otherwise, remove it
            return ''
        
        # Replace all tags
        text = re.sub(r'<[^>]+>', replace_tag, text)
        
        return text
    
    # ==================== ENTITY HANDLING ====================
    
    def _decode_entities(self, text: str) -> str:
        """
        Decode HTML entities like &amp; &lt; &#123;
        
        Args:
            text: Input text
        
        Returns:
            Text with decoded entities
        """
        try:
            return html.unescape(text)
        except Exception as e:
            logger.error(f"Error decoding entities: {e}")
            return text
    
    # ==================== WHITESPACE HANDLING ====================
    
    def _clean_whitespace(self, text: str) -> str:
        """
        Clean excessive whitespace
        
        Args:
            text: Input text
        
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    # ==================== VALIDATION ====================
    
    def contains_html(self, text: str) -> bool:
        """
        Check if text contains HTML tags
        
        Args:
            text: Input text
        
        Returns:
            True if HTML tags detected
        
        Examples:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.contains_html("<p>Hello</p>")
            True
            >>> cleaner.contains_html("Plain text")
            False
        """
        if not text:
            return False
        
        # Check for HTML tags
        return bool(re.search(r'<[^>]+>', text))
    
    def is_safe_html(self, text: str) -> bool:
        """
        Check if HTML contains only safe tags
        
        Args:
            text: Input text
        
        Returns:
            True if HTML is safe (or no HTML)
        """
        if not text:
            return True
        
        # Check for dangerous tags
        for tag in self.DANGEROUS_TAGS:
            pattern = re.compile(f'<{tag}[^>]*?>', re.IGNORECASE)
            if pattern.search(text):
                return False
        
        # Check for dangerous attributes
        for attr in self.DANGEROUS_ATTRIBUTES:
            pattern = re.compile(f'{attr}\\s*=', re.IGNORECASE)
            if pattern.search(text):
                return False
        
        return True
    
    # ==================== UTILITY METHODS ====================
    
    def truncate_html(
        self,
        html: str,
        max_length: int,
        suffix: str = "..."
    ) -> str:
        """
        Truncate HTML while preserving structure
        
        Args:
            html: Input HTML
            max_length: Maximum length of plain text
            suffix: Suffix to add if truncated
        
        Returns:
            Truncated HTML
        
        Examples:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.truncate_html("<p>Long text here</p>", 10)
            '<p>Long text...</p>'
        """
        # Extract plain text
        plain_text = self.extract_text(html)
        
        # If already short enough, return as-is
        if len(plain_text) <= max_length:
            return html
        
        # Truncate plain text
        truncated_text = plain_text[:max_length].rsplit(' ', 1)[0] + suffix
        
        # If original had HTML, wrap in basic tags
        if self.contains_html(html):
            return f"<p>{truncated_text}</p>"
        
        return truncated_text
    
    def extract_links(self, html: str) -> List[dict]:
        """
        Extract all links from HTML
        
        Args:
            html: Input HTML
        
        Returns:
            List of dicts with 'url' and 'text' keys
        
        Examples:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.extract_links('<a href="http://example.com">Click</a>')
            [{'url': 'http://example.com', 'text': 'Click'}]
        """
        links = []
        
        # Find all <a> tags
        pattern = re.compile(
            r'<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in pattern.finditer(html):
            url = match.group(1)
            text = self.strip_all_tags(match.group(2))
            
            links.append({
                'url': url,
                'text': text.strip()
            })
        
        return links


# ==================== CONVENIENCE FUNCTIONS ====================

def clean_html(text: str, allow_safe_tags: bool = False) -> str:
    """
    Convenience function to clean HTML from text
    
    Args:
        text: Input text
        allow_safe_tags: If True, keep safe tags
    
    Returns:
        Cleaned text
    
    Examples:
        >>> clean_html("<p>Hello <script>alert('xss')</script> World</p>")
        'Hello  World'
    """
    cleaner = HTMLCleaner(allow_safe_tags=allow_safe_tags)
    return cleaner.clean(text)


def strip_html(text: str) -> str:
    """
    Strip all HTML tags from text
    
    Args:
        text: Input text
    
    Returns:
        Text without HTML
    
    Examples:
        >>> strip_html("<p>Hello <b>World</b></p>")
        'Hello World'
    """
    cleaner = HTMLCleaner()
    return cleaner.strip_all_tags(text)


def extract_text_from_html(html: str) -> str:
    """
    Extract plain text from HTML
    
    Args:
        html: Input HTML
    
    Returns:
        Plain text
    
    Examples:
        >>> extract_text_from_html("<div><p>Hello</p><p>World</p></div>")
        'Hello World'
    """
    cleaner = HTMLCleaner()
    return cleaner.extract_text(html)


def is_safe_html(text: str) -> bool:
    """
    Check if HTML is safe (no scripts, dangerous tags)
    
    Args:
        text: Input text
    
    Returns:
        True if safe
    
    Examples:
        >>> is_safe_html("<p>Hello</p>")
        True
        >>> is_safe_html("<script>alert('xss')</script>")
        False
    """
    cleaner = HTMLCleaner()
    return cleaner.is_safe_html(text)


def sanitize_for_display(text: str) -> str:
    """
    Sanitize text for safe display in web pages
    
    Removes dangerous content but preserves basic formatting
    
    Args:
        text: Input text
    
    Returns:
        Sanitized text safe for display
    
    Examples:
        >>> sanitize_for_display("<p>Hello</p><script>alert('xss')</script>")
        '<p>Hello</p>'
    """
    cleaner = HTMLCleaner(allow_safe_tags=True)
    return cleaner.clean(text)