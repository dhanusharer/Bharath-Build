# Operations Runbook & Incident Response Playbook

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Classification**: On-Call & Reliability Operations  

---

## 1. Incident Response Playbooks

### Playbook A: Amazon Bedrock Quota Exhaustion / Throttling (`ThrottlingException`)
* **Symptoms**: CloudWatch metric `BedrockThrottlingCount` > 5; API returning HTTP 504 with `EXTRACTION_FAILED`.
* **Immediate Actions**:
  1. Inspect CloudWatch Logs to confirm AWS error: `Rate exceeded / ThrottlingException`.
  2. Check current concurrent request rate on AWS Service Quotas dashboard for Amazon Bedrock (`ap-south-1`).
  3. Verify if backend circuit breaker has engaged.
  4. Temporarily switch `BEDROCK_MODEL_ID` to standby fallback model (`anthropic.claude-3-haiku-20240307-v1:0`) via environment variable update in ECS Task Definition to restore extraction throughput.
  5. Submit emergency Service Quota increase ticket via AWS Management Console.

### Playbook B: Spike in Safety Gate Refusals (`SafetyGateRefusalSpike`)
* **Symptoms**: Alarm `SafetyGateRefusalCount` > 20% of total extractions over 15 minutes.
* **Immediate Actions**:
  1. Check recent client app release or mobile camera changes (e.g., photo compression regression producing blurred uploads).
  2. Sample anonymized audit logs in `validation_results` table for common violation codes:
     * If `MISSING_DOSAGE_VALUE` is spiking: Check if a new regional doctor handwriting layout has emerged.
     * If `IMAGE_BLURRY` is spiking: Check frontend camera capture resolution or client canvas compression settings.
  3. Verify that the safety gate has NOT degraded to fail-open (ensure fail-closed refusal is holding).

### Playbook C: TTS Provider Outage / Unavailability (`TTSProviderFailure`)
* **Symptoms**: Hindi or Kannada voice generation failing; users see visual cards but audio player shows error.
* **Immediate Actions**:
  1. Check AWS Polly service health in Mumbai region (`ap-south-1`).
  2. Check `TTS_DEFAULT_PROVIDER` status.
  3. Confirm fallback mechanism: system automatically renders visual high-contrast cards and informs the user via text badge that audio is temporarily unavailable.
  4. If Polly is down, toggle `TTS_DEFAULT_PROVIDER=mock` or activate standby regional provider adapter.

### Playbook D: PostgreSQL Connection Pool Exhaustion
* **Symptoms**: API returning HTTP 503; logs showing `asyncpg.exceptions.TooManyConnectionsError`.
* **Immediate Actions**:
  1. Run `SELECT count(*), state FROM pg_stat_activity GROUP BY state;` in RDS console.
  2. Check for leaked or hanging database sessions due to unclosed async transactions.
  3. Restart ECS tasks to flush stale client connections if pool is locked.
  4. Increase `DB_POOL_SIZE` or configure AWS RDS Proxy to pool database connections across tasks.

---

## 2. Routine Operational Tasks

### Running Database Migrations
```bash
# Execute within ECS migration task container
uv run alembic upgrade head
```

### Rotating Application Secrets
1. Generate a new high-entropy string: `openssl rand -hex 32`.
2. Update secret in AWS Secrets Manager: `aws secretsmanager update-secret --secret-id medication-access/dev/secrets --secret-string ...`
3. Force a new deployment of ECS tasks to refresh environment configurations: `aws ecs update-service --cluster app-cluster --service api-service --force-new-deployment`.
