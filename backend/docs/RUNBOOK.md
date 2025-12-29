# Operations Runbook

> **Last Updated**: December 2025  
> **Audience**: On-call engineers, DevOps team  
> **Severity Levels**: P1 (Critical), P2 (High), P3 (Medium), P4 (Low)

## Table of Contents

- [Quick Reference](#quick-reference)
- [Service Overview](#service-overview)
- [Health Checks](#health-checks)
- [Common Incidents](#common-incidents)
- [Database Operations](#database-operations)
- [Job Management](#job-management)
- [Scaling](#scaling)
- [Maintenance Procedures](#maintenance-procedures)

---

## Quick Reference

### Service URLs

| Service | Port | Health Check | Docs |
|---------|------|--------------|------|
| Analytics | 8001 | `/health` | `/docs` |
| Data | 8002 | `/health` | `/docs` |
| Auth | 8003 | `/health` | `/docs` |

### Critical Commands

```bash
# Check all services
curl http://localhost:8001/health && \
curl http://localhost:8002/health && \
curl http://localhost:8003/health

# View error logs
tail -f logs/*-error.log

# Restart service
make service_analytics  # or service_data, service_auth

# Database status
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'google_analytics_db';"

# Kill stuck jobs
uv run python scripts/cancel_running_jobs.py
```

### Escalation Path

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| P1 | 15 minutes | Page on-call → Team Lead → Manager |
| P2 | 1 hour | Slack alert → On-call |
| P3 | 4 hours | Ticket → On-call |
| P4 | 24 hours | Ticket → Team |

---

## Service Overview

### Architecture

```
                    ┌─────────────────┐
                    │     Nginx       │
                    │  (Port 80/443)  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Auth      │     │   Data      │     │  Analytics  │
  │   :8003     │     │   :8002     │     │   :8001     │
  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │    :5432        │
                    └─────────────────┘
```

### Dependencies

| Service | External Dependencies |
|---------|----------------------|
| Auth | External IdP, PostgreSQL |
| Data | BigQuery, SFTP, PostgreSQL |
| Analytics | PostgreSQL, SMTP |

---

## Health Checks

### Service Health

```bash
# Check individual service
curl -s http://localhost:8001/health | jq .

# Expected response
{
  "service": "analytics-service",
  "version": "0.0.1",
  "status": "healthy",
  "timestamp": 1700000000.0
}
```

### Database Health

```bash
# Check connection count
psql -c "SELECT count(*) as connections, state FROM pg_stat_activity WHERE datname = 'google_analytics_db' GROUP BY state;"

# Check long-running queries
psql -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE datname = 'google_analytics_db' AND state != 'idle' AND now() - pg_stat_activity.query_start > interval '5 minutes';"

# Check table sizes
psql -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;"
```

### External Service Health

```bash
# Check BigQuery connectivity (requires valid tenant)
curl -X GET "http://localhost:8002/api/v1/availability" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"

# Check external IdP
curl -s "https://idp.example.com/health" | jq .
```

---

## Common Incidents

### INC-001: Service Not Responding (P1)

**Symptoms**:
- Health check returns non-200
- Connection refused errors
- Timeout errors

**Diagnosis**:
```bash
# Check if process is running
ps aux | grep uvicorn

# Check port binding
lsof -i :8001

# Check logs
tail -100 logs/analytics-service-error.log
```

**Resolution**:
```bash
# Kill and restart
pkill -f "uvicorn services.analytics_service"
make service_analytics &

# If OOM suspected, check memory
free -h
docker stats  # if containerized
```

---

### INC-002: Database Connection Exhausted (P1)

**Symptoms**:
- "too many connections" errors
- Slow API responses
- Connection timeout errors

**Diagnosis**:
```bash
# Check current connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'google_analytics_db';"

# Check connections by state
psql -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'google_analytics_db' GROUP BY state;"

# Check which services are connected
psql -c "SELECT application_name, count(*) FROM pg_stat_activity WHERE datname = 'google_analytics_db' GROUP BY application_name;"
```

**Resolution**:
```bash
# Kill idle connections older than 10 minutes
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'google_analytics_db' AND state = 'idle' AND query_start < now() - interval '10 minutes';"

# Reduce pool size in .env
DATABASE_POOL_SIZE=3
DATABASE_MAX_OVERFLOW=2

# Restart services
pkill -f uvicorn
make services_start
```

**Prevention**:
- Monitor connection count
- Set appropriate pool sizes
- Enable connection recycling

---

### INC-003: Ingestion Job Stuck (P2)

**Symptoms**:
- Job in "processing" state for > 30 minutes
- No progress in logs
- No new data appearing

**Diagnosis**:
```bash
# Check stuck jobs
psql -c "SELECT job_id, status, created_at, started_at, error_message FROM processing_jobs WHERE status = 'processing' AND started_at < now() - interval '30 minutes';"

# Check job progress in logs
grep "job_id_here" logs/data-ingestion-service.log | tail -50
```

**Resolution**:
```bash
# Cancel stuck jobs via script
uv run python scripts/cancel_running_jobs.py

# Or manually update status
psql -c "UPDATE processing_jobs SET status = 'failed', error_message = 'Manually cancelled - stuck', completed_at = now() WHERE job_id = 'job_id_here';"

# Restart data service
pkill -f "uvicorn services.data_service"
make service_data &
```

---

### INC-004: Email Sending Failure (P3)

**Symptoms**:
- Email jobs failing
- SMTP connection errors
- Zero emails sent

**Diagnosis**:
```bash
# Check email job status
psql -c "SELECT job_id, status, total_emails, emails_sent, emails_failed, error_message FROM email_sending_jobs ORDER BY created_at DESC LIMIT 5;"

# Check email history
psql -c "SELECT status, count(*) FROM email_send_history WHERE sent_at > now() - interval '1 day' GROUP BY status;"

# Check SMTP config
psql -c "SELECT id, name, email_config->>'server' as smtp_server FROM tenant_config WHERE id = 'tenant_id_here';"
```

**Resolution**:
```bash
# Verify SMTP credentials
telnet smtp.example.com 587

# Check firewall rules
nc -zv smtp.example.com 587

# Retry failed job
psql -c "UPDATE email_sending_jobs SET status = 'queued', error_message = NULL WHERE job_id = 'job_id_here';"
```

---

### INC-005: High API Latency (P3)

**Symptoms**:
- X-Process-Time > 2 seconds
- Dashboard loading slowly
- Timeout errors

**Diagnosis**:
```bash
# Check slow queries
psql -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '2 seconds';"

# Check table bloat
psql -c "SELECT relname, n_dead_tup, n_live_tup, round(n_dead_tup * 100.0 / (n_live_tup + 1)) as dead_percent FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;"

# Check missing indexes
psql -c "SELECT relname, seq_scan, idx_scan FROM pg_stat_user_tables WHERE seq_scan > 1000 ORDER BY seq_scan DESC LIMIT 10;"
```

**Resolution**:
```bash
# Run VACUUM ANALYZE
psql -c "VACUUM ANALYZE purchase;"
psql -c "VACUUM ANALYZE add_to_cart;"
psql -c "VACUUM ANALYZE page_view;"

# Update statistics
psql -c "ANALYZE;"

# Kill long-running queries
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';"
```

---

### INC-006: Authentication Failures (P2)

**Symptoms**:
- Users can't log in
- Token validation failing
- 401 errors on all requests

**Diagnosis**:
```bash
# Check auth service logs
tail -100 logs/auth-service-error.log

# Check external IdP connectivity
curl -v "https://idp.example.com/health"

# Check tenant config
psql -c "SELECT id, name, is_active FROM tenant_config WHERE id = 'tenant_id_here';"
```

**Resolution**:
```bash
# If IdP is down, wait for recovery

# If tenant disabled
psql -c "UPDATE tenant_config SET is_active = true WHERE id = 'tenant_id_here';"

# Restart auth service
pkill -f "uvicorn services.auth_service"
make service_auth &
```

---

## Database Operations

### Backup

```bash
# Full backup
pg_dump -h localhost -U analytics_user -Fc google_analytics_db > backup_$(date +%Y%m%d_%H%M%S).dump

# Table-specific backup
pg_dump -h localhost -U analytics_user -t purchase -Fc google_analytics_db > purchase_backup.dump
```

### Restore

```bash
# Full restore (WARNING: destructive)
pg_restore -h localhost -U analytics_user -d google_analytics_db --clean backup.dump

# Table-specific restore
pg_restore -h localhost -U analytics_user -d google_analytics_db -t purchase backup.dump
```

### Schema Updates

```bash
# Apply new functions
uv run python scripts/init_db.py

# Manual migration
psql -f database/migrations/001_add_column.sql
```

### Data Cleanup

```bash
# Delete old job records (> 90 days)
psql -c "DELETE FROM processing_jobs WHERE created_at < now() - interval '90 days';"

# Delete old email history (> 1 year)
psql -c "DELETE FROM email_send_history WHERE sent_at < now() - interval '1 year';"

# Vacuum after delete
psql -c "VACUUM ANALYZE processing_jobs; VACUUM ANALYZE email_send_history;"
```

---

## Job Management

### View Running Jobs

```bash
# All processing jobs
psql -c "SELECT job_id, tenant_id, status, data_types, start_date, end_date, created_at, started_at FROM processing_jobs WHERE status IN ('queued', 'processing') ORDER BY created_at DESC;"

# All email jobs
psql -c "SELECT job_id, tenant_id, status, total_emails, emails_sent, created_at FROM email_sending_jobs WHERE status IN ('queued', 'processing') ORDER BY created_at DESC;"
```

### Cancel Jobs

```bash
# Cancel specific job
psql -c "UPDATE processing_jobs SET status = 'failed', error_message = 'Manually cancelled', completed_at = now() WHERE job_id = 'job_id_here';"

# Cancel all stuck jobs
uv run python scripts/cancel_running_jobs.py
```

### Retry Failed Jobs

```bash
# Mark job for retry (via API)
curl -X POST "http://localhost:8002/api/v1/ingest/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-31", "data_types": ["events"]}'
```

---

## Scaling

### Horizontal Scaling

```bash
# Run multiple instances on different ports
uv run uvicorn services.analytics_service:app --port 8011 &
uv run uvicorn services.analytics_service:app --port 8012 &
uv run uvicorn services.analytics_service:app --port 8013 &

# Update nginx upstream
upstream analytics {
    server localhost:8011;
    server localhost:8012;
    server localhost:8013;
}
```

### Database Scaling

```bash
# Add read replica for analytics queries
# Configure in application:
POSTGRES_READ_HOST=replica.db.example.com
```

### Resource Limits

```bash
# Limit process memory (systemd)
MemoryLimit=2G

# Limit connections per service
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=3
```

---

## Maintenance Procedures

### Rolling Restart

```bash
#!/bin/bash
# rolling_restart.sh

services=("analytics_service:8001" "data_service:8002" "auth_service:8003")

for svc in "${services[@]}"; do
    name=$(echo $svc | cut -d: -f1)
    port=$(echo $svc | cut -d: -f2)
    
    echo "Restarting $name..."
    
    # Start new instance on temp port
    uv run uvicorn services.$name:app --port $((port + 100)) &
    new_pid=$!
    
    # Wait for new instance to be healthy
    sleep 10
    curl -s http://localhost:$((port + 100))/health > /dev/null
    
    # Kill old instance
    pkill -f "uvicorn services.$name:app --port $port"
    
    # Move new instance to correct port
    kill $new_pid
    uv run uvicorn services.$name:app --port $port &
    
    echo "$name restarted"
    sleep 5
done
```

### Database Maintenance

```bash
# Weekly maintenance script
#!/bin/bash

echo "Starting database maintenance..."

# Vacuum and analyze
psql -c "VACUUM ANALYZE;"

# Reindex
psql -c "REINDEX DATABASE google_analytics_db;"

# Update statistics
psql -c "ANALYZE;"

# Check for bloat
psql -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as size FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;"

echo "Database maintenance complete"
```

### Log Rotation

```bash
# /etc/logrotate.d/analytics
/path/to/backend/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 analytics analytics
}
```

---

## Monitoring Checklist

### Daily Checks

- [ ] All services returning 200 on `/health`
- [ ] No stuck jobs (> 30 min processing)
- [ ] Database connections < 80% of max
- [ ] No errors in last 24h logs
- [ ] Disk space > 20% free

### Weekly Checks

- [ ] Review failed jobs and root causes
- [ ] Check slow query log
- [ ] Verify backups are running
- [ ] Review resource utilization trends
- [ ] Update documentation if needed

### Monthly Checks

- [ ] Run database maintenance
- [ ] Review and rotate credentials
- [ ] Update dependencies (security patches)
- [ ] Capacity planning review
- [ ] Runbook accuracy review

---

