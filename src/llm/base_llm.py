"""Base LLM interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLM(ABC):
    """Base class for all LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model", "")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 4000)
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using the LLM
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Generated text response
        """
        pass
    
    def generate_documentation(self, code_info: Dict[str, Any], language: str, chunk_meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate technical documentation for parsed code
        
        Args:
            code_info: Parsed code information
            language: Programming language
            
        Returns:
            Generated documentation
        """
        system_prompt = self._get_system_prompt(language)
        user_prompt = self._build_documentation_prompt(code_info, language, chunk_meta)
        return self.generate(user_prompt, system_prompt)
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt for documentation generation"""
        return f"""You are a technical documentation expert. Generate comprehensive, well-structured technical documentation for {language} source code.

Your documentation should include:
1. Overview and purpose
2. Architecture and structure
3. Key components (classes, functions, interfaces)
4. Usage examples
5. API documentation
6. Dependencies and imports

Format the output in clear, professional markdown with proper headings, code blocks, and explanations."""
    
    def _build_documentation_prompt(self, code_info: Dict[str, Any], language: str, chunk_meta: Optional[Dict[str, Any]] = None) -> str:
        """Build the prompt for documentation generation"""
        prompt = f"Generate technical documentation for the following {language} code:\n\n"
        
        if chunk_meta:
            chunk_index = chunk_meta.get("index", 1)
            chunk_total = chunk_meta.get("total", 1)
            prompt += f"Note: This is chunk {chunk_index} of {chunk_total} for a large file.\n\n"
        
        # Add namespace/package
        if "namespace" in code_info:
            prompt += f"Namespace: {code_info['namespace']}\n\n"
        elif "package" in code_info:
            prompt += f"Package: {code_info['package']}\n\n"
        
        # Add imports
        if "imports" in code_info and code_info["imports"]:
            prompt += f"Imports:\n" + "\n".join(f"- {imp}" for imp in code_info["imports"]) + "\n\n"
        elif "using" in code_info and code_info["using"]:
            prompt += f"Using statements:\n" + "\n".join(f"- {u}" for u in code_info["using"]) + "\n\n"
        elif "use" in code_info and code_info["use"]:
            prompt += f"Use statements:\n" + "\n".join(f"- {u}" for u in code_info["use"]) + "\n\n"
        
        # Add classes
        if "classes" in code_info and code_info["classes"]:
            prompt += "Classes:\n"
            for cls in code_info["classes"]:
                prompt += f"\n- {cls['name']}"
                if "extends" in cls and cls["extends"]:
                    prompt += f" extends {cls['extends']}"
                if "implements" in cls and cls["implements"]:
                    prompt += f" implements {', '.join(cls['implements'])}"
                if "inherits" in cls and cls["inherits"]:
                    prompt += f" : {', '.join(cls['inherits'])}"
                prompt += "\n"
                if "methods" in cls:
                    prompt += f"  Methods: {len(cls['methods'])}\n"
                if "fields" in cls:
                    prompt += f"  Fields: {len(cls['fields'])}\n"
                if "properties" in cls:
                    prompt += f"  Properties: {len(cls['properties'])}\n"
            prompt += "\n"
        
        # Add interfaces
        if "interfaces" in code_info and code_info["interfaces"]:
            prompt += "Interfaces:\n"
            for iface in code_info["interfaces"]:
                prompt += f"- {iface['name']}\n"
            prompt += "\n"

        # Add enums
        if "enums" in code_info and code_info["enums"]:
            prompt += "Enums:\n"
            for enum in code_info["enums"]:
                prompt += f"- {enum['name']}\n"
            prompt += "\n"

        # Add type aliases
        if "types" in code_info and code_info["types"]:
            prompt += "Type Aliases:\n"
            for type_alias in code_info["types"]:
                prompt += f"- {type_alias['name']}\n"
            prompt += "\n"
        
        # Add functions (for PHP)
        if "functions" in code_info and code_info["functions"]:
            prompt += f"Functions: {len(code_info['functions'])}\n\n"
        
        # Add messaging flows if available
        if "messaging_flows" in code_info and code_info["messaging_flows"]:
            flows = code_info["messaging_flows"]
            if flows.get("flows"):
                prompt += "Messaging Flows:\n"
                for flow in flows["flows"]:
                    consumers = ", ".join(flow.get("consumers", [])) or "N/A"
                    sagas = ", ".join(flow.get("sagas", [])) or "N/A"
                    prompt += f"- Queue {flow.get('queue')}: consumers={consumers}; sagas={sagas}\n"
                prompt += "\n"
            if flows.get("publishes"):
                prompt += f"Publishes: {', '.join(flows['publishes'])}\n\n"
            if flows.get("sends"):
                prompt += f"Sends: {', '.join(flows['sends'])}\n\n"
            if flows.get("send_endpoints"):
                prompt += f"Send endpoints: {', '.join(flows['send_endpoints'])}\n\n"
        
        # Add comments if available
        if "comments" in code_info and code_info["comments"]:
            prompt += f"Comments found: {len(code_info['comments'])}\n\n"
        
        prompt += "\nPlease generate comprehensive technical documentation for this code."
        return prompt







