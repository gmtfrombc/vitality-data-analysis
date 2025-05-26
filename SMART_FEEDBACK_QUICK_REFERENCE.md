# Smart Feedback System - Quick Reference Card

## 🎯 Priority Levels

| Priority | Icon | Appearance | When It Appears |
|----------|------|------------|-----------------|
| **High** | 🎯 | Orange border | Novel/complex queries, low confidence |
| **Medium** | 💭 | Blue border | Standard requests, shows analytics |
| **Low** | 👍 | Gray dashed | Simple queries, high confidence |
| **Skip** | - | No widget | Very similar recent queries, fatigue detected |

## 📊 Understanding Analytics

```
📊 System Insights: Request rate: 75% | Response rate: 85% | Total requests: 150
```

- **Request Rate**: % of queries requesting feedback (target: 60-80%)
- **Response Rate**: % of requests getting responses (target: >70%)
- **Total Requests**: Number of feedback requests made

## 👍👎 Feedback Best Practices

### ✅ Good Corrections
```
"The average BMI should be 24.8, not 26.2. Please exclude 
patients under 18 years old from the calculation."
```

### ❌ Poor Corrections
```
"Wrong"
"This is bad"
```

## 🔧 Fatigue Detection

System reduces requests when:
- **>5 requests** in the last hour
- **>70% negative** feedback in 24 hours

## 🎛️ Priority Calculation

| Factor | Weight | Impact |
|--------|--------|--------|
| Confidence | 25% | Lower = Higher priority |
| Novelty | 30% | Higher = Higher priority |
| Recency | 25% | Recent similar = Lower priority |
| Learning Value | 20% | Higher = Higher priority |

## 🚨 Troubleshooting

**No feedback requests?** → Normal! System detected fatigue or high confidence

**Wrong priority?** → Multiple factors considered, not just complexity

**Corrections not applied?** → Stored for learning, improves future analyses

## 📞 Quick Help

- Technical issues: Check status, refresh page
- System feedback: Use correction interface
- Priority questions: Multiple factors determine priority

---
*Smart Feedback System v2.2 | January 2025* 