"""Architecture documentation synthesizer

This module generates architecture-centric documentation by:
1. Loading document structure configurations
2. Synthesizing content for each section using LLM
3. Providing context to templates for rendering
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml


class ArchitectureSynthesizer:
    """Synthesizes architecture documentation from codebase analysis"""
    
    def __init__(self, llm, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the synthesizer
        
        Args:
            llm: LLM instance for generating content
            config: Optional configuration dictionary
        """
        self.llm = llm
        self.config = config or {}
        self.doc_structures_dir = Path(__file__).parent.parent / "doc_structures"
    
    def load_doc_structure(self, structure_name: str) -> Dict[str, Any]:
        """
        Load a document structure configuration
        
        Args:
            structure_name: Name of the structure file (e.g., 'dotnet-cqrs.yaml')
            
        Returns:
            Parsed structure configuration
        """
        # Handle both with and without .yaml extension
        if not structure_name.endswith('.yaml') and not structure_name.endswith('.yml'):
            structure_name = f"{structure_name}.yaml"
        
        structure_path = self.doc_structures_dir / structure_name
        
        if not structure_path.exists():
            # Try to find by name field
            for yaml_file in self.doc_structures_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        content = yaml.safe_load(f)
                        if content and content.get('name') == structure_name.replace('.yaml', ''):
                            return content
                except Exception:
                    continue
            
            raise FileNotFoundError(
                f"Document structure '{structure_name}' not found in {self.doc_structures_dir}"
            )
        
        with open(structure_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_available_structures(self) -> List[str]:
        """Get list of available document structure files"""
        structures = []
        if self.doc_structures_dir.exists():
            for yaml_file in self.doc_structures_dir.glob("*.yaml"):
                if yaml_file.name != 'README.md':
                    structures.append(yaml_file.stem)
        return sorted(structures)
    
    def synthesize(
        self,
        doc_structure: Dict[str, Any],
        files: List[Dict[str, Any]],
        processed_files_by_language: Dict[str, List[Dict[str, Any]]],
        service_catalog: Optional[Dict[str, Any]] = None,
        messaging_flows: Optional[List[Dict[str, Any]]] = None,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Synthesize architecture documentation for all sections
        
        Args:
            doc_structure: Document structure configuration
            files: Raw file data with content
            processed_files_by_language: Processed file information by language
            service_catalog: Optional service catalog data
            messaging_flows: Optional messaging flow data
            progress_callback: Optional callback for progress updates
            
        Returns:
            Document structure with synthesized content
        """
        # Build the codebase context for the LLM
        codebase_context = self._build_codebase_context(
            files, processed_files_by_language, service_catalog, messaging_flows
        )
        
        # Process each section
        sections = doc_structure.get('sections', [])
        total_sections = self._count_sections(sections)
        processed_count = 0
        
        synthesized_sections = []
        for section in sections:
            synthesized_section = self._synthesize_section(
                section, codebase_context, doc_structure
            )
            synthesized_sections.append(synthesized_section)
            
            # Update progress
            processed_count += 1
            if section.get('subsections'):
                processed_count += len(section['subsections'])
            
            if progress_callback:
                progress_callback(processed_count, total_sections, section.get('title', 'Unknown'))
        
        # Return enriched structure
        return {
            'title': doc_structure.get('title', doc_structure.get('name', 'Architecture Documentation')),
            'sections': synthesized_sections,
            'show_file_reference': doc_structure.get('show_file_reference', True),
            'show_integration_graph': doc_structure.get('show_integration_graph', True),
            'show_sequence_diagram': doc_structure.get('show_sequence_diagram', True)
        }
    
    def _count_sections(self, sections: List[Dict[str, Any]]) -> int:
        """Count total sections including subsections"""
        count = 0
        for section in sections:
            count += 1
            if section.get('subsections'):
                count += len(section['subsections'])
        return count
    
    def _build_codebase_context(
        self,
        files: List[Dict[str, Any]],
        processed_files_by_language: Dict[str, List[Dict[str, Any]]],
        service_catalog: Optional[Dict[str, Any]] = None,
        messaging_flows: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build a comprehensive codebase context for the LLM"""
        context_parts = []
        
        # Project structure
        context_parts.append("## Project Structure\n")
        files_by_project = self._group_files_by_project(files)
        for project, project_files in files_by_project.items():
            context_parts.append(f"\n### {project}\n")
            for f in project_files:
                context_parts.append(f"- {f.get('relative_path', f.get('path', 'unknown'))}")
        
        # File contents (summarized)
        context_parts.append("\n\n## File Contents\n")
        for file_info in files:
            rel_path = file_info.get('relative_path', file_info.get('path', 'unknown'))
            content = file_info.get('content', '')
            
            # Truncate very long files
            if len(content) > 8000:
                content = content[:8000] + "\n... (truncated)"
            
            context_parts.append(f"\n### {rel_path}\n```\n{content}\n```\n")
        
        # Service catalog
        if service_catalog:
            context_parts.append("\n## Service Catalog\n")
            if service_catalog.get('controllers'):
                context_parts.append("### Controllers\n")
                for ctrl in service_catalog['controllers']:
                    route = ctrl.get('route', '')
                    context_parts.append(f"- {ctrl['name']}{f' (Route: {route})' if route else ''}")
            
            if service_catalog.get('endpoints'):
                context_parts.append("\n### Endpoints\n")
                for ep in service_catalog['endpoints']:
                    verbs = ', '.join(ep.get('http_verbs', []))
                    context_parts.append(f"- {verbs} {ep.get('route', '')} -> {ep.get('controller', '')}.{ep.get('method', '')}")
            
            if service_catalog.get('services'):
                context_parts.append(f"\n### Services\n{', '.join(service_catalog['services'])}")
            
            if service_catalog.get('interfaces'):
                context_parts.append(f"\n### Interfaces\n{', '.join(service_catalog['interfaces'])}")
        
        # Messaging flows
        if messaging_flows:
            context_parts.append("\n## Messaging Flows\n")
            for flow in messaging_flows:
                queue = flow.get('queue', 'unknown')
                consumers = ', '.join(flow.get('consumers', []))
                context_parts.append(f"- Queue: {queue} -> Consumers: {consumers}")
        
        return '\n'.join(context_parts)
    
    def _group_files_by_project(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group files by their project/directory"""
        grouped = {}
        for file_info in files:
            path = file_info.get('relative_path', file_info.get('path', ''))
            parts = path.split('/')
            project = parts[0] if len(parts) > 1 else 'root'
            
            if project not in grouped:
                grouped[project] = []
            grouped[project].append(file_info)
        
        return grouped
    
    def _synthesize_section(
        self,
        section: Dict[str, Any],
        codebase_context: str,
        doc_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize content for a single section"""
        result = {
            'id': section.get('id', ''),
            'title': section.get('title', ''),
            'description': section.get('description', ''),
            'content': '',
            'subsections': []
        }
        
        # Generate content for the main section if it has a prompt
        if section.get('prompt'):
            result['content'] = self._generate_section_content(
                section['title'],
                section['prompt'],
                codebase_context
            )
        
        # Process subsections
        if section.get('subsections'):
            for subsection in section['subsections']:
                sub_result = {
                    'id': subsection.get('id', ''),
                    'title': subsection.get('title', ''),
                    'content': ''
                }
                
                if subsection.get('prompt'):
                    sub_result['content'] = self._generate_section_content(
                        subsection['title'],
                        subsection['prompt'],
                        codebase_context
                    )
                
                result['subsections'].append(sub_result)
        
        return result
    
    def _generate_section_content(
        self,
        section_title: str,
        prompt: str,
        codebase_context: str
    ) -> str:
        """Generate content for a section using the LLM"""
        system_prompt = """You are a technical documentation expert writing architecture documentation.

Your task is to analyze the provided codebase and write a specific documentation section.

Guidelines:
- Write clear, professional prose (not bullet points unless specifically appropriate)
- Be concise but comprehensive
- Reference specific files, classes, and methods when relevant
- Include code examples or configuration snippets when helpful
- Focus on the architectural aspects and design decisions
- Explain the "why" not just the "what"

Do NOT include markdown headers in your response (the section title is provided separately).
Write as continuous prose with occasional sub-points where appropriate."""

        user_prompt = f"""# Section: {section_title}

## Instructions
{prompt}

## Codebase Context
{codebase_context}

Please write the documentation for the "{section_title}" section based on the codebase context provided."""

        try:
            return self.llm.generate(user_prompt, system_prompt)
        except Exception as e:
            return f"*Error generating content: {str(e)}*"
    
    def synthesize_quick(
        self,
        doc_structure: Dict[str, Any],
        files: List[Dict[str, Any]],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Quick synthesis using minimal context (faster, less accurate)
        
        Args:
            doc_structure: Document structure configuration
            files: Raw file data with content
            progress_callback: Optional callback for progress updates
            
        Returns:
            Document structure with synthesized content
        """
        return self.synthesize(
            doc_structure, files, {}, None, None, progress_callback
        )


def load_doc_structure_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load a document structure from a file path
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Parsed structure configuration
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
