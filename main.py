#!/usr/bin/env python3
"""
TechDocGen by IBMC - Technical Documentation Generator
SRS-compliant CLI (IF-02): scan, catalog, diagram commands
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def _resolve_repos(ctx, param, value):
    """Collect multiple --repo values for FR-17 multi-repository support"""
    if value is None:
        return []
    # Store in ctx.ensure_object for multiple invocations
    repos = list(ctx.ensure_object(dict).get("repos", []) or [])
    if value:
        repos.append(value)
    ctx.ensure_object(dict)["repos"] = repos
    return value


def _get_repos(ctx):
    return ctx.ensure_object(dict).get("repos", []) or []


def _read_multi_repo_files(repos, branch, config, generator):
    """FR-17: Read files from multiple repositories"""
    from src.readers import GitReader, FolderReader
    all_files = []
    for repo in repos:
        path = Path(repo)
        if path.exists() and path.is_dir():
            if (path / ".git").exists():
                reader = GitReader(repo, branch, config)
            else:
                reader = FolderReader(repo, config)
        else:
            reader = GitReader(repo, branch, config)
        files = reader.read()
        for f in files:
            f["_repo"] = repo
        all_files.extend(files)
    return all_files


@click.group()
@click.option('--config', '-c', help='Path to config.yaml file')
@click.option('--provider', '-p', type=click.Choice(['ollama', 'mcp'], case_sensitive=False),
              help='LLM provider to use')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, provider, verbose):
    """TechDocGen - AI-Powered Technical Documentation Generator for CoreTax"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["provider"] = provider
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option('--repo', '-r', 'repos', multiple=True, required=True,
              help='Path(s) to Git repository (repeat for multi-repo - FR-17)')
@click.option('--domain', '-d', help='Probis/domain name for focused analysis (FR-15)')
@click.option('--verbosity', '-v', type=click.Choice(['concise', 'detailed'], case_sensitive=False),
              default='detailed', help='Concise=diagram-heavy; Detailed=full narrative (FR-14)')
@click.option('--output-dir', '-o', type=click.Path(), default='./docs',
              help='Output directory for documentation')
@click.option('--format', '-f', 'output_format', type=click.Choice(['md', 'pdf', 'both'], case_sensitive=False),
              default='md', help='Output format: md, pdf, or both')
@click.option('--branch', '-b', help='Git branch to use')
@click.option('--doc-structure', help='Document structure (e.g., dotnet-cqrs, generic)')
@click.option('--stream', is_flag=True, help='Stream output for large repos')
@click.pass_context
def scan(ctx, repos, domain, verbosity, output_dir, output_format, branch, doc_structure, stream):
    """
    Scan repository and generate documentation (SRS IF-02).
    
    Supports multi-repository (FR-17), Probis-oriented analysis (FR-15),
    and configurable verbosity (FR-14).
    """
    console.print("[bold blue]TechDocGen[/bold blue] - Scanning repository...\n")
    try:
        from src.generator import DocumentationGenerator
        generator = DocumentationGenerator(config_path=ctx.obj["config"], llm_provider=ctx.obj["provider"])
        
        # Apply verbosity to config (FR-14)
        generator.config.config.setdefault("documentation", {})["verbosity"] = verbosity
        
        if domain:
            # FR-15: Probis-oriented - use domain profile from config
            output_path = str(Path(output_dir) / f"{domain}_technical_docs.md")
            out = generator.generate_from_domain(domain, output_path=output_path, streaming=stream)
            console.print(f"[bold green]✓ Documentation generated![/bold green]")
            console.print(f"[dim]Output: {out.absolute()}[/dim]")
            _maybe_generate_pdf(output_format, str(out), output_dir)
            return
        
        # Read from single or multiple repos (FR-17)
        files = _read_multi_repo_files(list(repos), branch, generator.config.config, generator)
        if not files:
            raise ValueError("No source files found in repository")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Generating documentation...", total=None)
            if doc_structure:
                docs = generator.generate_architecture_docs_from_files(
                    files, doc_structure_name=doc_structure, output_path=str(Path(output_dir) / "technical_docs.md"),
                    progress_callback=lambda c, t, m: progress.update(task, description=m)
                )
            else:
                docs = generator.generate_docs_from_files(files)
            progress.update(task, description="Saving...")
            out_path = Path(output_dir) / "technical_docs.md"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_file = generator.save_documentation(docs, str(out_path))
        
        console.print(f"[bold green]✓ Documentation generated![/bold green]")
        console.print(f"[dim]Output: {out_file.absolute()}[/dim]")
        _maybe_generate_pdf(output_format, str(out_file), output_dir)
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


@cli.command()
@click.option('--repo', '-r', 'repos', multiple=True, required=True,
              help='Path(s) to Git repository')
@click.option('--output-dir', '-o', type=click.Path(), default='./docs',
              help='Output directory for service catalog')
@click.option('--branch', '-b', help='Git branch to use')
@click.pass_context
def catalog(ctx, repos, output_dir, branch):
    """
    Generate service catalog (SRS FR-12, IF-02).
    
    Produces catalog of microservices, endpoints, event subscriptions, and dependencies.
    """
    console.print("[bold blue]TechDocGen[/bold blue] - Generating service catalog...\n")
    try:
        from src.generator import DocumentationGenerator
        generator = DocumentationGenerator(config_path=ctx.obj["config"], llm_provider=ctx.obj["provider"])
        files = _read_multi_repo_files(list(repos), branch, generator.config.config, generator)
        if not files:
            raise ValueError("No source files found")
        
        catalog_data = generator.dependency_analyzer.analyze_files(files, generator.parsers)
        from src.service_catalog import build_service_catalog
        service_catalog = build_service_catalog(files, generator.dependency_analyzer)
        
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "service_catalog.md"
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# Service Catalog\n\n")
            f.write(f"*Generated by TechDocGen - {len(files)} files analyzed*\n\n")
            if service_catalog.get("controllers"):
                f.write("## Controllers\n\n")
                for c in service_catalog["controllers"]:
                    f.write(f"- **{c.get('name')}** Route: {c.get('route', '')}\n")
            if service_catalog.get("endpoints"):
                f.write("\n## API Endpoints\n\n")
                for ep in service_catalog["endpoints"]:
                    verbs = ", ".join(ep.get("http_verbs", []))
                    f.write(f"- {verbs} {ep.get('route', '')} -> {ep.get('controller')}.{ep.get('method')}\n")
            if service_catalog.get("services"):
                f.write("\n## Services\n\n")
                f.write(", ".join(service_catalog["services"]) + "\n")
        
        console.print(f"[bold green]✓ Service catalog generated![/bold green]")
        console.print(f"[dim]Output: {out_path.absolute()}[/dim]")
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        raise click.Abort()


@cli.command()
@click.option('--repo', '-r', 'repos', multiple=True, required=True, help='Path to repository')
@click.option('--type', '-t', 'diagram_type', type=click.Choice(['sequence', 'architecture', 'integration']),
              default='sequence', help='Diagram type (SRS IF-02)')
@click.option('--service', '-s', help='Service name to focus on')
@click.option('--output-dir', '-o', type=click.Path(), default='./docs',
              help='Output directory')
@click.option('--branch', '-b', help='Git branch to use')
@click.pass_context
def diagram(ctx, repos, diagram_type, service, output_dir, branch):
    """
    Generate diagram: sequence, architecture, or integration (SRS FR-09, FR-10, FR-11, IF-02).
    """
    console.print(f"[bold blue]TechDocGen[/bold blue] - Generating {diagram_type} diagram...\n")
    try:
        from src.generator import DocumentationGenerator
        generator = DocumentationGenerator(config_path=ctx.obj["config"], llm_provider=ctx.obj["provider"])
        files = _read_multi_repo_files(list(repos), branch, generator.config.config, generator)
        if not files:
            raise ValueError("No source files found")
        
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        if diagram_type == "sequence":
            from src.service_catalog import build_service_catalog
            from src.app_sequence_diagram import build_app_sequence_diagram
            catalog = build_service_catalog(files, generator.dependency_analyzer)
            messaging_flows = []
            message_types = []
            for f in files:
                flows = generator._extract_messaging_flows(f.get("content", ""), f.get("language", ""))
                if flows and flows.get("flows"):
                    for fl in flows["flows"]:
                        messaging_flows.append({
                            "queue": fl.get("queue"),
                            "consumers": fl.get("consumers", []),
                            "sagas": fl.get("sagas", []),
                            "file": f.get("relative_path", f.get("path", ""))
                        })
                if flows and flows.get("source_type") == "masstransit":
                    for msg in (flows.get("publishes") or []) + (flows.get("sends") or []):
                        message_types.append({"message": msg, "service": f.get("relative_path", "")})
                    for c in (flows.get("consumer_messages") or []):
                        if c.get("message"):
                            message_types.append({"message": c["message"], "consumer": c.get("consumer", "")})
            mermaid = build_app_sequence_diagram(catalog, messaging_flows, message_types)
            out_path = out_dir / ("sequence_diagram.md" if service else "sequence_diagram.md")
            with open(out_path, "w") as f:
                f.write("# Sequence Diagram\n\n")
                f.write(mermaid or "No sequence diagram generated.")
        
        elif diagram_type == "architecture":
            analysis = generator.dependency_analyzer.analyze_files(files, generator.parsers)
            mermaid = generator.dependency_analyzer.generate_mermaid_block()
            out_path = out_dir / "architecture_diagram.md"
            with open(out_path, "w") as f:
                f.write("# Clean Architecture Diagram\n\n")
                f.write(mermaid or "No architecture diagram generated.")
        
        elif diagram_type == "integration":
            integration_records = []
            for f in files:
                flows = generator._extract_messaging_flows(f.get("content", ""), f.get("language", ""))
                if flows:
                    integration_records.append({"source_type": flows.get("source_type"), "file": f.get("relative_path", ""), "flows": flows})
            mermaid = generator._build_integration_graph(integration_records)
            out_path = out_dir / "integration_graph.md"
            with open(out_path, "w") as f:
                f.write("# Integration Graph (Messaging Topology)\n\n")
                f.write(mermaid or "No integration graph generated.")
        
        console.print(f"[bold green]✓ {diagram_type} diagram generated![/bold green]")
        console.print(f"[dim]Output: {out_dir.absolute()}[/dim]")
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


def _maybe_generate_pdf(output_format: str, md_path: str, output_dir: str):
    """Generate PDF if format is pdf or both"""
    if output_format not in ("pdf", "both"):
        return
    try:
        from src.pdf_generator import PDFGenerator
        pdf_gen = PDFGenerator()
        with open(md_path, "r") as f:
            content = f.read()
        pdf_bytes = pdf_gen.generate_pdf_from_markdown(content)
        pdf_path = Path(md_path).with_suffix(".pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes.getvalue())
        console.print(f"[dim]PDF: {pdf_path.absolute()}[/dim]")
    except Exception as e:
        console.print(f"[dim]PDF generation skipped: {e}[/dim]")


@cli.command()
@click.option('--source', '-s', help='Source path: file, folder, or git URL')
@click.option('--output', '-o', help='Output file path')
@click.option('--branch', '-b', help='Git branch')
@click.option('--domain', help='Domain profile name (Probis - FR-15)')
@click.option('--all-domains', is_flag=True, help='Generate for all domain profiles')
@click.option('--doc-structure', help='Document structure (e.g., dotnet-cqrs)')
@click.option('--list-structures', is_flag=True, help='List available document structures')
@click.option('--dep-map', is_flag=True, help='Generate dependency map')
@click.option('--stream', is_flag=True, help='Stream output for large repos')
@click.pass_context
def generate(ctx, source, output, branch, domain, all_domains, doc_structure, list_structures, dep_map, stream):
    """
    Generate documentation (legacy interface). For repos use: scan --repo <path>.
    """
    from src.generator import DocumentationGenerator
    config = ctx.obj.get("config")
    provider = ctx.obj.get("provider")
    gen = DocumentationGenerator(config_path=config, llm_provider=provider)
    console.print("[bold blue]TechDocGen[/bold blue]\n")
    
    if list_structures:
        for s in gen.get_available_doc_structures():
            console.print(f"  - {s}")
        return
    
    if not source and not domain and not all_domains:
        raise click.BadParameter("Provide --source or --domain/--all-domains. Or use: scan --repo <path>")
    
    if domain or all_domains:
        if all_domains:
            for out in gen.generate_all_domains():
                console.print(f"[green]✓[/green] {out}")
        else:
            out = gen.generate_from_domain(domain, output_path=output, streaming=stream)
            console.print(f"[green]✓[/green] {out}")
        return
    
    source_type = 'folder'
    if source:
        p = Path(source)
        if source.startswith(('http', 'git@')) or source.endswith('.git'):
            source_type = 'git'
        elif p.is_file():
            source_type = 'file'
        elif p.is_dir():
            source_type = 'git' if (p / ".git").exists() else 'folder'
        else:
            source_type = 'git'  # assume remote URL
    
    reader = gen._get_reader(source_type, source, branch)
    if dep_map:
        files = reader.read()
        dep_file = gen.generate_dependency_map(files)
        console.print(f"[green]✓[/green] Dependency map: {dep_file}")
    if stream:
        out = gen.generate_docs_streaming(reader, output or "./docs/technical_docs.md")
    else:
        files = reader.read()
        docs = gen.generate_docs_from_files(files)
        out = gen.save_documentation(docs, output)
    console.print(f"[green]✓[/green] {out}")


if __name__ == '__main__':
    cli()
