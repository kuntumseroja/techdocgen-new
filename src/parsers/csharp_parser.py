"""C# (.NET) code parser - SRS FR-01, FR-02, FR-03: CQRS/DDD, MassTransit, EF Core"""

import re
from typing import Dict, List, Any
from .base_parser import BaseParser


class CSharpParser(BaseParser):
    """Parser for C# source code with CQRS/DDD, MassTransit, EF Core pattern recognition"""
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse C# code including CQRS/DDD patterns (FR-01), MassTransit (FR-02), EF Core (FR-03)"""
        classes = self._extract_classes(code)
        result = {
            "namespace": self._extract_namespace(code),
            "using": self._extract_usings(code) if self.include_imports else [],
            "classes": classes,
            "interfaces": self._extract_interfaces(code),
            "enums": self._extract_enums(code),
            "structs": self._extract_structs(code),
            "comments": self.extract_comments(code) if self.include_comments else [],
            # FR-01: CQRS/DDD pattern elements
            "cqrs_ddd": self._extract_cqrs_ddd_patterns(code, classes),
            # FR-03: EF Core/Tibero data model
            "ef_core": self._extract_ef_core(code),
        }
        return result
    
    def _extract_cqrs_ddd_patterns(self, code: str, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """FR-01: Extract Commands, Queries, Handlers, Events, Consumers, Sagas, Aggregates, Entities, Value Objects, Repositories"""
        patterns = {
            "commands": [],
            "queries": [],
            "handlers": [],
            "events": [],
            "consumers": [],
            "sagas": [],
            "aggregates": [],
            "entities": [],
            "value_objects": [],
            "repositories": [],
        }
        # Commands - ICommand, IRequest
        for m in re.finditer(r"(?:class|record|interface)\s+(\w+)\s*[:\s].*?(?:ICommand|IRequest)[<\s]", code):
            patterns["commands"].append({"name": m.group(1), "type": "command"})
        for m in re.finditer(r"class\s+(\w+Command)\b", code):
            if m.group(1) not in [c["name"] for c in patterns["commands"]]:
                patterns["commands"].append({"name": m.group(1), "type": "command"})
        # Queries
        for m in re.finditer(r"(?:class|record|interface)\s+(\w+)\s*[:\s].*?(?:IQuery|IRequest)[<\s]", code):
            patterns["queries"].append({"name": m.group(1), "type": "query"})
        for m in re.finditer(r"class\s+(\w+Query)\b", code):
            if m.group(1) not in [q["name"] for q in patterns["queries"]]:
                patterns["queries"].append({"name": m.group(1), "type": "query"})
        # Handlers - IRequestHandler, ICommandHandler
        for m in re.finditer(r"class\s+(\w+)\s*:\s*[^{\n]*(?:IRequestHandler|ICommandHandler|IQueryHandler)[<\s]", code):
            patterns["handlers"].append({"name": m.group(1)})
        # Events
        for m in re.finditer(r"(?:class|record|interface)\s+(\w+)\s*[:\s].*?(?:IEvent|INotification)[<\s]", code):
            patterns["events"].append({"name": m.group(1)})
        for m in re.finditer(r"(?:class|record)\s+(\w+Event)\b", code):
            if m.group(1) not in [e["name"] for e in patterns["events"]]:
                patterns["events"].append({"name": m.group(1)})
        # Consumers - IConsumer<T>
        for m in re.finditer(r"class\s+(\w+)\s*:\s*[^{\n]*IConsumer<\s*([\w.]+)\s*>", code):
            patterns["consumers"].append({"consumer": m.group(1), "message": m.group(2)})
        # Sagas - Saga, StateMachineSaga
        for m in re.finditer(r"(?:class|:)\s*(\w+)\s*[:\s].*?(?:Saga|StateMachineSaga)[<\s]", code):
            patterns["sagas"].append({"name": m.group(1)})
        # Aggregates - often inherit from Entity or have Aggregate in name
        for m in re.finditer(r"class\s+(\w+)\s*:\s*[^{\n]*(?:AggregateRoot|Entity)[^\s]*", code):
            patterns["aggregates"].append({"name": m.group(1)})
        for m in re.finditer(r"class\s+(\w+Aggregate)\b", code):
            if m.group(1) not in [a["name"] for a in patterns["aggregates"]]:
                patterns["aggregates"].append({"name": m.group(1)})
        # Entities - DbSet, or class inheriting Entity
        for m in re.finditer(r"class\s+(\w+)\s*:\s*[^{\n]*Entity", code):
            if m.group(1) not in [e["name"] for e in patterns["entities"]]:
                patterns["entities"].append({"name": m.group(1)})
        for cls in classes:
            if cls.get("name", "").endswith("Entity") and cls["name"] not in [e["name"] for e in patterns["entities"]]:
                patterns["entities"].append({"name": cls["name"]})
        # Value Objects - often record or sealed class
        for m in re.finditer(r"(?:record|sealed\s+class)\s+(\w+)\s*[:\s]", code):
            if "Value" in m.group(1) or m.group(1).endswith("Value"):
                patterns["value_objects"].append({"name": m.group(1)})
        # Repositories - IRepository, *Repository
        for m in re.finditer(r"(?:interface)\s+(I\w*Repository)\b", code):
            patterns["repositories"].append({"name": m.group(1), "type": "interface"})
        for m in re.finditer(r"class\s+(\w+Repository)\s*:", code):
            patterns["repositories"].append({"name": m.group(1), "type": "implementation"})
        return patterns
    
    def _extract_ef_core(self, code: str) -> Dict[str, Any]:
        """FR-03: Extract DbContext, entities, relationships (one-to-many, many-to-many)"""
        result = {"db_contexts": [], "entities": [], "relationships": []}
        # DbContext (including namespaced e.g. Microsoft.EntityFrameworkCore.DbContext)
        for m in re.finditer(r"class\s+(\w+)\s*:\s*[\w.]*DbContext\b", code):
            result["db_contexts"].append({"name": m.group(1)})
        # DbSet entities
        for m in re.finditer(r"DbSet<\s*([\w.]+)\s*>\s+(\w+)", code):
            result["entities"].append({"type": m.group(1), "property": m.group(2)})
        # HasOne, HasMany, WithOne, WithMany (relationship config)
        for m in re.finditer(r"\.(HasOne|HasMany|WithOne|WithMany)\s*<\s*([\w.]+)\s*>", code):
            result["relationships"].append({"relation": m.group(1), "target": m.group(2)})
        return result
    
    def _extract_namespace(self, code: str) -> str:
        """Extract namespace declaration"""
        match = re.search(r'namespace\s+([\w.]+)', code)
        return match.group(1) if match else ""
    
    def _extract_usings(self, code: str) -> List[str]:
        """Extract using statements"""
        usings = re.findall(r'using\s+(?:static\s+)?([\w.*=]+);', code)
        return usings
    
    def _extract_classes(self, code: str) -> List[Dict[str, Any]]:
        """Extract class definitions"""
        classes = []
        pattern = r'(?:public|private|internal|protected|abstract|sealed|static|partial)?\s*class\s+(\w+)(?:\s*:\s*([\w,\s<>]+))?\s*\{'
        
        for match in re.finditer(pattern, code):
            class_name = match.group(1)
            inherits = [i.strip() for i in match.group(2).split(',')] if match.group(2) else []
            
            start_pos = match.end()
            body = self._extract_balanced_braces(code, start_pos - 1)
            
            class_info = {
                "name": class_name,
                "inherits": inherits,
                "methods": self._extract_methods(body),
                "properties": self._extract_properties(body),
                "fields": self._extract_fields(body),
                "modifiers": self._extract_modifiers(match.group(0))
            }
            classes.append(class_info)
        
        return classes
    
    def _extract_interfaces(self, code: str) -> List[Dict[str, Any]]:
        """Extract interface definitions"""
        interfaces = []
        pattern = r'(?:public|private|internal|protected)?\s*interface\s+(\w+)(?:\s*:\s*([\w,\s]+))?\s*\{'
        
        for match in re.finditer(pattern, code):
            interface_name = match.group(1)
            extends = [i.strip() for i in match.group(2).split(',')] if match.group(2) else []
            
            start_pos = match.end()
            body = self._extract_balanced_braces(code, start_pos - 1)
            
            interface_info = {
                "name": interface_name,
                "extends": extends,
                "methods": self._extract_methods(body),
                "properties": self._extract_properties(body)
            }
            interfaces.append(interface_info)
        
        return interfaces
    
    def _extract_enums(self, code: str) -> List[Dict[str, Any]]:
        """Extract enum definitions"""
        enums = []
        pattern = r'(?:public|private|internal)?\s*enum\s+(\w+)\s*\{'
        
        for match in re.finditer(pattern, code):
            enum_name = match.group(1)
            start_pos = match.end()
            body = self._extract_balanced_braces(code, start_pos - 1)
            
            constants = re.findall(r'(\w+)(?:\s*=\s*[^,}]+)?', body)
            
            enum_info = {
                "name": enum_name,
                "constants": constants
            }
            enums.append(enum_info)
        
        return enums
    
    def _extract_structs(self, code: str) -> List[Dict[str, Any]]:
        """Extract struct definitions"""
        structs = []
        pattern = r'(?:public|private|internal)?\s*struct\s+(\w+)(?:\s*:\s*([\w,\s]+))?\s*\{'
        
        for match in re.finditer(pattern, code):
            struct_name = match.group(1)
            inherits = [i.strip() for i in match.group(2).split(',')] if match.group(2) else []
            
            start_pos = match.end()
            body = self._extract_balanced_braces(code, start_pos - 1)
            
            struct_info = {
                "name": struct_name,
                "inherits": inherits,
                "fields": self._extract_fields(body),
                "properties": self._extract_properties(body)
            }
            structs.append(struct_info)
        
        return structs
    
    def _extract_methods(self, code: str) -> List[Dict[str, Any]]:
        """Extract method definitions"""
        methods = []
        pattern = r'(?:public|private|internal|protected|static|virtual|override|abstract|async)?\s*(?:[\w<>,\s\[\]]+\s+)?(\w+)\s*\([^)]*\)\s*\{'
        
        for match in re.finditer(pattern, code):
            method_name = match.group(1)
            if method_name in ['if', 'for', 'while', 'switch', 'try', 'catch', 'using']:
                continue
            
            method_info = {
                "name": method_name,
                "signature": match.group(0).split('{')[0].strip(),
                "modifiers": self._extract_modifiers(match.group(0))
            }
            methods.append(method_info)
        
        return methods
    
    def _extract_properties(self, code: str) -> List[Dict[str, Any]]:
        """Extract property definitions"""
        properties = []
        pattern = r'(?:public|private|internal|protected|static|virtual|override)?\s*([\w<>,\s\[\]]+)\s+(\w+)\s*\{\s*(?:get|set)'
        
        for match in re.finditer(pattern, code):
            prop_type = match.group(1).strip()
            prop_name = match.group(2)
            
            prop_info = {
                "name": prop_name,
                "type": prop_type,
                "modifiers": self._extract_modifiers(match.group(0))
            }
            properties.append(prop_info)
        
        return properties
    
    def _extract_fields(self, code: str) -> List[Dict[str, Any]]:
        """Extract field definitions"""
        fields = []
        pattern = r'(?:public|private|internal|protected|static|readonly|const)?\s*([\w<>,\s\[\]]+)\s+(\w+)\s*(?:=\s*[^;]+)?;'
        
        for match in re.finditer(pattern, code):
            field_type = match.group(1).strip()
            field_name = match.group(2)
            
            field_info = {
                "name": field_name,
                "type": field_type,
                "modifiers": self._extract_modifiers(match.group(0))
            }
            fields.append(field_info)
        
        return fields
    
    def _extract_modifiers(self, declaration: str) -> List[str]:
        """Extract access and other modifiers"""
        modifiers = []
        modifier_keywords = ['public', 'private', 'internal', 'protected', 'static', 'virtual', 'override', 'abstract', 'sealed', 'partial', 'async', 'readonly', 'const']
        for mod in modifier_keywords:
            if mod in declaration:
                modifiers.append(mod)
        return modifiers
    
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







