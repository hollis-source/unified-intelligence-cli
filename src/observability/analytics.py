from __future__ import annotations

from typing import List
from statistics import mean, pstdev

from src.observability.entities import UsageEntry


class UsageAnalytics:
    @staticmethod
    def detect_anomalies(entries: List[UsageEntry], std_threshold: float = 2.0) -> List[UsageEntry]:
        if not entries:
            return []
        vals = [e.input_tokens for e in entries]
        m = mean(vals)
        # population std; if zero variance, mark any value > 5x mean as anomaly
        try:
            s = pstdev(vals)
        except Exception:
            s = 0.0
        anomalies: List[UsageEntry] = []
        for e in entries:
            if s > 0 and (e.input_tokens > m + std_threshold * s):
                anomalies.append(e)
            elif s == 0 and m > 0 and e.input_tokens > 5 * m:
                anomalies.append(e)
        # Also include any single entry that's > 5x the median-ish (fallback):
        if not anomalies:
            baseline = sorted(vals)[len(vals)//2]
            anomalies = [e for e in entries if e.input_tokens >= 5 * max(1, baseline)]
        return anomalies

