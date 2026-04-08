# Deployment Guide

## Deployment Options

| Method | Use Case | Complexity |
|--------|----------|------------|
| Docker Compose | Development, staging | Low |
| Kubernetes | Production, multi-region | High |
| Manual | Single-node, testing | Medium |

---

## Docker Compose Deployment

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 8 GB RAM minimum
- 20 GB free disk space

### 1. Configure Environment

```bash
cd cps-enterprise-dcs
cp .env.example .env
```

Edit `.env` and set secure values for:

```bash
POSTGRES_PASSWORD=<strong-password>
DCS_MASTER_KEY=$(openssl rand -base64 32)
VAULT_TOKEN=<vault-token>
```

### 2. Start Services

```bash
# From the repo root
make docker-up

# Or directly:
docker-compose -f cps-enterprise-dcs/infrastructure/docker-compose.yml up -d
```

### 3. Verify Health

```bash
make docker-ps

# Check individual service logs
make docker-logs
```

### 4. Access Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| POS Interface | http://localhost:3000 | Demo: any/any |
| Grafana | http://localhost:3001 | admin/admin |
| Prometheus | http://localhost:9090 | — |
| Vault UI | http://localhost:8200 | Token from `.env` |
| PostgreSQL | localhost:5432 | From `.env` |

### Services Started

The Docker Compose stack runs these services:

| Service | Image | Ports |
|---------|-------|-------|
| PostgreSQL 16 | `postgres:16-alpine` | 5432 |
| Redis 7 | `redis:7-alpine` | 6379 |
| HashiCorp Vault | `hashicorp/vault:1.15` | 8200 |
| Zookeeper | `confluentinc/cp-zookeeper:7.5.0` | 2181 |
| Kafka | `confluentinc/cp-kafka:7.5.0` | 9092 |
| Prometheus | `prom/prometheus:v2.48.0` | 9090 |
| Grafana | `grafana/grafana:10.2.0` | 3001 |
| Regional Agent | Go custom build | 12000, 12001, 50052 |
| Local Agent | Python custom build | 50051 |
| POS Interface | React custom build | 3000 |
| Nginx | `nginx:alpine` | 80, 443 |

### Stop Services

```bash
make docker-down

# Or to stop and remove volumes:
docker-compose -f cps-enterprise-dcs/infrastructure/docker-compose.yml down -v
```

---

## Manual Deployment

### PostgreSQL Event Store

1. Install PostgreSQL 16+
2. Create the database and apply the schema:

```bash
createdb dcs_eventstore
psql -d dcs_eventstore -f cps-enterprise-dcs/event-store/schema.sql
```

### Redis

```bash
redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Regional Agent

```bash
cd cps-enterprise-dcs/regional-agent
go build -o bin/regional-agent ./...

# Configure via environment variables
export DCS_AGENT_ID=regional-001
export DCS_REGION_ID=region-001
export DCS_RPC_ADDR=:12000
export DCS_RAFT_ADDR=:12001
export DCS_GRPC_PORT=50052
export DCS_POSTGRESQL_URL=postgres://dcs_admin:password@localhost:5432/dcs_eventstore?sslmode=disable
export DCS_REDIS_URL=localhost:6379
export DCS_BOOTSTRAP=true

./bin/regional-agent
```

### Local Agent

```bash
cd cps-enterprise-dcs/local-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DCS_AGENT_ID=local-001
export DCS_BRANCH_ID=BR001
export DCS_REGION_ID=region-001
export DCS_GRPC_PORT=50051
export DCS_REGIONAL_ENDPOINT=localhost:50052

python -m src.main
```

### POS Interface

```bash
cd cps-enterprise-dcs/pos-interface
npm install
npm run build

# Serve with any static file server
npx serve dist -l 3000
```

---

## Production Checklist

### Security

- [ ] Replace Vault dev mode with production seal/unseal configuration
- [ ] Generate and configure TLS certificates for all services
- [ ] Set strong passwords for PostgreSQL (`POSTGRES_PASSWORD`)
- [ ] Generate a production master key (`DCS_MASTER_KEY`)
- [ ] Enable encryption (`ENABLE_ENCRYPTION=true`)
- [ ] Enable audit logging (`ENABLE_AUDIT_LOG=true`)
- [ ] Configure network policies to restrict inter-service access
- [ ] Set up certificate rotation

### Database

- [ ] Configure PostgreSQL connection pooling (PgBouncer)
- [ ] Set up automated backups for the event store
- [ ] Configure WAL archiving for point-in-time recovery
- [ ] Review and test the partitioning strategy for event_store
- [ ] Create additional audit_log partitions beyond the initial months

### Kafka

- [ ] Set replication factor > 1 for production topics
- [ ] Configure retention policies for event topics
- [ ] Set up Kafka monitoring (consumer lag, partition health)
- [ ] Configure `KAFKA_ADVERTISED_LISTENERS` for your network

### Monitoring

- [ ] Configure Prometheus scrape targets for all agents
- [ ] Import Grafana dashboards for DCS metrics
- [ ] Set up alerting rules (PagerDuty, Slack, email)
- [ ] Configure log aggregation (ELK, Loki)
- [ ] Set up distributed tracing (OpenTelemetry → Jaeger)

### High Availability

- [ ] Deploy 3+ Regional Agent nodes for Raft quorum
- [ ] Configure PostgreSQL streaming replication
- [ ] Set up Redis Sentinel or Redis Cluster
- [ ] Deploy multiple Kafka brokers
- [ ] Configure load balancing for POS interfaces

### Performance

- [ ] Tune `SYNC_INTERVAL` based on network conditions
- [ ] Adjust `BATCH_SIZE` for event streaming throughput
- [ ] Set `MAX_CONNECTIONS` based on expected concurrency
- [ ] Configure Redis `maxmemory` based on available RAM
- [ ] Review PostgreSQL `shared_buffers` and `work_mem`

---

## Scaling

### Horizontal Scaling

- **POS Interface**: Stateless — deploy behind a load balancer
- **Local Agent**: One per branch — scales with number of branches
- **Regional Agent**: Raft cluster — minimum 3 nodes per region, odd numbers preferred
- **PostgreSQL**: Read replicas for query offloading; partitioning for write throughput

### Multi-Region

```
Region A                    Region B
┌──────────────────┐       ┌──────────────────┐
│ Regional Agent   │◄─────►│ Regional Agent   │
│ (Raft Cluster)   │ gRPC  │ (Raft Cluster)   │
├──────────────────┤       ├──────────────────┤
│ Local Agent x N  │       │ Local Agent x N  │
│ POS x N          │       │ POS x N          │
│ PostgreSQL       │       │ PostgreSQL       │
│ Redis            │       │ Redis            │
│ Kafka            │       │ Kafka            │
└──────────────────┘       └──────────────────┘
```

Each region runs its own full stack. Cross-region communication happens at the Regional Agent level via gRPC.

---

## Backup & Recovery

### Event Store Backup

```bash
# Full backup
pg_dump -Fc dcs_eventstore > dcs_eventstore_$(date +%Y%m%d).dump

# Restore
pg_restore -d dcs_eventstore dcs_eventstore_20240101.dump
```

### Docker Volume Backup

```bash
# Backup PostgreSQL data
docker run --rm -v dcs_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .

# Backup Redis data
docker run --rm -v dcs_redis_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/redis_data.tar.gz -C /data .
```

### Recovery Strategy

Since DCS uses event sourcing, the event store is the primary recovery target. All other state (projections, CRDT states, saga states) can be rebuilt by replaying events from the event store.

1. Restore the PostgreSQL event store from backup
2. Restart all agents — they will rebuild local state from the event store
3. CRDT states will reconverge automatically as agents sync
