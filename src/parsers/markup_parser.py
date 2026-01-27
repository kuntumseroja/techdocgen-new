"""Markup (HTML) parser"""

import re
from typing import Dict, List, Any
from .base_parser import BaseParser


class MarkupParser(BaseParser):
    """Parser for HTML/markup files"""
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse markup"""
        tags = re.findall(r'<\s*([a-zA-Z][\w-]*)', code)
        custom_tags = sorted({tag for tag in tags if '-' in tag})
        return {
            "tags": tags,
            "custom_elements": custom_tags,
            "comments": self._extract_html_comments(code) if self.include_comments else []
        }
    
    def _extract_html_comments(self, code: str) -> List[str]:
        """Extract HTML comments"""
        return re.findall(r'<!--(.*?)-->', code, re.DOTALL)
