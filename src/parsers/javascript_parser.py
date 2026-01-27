"""JavaScript code parser"""

import re
from typing import Dict, List, Any
from .base_parser import BaseParser


class JavaScriptParser(BaseParser):
    """Parser for JavaScript source code"""
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse JavaScript code"""
        result = {
            "imports": self._extract_imports(code) if self.include_imports else [],
            "classes": self._extract_classes(code),
            "functions": self._extract_functions(code),
            "comments": self.extract_comments(code) if self.include_comments else []
        }
        return result
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import/require statements"""
        imports = re.findall(r'import\s+(?:[\w*\s{},]+)\s+from\s+[\'"]([^\'"]+)[\'"]', code)
        requires = re.findall(r'require\(\s*[\'"]([^\'"]+)[\'"]\s*\)', code)
        return imports + requires
    
    def _extract_classes(self, code: str) -> List[Dict[str, Any]]:
        """Extract class definitions"""
        classes = []
        pattern = r'class\s+(\w+)(?:\s+extends\s+([\w.]+))?\s*\{'
        
        for match in re.finditer(pattern, code):
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            start_pos = match.end()
            body = self._extract_balanced_braces(code, start_pos - 1)
            
            class_info = {
                "name": class_name,
                "extends": extends,
                "methods": self._extract_methods(body)
            }
            classes.append(class_info)
        
        return classes
    
    def _extract_functions(self, code: str) -> List[Dict[str, Any]]:
        """Extract standalone functions and arrow functions"""
        functions = []
        func_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*\{'
        arrow_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>'
        
        for match in re.finditer(func_pattern, code):
            functions.append({
                "name": match.group(1),
                "signature": match.group(0).split('{')[0].strip()
            })
        
        for match in re.finditer(arrow_pattern, code):
            functions.append({
                "name": match.group(1),
                "signature": match.group(0).strip()
            })
        
        return functions
    
    def _extract_methods(self, code: str) -> List[Dict[str, Any]]:
        """Extract method definitions within class body"""
        methods = []
        pattern = r'(?m)^\s*(\w+)\s*\([^)]*\)\s*\{'
        
        for match in re.finditer(pattern, code):
            method_name = match.group(1)
            if method_name in ['if', 'for', 'while', 'switch', 'catch']:
                continue
            methods.append({
                "name": method_name,
                "signature": match.group(0).split('{')[0].strip()
            })
        
        return methods
    
    def _extract_balanced_braces(self, code: str, start_pos: int) -> str:
        """Extract balanced brace content"""
        if start_pos >= len(code) or code[start_pos] != '{':
            return ""
        
        depth = 0
        end_pos = start_pos
        
        for i in range(start_pos, len(code)):
            if code[i] == '{':
                depth += 1
            elif code[i] == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
        
        return code[start_pos:end_pos]
