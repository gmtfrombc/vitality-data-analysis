# AAA Learning System Deployment Guide

## Pre-Deployment Checklist

### System Requirements
- [ ] Python 3.8+
- [ ] SQLite 3.8+
- [ ] Panel framework
- [ ] OpenAI API access
- [ ] Sufficient storage for learning data (minimum 1GB)

### Database Preparation
- [ ] Run all migrations: `python -c "from app.utils.db_migrations import apply_pending_migrations; apply_pending_migrations()"`
- [ ] Verify all learning tables exist
- [ ] Create performance indexes: `python -c "from app.services.correction_service import CorrectionService; cs = CorrectionService(); cs._create_performance_indexes()"`

### Configuration Validation
- [ ] Environment variables properly set
- [ ] Database file permissions correct
- [ ] Log directory writable
- [ ] API keys configured

## Deployment Steps

### 1. Database Migration
```bash
# Apply all pending migrations
python -c "from app.utils.db_migrations import apply_pending_migrations; apply_pending_migrations('patient_data.db')"

# Verify learning system tables
python -c "
from app.services.correction_service import CorrectionService
cs = CorrectionService()
print('Learning system initialized successfully')
"
```

### 2. System Health Check
```bash
# Run comprehensive health check
python -c "
from app.utils.learning_metrics import LearningSystemMonitor
monitor = LearningSystemMonitor()
health = monitor.get_system_health()
print(f'System Status: {health.overall_status}')
print(monitor.generate_health_report())
"
```

### 3. Performance Validation
```bash
# Test pattern lookup performance
python -c "
from app.services.correction_service import CorrectionService
import time
cs = CorrectionService()
start = time.time()
patterns = cs.find_similar_patterns('test query')
print(f'Pattern lookup: {(time.time() - start) * 1000:.2f}ms')
"
```

## Post-Deployment Monitoring

### Daily Health Checks
- Monitor system health status
- Check error rates and pattern accuracy
- Verify cache performance
- Review learning metrics

### Weekly Maintenance
- Clean up old cache entries
- Review pattern quality
- Analyze correction trends
- Update performance indexes if needed

### Monthly Reviews
- Comprehensive accuracy analysis
- Pattern effectiveness review
- Performance optimization opportunities
- User feedback analysis

## Troubleshooting

### Common Issues

#### High Error Rate
- Check correction session logs
- Review pattern matching accuracy
- Validate user feedback quality
- Verify intent parsing functionality

#### Poor Performance
- Check cache hit rates
- Review database query performance
- Monitor pattern lookup times
- Validate index effectiveness

#### Pattern Learning Issues
- Verify correction application success
- Check pattern creation logs
- Review similarity calculation accuracy
- Validate intent normalization

## Monitoring Commands

### Health Status
```bash
python -c "from app.utils.learning_metrics import create_monitoring_dashboard; print(create_monitoring_dashboard()['report'])"
```

### Performance Metrics
```bash
python -c "
from app.utils.learning_metrics import LearningSystemMonitor
monitor = LearningSystemMonitor()
metrics = monitor.get_comprehensive_metrics()
print(f'Pattern Accuracy: {metrics.accuracy_metrics[\"pattern_accuracy\"]:.1%}')
print(f'Response Time: {metrics.performance_metrics[\"average_response_time_ms\"]:.1f}ms')
"
```

### Cache Cleanup
```bash
python -c "
from app.services.correction_service import CorrectionService
cs = CorrectionService()
cs.cleanup_old_cache_entries(7)  # Clean entries older than 7 days
"
```

## Production Readiness Validation

### Performance Benchmarks
- Pattern lookup time < 100ms
- Cache hit rate > 80%
- Overall accuracy > 85%
- Error rate < 10%

### Stability Requirements
- System health status: "healthy"
- Database connectivity: stable
- Pattern learning: active
- Cache performance: good or better

### Monitoring Setup
- Health checks automated
- Performance metrics tracked
- Error alerts configured
- Usage statistics collected

## Rollback Procedures

### Emergency Rollback
1. Stop the application
2. Restore previous database backup
3. Revert code changes
4. Restart with previous version
5. Verify system functionality

### Gradual Rollback
1. Disable learning features
2. Monitor system stability
3. Gradually restore functionality
4. Validate each component

## Security Considerations

### Data Protection
- Encrypt sensitive learning data
- Secure API keys and credentials
- Implement access controls
- Regular security audits

### Privacy Compliance
- Anonymize user feedback
- Secure correction sessions
- Implement data retention policies
- Regular privacy reviews

## Maintenance Schedule

### Daily (Automated)
- System health checks
- Performance monitoring
- Error rate tracking
- Cache optimization

### Weekly (Manual)
- Pattern quality review
- Correction trend analysis
- Performance optimization
- Security updates

### Monthly (Comprehensive)
- Full system audit
- Accuracy assessment
- User feedback analysis
- Capacity planning

## Support and Documentation

### Technical Support
- System logs location: `/logs/`
- Error tracking: Application logs
- Performance metrics: Learning metrics dashboard
- Health status: Monitoring commands

### Documentation Updates
- Keep deployment guide current
- Update troubleshooting procedures
- Maintain monitoring commands
- Document configuration changes

## Success Metrics

### Deployment Success Criteria
- [ ] All tests pass with >95% coverage
- [ ] Performance benchmarks met
- [ ] System health status: "healthy"
- [ ] Learning features functional
- [ ] Monitoring active

### Operational Success Metrics
- Pattern accuracy > 85%
- Response time < 150ms
- Error rate < 10%
- User satisfaction > 90%
- System uptime > 99% 