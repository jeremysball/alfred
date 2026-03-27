# Project Omega

## Overview
Real-time data processing pipeline with ML inference.

## Architecture
- **Ingestion**: Kafka streams
- **Processing**: Rust workers
- **Inference**: ONNX Runtime
- **Storage**: TimescaleDB

## Quick Start
```bash
cargo build --release
./scripts/setup.sh
cargo run --bin omega-server
```

## Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KAFKA_BROKERS` | Yes | - | Comma-separated broker list |
| `MODEL_PATH` | Yes | - | Path to ONNX model |
| `DB_URL` | Yes | - | TimescaleDB connection string |
| `WORKER_THREADS` | No | 4 | Number of worker threads |
| `BATCH_SIZE` | No | 128 | Inference batch size |

## Monitoring
- Metrics: Prometheus on `:9090/metrics`
- Health: `:8080/health`
- Traces: Jaeger collector

## License
MIT