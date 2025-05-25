# AAA Learning System - Admin Monitoring Guide

## Overview

This guide provides simple, step-by-step instructions for monitoring the AAA Learning System after deployment. All monitoring is done through command-line interface (CLI) commands - there is no dashboard UI for monitoring at this time.

## Quick Health Check (Daily - 2 minutes)

### Step 1: Open Terminal
- Open Terminal application on your Mac
- Navigate to your project directory:
  ```bash
  cd "/Users/gmtfr/VP Data Analysis - 4-2025"
  ```

### Step 2: Run Basic Health Check
Copy and paste this command:
```bash
python scripts/learning_system_health_check.py
```

**What to look for:**
- ✅ **GREEN checkmarks** = Good
- ⚠️ **YELLOW warnings** = Monitor closely
- ❌ **RED errors** = Needs attention

**Expected output for healthy system:**
```
Overall Status: ✅ HEALTHY
Database: ✅ Connected
Pattern Learning: ✅ Active
Cache Performance: Good
Error Rate: 0.0%
```

### Step 3: Quick Action Guide
- **If all green**: System is healthy, no action needed
- **If yellow warnings**: Continue monitoring, check again tomorrow
- **If red errors**: Follow troubleshooting steps below

## Detailed Health Check (Weekly - 5 minutes)

### Run Detailed Analysis
```bash
python scripts/learning_system_health_check.py --detailed
```

**What to look for:**
- **Pattern Accuracy**: Should be >70%
- **Response Time**: Should be <150ms
- **Active Patterns**: Should increase over time
- **Recent Corrections**: Shows system is learning

### Performance Benchmark (Weekly)
```bash
python scripts/learning_system_health_check.py --benchmark
```

**What to look for:**
- **Overall: ✅ PASSED** = Good performance
- **Average Lookup Time**: Should be <100ms
- **Overall: ❌ FAILED** = Performance issues

## Monthly System Review (15 minutes)

### Step 1: Generate Full Report
```bash
python -c "from app.utils.learning_metrics import create_monitoring_dashboard; print(create_monitoring_dashboard()['report'])"
```

### Step 2: Clean Up Old Data
```bash
python -c "from app.services.correction_service import CorrectionService; cs = CorrectionService(); cs.cleanup_old_cache_entries(30)"
```

### Step 3: Review Trends
Look for these patterns over time:
- **Increasing pattern accuracy** = System is learning well
- **Decreasing error rates** = System is improving
- **Stable response times** = Performance is consistent

## Troubleshooting Common Issues

### Problem: High Error Rate (>10%)
**Symptoms:** Error Rate shows >10% in health check

**Steps to fix:**
1. Check recent user feedback quality
2. Review correction logs:
   ```bash
   ls -la logs/ | grep correction
   ```
3. If problem persists, contact technical support

### Problem: Poor Performance (>150ms response time)
**Symptoms:** Response times consistently above 150ms

**Steps to fix:**
1. Run cache cleanup:
   ```bash
   python -c "from app.services.correction_service import CorrectionService; cs = CorrectionService(); cs.cleanup_old_cache_entries(7)"
   ```
2. Check database size and consider archiving old data
3. Restart the application

### Problem: Pattern Learning Inactive
**Symptoms:** Pattern Learning shows ❌ Inactive

**Steps to fix:**
1. Check if users are providing feedback through the system
2. Verify database connectivity
3. Restart the application:
   ```bash
   python run.py
   ```

### Problem: Database Connection Issues
**Symptoms:** Database shows ❌ Disconnected

**Steps to fix:**
1. Check database file exists:
   ```bash
   ls -la patient_data.db
   ```
2. Check file permissions:
   ```bash
   ls -la patient_data.db
   ```
3. If file is missing or corrupted, restore from backup

## Automated Monitoring Setup (Optional)

### Set Up Daily Automated Checks
You can set up the system to automatically run health checks and notify you:

1. Open Terminal and run:
   ```bash
   crontab -e
   ```

2. Add this line (runs daily at 9 AM):
   ```
   0 9 * * * cd "/Users/gmtfr/VP Data Analysis - 4-2025" && python scripts/learning_system_health_check.py --json > logs/daily_health_$(date +\%Y-\%m-\%d).log
   ```

3. Save and exit (press Ctrl+X, then Y, then Enter)

### Check Automated Results
View daily health logs:
```bash
ls -la logs/daily_health_*.log
cat logs/daily_health_$(date +%Y-%m-%d).log
```

## Understanding the Monitoring Data

### Health Status Levels
- **Healthy**: All systems operating normally
- **Warning**: Minor issues detected, monitor closely
- **Critical**: Immediate attention required

### Key Metrics Explained
- **Pattern Accuracy**: How often the system's learned patterns are correct
- **Response Time**: How fast the system responds to queries
- **Error Rate**: Percentage of operations that fail
- **Cache Performance**: How efficiently the system stores and retrieves data
- **Active Patterns**: Number of learned patterns being used

### Normal vs. Concerning Values
| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Pattern Accuracy | >85% | 70-85% | <70% |
| Response Time | <100ms | 100-150ms | >150ms |
| Error Rate | <5% | 5-10% | >10% |
| Cache Performance | Good/Excellent | Fair | Poor |

## When to Contact Technical Support

Contact technical support if you see:
- ❌ Critical status for more than 24 hours
- Error rates consistently above 15%
- Response times consistently above 200ms
- Database connection failures
- System crashes or inability to start

## Monitoring Schedule Summary

### Daily (2 minutes)
- [ ] Run basic health check
- [ ] Verify system status is healthy or warning (not critical)

### Weekly (5 minutes)
- [ ] Run detailed health check
- [ ] Run performance benchmark
- [ ] Review pattern accuracy trends

### Monthly (15 minutes)
- [ ] Generate full system report
- [ ] Clean up old cache data
- [ ] Review overall system trends
- [ ] Archive old log files if needed

## Log File Locations

All monitoring data is stored in the `logs/` directory:
- `logs/daily_health_*.log` - Daily automated health checks
- `logs/self_test_*` - System self-test results
- `logs/nightly_test_*` - Automated nightly test results

## Emergency Contacts

- **System Issues**: Check troubleshooting section first
- **Data Loss**: Restore from most recent backup
- **Performance Problems**: Run cleanup commands and restart application 