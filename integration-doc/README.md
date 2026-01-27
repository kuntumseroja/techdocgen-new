# Integration Demo

This folder contains a minimal, cross-stack demo for the new capabilities:

- Node.js RabbitMQ producer/consumer (amqplib)
- C# MassTransit consumer + publisher
- Infra JSON/YAML for exchanges/queues/bindings
- Integration graph output in generated docs

## Run docgen on this folder

```bash
python main.py --source ./integration-doc --type folder --output ./docs/integration_demo.md
```

## What you should see

- Messaging flows extracted from Node.js and C# code
- Infra config mapping from YAML/JSON
- A merged Integration Graph section (Mermaid)
