"""Technical documentation generator"""

from typing import List, Dict, Any, Optional
import re
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from .config import Config
from .readers import FileReader, FolderReader, GitReader
from .parsers import (
    JavaParser,
    CSharpParser,
    VBNetParser,
    FSharpParser,
    PHPParser,
    JavaScriptParser,
    TypeScriptParser,
    MarkupParser,
    ConfigParser
)
from .llm.llm_factory import LLMFactory
from .sequence_diagram import SequenceDiagramGenerator
from .dependency_analyzer import DependencyAnalyzer
from .template_engine import TemplateEngine
from .flow_extractors import MassTransitFlowExtractor, AmqplibFlowExtractor, InfraConfigFlowExtractor
from .streaming_writer import StreamingDocWriter
from .correlation_analyzer import build_correlation_signals, build_correlation_mermaid
from .call_graph_analyzer import build_csharp_class_call_graphs
from .service_catalog import build_service_catalog
from .app_sequence_diagram import build_app_sequence_diagram
from .architecture_synthesizer import ArchitectureSynthesizer


class DocumentationGenerator:
    """Main class for generating technical documentation"""
    
    def __init__(self, config_path: Optional[str] = None, llm_provider: Optional[str] = None):
        self.config = Config(config_path)
        self.llm_provider = llm_provider or self.config.get_default_provider()
        self.llm = LLMFactory.create(self.llm_provider, self.config.config)
        
        # Initialize parsers
        self.parsers = self._build_parsers(self.config.config)
        
        # Initialize sequence diagram generator
        self.sequence_diagram_gen = SequenceDiagramGenerator(self.config.config)
        
        # Initialize dependency analyzer
        self.dependency_analyzer = DependencyAnalyzer(self.config.config)
        
        # Initialize template engine
        template_dir = self.config.config.get("documentation", {}).get("template_dir")
        template_name = self.config.config.get("documentation", {}).get("template", "confluence.md")
        self.template_engine = TemplateEngine(template_dir, self.config.config)
        self.template_name = template_name
        
        # Ensure default template exists
        self.template_engine.create_default_template()
        
        # Chunking and streaming
        doc_config = self.config.config.get("documentation", {})
        self.chunk_size_chars = doc_config.get("chunk_size_chars", 0)
        self.chunk_overlap_chars = doc_config.get("chunk_overlap_chars", 0)
        self.streaming_mode = doc_config.get("streaming_mode", False)
        
        # Messaging flow extractor
        self.mass_transit_extractor = MassTransitFlowExtractor()
        self.amqplib_extractor = AmqplibFlowExtractor()
        self.infra_config_extractor = InfraConfigFlowExtractor()
    
    def generate_from_file(self, file_path: str, progress_callback=None) -> str:
        """Generate documentation from a single file"""
        reader = FileReader(file_path, self.config.config)
        files = reader.read()
        return self._generate_docs(files, progress_callback)
    
    def generate_from_folder(self, folder_path: str, progress_callback=None) -> str:
        """Generate documentation from a folder"""
        reader = FolderReader(folder_path, self.config.config)
        files = reader.read()
        return self._generate_docs(files, progress_callback)
    
    def generate_from_git(self, repo_path: str, branch: Optional[str] = None, progress_callback=None) -> str:
        """Generate documentation from a Git repository"""
        reader = GitReader(repo_path, branch, self.config.config)
        files = reader.read()
        return self._generate_docs(files, progress_callback)
    
    def _get_reader(self, source_type: str, source: str, branch: Optional[str] = None, config_override: Optional[Dict[str, Any]] = None):
        """Get appropriate reader for source type"""
        config = config_override or self.config.config
        if source_type == 'file':
            return FileReader(source, config)
        elif source_type == 'folder':
            return FolderReader(source, config)
        elif source_type == 'git':
            return GitReader(source, branch, config)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
    
    def generate_docs_from_files(self, files: List[Dict[str, Any]], progress_callback=None) -> str:
        """Generate documentation from already-read files"""
        return self._generate_docs(files, progress_callback)

    def generate_architecture_docs_from_files(
        self,
        files: List[Dict[str, Any]],
        doc_structure_name: str = "generic",
        output_path: Optional[str] = None,
        progress_callback=None,
        llm_override=None,
        llm_provider_override: Optional[str] = None
    ) -> str:
        """Generate architecture-centric documentation from already-read files"""
        return self._generate_architecture_docs(
            files,
            doc_structure_name=doc_structure_name,
            output_path=output_path,
            progress_callback=progress_callback,
            llm_override=llm_override,
            llm_provider_override=llm_provider_override
        )
    
    def generate_docs_streaming(self, reader, output_path: str, progress_callback=None, llm_override=None, llm_provider_override: Optional[str] = None, chunk_size_chars: Optional[int] = None, chunk_overlap_chars: Optional[int] = None, parsers_override: Optional[Dict[str, Any]] = None) -> Path:
        """Generate documentation in streaming mode to handle large repos"""
        llm = llm_override or self.llm
        model_name = getattr(llm, "model", "")
        llm_provider = llm_provider_override or self.llm_provider
        writer = StreamingDocWriter(output_path, llm_provider, model_name)
        chunk_size_chars = self.chunk_size_chars if chunk_size_chars is None else chunk_size_chars
        chunk_overlap_chars = self.chunk_overlap_chars if chunk_overlap_chars is None else chunk_overlap_chars
        parsers = parsers_override or self.parsers
        
        processed_files = 0
        integration_records = []
        for file_info in reader.iter_files():
            language = file_info["language"]
            if language == "unknown":
                continue
            parser = parsers.get(language)
            if not parser:
                continue
            processed_files += 1
            if progress_callback:
                progress_callback(processed_files, None, file_info.get("name", "Unknown"))
            
            try:
                processed = self._process_file(
                    file_info,
                    parser,
                    language,
                    llm,
                    chunk_size_chars=chunk_size_chars,
                    chunk_overlap_chars=chunk_overlap_chars
                )
                if processed.get("messaging_flows"):
                    integration_records.append({
                        "source_type": processed["messaging_flows"].get("source_type"),
                        "file": file_info.get("relative_path", file_info.get("path", "")),
                        "flows": processed["messaging_flows"]
                    })
                writer.write_file_section(processed, language)
            except Exception as e:
                error_msg = str(e) if str(e) else type(e).__name__
                writer.write_file_section({
                    "name": file_info.get("name", "Unknown"),
                    "path": file_info.get("path", ""),
                    "relative_path": file_info.get("relative_path", file_info.get("path", "")),
                    "documentation": f"*Error processing file: {error_msg}*",
                    "parsed_info": {"classes": [], "functions": [], "imports": []},
                    "sequence_diagram": None
                }, language)
        
        integration_graph = self._build_integration_graph(integration_records)
        message_types = []
        for record in integration_records:
            flows = record.get("flows", {})
            if record.get("source_type") == "masstransit":
                for msg in flows.get("publishes", []) or []:
                    message_types.append({"message": msg, "service": record.get("file", "")})
                for msg in flows.get("sends", []) or []:
                    message_types.append({"message": msg, "service": record.get("file", "")})
                for cons in flows.get("consumer_messages", []) or []:
                    if cons.get("message"):
                        message_types.append({"message": cons.get("message"), "consumer": cons.get("consumer", "")})
        app_sequence_diagram = build_app_sequence_diagram(
            {"controllers": [], "services": [], "interfaces": [], "endpoints": [], "controller_dependencies": {}},
            messaging_flows,
            message_types
        )
        writer.finalize(
            integration_graph=integration_graph,
            app_sequence_diagram=app_sequence_diagram
        )
        return Path(output_path)
    
    def _generate_docs(self, files: List[Dict[str, Any]], progress_callback=None, template_name: Optional[str] = None, llm_override=None, llm_provider_override: Optional[str] = None, chunk_size_chars: Optional[int] = None, chunk_overlap_chars: Optional[int] = None, parsers_override: Optional[Dict[str, Any]] = None) -> str:
        """Generate documentation from parsed files using templates"""
        if not files:
            return "# Technical Documentation\n\n**TechDocGen by IBMC**\n\nNo source files found."
        
        llm = llm_override or self.llm
        llm_provider = llm_provider_override or self.llm_provider
        template_name = template_name or self.template_name
        chunk_size_chars = self.chunk_size_chars if chunk_size_chars is None else chunk_size_chars
        chunk_overlap_chars = self.chunk_overlap_chars if chunk_overlap_chars is None else chunk_overlap_chars
        parsers = parsers_override or self.parsers
        
        # Analyze dependencies if enabled
        dependency_analysis = None
        dependency_map_markdown = None
        dependency_graph_mermaid = None
        include_dep_map = self.config.config.get("documentation", {}).get("include_dependency_map", False)
        include_visualization = self.config.config.get("output", {}).get("include_architecture_diagram", False)
        if (include_dep_map or include_visualization) and len(files) > 1:
            try:
                dependency_analysis = self.dependency_analyzer.analyze_files(files, self.parsers)
                if include_dep_map:
                    dependency_map_markdown = self.dependency_analyzer.generate_markdown_report()
                if include_visualization:
                    dependency_graph_mermaid = self.dependency_analyzer.generate_mermaid_block()
            except Exception as e:
                # Silently fail dependency analysis - don't break documentation
                pass
        
        # Group files by language
        files_by_language = {}
        for file_info in files:
            lang = file_info["language"]
            if lang not in files_by_language:
                files_by_language[lang] = []
            files_by_language[lang].append(file_info)
        
        # Count total files for progress tracking
        total_files = sum(len(lang_files) for lang_files in files_by_language.values() if lang_files)
        processed_files = 0
        
        # Process each file to generate documentation and parse structure
        processed_files_by_language = {}
        messaging_flows = []
        integration_records = []
        
        for language, lang_files in files_by_language.items():
            if language == "unknown":
                continue
            
            processed_files_by_language[language] = []
            
            # Get parser for this language
            parser = parsers.get(language)
            if not parser:
                continue
            
            # Process each file sequentially
            for file_info in lang_files:
                file_name = file_info.get('name', 'Unknown')
                processed_files += 1
                
                # Report progress
                if progress_callback:
                    progress_callback(processed_files, total_files, file_name)
                
                try:
                    processed = self._process_file(
                        file_info,
                        parser,
                        language,
                        llm,
                        chunk_size_chars=chunk_size_chars,
                        chunk_overlap_chars=chunk_overlap_chars
                    )
                    parsed_info = processed["parsed_info"]
                    llm_doc = processed["documentation"]
                    file_messaging = processed.get("messaging_flows")
                    if file_messaging:
                        integration_records.append({
                            "source_type": file_messaging.get("source_type"),
                            "file": file_info.get("relative_path", file_info.get("path", "")),
                            "flows": file_messaging
                        })
                        if file_messaging.get("flows"):
                            for flow in file_messaging["flows"]:
                                messaging_flows.append({
                                    "queue": flow.get("queue"),
                                    "consumers": flow.get("consumers", []),
                                    "sagas": flow.get("sagas", []),
                                    "file": file_info.get("relative_path", file_info.get("path", ""))
                                })
                    
                    # Generate sequence diagram if enabled
                    sequence_diagram = None
                    try:
                        classes = parsed_info.get("classes", [])
                        include_diagram = self.config.config.get("documentation", {}).get("include_sequence_diagrams", True)
                        
                        if include_diagram and len(classes) > 0:
                            # Try simple diagram first (more reliable)
                            sequence_diagram = self.sequence_diagram_gen.generate_sequence_diagram(
                                parsed_info, file_info["content"], language
                            )
                            
                            # Only try LLM if simple diagram not available and we have multiple classes
                            if not sequence_diagram and len(classes) > 1:
                                sequence_diagram = self.sequence_diagram_gen.generate_from_llm_analysis(
                                    parsed_info, file_info["content"], self.llm
                                )
                    except Exception:
                        # Silently fail diagram generation
                        pass
                    
                    # Prepare file data for template
                    processed_file_info = {
                        "name": file_name,
                        "path": file_info.get("path", ""),
                        "relative_path": file_info.get("relative_path", file_info.get("path", "")),
                        "documentation": llm_doc,
                        "parsed_info": parsed_info,
                        "sequence_diagram": sequence_diagram,
                        "messaging_flows": processed.get("messaging_flows"),
                        "call_graphs": processed.get("call_graphs", [])
                    }
                    
                    processed_files_by_language[language].append(processed_file_info)
                    
                except Exception as e:
                    import traceback
                    error_msg = str(e) if str(e) else type(e).__name__
                    # Create error file info for template
                    processed_file_info = {
                        "name": file_name,
                        "path": file_info.get("path", ""),
                        "relative_path": file_info.get("relative_path", file_info.get("path", "")),
                        "documentation": f"*Error processing file: {error_msg}*\n\n<details><summary>Error Details</summary>\n\n```\n{traceback.format_exc()}\n```\n\n</details>",
                        "parsed_info": {"classes": [], "functions": [], "imports": []},
                        "sequence_diagram": None,
                        "call_graphs": []
                    }
                    processed_files_by_language[language].append(processed_file_info)
        
        # Prepare template context
        # Get model name from LLM instance
        model_name = getattr(llm, 'model', '')
        integration_graph = self._build_integration_graph(integration_records)
        service_catalog = build_service_catalog(
            files,
            self.dependency_analyzer if dependency_analysis else None
        )
        message_types = []
        for record in integration_records:
            flows = record.get("flows", {})
            if record.get("source_type") == "masstransit":
                for msg in flows.get("publishes", []) or []:
                    message_types.append({"message": msg, "service": record.get("file", "")})
                for msg in flows.get("sends", []) or []:
                    message_types.append({"message": msg, "service": record.get("file", "")})
                for cons in flows.get("consumer_messages", []) or []:
                    if cons.get("message"):
                        message_types.append({"message": cons.get("message"), "consumer": cons.get("consumer", "")})
        app_sequence_diagram = build_app_sequence_diagram(
            service_catalog,
            messaging_flows,
            message_types
        )
        correlation_signals = build_correlation_signals(
            files,
            dependency_analysis["dependency_map"] if dependency_analysis else None
        )
        correlation_graph = build_correlation_mermaid(correlation_signals)
        template_context = {
            "llm_provider": llm_provider,
            "model_name": model_name,
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total_files,
            "files_by_language": processed_files_by_language,
            "dependency_map": dependency_map_markdown,
            "dependency_graph": dependency_graph_mermaid,
            "languages": [lang for lang in processed_files_by_language.keys() if lang != "unknown"],
            "messaging_flows": messaging_flows,
            "integration_graph": integration_graph,
            "service_catalog": service_catalog,
            "app_sequence_diagram": app_sequence_diagram,
            "correlation_signals": correlation_signals,
            "correlation_graph": correlation_graph
        }
        
        # Render template
        try:
            # Try to use specified template, fallback to default if not found
            documentation = self.template_engine.render(template_name, template_context)
        except Exception as e:
            # If template rendering fails, fallback to default template
            try:
                documentation = self.template_engine.render("default.md", template_context)
            except Exception:
                # Last resort: return basic documentation
                model_name = getattr(llm, 'model', '')
                local_prefix = "local " if llm_provider == 'ollama' else ""
                return f"# Technical Documentation\n\n**TechDocGen by IBMC**\n\nModel Use : {local_prefix}{model_name}\n\nError rendering template: {str(e)}"
        
        return documentation
    
    def _process_file(self, file_info: Dict[str, Any], parser, language: str, llm, chunk_size_chars: Optional[int] = None, chunk_overlap_chars: Optional[int] = None) -> Dict[str, Any]:
        """Parse and generate documentation for a single file, with chunking support"""
        content = file_info["content"]
        messaging_flows = self._extract_messaging_flows(content, language)
        call_graphs = []
        if language == "csharp":
            try:
                call_graphs = build_csharp_class_call_graphs(content)
            except Exception:
                call_graphs = []
        
        chunk_size_chars = self.chunk_size_chars if chunk_size_chars is None else chunk_size_chars
        chunk_overlap_chars = self.chunk_overlap_chars if chunk_overlap_chars is None else chunk_overlap_chars
        chunks = self._chunk_content(content, chunk_size_chars, chunk_overlap_chars)
        docs = []
        parsed_infos = []
        chunk_total = len(chunks)
        
        for idx, chunk in enumerate(chunks, 1):
            parsed_info = parser.parse(chunk)
            if messaging_flows:
                parsed_info["messaging_flows"] = messaging_flows
            chunk_meta = {"index": idx, "total": chunk_total} if chunk_total > 1 else None
            llm_doc = llm.generate_documentation(parsed_info, language, chunk_meta)
            parsed_infos.append(parsed_info)
            docs.append(llm_doc)
        
        merged_info = self._merge_parsed_info(parsed_infos)
        if messaging_flows:
            merged_info["messaging_flows"] = messaging_flows
        
        if len(docs) == 1:
            documentation = docs[0]
        else:
            documentation = "\n\n".join(
                f"#### Chunk {i + 1}/{chunk_total}\n\n{doc}" for i, doc in enumerate(docs)
            )
        
        return {
            "name": file_info.get("name", "Unknown"),
            "path": file_info.get("path", ""),
            "relative_path": file_info.get("relative_path", file_info.get("path", "")),
            "documentation": documentation,
            "parsed_info": merged_info,
            "messaging_flows": messaging_flows,
            "call_graphs": call_graphs
        }
    
    def _build_parsers(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build parser instances with provided config"""
        return {
            "java": JavaParser(config),
            "csharp": CSharpParser(config),
            "vbnet": VBNetParser(config),
            "fsharp": FSharpParser(config),
            "php": PHPParser(config),
            "javascript": JavaScriptParser(config),
            "typescript": TypeScriptParser(config),
            "markup": MarkupParser(config),
            "config": ConfigParser(config)
        }
    
    def _chunk_content(self, content: str, chunk_size_chars: int, chunk_overlap_chars: int) -> List[str]:
        """Chunk content for large files"""
        if not chunk_size_chars or len(content) <= chunk_size_chars:
            return [content]
        chunks = []
        start = 0
        overlap = max(chunk_overlap_chars or 0, 0)
        while start < len(content):
            end = min(len(content), start + chunk_size_chars)
            chunks.append(content[start:end])
            if end >= len(content):
                break
            start = end - overlap if overlap else end
        return chunks
    
    def _merge_parsed_info(self, parsed_infos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge parsed info from multiple chunks"""
        merged: Dict[str, Any] = {}
        for info in parsed_infos:
            for key, value in info.items():
                if value is None or value == "":
                    continue
                if isinstance(value, list):
                    existing = merged.setdefault(key, [])
                    if value and isinstance(value[0], dict) and "name" in value[0]:
                        existing_names = {item.get("name") for item in existing if isinstance(item, dict)}
                        for item in value:
                            if item.get("name") not in existing_names:
                                existing.append(item)
                    else:
                        for item in value:
                            if item not in existing:
                                existing.append(item)
                elif key not in merged:
                    merged[key] = value
        return merged
    
    def _extract_messaging_flows(self, content: str, language: str) -> Optional[Dict[str, Any]]:
        """Extract messaging flows for supported languages"""
        if language == "csharp":
            if "MassTransit" in content or "ReceiveEndpoint" in content:
                flows = self.mass_transit_extractor.extract(content)
                flows["source_type"] = "masstransit"
                return flows
        if language in {"javascript", "typescript"}:
            if "amqplib" in content or ".publish(" in content or ".sendToQueue(" in content:
                flows = self.amqplib_extractor.extract(content)
                flows["source_type"] = "amqplib"
                return flows
        if language == "config":
            flows = self.infra_config_extractor.extract(content)
            if flows:
                flows["source_type"] = "infra_config"
                return flows
        return None

    def _build_integration_graph(self, integration_records: List[Dict[str, Any]]) -> Optional[str]:
        """Build a cross-stack integration graph (Mermaid)"""
        if not integration_records:
            return None
        
        exchanges = {}
        queues = {}
        bindings = []
        publishers = []
        consumers = []
        message_publishers = []
        message_consumers = []
        
        for record in integration_records:
            flows = record.get("flows", {})
            source_type = record.get("source_type")
            file_id = record.get("file", "unknown")
            
            if source_type == "infra_config":
                for ex in flows.get("exchanges", []) or []:
                    name = ex.get("name")
                    if name:
                        exchanges[name] = ex.get("type", "")
                for q in flows.get("queues", []) or []:
                    name = q.get("name")
                    if name:
                        queues[name] = q.get("durable", False)
                for b in flows.get("bindings", []) or []:
                    bindings.append({
                        "exchange": b.get("exchange"),
                        "queue": b.get("queue"),
                        "routing_key": b.get("routing_key", "")
                    })
            
            if source_type == "amqplib":
                for ex in flows.get("exchanges", []) or []:
                    name = ex.get("name")
                    if name:
                        exchanges[name] = ex.get("type", "")
                for q in flows.get("queues", []) or []:
                    name = q.get("name")
                    if name:
                        queues[name] = True
                for b in flows.get("bindings", []) or []:
                    bindings.append({
                        "exchange": b.get("exchange"),
                        "queue": b.get("queue"),
                        "routing_key": b.get("routing_key", "")
                    })
                for pub in flows.get("publishes", []) or []:
                    publishers.append({
                        "service": file_id,
                        "exchange": pub.get("exchange"),
                        "routing_key": pub.get("routing_key", "")
                    })
                for send in flows.get("send_to_queue", []) or []:
                    publishers.append({
                        "service": file_id,
                        "queue": send.get("queue")
                    })
                for cons in flows.get("consumes", []) or []:
                    consumers.append({
                        "queue": cons.get("queue"),
                        "service": file_id
                    })
            
            if source_type == "masstransit":
                for flow in flows.get("flows", []) or []:
                    queue = flow.get("queue")
                    if queue:
                        queues[queue] = True
                        consumers.append({
                            "queue": queue,
                            "service": ", ".join(flow.get("consumers", [])) or file_id
                        })
                for msg in flows.get("publishes", []) or []:
                    message_publishers.append({
                        "message": msg,
                        "service": file_id
                    })
                for msg in flows.get("sends", []) or []:
                    message_publishers.append({
                        "message": msg,
                        "service": file_id
                    })
                for cons in flows.get("consumer_messages", []) or []:
                    if cons.get("message"):
                        message_consumers.append({
                            "message": cons.get("message"),
                            "consumer": cons.get("consumer") or file_id
                        })
                for send_ep in flows.get("send_endpoints", []) or []:
                    if isinstance(send_ep, str) and send_ep.startswith("queue:"):
                        queue_name = send_ep.split("queue:", 1)[1]
                        publishers.append({
                            "service": file_id,
                            "queue": queue_name
                        })
        
        if not (exchanges or queues or bindings or publishers or consumers or message_publishers or message_consumers):
            return None
        
        mermaid = ["```mermaid", "graph LR"]
        added_nodes = set()
        for ex, ex_type in sorted(exchanges.items()):
            ex_label = self._safe_label(ex)
            label = f"{ex_label} ({self._safe_label(ex_type)})" if ex_type else ex_label
            node_id = f"EX_{self._safe_id(ex)}"
            if node_id not in added_nodes:
                mermaid.append(f'  {node_id}["Exchange {label}"]')
                added_nodes.add(node_id)
        for q in sorted(queues.keys()):
            node_id = f"Q_{self._safe_id(q)}"
            if node_id not in added_nodes:
                mermaid.append(f'  {node_id}["Queue {self._safe_label(q)}"]')
                added_nodes.add(node_id)
        
        for bind in bindings:
            ex = bind.get("exchange")
            q = bind.get("queue")
            rk = bind.get("routing_key")
            if not ex or not q:
                continue
            mermaid.append(f"  EX_{self._safe_id(ex)} --> Q_{self._safe_id(q)}")
        
        for pub in publishers:
            service = pub.get("service", "unknown")
            svc_id = self._safe_id(service)
            node_id = f"S_{svc_id}"
            if node_id not in added_nodes:
                mermaid.append(f'  {node_id}["Service {self._safe_label(service)}"]')
                added_nodes.add(node_id)
            if pub.get("exchange"):
                mermaid.append(f"  {node_id} --> EX_{self._safe_id(pub['exchange'])}")
            if pub.get("queue"):
                mermaid.append(f"  {node_id} --> Q_{self._safe_id(pub['queue'])}")
        
        for cons in consumers:
            service = cons.get("service", "unknown")
            svc_id = self._safe_id(service)
            node_id = f"S_{svc_id}"
            if node_id not in added_nodes:
                mermaid.append(f'  {node_id}["Service {self._safe_label(service)}"]')
                added_nodes.add(node_id)
            queue = cons.get("queue")
            if queue:
                mermaid.append(f"  Q_{self._safe_id(queue)} --> {node_id}")

        for pub in message_publishers:
            message = pub.get("message")
            service = pub.get("service", "unknown")
            if not message:
                continue
            msg_id = self._safe_id(f"MSG_{message}")
            svc_id = self._safe_id(service)
            msg_node = f"MSG_{msg_id}"
            if msg_node not in added_nodes:
                mermaid.append(f'  {msg_node}["Message {self._safe_label(message)}"]')
                added_nodes.add(msg_node)
            mermaid.append(f"  S_{svc_id} --> {msg_node}")

        for cons in message_consumers:
            message = cons.get("message")
            consumer = cons.get("consumer", "unknown")
            if not message:
                continue
            msg_id = self._safe_id(f"MSG_{message}")
            cons_id = self._safe_id(consumer)
            msg_node = f"MSG_{msg_id}"
            cons_node = f"C_{cons_id}"
            if msg_node not in added_nodes:
                mermaid.append(f'  {msg_node}["Message {self._safe_label(message)}"]')
                added_nodes.add(msg_node)
            if cons_node not in added_nodes:
                mermaid.append(f'  {cons_node}["Consumer {self._safe_label(consumer)}"]')
                added_nodes.add(cons_node)
            mermaid.append(f"  {msg_node} --> {cons_node}")
        
        mermaid.append("```")
        return "\n".join(mermaid)

    def _safe_id(self, value: str) -> str:
        """Create a safe Mermaid node id"""
        return "".join(ch if ch.isalnum() else "_" for ch in value)

    def _safe_label(self, value: str) -> str:
        text = str(value or "")
        text = re.sub(r'[\[\]"`<>|]', '', text)
        text = text.replace("\\", " ")
        text = text.replace("\n", " ").replace("\r", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text or "label"
    
    def generate_from_domain(self, domain_name: str, output_path: Optional[str] = None, streaming: Optional[bool] = None) -> Path:
        """Generate documentation for a configured domain profile"""
        domains = self.config.config.get("domains", [])
        domain = next((d for d in domains if d.get("name") == domain_name), None)
        if not domain:
            raise ValueError(f"Domain '{domain_name}' not found in config.yaml")
        
        domain_type = domain.get("type", "folder")
        source = domain.get("source") or domain.get("path")
        if not source:
            raise ValueError(f"Domain '{domain_name}' missing 'source' or 'path'")
        
        domain_config = deepcopy(self.config.config)
        doc_config = domain_config.get("documentation", {})
        if domain.get("exclude_patterns") is not None:
            doc_config["exclude_patterns"] = domain.get("exclude_patterns")
        if domain.get("include_patterns") is not None:
            doc_config["include_patterns"] = domain.get("include_patterns")
        if domain.get("chunk_size_chars") is not None:
            doc_config["chunk_size_chars"] = domain.get("chunk_size_chars")
        if domain.get("chunk_overlap_chars") is not None:
            doc_config["chunk_overlap_chars"] = domain.get("chunk_overlap_chars")
        if domain.get("streaming_mode") is not None:
            doc_config["streaming_mode"] = domain.get("streaming_mode")
        domain_config["documentation"] = doc_config
        
        if domain.get("extensions"):
            domain_config["extensions"] = domain.get("extensions")
        if domain.get("languages"):
            domain_config["languages"] = domain.get("languages")
        
        template_name = domain.get("template", self.template_name)
        doc_structure_name = domain.get("doc_structure")
        streaming = doc_config.get("streaming_mode") if streaming is None else streaming
        output_path = output_path or domain.get("output") or str(Path("./docs") / f"{domain_name}_technical_docs.md")
        chunk_size_chars = doc_config.get("chunk_size_chars", self.chunk_size_chars)
        chunk_overlap_chars = doc_config.get("chunk_overlap_chars", self.chunk_overlap_chars)
        
        reader = self._get_reader(domain_type, source, domain.get("branch"), config_override=domain_config)
        
        llm_provider = domain.get("provider", self.llm_provider)
        llm = self.llm if llm_provider == self.llm_provider else LLMFactory.create(llm_provider, domain_config)
        domain_parsers = self._build_parsers(domain_config)
        
        # Check if domain uses architecture-centric documentation
        doc_structure_name = domain.get("doc_structure")
        
        if doc_structure_name:
            # Use architecture-centric documentation mode
            files = reader.read()
            documentation = self._generate_architecture_docs(
                files,
                doc_structure_name=doc_structure_name,
                output_path=output_path,
                llm_override=llm,
                llm_provider_override=llm_provider
            )
            return self.save_documentation(documentation, output_path)
        
        if doc_structure_name:
            files = reader.read()
            documentation = self.generate_architecture_docs_from_files(
                files,
                doc_structure_name=doc_structure_name,
                output_path=output_path,
                llm_override=llm,
                llm_provider_override=llm_provider
            )
            return self.save_documentation(documentation, output_path)

        if streaming:
            return self.generate_docs_streaming(
                reader,
                output_path,
                llm_override=llm,
                llm_provider_override=llm_provider,
                chunk_size_chars=chunk_size_chars,
                chunk_overlap_chars=chunk_overlap_chars,
                parsers_override=domain_parsers
            )
        
        files = reader.read()
        documentation = self._generate_docs(
            files,
            template_name=template_name,
            llm_override=llm,
            llm_provider_override=llm_provider,
            chunk_size_chars=chunk_size_chars,
            chunk_overlap_chars=chunk_overlap_chars,
            parsers_override=domain_parsers
        )
        return self.save_documentation(documentation, output_path)
    
    def generate_all_domains(self) -> List[Path]:
        """Generate documentation for all configured domain profiles"""
        outputs = []
        for domain in self.config.config.get("domains", []):
            name = domain.get("name")
            if not name:
                continue
            outputs.append(self.generate_from_domain(name))
        return outputs
    
    def generate_architecture_docs(
        self,
        source_path: str,
        doc_structure_name: str = "generic",
        output_path: Optional[str] = None,
        progress_callback=None
    ) -> str:
        """
        Generate architecture-centric documentation using document structure templates
        
        This method synthesizes documentation organized by architectural concerns
        rather than by individual files.
        
        Args:
            source_path: Path to source folder
            doc_structure_name: Name of document structure (e.g., 'dotnet-cqrs', 'generic')
            output_path: Optional output file path
            progress_callback: Optional progress callback
            
        Returns:
            Generated documentation string
        """
        # Read source files
        reader = FolderReader(source_path, self.config.config)
        files = reader.read()
        
        if not files:
            return "# Architecture Documentation\n\n**TechDocGen by IBMC**\n\nNo source files found."
        
        return self._generate_architecture_docs(
            files, doc_structure_name, output_path, progress_callback
        )
    
    def _generate_architecture_docs(
        self,
        files: List[Dict[str, Any]],
        doc_structure_name: str = "generic",
        output_path: Optional[str] = None,
        progress_callback=None,
        llm_override=None,
        llm_provider_override: Optional[str] = None
    ) -> str:
        """
        Internal method to generate architecture documentation from files
        
        Args:
            files: List of file dictionaries
            doc_structure_name: Name of document structure
            output_path: Optional output file path
            progress_callback: Optional progress callback
            llm_override: Optional LLM override
            llm_provider_override: Optional LLM provider override
            
        Returns:
            Generated documentation string
        """
        llm = llm_override or self.llm
        llm_provider = llm_provider_override or self.llm_provider
        model_name = getattr(llm, 'model', '')
        
        # Initialize architecture synthesizer
        synthesizer = ArchitectureSynthesizer(llm, self.config.config)
        
        # Load document structure
        try:
            doc_structure = synthesizer.load_doc_structure(doc_structure_name)
        except FileNotFoundError as e:
            return f"# Error\n\nDocument structure not found: {e}"
        
        # Group files by language
        files_by_language = {}
        for file_info in files:
            lang = file_info["language"]
            if lang not in files_by_language:
                files_by_language[lang] = []
            files_by_language[lang].append(file_info)
        
        # Process files to get parsed info
        processed_files_by_language = {}
        messaging_flows = []
        integration_records = []
        
        total_files = sum(len(lang_files) for lang_files in files_by_language.values() if lang_files)
        processed_count = 0
        
        for language, lang_files in files_by_language.items():
            if language == "unknown":
                continue
            
            processed_files_by_language[language] = []
            parser = self.parsers.get(language)
            if not parser:
                continue
            
            for file_info in lang_files:
                processed_count += 1
                file_name = file_info.get('name', 'Unknown')
                
                if progress_callback:
                    progress_callback(processed_count, total_files, f"Parsing: {file_name}")
                
                try:
                    parsed_info = parser.parse(file_info["content"])
                    file_messaging = self._extract_messaging_flows(file_info["content"], language)
                    
                    if file_messaging:
                        integration_records.append({
                            "source_type": file_messaging.get("source_type"),
                            "file": file_info.get("relative_path", file_info.get("path", "")),
                            "flows": file_messaging
                        })
                        if file_messaging.get("flows"):
                            for flow in file_messaging["flows"]:
                                messaging_flows.append({
                                    "queue": flow.get("queue"),
                                    "consumers": flow.get("consumers", []),
                                    "sagas": flow.get("sagas", []),
                                    "file": file_info.get("relative_path", file_info.get("path", ""))
                                })
                    
                    processed_files_by_language[language].append({
                        "name": file_name,
                        "path": file_info.get("path", ""),
                        "relative_path": file_info.get("relative_path", file_info.get("path", "")),
                        "parsed_info": parsed_info,
                        "messaging_flows": file_messaging
                    })
                except Exception:
                    processed_files_by_language[language].append({
                        "name": file_name,
                        "path": file_info.get("path", ""),
                        "relative_path": file_info.get("relative_path", file_info.get("path", "")),
                        "parsed_info": {"classes": [], "functions": [], "imports": []},
                        "messaging_flows": None
                    })
        
        # Build service catalog
        service_catalog = build_service_catalog(
            files,
            self.dependency_analyzer if self.config.config.get("documentation", {}).get("include_dependency_map", False) else None
        )
        
        # Build integration graph
        integration_graph = self._build_integration_graph(integration_records)
        
        # Build app sequence diagram
        message_types = []
        for record in integration_records:
            flows = record.get("flows", {})
            if record.get("source_type") == "masstransit":
                for msg in flows.get("publishes", []) or []:
                    message_types.append({"message": msg, "service": record.get("file", "")})
                for msg in flows.get("sends", []) or []:
                    message_types.append({"message": msg, "service": record.get("file", "")})
                for cons in flows.get("consumer_messages", []) or []:
                    if cons.get("message"):
                        message_types.append({"message": cons.get("message"), "consumer": cons.get("consumer", "")})
        
        app_sequence_diagram = build_app_sequence_diagram(
            service_catalog,
            messaging_flows,
            message_types
        )
        
        # Synthesize architecture documentation
        if progress_callback:
            progress_callback(processed_count, total_files, "Synthesizing architecture documentation...")
        
        synthesized_structure = synthesizer.synthesize(
            doc_structure,
            files,
            processed_files_by_language,
            service_catalog,
            messaging_flows,
            progress_callback
        )
        
        # Prepare template context
        template_context = {
            "llm_provider": llm_provider,
            "model_name": model_name,
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total_files,
            "files_by_language": processed_files_by_language,
            "languages": [lang for lang in processed_files_by_language.keys() if lang != "unknown"],
            "messaging_flows": messaging_flows,
            "integration_graph": integration_graph if synthesized_structure.get('show_integration_graph', True) else None,
            "service_catalog": service_catalog,
            "app_sequence_diagram": app_sequence_diagram if synthesized_structure.get('show_sequence_diagram', True) else None,
            "doc_structure": synthesized_structure,
            "show_file_reference": synthesized_structure.get('show_file_reference', True)
        }
        
        # Render template
        template_name = doc_structure.get('template', 'architecture.md')
        try:
            documentation = self.template_engine.render(template_name, template_context)
        except Exception as e:
            # Fallback to basic output
            documentation = self._fallback_architecture_render(synthesized_structure, template_context)
        
        return documentation
    
    def _fallback_architecture_render(
        self,
        doc_structure: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Fallback rendering if template fails"""
        parts = [
            f"# {doc_structure.get('title', 'Architecture Documentation')}\n",
            f"**Generated by:** TechDocGen by IBMC\n",
            f"**Model Use:** {context.get('llm_provider', '')} {context.get('model_name', '')}\n",
            f"**Generation Date:** {context.get('generation_date', '')}\n",
            "---\n"
        ]
        
        for section in doc_structure.get('sections', []):
            parts.append(f"\n# {section.get('title', 'Section')}\n")
            if section.get('content'):
                parts.append(f"{section['content']}\n")
            
            for subsection in section.get('subsections', []):
                parts.append(f"\n## {subsection.get('title', 'Subsection')}\n")
                if subsection.get('content'):
                    parts.append(f"{subsection['content']}\n")
        
        return '\n'.join(parts)
    
    def get_available_doc_structures(self) -> List[str]:
        """Get list of available document structure configurations"""
        synthesizer = ArchitectureSynthesizer(self.llm, self.config.config)
        return synthesizer.get_available_structures()
    
    def save_documentation(self, documentation: str, output_path: Optional[str] = None) -> Path:
        """Save documentation to file"""
        if output_path:
            output_file = Path(output_path)
        else:
            output_dir = Path(self.config.get("output.directory", "./docs"))
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = self.config.get("output.filename_template", "technical_docs.md")
            output_file = output_dir / filename
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(documentation)
        
        return output_file
    
    def generate_dependency_map(self, files: List[Dict[str, Any]], format: str = "json", output_path: Optional[str] = None) -> Path:
        """
        Generate dependency map from files
        
        Args:
            files: List of file dictionaries
            format: Output format ('json', 'dot', 'mermaid', 'markdown')
            output_path: Optional output file path
            
        Returns:
            Path to generated dependency map file
        """
        # Analyze dependencies
        analysis = self.dependency_analyzer.analyze_files(files, self.parsers)
        
        # Determine output path
        if not output_path:
            output_dir = Path(self.config.get("output.directory", "./docs"))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            ext_map = {
                "json": ".json",
                "dot": ".dot",
                "mermaid": ".mmd",
                "markdown": ".md"
            }
            ext = ext_map.get(format, ".json")
            output_path = str(output_dir / f"dependency_map{ext}")
        
        # Export based on format
        if format == "json":
            return self.dependency_analyzer.export_json(output_path)
        elif format == "dot":
            return self.dependency_analyzer.export_dot(output_path)
        elif format == "mermaid":
            return self.dependency_analyzer.export_mermaid(output_path)
        elif format == "markdown":
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(self.dependency_analyzer.generate_markdown_report())
            return output_file
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json', 'dot', 'mermaid', or 'markdown'")

