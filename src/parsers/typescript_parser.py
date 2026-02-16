"""TypeScript code parser - SRS FR-04 (Node.js Express/NestJS), FR-05 (Angular micro-frontend)"""

import re
from typing import Dict, List, Any
from .base_parser import BaseParser


class TypeScriptParser(BaseParser):
    """Parser for TypeScript/JavaScript: Node.js (Express/NestJS) + Angular micro-frontend"""
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse TypeScript code with FR-04 (Express/NestJS) and FR-05 (Angular) extraction"""
        result = {
            "imports": self._extract_imports(code) if self.include_imports else [],
            "classes": self._extract_classes(code),
            "interfaces": self._extract_interfaces(code),
            "types": self._extract_types(code),
            "enums": self._extract_enums(code),
            "functions": self._extract_functions(code),
            "comments": self.extract_comments(code) if self.include_comments else [],
            # FR-04: Express/NestJS routes, controllers, amqplib
            "nodejs": self._extract_nodejs_routes(code),
            # FR-05: Angular components, services, modules, routing, guards, interceptors
            "angular": self._extract_angular_elements(code),
        }
        return result
    
    def _extract_nodejs_routes(self, code: str) -> Dict[str, Any]:
        """FR-04: API routes, middleware, controllers, amqplib integration points"""
        routes = []
        # Express: app.get|post|put|delete|patch('path', ...), router.get('path', ...)
        for m in re.finditer(r'(?:app|router)\s*\.\s*(get|post|put|delete|patch|all)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', code):
            routes.append({"method": m.group(1).upper(), "path": m.group(2)})
        # NestJS: @Controller('path'), @Get(), @Post('path')
        controller_path = ""
        for m in re.finditer(r'@Controller\s*\(\s*[\'"`]([^\'"`]*)[\'"`]\s*\)', code):
            controller_path = m.group(1)
        for m in re.finditer(r'@(Get|Post|Put|Delete|Patch|Options|Head)\s*(?:\(\s*[\'"`]([^\'"`]*)[\'"`]\s*\))?', code):
            path = m.group(2) or ""
            full = (controller_path.rstrip("/") + "/" + path.lstrip("/")).replace("//", "/") or controller_path
            routes.append({"method": m.group(1).upper(), "path": full or controller_path})
        # amqplib usage
        amqplib = "amqplib" in code or "amqp.connect" in code
        return {"routes": routes, "amqplib": amqplib}
    
    def _extract_angular_elements(self, code: str) -> Dict[str, Any]:
        """FR-05: Components, services, modules, routing, guards, interceptors"""
        result = {
            "components": [],
            "services": [],
            "modules": [],
            "routing": [],
            "guards": [],
            "interceptors": [],
        }
        # @Component
        for m in re.finditer(r'@Component\s*\(\s*\{[^}]*selector\s*:\s*[\'"`]([^\'"`]+)[\'"`]', code):
            result["components"].append({"selector": m.group(1)})
        for m in re.finditer(r'export\s+class\s+(\w+)\s*[^{\n]*@Component', code):
            result["components"].append({"class": m.group(1)})
        # @Injectable (services)
        for m in re.finditer(r'export\s+class\s+(\w+)\s*(?:Service|Injectable)', code):
            result["services"].append({"name": m.group(1)})
        for m in re.finditer(r'@Injectable\s*\([^)]*\)[^}]*export\s+class\s+(\w+)', code):
            if m.group(1) not in [s.get("name") for s in result["services"]]:
                result["services"].append({"name": m.group(1)})
        # @NgModule
        for m in re.finditer(r'@NgModule\s*\([^)]*\)[^}]*export\s+class\s+(\w+)Module', code):
            result["modules"].append({"name": m.group(1)})
        # RouterModule, routes config
        for m in re.finditer(r'path\s*:\s*[\'"`]([^\'"`]+)[\'"`]\s*(?:,|})', code):
            result["routing"].append({"path": m.group(1)})
        for m in re.finditer(r'Routes\s*=\s*\[\s*(\{[^]]+\})', code):
            result["routing"].append({"config": "present"})
        # Guards
        for m in re.finditer(r'canActivate\s*:\s*\[([^\]]+)\]', code):
            result["guards"].append({"guards": m.group(1).split(",")})
        for m in re.finditer(r'implements\s+CanActivate', code):
            result["guards"].append({"type": "CanActivate"})
        # Interceptors
        for m in re.finditer(r'implements\s+HttpInterceptor', code):
            result["interceptors"].append({"type": "HttpInterceptor"})
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
