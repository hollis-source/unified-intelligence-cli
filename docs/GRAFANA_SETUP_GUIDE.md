# Grafana Dashboard Setup Guide

**Dashboard**: Optimization Metrics Monitoring
**File**: `grafana_dashboard_optimizations.json`
**Metrics Source**: `/metrics/optimizations` endpoint (Prometheus format)
**Validated Metrics**: Cache (80% hit rate) + Parallel (3.89x speedup)

## Overview

Pre-configured Grafana dashboard for monitoring performance optimizations:
- **9 panels** covering cache, parallel execution, and batch processing
- **Thresholds** aligned with validation targets (≥30% cache, ≥3x parallel)
- **Real-time monitoring** via HTTP endpoint
- **Production-ready** (95% confidence)

---

## Quick Start

### 1. Prerequisites

- Grafana installed (v8.0+ recommended)
- Health server running: `python -m src.observability.health_server`
- Optimizations deployed (cache + parallel)

### 2. Import Dashboard

**Option A: Grafana UI** (recommended)
1. Open Grafana: http://localhost:3000
2. Navigate: **Dashboards → Import**
3. Click: **Upload JSON file**
4. Select: `grafana_dashboard_optimizations.json`
5. Click: **Import**

**Option B: Grafana API**
```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @grafana_dashboard_optimizations.json
```

### 3. Configure Data Source

**Step 1: Add Prometheus Data Source**

1. Navigate: **Configuration → Data Sources**
2. Click: **Add data source**
3. Select: **Prometheus**
4. Configure:
   - **Name**: Optimization Metrics
   - **URL**: http://localhost:8080 (health server)
   - **Access**: Server (default)
5. Click: **Save & Test**

**Step 2: Point Dashboard to Data Source**

If dashboard doesn't auto-connect:
1. Open dashboard: **Optimization Metrics**
2. Click: **Settings** (gear icon)
3. Navigate: **Variables**
4. Update: **datasource** variable to "Optimization Metrics"
5. Click: **Save dashboard**

---

## Dashboard Panels

### Panel 1: Cache Hit Rate (Stat)

**Purpose**: Monitor cache effectiveness
**Metric**: `cache_hit_rate_percent`
**Thresholds**:
- 🔴 Red: <30% (below target)
- 🟡 Yellow: 30-40% (meets target)
- 🟢 Green: >40% (exceeds target)

**Expected Value**: 40-80% (validated: 80%)

### Panel 2: Cache Hits vs Misses (Timeseries)

**Purpose**: Track cache usage over time
**Metrics**:
- `rate(cache_hits_total[5m])` - Hits per second
- `rate(cache_misses_total[5m])` - Misses per second

**Interpretation**:
- Rising hits: Cache warming up / good patterns
- Flat misses: Stable workload
- Rising misses: New patterns / cache eviction

### Panel 3: Cache Latency Comparison (Bar Gauge)

**Purpose**: Compare hit vs miss latency
**Metrics**:
- `cache_hit_latency_ms_avg` - Average hit latency
- `cache_miss_latency_ms_avg` - Average miss latency

**Expected Ratio**: Miss latency 3-5x higher than hit latency

### Panel 4: Parallel Execution Throughput (Timeseries)

**Purpose**: Monitor parallel execution rate
**Metric**: `rate(parallel_executions_total[5m])`
**Unit**: Executions per second

**Expected Pattern**: Bursts during parallel workflows

### Panel 5: Parallel Execution Latency (Gauge)

**Purpose**: Track parallel execution performance
**Metric**: `parallel_execution_latency_ms_avg`
**Thresholds**:
- 🟢 Green: <500ms
- 🟡 Yellow: 500-800ms
- 🔴 Red: >800ms

**Expected Value**: 200-300ms (with 4 workers, 100ms tasks)

### Panel 6: Batch Processing Throughput (Stat)

**Purpose**: Monitor batch processing rate
**Metric**: `batch_processing_throughput_avg`
**Thresholds**:
- 🔴 Red: <0.5 projects/sec
- 🟡 Yellow: 0.5-1.0 projects/sec
- 🟢 Green: >1.0 projects/sec

**Expected Value**: 0.5-1.5 projects/sec (depending on project size)

### Panel 7: Batch Processing - Total Projects (Timeseries)

**Purpose**: Track cumulative project completions
**Metric**: `batch_processing_projects_total`
**Unit**: Projects

**Interpretation**: Steadily increasing = healthy batch processing

### Panel 8: Batch Processing - Batches Completed (Stat)

**Purpose**: Count completed batch runs
**Metric**: `batch_processing_batches_total`
**Unit**: Batches

### Panel 9: Performance Claims Validation (Table)

**Purpose**: Compare actual vs claimed metrics
**Metrics**:
- `cache_hit_rate_percent` (Claimed: 40%, Target: ≥30%, Actual: 80%)
- `batch_processing_throughput_avg` (Claimed: 3-4x, Target: ≥0.5 proj/s)

**Use Case**: Quick validation that optimizations meet claims

---

## Dashboard Configuration

### Time Range

**Default**: Last 6 hours
**Recommendation**:
- Development: Last 1 hour
- Staging: Last 6 hours
- Production: Last 24 hours

**Change**: Top-right corner → Select time range

### Refresh Rate

**Default**: 30 seconds
**Options**:
- Real-time monitoring: 5-10 seconds
- Standard monitoring: 30 seconds
- Historical analysis: Disable auto-refresh

**Change**: Top-right corner → Select refresh rate

### Dashboard Settings

```json
{
  "refresh": "30s",           // Auto-refresh every 30 seconds
  "timezone": "browser",      // Use browser timezone
  "tags": ["optimization", "performance", "cache", "parallel", "batch"]
}
```

---

## Alerts Setup

### Alert 1: Low Cache Hit Rate

**Condition**: `cache_hit_rate_percent < 30` for 5 minutes
**Severity**: Warning
**Action**: Investigate cache configuration (TTL, max_entries)

**Create Alert**:
1. Open Panel 1 (Cache Hit Rate)
2. Click: **Edit** → **Alert** tab
3. Configure:
   - **Condition**: `cache_hit_rate_percent` WHEN `avg()` OF query(A) IS BELOW 30
   - **For**: 5m
4. Add notification channel
5. Save

### Alert 2: Parallel Execution High Latency

**Condition**: `parallel_execution_latency_ms_avg > 800` for 5 minutes
**Severity**: Warning
**Action**: Check worker count, LLM provider response time

**Create Alert**: Similar to Alert 1, using Panel 5 (Parallel Execution Latency)

### Alert 3: Batch Processing Stalled

**Condition**: No change in `batch_processing_projects_total` for 30 minutes
**Severity**: Critical
**Action**: Check batch processor, LLM provider availability

---

## Troubleshooting

### Issue: No Data in Dashboard

**Symptoms**: All panels show "No data"

**Causes & Fixes**:
1. **Health server not running**:
   ```bash
   python -m src.observability.health_server
   ```

2. **Data source not configured**:
   - Verify Prometheus data source URL: http://localhost:8080
   - Test connection: **Configuration → Data Sources → Test**

3. **No metrics generated yet**:
   - Run optimizations to generate metrics
   - Verify metrics files exist:
     ```bash
     ls -la ~/.claude/*.json
     ```

4. **Firewall blocking**:
   - Check port 8080 is accessible
   - Test endpoint:
     ```bash
     curl http://localhost:8080/metrics/optimizations
     ```

### Issue: Wrong Metric Values

**Symptoms**: Metrics don't match validation results

**Causes & Fixes**:
1. **Stale metrics files**:
   ```bash
   # Clear and restart
   rm ~/.claude/cache_metrics.json
   rm ~/.claude/parallel_metrics.json
   # Run tests again
   pytest tests/integration/test_optimization_validation.py
   ```

2. **Dashboard using wrong data source**:
   - Check dashboard settings → Variables → datasource
   - Should point to Prometheus source with health server URL

3. **Time range mismatch**:
   - Adjust time range to include metric generation period
   - Metrics are point-in-time snapshots, not time-series

### Issue: Panels Not Updating

**Symptoms**: Dashboard shows old data

**Causes & Fixes**:
1. **Auto-refresh disabled**:
   - Enable in top-right corner
   - Set to 30s or lower

2. **Browser cache**:
   - Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

3. **Grafana cache**:
   - Restart Grafana service
   - Clear browser local storage

---

## Production Recommendations

### Monitoring Strategy

**Baseline Period** (Week 1):
- Monitor every hour
- Document typical ranges for each metric
- Identify daily/weekly patterns
- Tune alert thresholds based on observed values

**Steady State** (Week 2+):
- Review dashboard daily
- Investigate alerts within 1 hour
- Weekly trend analysis
- Monthly capacity planning

### Key Metrics to Watch

| Metric | Target | Action if Below/Above |
|--------|--------|----------------------|
| Cache hit rate | ≥30% (expect 40-80%) | Review task patterns, tune TTL |
| Parallel speedup | ≥3x (expect 3.89x) | Check worker count, LLM latency |
| Batch throughput | ≥0.5 proj/s | Check rate limiter, project complexity |

### Dashboard Maintenance

**Weekly**:
- [ ] Verify all panels loading
- [ ] Check alert notifications working
- [ ] Review metric trends
- [ ] Update dashboard annotations for deployments

**Monthly**:
- [ ] Archive old dashboard versions
- [ ] Update thresholds based on production data
- [ ] Add new panels for additional metrics
- [ ] Review and optimize queries

---

## Advanced Configuration

### Custom Queries

**Add custom panel**:
1. Click: **Add panel**
2. Select: **Prometheus** data source
3. Enter query (examples below)
4. Configure visualization
5. Save

**Example Queries**:

```promql
# Cache efficiency over time
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))

# Parallel speedup estimation
(parallel_executions_total * 100) / parallel_execution_latency_ms_avg

# Batch processing success rate
batch_processing_projects_total / batch_processing_batches_total
```

### Dashboard Variables

**Add variable for dynamic filtering**:
1. Dashboard settings → Variables
2. Add variable:
   - **Name**: provider
   - **Type**: Query
   - **Query**: `label_values(provider)`
3. Use in panels: `cache_hits_total{provider="$provider"}`

### Export/Backup

**Export dashboard**:
1. Dashboard → Settings (gear icon)
2. JSON Model tab
3. Copy JSON or click "Save JSON to file"
4. Store in version control

---

## References

- **Dashboard JSON**: `grafana_dashboard_optimizations.json`
- **Metrics Endpoint**: `src/observability/health_server.py:323-423`
- **Validation Results**: `docs/OPTIMIZATION_VALIDATION_RESULTS.md`
- **Deployment Guide**: `docs/OPTIMIZATION_DEPLOYMENT_GUIDE.md`
- **Grafana Docs**: https://grafana.com/docs/grafana/latest/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-11
**Dashboard Version**: 1
**Production Ready**: ✅ YES
