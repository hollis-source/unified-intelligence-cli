# Dashboard Enhancement TODOs

## Status: Partially Complete

This document tracks remaining enhancements for the unified metrics dashboard system.

### ✅ Completed (This Session)

1. **Dashboard POST Integration** ✅
   - Added automatic metric submission to unified dashboard
   - Mode/priority mapping implemented
   - Authentication configured
   - File: `autonomous_dev_tool.py`

2. **Metrics Backfill** ✅
   - Created utility script for backfilling historical metrics
   - Successfully backfilled 12 metrics (100% success rate)
   - File: `backfill_metrics.py`

3. **Retry Logic with Exponential Backoff** ✅
   - 3 attempts with 1s, 2s, 4s delays
   - Prevents data loss from transient network failures
   - File: `autonomous_dev_tool.py` (enhanced)

4. **Stopping Criteria Detection** ✅
   - Automatic stagnation detection (no commits in last N iterations)
   - Graceful loop termination
   - Prevents infinite validation loops
   - File: `src/claude_orchestrator/orchestrators/autonomous_orchestrator.py`

5. **Production Deployment** ✅
   - Deployed `autonomous_dev_tool.py` to SYD2
   - Set environment variables (DASHBOARD_API_KEY, DASHBOARD_API_URL)
   - Location: `/opt/autonomous/autonomous_dev_tool.py`

6. **Priority Queue Complete** ✅
   - All 8 priorities resolved (7 completed, 1 cancelled)
   - `syd2_phase4_ml` cancelled as not applicable
   - File: `priorities.yaml` v1.6

### 🔄 Remaining Work

#### 1. Dashboard API Deduplication

**Priority:** Medium
**Effort:** 1-2 hours
**Status:** Not started

**Task:**
- Modify `/opt/docserver/src/adapters/web/api.py` on SYD2
- Add deduplication check before inserting metrics
- Check by natural key: `timestamp + iteration_number`
- Return 200 OK if exists, 201 Created if new
- Makes API idempotent (backfill can run multiple times safely)

**Implementation:**
```python
# In sqlite_adapter.py
def get_metric_by_timestamp_and_iteration(timestamp: str, iteration_number: int):
    """Check if metric already exists."""
    # Query DB by timestamp + iteration_number

# In api.py
def record_iteration_metric(...):
    # Check if exists
    existing = db.get_metric_by_timestamp_and_iteration(...)
    if existing:
        return {"message": "Metric already exists", "metric": existing}
    # Otherwise insert as normal
```

**Testing:**
- Run `backfill_metrics.py` twice
- Verify second run returns 200 OK (not 201 Created)
- Verify no duplicate metrics in database

#### 2. Dashboard Charts/Visualizations

**Priority:** Low
**Effort:** 2-4 hours
**Status:** Not started

**Task:**
- Add interactive charts to `static/dashboard.html` on SYD2
- Use Chart.js (already imported)
- Visualizations needed:
  - Success rate over time (line chart)
  - Duration by mode (bar chart)
  - Tasks by goal (pie chart)
  - Iteration timeline (area chart)

**Data Sources:**
- GET `/api/metrics/iterations` (existing)
- GET `/api/metrics/dashboard` (existing)
- All endpoints return JSON ready for charts

**Implementation:**
```javascript
// In dashboard.html
const ctx = document.getElementById('successRateChart');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: timestamps,
    datasets: [{
      label: 'Success Rate',
      data: successRates
    }]
  }
});
```

**Testing:**
- Verify charts render correctly
- Test with 39+ metrics data
- Verify auto-refresh updates charts

#### 3. Environment Variable Security

**Priority:** Low
**Effort:** 15 minutes
**Status:** Complete but can be improved

**Current:** API key in `.bashrc` (acceptable)
**Better:** Use systemd environment file or secrets manager

**Implementation:**
```bash
# For systemd service (if running as service)
echo "DASHBOARD_API_KEY=auggie-secret-key" > /etc/systemd/system/autonomous.env
# Then in service file: EnvironmentFile=/etc/systemd/system/autonomous.env
```

### 📊 Current Metrics

- **Total iterations tracked:** 39
- **Success rate:** 100%
- **Dashboard URL:** http://syd2.jacobhollis.com:8080/dashboard.html
- **API endpoints:** All functional
- **Retry logic:** 3 attempts with exponential backoff
- **Stagnation detection:** 3-iteration threshold

### 🎯 Recommended Next Steps

1. **Deduplication** (Medium priority, 1-2h)
   - Most important for operational safety
   - Prevents accidental duplicate data
   - Required before running backfill in production

2. **Charts** (Low priority, 2-4h)
   - Enhances dashboard UX
   - Not critical for functionality
   - Can be done incrementally

3. **Security** (Low priority, 15min)
   - Current setup acceptable for internal tool
   - Consider if exposing publicly

### 💡 Notes

- All critical production features complete (retry, stopping criteria, deployment)
- Deduplication nice-to-have but not blocking
- Charts improve UX but dashboard functional without them
- System is production-ready as-is

---

**Last Updated:** 2025-10-14
**Session:** Metrics Dashboard Integration + Enhancements
**Status:** Production-ready with optional improvements remaining
