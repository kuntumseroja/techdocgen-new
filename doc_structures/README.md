# Document Structure Configurations

This directory contains YAML configuration files that define **architecture-centric documentation structures**.

## What is a Document Structure?

A document structure defines:
1. **Sections** - The high-level architecture topics to document
2. **Subsections** - Detailed breakdowns within each section
3. **Prompts** - Instructions for the LLM to generate content for each section
4. **Display Options** - What additional information to include

## Available Structures

| File | Description | Best For |
|------|-------------|----------|
| `generic.yaml` | Generic architecture documentation | Most projects |
| `dotnet-cqrs.yaml` | .NET CQRS-style systems | MassTransit, RabbitMQ, EF Core projects |

## Creating Custom Structures

1. Copy `generic.yaml` to a new file (e.g., `my-project.yaml`)
2. Modify the sections to match your architecture
3. Update prompts to guide the LLM for your specific patterns
4. Reference it in your domain configuration

### Example Usage

In `config.yaml`:

```yaml
domains:
  - name: "my-service"
    type: "folder"
    path: "./my-service"
    doc_structure: "my-project.yaml"  # Reference your custom structure
    template: "architecture.md"
```

Or via CLI:

```bash
python main.py --source ./my-project --doc-structure dotnet-cqrs.yaml
```

## Section Configuration

Each section supports:

```yaml
sections:
  - id: unique-id           # Unique identifier
    title: "Section Title"  # Display title
    prompt: |               # LLM prompt for this section
      Describe...
    subsections:            # Optional nested sections
      - id: sub-id
        title: "Subsection Title"
        prompt: |
          Describe...
```

## Prompt Best Practices

1. **Be specific** - Tell the LLM exactly what to look for
2. **Use bullet points** - Structure what you want documented
3. **Reference patterns** - Mention specific patterns/frameworks to look for
4. **Guide the output** - Describe the expected format

### Good Prompt Example

```yaml
prompt: |
  Describe the messaging configuration:
  - RabbitMQ connection settings (host, credentials)
  - MassTransit consumer registration
  - Queue naming conventions
  - Error handling and retry policies
```

### Bad Prompt Example

```yaml
prompt: "Describe the messaging."  # Too vague
```

## Display Options

```yaml
show_file_reference: true    # Show source files list
show_integration_graph: true # Show Mermaid integration diagram
show_sequence_diagram: true  # Show application sequence diagram
```
