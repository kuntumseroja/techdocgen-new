"""TypeScript code parser"""

import re
from typing import Dict, List, Any
from .base_parser import BaseParser


class TypeScriptParser(BaseParser):
    """Parser for TypeScript source code"""
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse TypeScript code"""
        result = {
            "imports": self._extract_imports(code) if self.include_imports else [],
            "classes": self._extract_classes(code),
            "interfaces": self._extract_interfaces(code),
            "types": self._extract_types(code),
            "enums": self._extract_enums(code),
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
        """Extract class definitions (including decorators)"""
        classes = []
        pattern = r'(?:@\w+\([^)]*\)\s*)*(?:export\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w,\s.]+))?\s*\{'
        
        for match in re.finditer(pattern, code):
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            implements = [i.strip() for i in match.group(3).split(',')] if match.group(3) else []
            decorators = self._extract_decorators(code[:match.start()])
            
            start_pos = match.end()
            body = self._extract_balanced_braces(code, start_pos - 1)
            
            class_info = {
                "name": class_name,
                "extends": extends,
                "implements": implements,
                "decorators": decorators,
                "methods": self._extract_methods(body),
                "properties": self._extract_properties(body)
            }
            classes.append(class_info)
        
        return classes
    
    def _extract_interfaces(self, code: str) -> List[Dict[str, Any]]:
        """Extract interface definitions"""
        interfaces = []
        pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s.]+))?\s*\{'
        
        for match in re.finditer(pattern, code):
            interface_name = match.group(1)
            extends = [i.strip() for i in match.group(2).split(',')] if match.group(2) else []
            interfaces.append({
                "name": interface_name,
                "extends": extends
            })
        
        return interfaces
    
    def _extract_types(self, code: str) -> List[Dict[str, Any]]:
        """Extract type alias definitions"""
        types = []
        pattern = r'(?:export\s+)?type\s+(\w+)\s*='
        for match in re.finditer(pattern, code):
            types.append({"name": match.group(1)})
        return types
    
    def _extract_enums(self, code: str) -> List[Dict[str, Any]]:
        """Extract enum definitions"""
        enums = []
        pattern = r'(?:export\s+)?enum\s+(\w+)\s*\{'
        for match in re.finditer(pattern, code):
            enums.append({"name": match.group(1)})
        return enums
    
    def _extract_functions(self, code: str) -> List[Dict[str, Any]]:
        """Extract standalone functions and arrow functions"""
        functions = []
        func_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*(?::\s*[\w<>\[\]\|]+)?\s*\{'
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
        pattern = r'(?m)^\s*(?:public|private|protected|async|static)?\s*(\w+)\s*\([^)]*\)\s*(?::\s*[\w<>\[\]\|]+)?\s*\{'
        
        for match in re.finditer(pattern, code):
            method_name = match.group(1)
            if method_name in ['if', 'for', 'while', 'switch', 'catch']:
                continue
            methods.append({
                "name": method_name,
                "signature": match.group(0).split('{')[0].strip()
            })
        
        return methods
    
    def _extract_properties(self, code: str) -> List[Dict[str, Any]]:
        """Extract property definitions"""
        properties = []
        pattern = r'(?m)^\s*(?:public|private|protected|readonly)?\s*(\w+)\s*:\s*([^;=]+);'
        
        for match in re.finditer(pattern, code):
            properties.append({
                "name": match.group(1),
                "type": match.group(2).strip()
            })
        
        return properties
    
    def _extract_decorators(self, prefix: str) -> List[str]:
        """Extract decorator names near class definition"""
        lines = prefix.splitlines()[-5:]
        decorators = []
        for line in lines:
            match = re.search(r'@(\w+)', line.strip())
            if match:
                decorators.append(match.group(1))
        return decorators
    
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
