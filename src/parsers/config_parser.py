"""Config file parser for JSON/YAML"""

import json
from typing import Dict, List, Any
import yaml
from .base_parser import BaseParser


class ConfigParser(BaseParser):
    """Parser for configuration files (JSON/YAML)"""
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse configuration content"""
        parsed = self._parse_content(code)
        return {
            "config_type": parsed.get("type"),
            "top_level_keys": parsed.get("keys", []),
            "comments": self.extract_comments(code) if self.include_comments else []
        }
    
    def _parse_content(self, code: str) -> Dict[str, Any]:
        """Try parsing JSON, then YAML"""
        try:
            data = json.loads(code)
            return {"type": "json", "keys": self._extract_keys(data)}
        except Exception:
            pass
        
        try:
            data = yaml.safe_load(code)
            return {"type": "yaml", "keys": self._extract_keys(data)}
        except Exception:
            return {"type": "unknown", "keys": []}
    
    def _extract_keys(self, data: Any) -> List[str]:
        """Extract top-level keys from parsed config"""
        if isinstance(data, dict):
            return list(data.keys())
        return []
