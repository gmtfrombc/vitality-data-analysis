# SPRINT 3.1 PROMPT - Maintenance Automation & Configuration

## PROJECT CONTEXT

You are working on the **Admin Monitoring Dashboard Project** - creating a web-based monitoring interface for the AAA (Ask Anything AI Assistant) Learning System. This is Sprint 3.1 of an 8-sprint project across 3 phases.

### Project Overview
The AAA is a healthcare data analysis assistant with a recently deployed Learning Enhancement system. We're building a modern, visual dashboard that allows non-technical healthcare administrators to monitor system health, performance, and learning metrics through a web interface.

### Current System Status (After Sprint 2.3)
The AAA now has:
- **Complete Phase 1**: Basic dashboard with health status, interactive features, and user testing
- **Complete Phase 2**: Historical trends, learning analytics, and performance benchmarks
- **Export Capabilities**: Professional report generation with CSV/PDF/JSON formats
- **Benchmark Service**: Automated performance testing and optimization recommendations
- **Interactive Charts**: Comprehensive visualizations with time period selectors

### Sprint 3.1 Focus
This sprint focuses on **Maintenance Automation & Configuration** - implementing one-click maintenance operations, advanced system configuration, and automated maintenance scheduling.

## SPRINT 3.1 OBJECTIVES

**Goal**: Implement comprehensive maintenance automation tools and advanced system configuration capabilities to enable non-technical administrators to maintain optimal system performance.

**Key Deliverables**:
1. Maintenance Service with automated operations (cache cleanup, DB optimization, log rotation)
2. One-Click Maintenance Interface with progress tracking and scheduling
3. System Configuration Panel for advanced settings and preferences
4. Advanced Alert Management with escalation and notification rules
5. Maintenance Scheduling with automated execution and reporting
6. System Optimization Tools with performance recommendations

**User Impact**: Healthcare administrators can maintain system performance through automated tools without requiring technical expertise.

## TECHNICAL REQUIREMENTS

### Maintenance Service

Create `app/services/maintenance_service.py`:

```python
"""
Maintenance Service for AAA Admin Monitoring

This service provides automated maintenance operations for the AAA system,
including cache cleanup, database optimization, log rotation, and system tuning.

Sprint 3.1 Features:
- Automated maintenance operations
- Scheduled maintenance execution
- Performance optimization
- System health monitoring
- Maintenance reporting
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

from app.utils.saved_questions_db import DB_FILE
from app.services.dashboard_service import DashboardService
from app.utils.learning_metrics import LearningSystemMonitor

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceOperation:
    """Individual maintenance operation definition."""
    operation_id: str
    name: str
    description: str
    category: str  # 'database', 'cache', 'logs', 'system'
    estimated_duration_minutes: int
    risk_level: str  # 'low', 'medium', 'high'
    requires_downtime: bool
    prerequisites: List[str]
    operation_func: Callable


@dataclass
class MaintenanceResult:
    """Result of a maintenance operation."""
    operation_id: str
    operation_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    success: bool
    error_message: Optional[str]
    details: Dict[str, Any]
    performance_impact: Dict[str, float]
    recommendations: List[str]


@dataclass
class MaintenanceSchedule:
    """Scheduled maintenance configuration."""
    schedule_id: str
    name: str
    operations: List[str]  # operation_ids
    schedule_type: str  # 'daily', 'weekly', 'monthly', 'custom'
    schedule_config: Dict[str, Any]  # cron-like config
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    notification_settings: Dict[str, Any]


class MaintenanceService:
    """Service for automated system maintenance."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the maintenance service.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.dashboard_service = DashboardService(db_path)
        self.monitor = LearningSystemMonitor(db_path)
        
        # Initialize maintenance operations
        self.operations = self._initialize_operations()
        self._ensure_maintenance_tables()
        
        # Background scheduler
        self._scheduler_running = False
        self._scheduler_thread = None
    
    def _ensure_maintenance_tables(self):
        """Ensure maintenance tables exist."""
        try:
            with self._get_connection() as conn:
                # Maintenance execution history
                conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    operation_name TEXT NOT NULL,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    success BOOLEAN,
                    error_message TEXT,
                    details TEXT,
                    performance_impact TEXT,
                    recommendations TEXT,
                    triggered_by TEXT DEFAULT 'manual',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Maintenance schedules
                conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    operations TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_config TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    last_run DATETIME,
                    next_run DATETIME,
                    notification_settings TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # System configuration
                conn.execute("""
                CREATE TABLE IF NOT EXISTS system_configuration (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    config_type TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    requires_restart BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT DEFAULT 'system'
                )
                """)
                
                # Alert configurations (enhanced)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    rule_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    threshold_value REAL NOT NULL,
                    severity TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    escalation_rules TEXT,
                    notification_channels TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_history_date ON maintenance_history(started_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_history_operation ON maintenance_history(operation_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_schedules_next_run ON maintenance_schedules(next_run)")
                
        except Exception as e:
            logger.error(f"Error creating maintenance tables: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_operations(self) -> Dict[str, MaintenanceOperation]:
        """Initialize available maintenance operations."""
        operations = {}
        
        # Database operations
        operations['db_vacuum'] = MaintenanceOperation(
            operation_id='db_vacuum',
            name='Database Vacuum',
            description='Optimize database by reclaiming unused space and rebuilding indexes',
            category='database',
            estimated_duration_minutes=5,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._vacuum_database
        )
        
        operations['db_analyze'] = MaintenanceOperation(
            operation_id='db_analyze',
            name='Database Analysis',
            description='Update database statistics for query optimization',
            category='database',
            estimated_duration_minutes=2,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._analyze_database
        )
        
        operations['db_integrity_check'] = MaintenanceOperation(
            operation_id='db_integrity_check',
            name='Database Integrity Check',
            description='Verify database integrity and detect corruption',
            category='database',
            estimated_duration_minutes=10,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._check_database_integrity
        )
        
        # Cache operations
        operations['cache_cleanup'] = MaintenanceOperation(
            operation_id='cache_cleanup',
            name='Cache Cleanup',
            description='Clear expired cache entries and optimize cache performance',
            category='cache',
            estimated_duration_minutes=1,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._cleanup_cache
        )
        
        operations['cache_rebuild'] = MaintenanceOperation(
            operation_id='cache_rebuild',
            name='Cache Rebuild',
            description='Rebuild cache with fresh data for improved performance',
            category='cache',
            estimated_duration_minutes=3,
            risk_level='medium',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._rebuild_cache
        )
        
        # Log operations
        operations['log_rotation'] = MaintenanceOperation(
            operation_id='log_rotation',
            name='Log Rotation',
            description='Archive old logs and clean up log files',
            category='logs',
            estimated_duration_minutes=2,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._rotate_logs
        )
        
        operations['log_cleanup'] = MaintenanceOperation(
            operation_id='log_cleanup',
            name='Log Cleanup',
            description='Remove old log files and compress archives',
            category='logs',
            estimated_duration_minutes=3,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._cleanup_logs
        )
        
        # System operations
        operations['temp_cleanup'] = MaintenanceOperation(
            operation_id='temp_cleanup',
            name='Temporary File Cleanup',
            description='Remove temporary files and clean up working directories',
            category='system',
            estimated_duration_minutes=2,
            risk_level='low',
            requires_downtime=False,
            prerequisites=[],
            operation_func=self._cleanup_temp_files
        )
        
        operations['performance_optimization'] = MaintenanceOperation(
            operation_id='performance_optimization',
            name='Performance Optimization',
            description='Apply performance optimizations based on system analysis',
            category='system',
            estimated_duration_minutes=5,
            risk_level='medium',
            requires_downtime=False,
            prerequisites=['db_analyze'],
            operation_func=self._optimize_performance
        )
        
        return operations
    
    async def execute_maintenance_operation(self, operation_id: str, triggered_by: str = 'manual') -> MaintenanceResult:
        """Execute a single maintenance operation.
        
        Args:
            operation_id: ID of the operation to execute
            triggered_by: Who/what triggered the operation
            
        Returns:
            Maintenance result with details and performance impact
        """
        if operation_id not in self.operations:
            raise ValueError(f"Unknown maintenance operation: {operation_id}")
        
        operation = self.operations[operation_id]
        started_at = datetime.now()
        
        logger.info(f"Starting maintenance operation: {operation.name}")
        
        try:
            # Check prerequisites
            for prereq in operation.prerequisites:
                if not self._check_prerequisite(prereq):
                    raise ValueError(f"Prerequisite not met: {prereq}")
            
            # Get baseline performance metrics
            baseline_metrics = self._get_performance_baseline()
            
            # Execute the operation
            operation_details = await asyncio.get_event_loop().run_in_executor(
                None, operation.operation_func
            )
            
            # Get post-operation performance metrics
            post_metrics = self._get_performance_baseline()
            
            # Calculate performance impact
            performance_impact = self._calculate_performance_impact(baseline_metrics, post_metrics)
            
            # Generate recommendations
            recommendations = self._generate_maintenance_recommendations(operation_id, operation_details, performance_impact)
            
            completed_at = datetime.now()
            
            result = MaintenanceResult(
                operation_id=operation_id,
                operation_name=operation.name,
                started_at=started_at,
                completed_at=completed_at,
                success=True,
                error_message=None,
                details=operation_details,
                performance_impact=performance_impact,
                recommendations=recommendations
            )
            
            # Save to history
            self._save_maintenance_result(result, triggered_by)
            
            logger.info(f"Maintenance operation completed successfully: {operation.name}")
            return result
            
        except Exception as e:
            logger.error(f"Maintenance operation failed: {operation.name}, error: {e}")
            
            result = MaintenanceResult(
                operation_id=operation_id,
                operation_name=operation.name,
                started_at=started_at,
                completed_at=datetime.now(),
                success=False,
                error_message=str(e),
                details={},
                performance_impact={},
                recommendations=[f"Operation failed: {str(e)}"]
            )
            
            # Save failed result to history
            self._save_maintenance_result(result, triggered_by)
            return result
    
    async def execute_maintenance_suite(self, operation_ids: List[str], triggered_by: str = 'manual') -> List[MaintenanceResult]:
        """Execute multiple maintenance operations in sequence.
        
        Args:
            operation_ids: List of operation IDs to execute
            triggered_by: Who/what triggered the operations
            
        Returns:
            List of maintenance results
        """
        results = []
        
        logger.info(f"Starting maintenance suite with {len(operation_ids)} operations")
        
        for operation_id in operation_ids:
            try:
                result = await self.execute_maintenance_operation(operation_id, triggered_by)
                results.append(result)
                
                # If operation failed and is critical, stop the suite
                if not result.success and self.operations[operation_id].risk_level == 'high':
                    logger.warning(f"Critical operation failed, stopping maintenance suite: {operation_id}")
                    break
                    
            except Exception as e:
                logger.error(f"Error in maintenance suite for operation {operation_id}: {e}")
                # Continue with next operation
                continue
        
        logger.info(f"Maintenance suite completed with {len(results)} operations")
        return results
    
    def _vacuum_database(self) -> Dict[str, Any]:
        """Vacuum the database to reclaim space and optimize."""
        try:
            with self._get_connection() as conn:
                # Get database size before vacuum
                size_before = self._get_database_size()
                
                # Perform vacuum
                conn.execute("VACUUM")
                
                # Get database size after vacuum
                size_after = self._get_database_size()
                
                space_reclaimed = size_before - size_after
                
                return {
                    'size_before_mb': size_before / (1024 * 1024),
                    'size_after_mb': size_after / (1024 * 1024),
                    'space_reclaimed_mb': space_reclaimed / (1024 * 1024),
                    'space_reclaimed_percent': (space_reclaimed / size_before * 100) if size_before > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Database vacuum error: {e}")
            raise
    
    def _analyze_database(self) -> Dict[str, Any]:
        """Analyze database to update statistics."""
        try:
            with self._get_connection() as conn:
                # Get table count before analysis
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                # Perform analysis
                conn.execute("ANALYZE")
                
                # Get statistics
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_stat1")
                stats_count = cursor.fetchone()[0] if cursor.fetchone() else 0
                
                return {
                    'tables_analyzed': table_count,
                    'statistics_updated': stats_count,
                    'analysis_completed': True
                }
                
        except Exception as e:
            logger.error(f"Database analysis error: {e}")
            raise
    
    def _check_database_integrity(self) -> Dict[str, Any]:
        """Check database integrity."""
        try:
            with self._get_connection() as conn:
                # Perform integrity check
                cursor = conn.execute("PRAGMA integrity_check")
                results = cursor.fetchall()
                
                # Check if integrity is OK
                integrity_ok = len(results) == 1 and results[0][0] == 'ok'
                
                return {
                    'integrity_ok': integrity_ok,
                    'check_results': [row[0] for row in results],
                    'issues_found': len(results) - 1 if not integrity_ok else 0
                }
                
        except Exception as e:
            logger.error(f"Database integrity check error: {e}")
            raise
    
    def _cleanup_cache(self) -> Dict[str, Any]:
        """Clean up cache entries."""
        try:
            # This is a placeholder - implement based on your caching system
            # For now, we'll simulate cache cleanup
            
            cache_entries_before = 1000  # Simulated
            cache_entries_after = 750    # Simulated
            
            return {
                'cache_entries_before': cache_entries_before,
                'cache_entries_after': cache_entries_after,
                'entries_removed': cache_entries_before - cache_entries_after,
                'cache_hit_rate_improvement': 0.05  # 5% improvement
            }
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            raise
    
    def _rebuild_cache(self) -> Dict[str, Any]:
        """Rebuild cache with fresh data."""
        try:
            # This is a placeholder - implement based on your caching system
            
            return {
                'cache_rebuilt': True,
                'cache_entries_created': 500,
                'rebuild_duration_seconds': 2.5
            }
            
        except Exception as e:
            logger.error(f"Cache rebuild error: {e}")
            raise
    
    def _rotate_logs(self) -> Dict[str, Any]:
        """Rotate log files."""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return {'logs_rotated': 0, 'message': 'No log directory found'}
            
            rotated_count = 0
            total_size_before = 0
            total_size_after = 0
            
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB threshold
                    total_size_before += log_file.stat().st_size
                    
                    # Create rotated filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    rotated_name = f"{log_file.stem}_{timestamp}.log"
                    rotated_path = log_dir / rotated_name
                    
                    # Move and compress
                    shutil.move(str(log_file), str(rotated_path))
                    
                    # Create new empty log file
                    log_file.touch()
                    
                    total_size_after += rotated_path.stat().st_size
                    rotated_count += 1
            
            return {
                'logs_rotated': rotated_count,
                'total_size_before_mb': total_size_before / (1024 * 1024),
                'total_size_after_mb': total_size_after / (1024 * 1024),
                'space_freed_mb': (total_size_before - total_size_after) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Log rotation error: {e}")
            raise
    
    def _cleanup_logs(self) -> Dict[str, Any]:
        """Clean up old log files."""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return {'logs_cleaned': 0, 'message': 'No log directory found'}
            
            cutoff_date = datetime.now() - timedelta(days=30)  # Keep 30 days
            cleaned_count = 0
            space_freed = 0
            
            for log_file in log_dir.glob("*.log*"):
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    space_freed += log_file.stat().st_size
                    log_file.unlink()
                    cleaned_count += 1
            
            return {
                'logs_cleaned': cleaned_count,
                'space_freed_mb': space_freed / (1024 * 1024),
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Log cleanup error: {e}")
            raise
    
    def _cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up temporary files."""
        try:
            temp_dirs = [Path("temp"), Path("tmp"), Path("/tmp")]
            cleaned_count = 0
            space_freed = 0
            
            for temp_dir in temp_dirs:
                if temp_dir.exists() and temp_dir.is_dir():
                    for temp_file in temp_dir.glob("*"):
                        if temp_file.is_file():
                            # Only clean files older than 1 day
                            file_time = datetime.fromtimestamp(temp_file.stat().st_mtime)
                            if file_time < datetime.now() - timedelta(days=1):
                                space_freed += temp_file.stat().st_size
                                temp_file.unlink()
                                cleaned_count += 1
            
            return {
                'temp_files_cleaned': cleaned_count,
                'space_freed_mb': space_freed / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Temp file cleanup error: {e}")
            raise
    
    def _optimize_performance(self) -> Dict[str, Any]:
        """Apply performance optimizations."""
        try:
            optimizations_applied = []
            
            # Database optimizations
            with self._get_connection() as conn:
                # Set optimal pragma settings
                conn.execute("PRAGMA cache_size = 10000")
                conn.execute("PRAGMA temp_store = MEMORY")
                conn.execute("PRAGMA journal_mode = WAL")
                optimizations_applied.append("Database pragma optimization")
                
                # Update table statistics if needed
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_stat1")
                if not cursor.fetchone()[0]:
                    conn.execute("ANALYZE")
                    optimizations_applied.append("Database statistics update")
            
            return {
                'optimizations_applied': optimizations_applied,
                'optimization_count': len(optimizations_applied),
                'performance_improvement_estimated': '5-10%'
            }
            
        except Exception as e:
            logger.error(f"Performance optimization error: {e}")
            raise
    
    def _get_database_size(self) -> int:
        """Get current database size in bytes."""
        try:
            return Path(self.db_path).stat().st_size
        except Exception:
            return 0
    
    def _get_performance_baseline(self) -> Dict[str, float]:
        """Get current performance baseline metrics."""
        try:
            start_time = time.time()
            
            # Test database response time
            with self._get_connection() as conn:
                conn.execute("SELECT COUNT(*) FROM learned_patterns").fetchone()
            
            db_response_time = (time.time() - start_time) * 1000
            
            # Get system health
            health = self.monitor.get_system_health()
            
            return {
                'db_response_time_ms': db_response_time,
                'cache_performance': health.cache_performance,
                'error_rate': health.recent_error_rate,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance baseline: {e}")
            return {}
    
    def _calculate_performance_impact(self, before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
        """Calculate performance impact of maintenance operation."""
        impact = {}
        
        try:
            for metric in ['db_response_time_ms', 'cache_performance', 'error_rate']:
                if metric in before and metric in after:
                    before_value = before[metric]
                    after_value = after[metric]
                    
                    if before_value != 0:
                        change_percent = ((after_value - before_value) / before_value) * 100
                        impact[f'{metric}_change_percent'] = change_percent
                    
                    impact[f'{metric}_before'] = before_value
                    impact[f'{metric}_after'] = after_value
            
            return impact
            
        except Exception as e:
            logger.error(f"Error calculating performance impact: {e}")
            return {}
    
    def _generate_maintenance_recommendations(self, operation_id: str, details: Dict[str, Any], impact: Dict[str, float]) -> List[str]:
        """Generate recommendations based on maintenance results."""
        recommendations = []
        
        try:
            # Database-specific recommendations
            if operation_id == 'db_vacuum':
                space_reclaimed_percent = details.get('space_reclaimed_percent', 0)
                if space_reclaimed_percent > 10:
                    recommendations.append("Consider running vacuum more frequently - significant space was reclaimed")
                elif space_reclaimed_percent < 1:
                    recommendations.append("Database is well-optimized - vacuum frequency can be reduced")
            
            elif operation_id == 'db_integrity_check':
                if not details.get('integrity_ok', True):
                    recommendations.append("⚠️ Database integrity issues found - immediate attention required")
                    recommendations.append("Consider database backup and repair procedures")
            
            # Cache-specific recommendations
            elif operation_id == 'cache_cleanup':
                hit_rate_improvement = details.get('cache_hit_rate_improvement', 0)
                if hit_rate_improvement > 0.1:
                    recommendations.append("Cache cleanup significantly improved performance - consider more frequent cleanup")
            
            # Performance impact recommendations
            db_improvement = impact.get('db_response_time_ms_change_percent', 0)
            if db_improvement < -10:  # 10% improvement
                recommendations.append("✅ Significant database performance improvement achieved")
            elif db_improvement > 10:  # 10% degradation
                recommendations.append("⚠️ Database performance degraded - investigate potential issues")
            
            # General recommendations
            if not recommendations:
                recommendations.append("✅ Maintenance completed successfully with no issues detected")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Unable to generate recommendations due to analysis error"]
    
    def _check_prerequisite(self, prereq_operation_id: str) -> bool:
        """Check if prerequisite operation has been completed recently."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT success FROM maintenance_history 
                WHERE operation_id = ? AND started_at >= datetime('now', '-1 day')
                ORDER BY started_at DESC LIMIT 1
                """, (prereq_operation_id,))
                
                result = cursor.fetchone()
                return result is not None and result['success']
                
        except Exception as e:
            logger.error(f"Error checking prerequisite {prereq_operation_id}: {e}")
            return False
    
    def _save_maintenance_result(self, result: MaintenanceResult, triggered_by: str):
        """Save maintenance result to history."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT INTO maintenance_history 
                (operation_id, operation_name, started_at, completed_at, success, 
                 error_message, details, performance_impact, recommendations, triggered_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.operation_id,
                    result.operation_name,
                    result.started_at,
                    result.completed_at,
                    result.success,
                    result.error_message,
                    json.dumps(result.details),
                    json.dumps(result.performance_impact),
                    json.dumps(result.recommendations),
                    triggered_by
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving maintenance result: {e}")
    
    def get_maintenance_history(self, days: int = 30) -> List[MaintenanceResult]:
        """Get maintenance history for the specified period."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT * FROM maintenance_history 
                WHERE started_at >= datetime('now', '-{} days')
                ORDER BY started_at DESC
                """.format(days))
                
                results = []
                for row in cursor.fetchall():
                    result = MaintenanceResult(
                        operation_id=row['operation_id'],
                        operation_name=row['operation_name'],
                        started_at=datetime.fromisoformat(row['started_at']),
                        completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                        success=bool(row['success']),
                        error_message=row['error_message'],
                        details=json.loads(row['details']) if row['details'] else {},
                        performance_impact=json.loads(row['performance_impact']) if row['performance_impact'] else {},
                        recommendations=json.loads(row['recommendations']) if row['recommendations'] else []
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting maintenance history: {e}")
            return []
    
    def get_available_operations(self) -> List[MaintenanceOperation]:
        """Get list of available maintenance operations."""
        return list(self.operations.values())
    
    def create_maintenance_schedule(self, schedule: MaintenanceSchedule) -> bool:
        """Create a new maintenance schedule."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO maintenance_schedules 
                (schedule_id, name, operations, schedule_type, schedule_config, 
                 enabled, next_run, notification_settings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule.schedule_id,
                    schedule.name,
                    json.dumps(schedule.operations),
                    schedule.schedule_type,
                    json.dumps(schedule.schedule_config),
                    schedule.enabled,
                    schedule.next_run,
                    json.dumps(schedule.notification_settings)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating maintenance schedule: {e}")
            return False
    
    def start_scheduler(self):
        """Start the maintenance scheduler."""
        if not self._scheduler_running:
            self._scheduler_running = True
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()
            logger.info("Maintenance scheduler started")
    
    def stop_scheduler(self):
        """Stop the maintenance scheduler."""
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Maintenance scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._scheduler_running:
            try:
                self._check_scheduled_maintenance()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _check_scheduled_maintenance(self):
        """Check for scheduled maintenance that needs to run."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT * FROM maintenance_schedules 
                WHERE enabled = 1 AND next_run <= datetime('now')
                """)
                
                for row in cursor.fetchall():
                    schedule = MaintenanceSchedule(
                        schedule_id=row['schedule_id'],
                        name=row['name'],
                        operations=json.loads(row['operations']),
                        schedule_type=row['schedule_type'],
                        schedule_config=json.loads(row['schedule_config']),
                        enabled=bool(row['enabled']),
                        last_run=datetime.fromisoformat(row['last_run']) if row['last_run'] else None,
                        next_run=datetime.fromisoformat(row['next_run']) if row['next_run'] else None,
                        notification_settings=json.loads(row['notification_settings']) if row['notification_settings'] else {}
                    )
                    
                    # Execute scheduled maintenance
                    asyncio.create_task(self._execute_scheduled_maintenance(schedule))
                    
        except Exception as e:
            logger.error(f"Error checking scheduled maintenance: {e}")
    
    async def _execute_scheduled_maintenance(self, schedule: MaintenanceSchedule):
        """Execute scheduled maintenance."""
        try:
            logger.info(f"Executing scheduled maintenance: {schedule.name}")
            
            results = await self.execute_maintenance_suite(
                schedule.operations, 
                triggered_by=f"schedule:{schedule.schedule_id}"
            )
            
            # Update schedule
            next_run = self._calculate_next_run(schedule)
            
            with self._get_connection() as conn:
                conn.execute("""
                UPDATE maintenance_schedules 
                SET last_run = ?, next_run = ? 
                WHERE schedule_id = ?
                """, (datetime.now(), next_run, schedule.schedule_id))
                conn.commit()
            
            logger.info(f"Scheduled maintenance completed: {schedule.name}")
            
        except Exception as e:
            logger.error(f"Error executing scheduled maintenance {schedule.name}: {e}")
    
    def _calculate_next_run(self, schedule: MaintenanceSchedule) -> datetime:
        """Calculate next run time for a schedule."""
        now = datetime.now()
        
        if schedule.schedule_type == 'daily':
            return now + timedelta(days=1)
        elif schedule.schedule_type == 'weekly':
            return now + timedelta(weeks=1)
        elif schedule.schedule_type == 'monthly':
            return now + timedelta(days=30)
        else:
            # Custom schedule - implement based on schedule_config
            return now + timedelta(days=1)  # Default to daily
```

### Configuration Service

Create `app/services/configuration_service.py`:

```python
"""
Configuration Service for AAA Admin Monitoring

This service manages system configuration, user preferences,
and advanced settings for the admin dashboard.

Sprint 3.1 Features:
- System configuration management
- User preference storage
- Alert rule configuration
- Performance tuning settings
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE

logger = logging.getLogger(__name__)


@dataclass
class ConfigurationItem:
    """Individual configuration item."""
    key: str
    value: Any
    config_type: str  # 'string', 'integer', 'float', 'boolean', 'json'
    description: str
    category: str
    requires_restart: bool
    updated_at: datetime
    updated_by: str


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    rule_name: str
    metric_name: str
    condition_type: str  # 'greater_than', 'less_than', 'equals', 'not_equals'
    threshold_value: float
    severity: str  # 'info', 'warning', 'error', 'critical'
    enabled: bool
    escalation_rules: Dict[str, Any]
    notification_channels: List[str]
    created_at: datetime
    updated_at: datetime


class ConfigurationService:
    """Service for system configuration management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the configuration service.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self._ensure_config_tables()
        self._initialize_default_config()
    
    def _ensure_config_tables(self):
        """Ensure configuration tables exist."""
        try:
            with self._get_connection() as conn:
                # System configuration table (already created in maintenance service)
                # Alert rules table (already created in maintenance service)
                
                # User preferences table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, preference_key)
                )
                """)
                
                # Configuration history for audit trail
                conn.execute("""
                CREATE TABLE IF NOT EXISTS configuration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    change_reason TEXT
                )
                """)
                
        except Exception as e:
            logger.error(f"Error creating configuration tables: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_default_config(self):
        """Initialize default configuration values."""
        default_configs = [
            # Dashboard settings
            ('dashboard.refresh_interval', '30', 'integer', 'Dashboard auto-refresh interval in seconds', 'dashboard', False),
            ('dashboard.max_chart_points', '100', 'integer', 'Maximum data points to display in charts', 'dashboard', False),
            ('dashboard.theme', 'light', 'string', 'Dashboard theme (light/dark)', 'dashboard', False),
            
            # Performance settings
            ('performance.cache_ttl', '300', 'integer', 'Cache time-to-live in seconds', 'performance', False),
            ('performance.query_timeout', '30', 'integer', 'Database query timeout in seconds', 'performance', True),
            ('performance.max_concurrent_queries', '10', 'integer', 'Maximum concurrent database queries', 'performance', True),
            
            # Alert settings
            ('alerts.default_severity', 'warning', 'string', 'Default alert severity level', 'alerts', False),
            ('alerts.notification_cooldown', '300', 'integer', 'Cooldown period between notifications in seconds', 'alerts', False),
            ('alerts.max_alerts_per_hour', '20', 'integer', 'Maximum alerts to send per hour', 'alerts', False),
            
            # Maintenance settings
            ('maintenance.auto_vacuum_enabled', 'true', 'boolean', 'Enable automatic database vacuum', 'maintenance', False),
            ('maintenance.log_retention_days', '30', 'integer', 'Number of days to retain log files', 'maintenance', False),
            ('maintenance.backup_retention_days', '90', 'integer', 'Number of days to retain backup files', 'maintenance', False),
            
            # Learning system settings
            ('learning.pattern_confidence_threshold', '0.8', 'float', 'Minimum confidence threshold for patterns', 'learning', False),
            ('learning.max_patterns_per_type', '1000', 'integer', 'Maximum patterns to store per type', 'learning', False),
            ('learning.auto_cleanup_enabled', 'true', 'boolean', 'Enable automatic cleanup of old patterns', 'learning', False),
            
            # Export settings
            ('export.max_file_size_mb', '100', 'integer', 'Maximum export file size in MB', 'export', False),
            ('export.temp_file_retention_hours', '24', 'integer', 'Hours to retain temporary export files', 'export', False),
            ('export.default_format', 'pdf', 'string', 'Default export format', 'export', False),
        ]
        
        try:
            with self._get_connection() as conn:
                for key, value, config_type, description, category, requires_restart in default_configs:
                    # Only insert if not exists
                    cursor = conn.execute("SELECT 1 FROM system_configuration WHERE config_key = ?", (key,))
                    if not cursor.fetchone():
                        conn.execute("""
                        INSERT INTO system_configuration 
                        (config_key, config_value, config_type, description, category, requires_restart)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (key, value, config_type, description, category, requires_restart))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error initializing default configuration: {e}")
    
    def get_configuration(self, key: str) -> Optional[ConfigurationItem]:
        """Get a configuration item by key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT * FROM system_configuration WHERE config_key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if row:
                    return ConfigurationItem(
                        key=row['config_key'],
                        value=self._parse_config_value(row['config_value'], row['config_type']),
                        config_type=row['config_type'],
                        description=row['description'],
                        category=row['category'],
                        requires_restart=bool(row['requires_restart']),
                        updated_at=datetime.fromisoformat(row['updated_at']),
                        updated_by=row['updated_by']
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting configuration {key}: {e}")
            return None
    
    def get_configuration_by_category(self, category: str) -> List[ConfigurationItem]:
        """Get all configuration items in a category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT * FROM system_configuration WHERE category = ?
                ORDER BY config_key
                """, (category,))
                
                items = []
                for row in cursor.fetchall():
                    item = ConfigurationItem(
                        key=row['config_key'],
                        value=self._parse_config_value(row['config_value'], row['config_type']),
                        config_type=row['config_type'],
                        description=row['description'],
                        category=row['category'],
                        requires_restart=bool(row['requires_restart']),
                        updated_at=datetime.fromisoformat(row['updated_at']),
                        updated_by=row['updated_by']
                    )
                    items.append(item)
                
                return items
                
        except Exception as e:
            logger.error(f"Error getting configuration for category {category}: {e}")
            return []
    
    def set_configuration(self, key: str, value: Any, updated_by: str = 'system', change_reason: str = '') -> bool:
        """Set a configuration value."""
        try:
            # Get current value for history
            current_config = self.get_configuration(key)
            old_value = current_config.value if current_config else None
            
            # Convert value to string for storage
            if isinstance(value, bool):
                str_value = 'true' if value else 'false'
                config_type = 'boolean'
            elif isinstance(value, int):
                str_value = str(value)
                config_type = 'integer'
            elif isinstance(value, float):
                str_value = str(value)
                config_type = 'float'
            elif isinstance(value, (dict, list)):
                str_value = json.dumps(value)
                config_type = 'json'
            else:
                str_value = str(value)
                config_type = 'string'
            
            with self._get_connection() as conn:
                # Update configuration
                conn.execute("""
                UPDATE system_configuration 
                SET config_value = ?, config_type = ?, updated_at = ?, updated_by = ?
                WHERE config_key = ?
                """, (str_value, config_type, datetime.now(), updated_by, key))
                
                # Add to history
                conn.execute("""
                INSERT INTO configuration_history 
                (config_key, old_value, new_value, changed_by, change_reason)
                VALUES (?, ?, ?, ?, ?)
                """, (key, str(old_value) if old_value is not None else None, str_value, updated_by, change_reason))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting configuration {key}: {e}")
            return False
    
    def _parse_config_value(self, value: str, config_type: str) -> Any:
        """Parse configuration value based on type."""
        try:
            if config_type == 'boolean':
                return value.lower() in ('true', '1', 'yes', 'on')
            elif config_type == 'integer':
                return int(value)
            elif config_type == 'float':
                return float(value)
            elif config_type == 'json':
                return json.loads(value)
            else:
                return value
                
        except Exception as e:
            logger.error(f"Error parsing config value {value} as {config_type}: {e}")
            return value
    
    def get_all_categories(self) -> List[str]:
        """Get all configuration categories."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT DISTINCT category FROM system_configuration 
                ORDER BY category
                """)
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting configuration categories: {e}")
            return []
    
    def create_alert_rule(self, rule: AlertRule) -> bool:
        """Create a new alert rule."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO alert_rules 
                (rule_id, rule_name, metric_name, condition_type, threshold_value, 
                 severity, enabled, escalation_rules, notification_channels)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id,
                    rule.rule_name,
                    rule.metric_name,
                    rule.condition_type,
                    rule.threshold_value,
                    rule.severity,
                    rule.enabled,
                    json.dumps(rule.escalation_rules),
                    json.dumps(rule.notification_channels)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return False
    
    def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT * FROM alert_rules ORDER BY rule_name
                """)
                
                rules = []
                for row in cursor.fetchall():
                    rule = AlertRule(
                        rule_id=row['rule_id'],
                        rule_name=row['rule_name'],
                        metric_name=row['metric_name'],
                        condition_type=row['condition_type'],
                        threshold_value=row['threshold_value'],
                        severity=row['severity'],
                        enabled=bool(row['enabled']),
                        escalation_rules=json.loads(row['escalation_rules']) if row['escalation_rules'] else {},
                        notification_channels=json.loads(row['notification_channels']) if row['notification_channels'] else [],
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at'])
                    )
                    rules.append(rule)
                
                return rules
                
        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            return []
    
    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM alert_rules WHERE rule_id = ?", (rule_id,))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting alert rule {rule_id}: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT preference_key, preference_value FROM user_preferences 
                WHERE user_id = ?
                """, (user_id,))
                
                preferences = {}
                for row in cursor.fetchall():
                    try:
                        # Try to parse as JSON first
                        preferences[row['preference_key']] = json.loads(row['preference_value'])
                    except json.JSONDecodeError:
                        # Fall back to string value
                        preferences[row['preference_key']] = row['preference_value']
                
                return preferences
                
        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")
            return {}
    
    def set_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """Set a user preference."""
        try:
            # Convert value to JSON string
            if isinstance(value, (dict, list, bool, int, float)):
                str_value = json.dumps(value)
            else:
                str_value = str(value)
            
            with self._get_connection() as conn:
                conn.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (user_id, preference_key, preference_value)
                VALUES (?, ?, ?)
                """, (user_id, key, str_value))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting user preference {key} for {user_id}: {e}")
            return False
    
    def get_configuration_history(self, key: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get configuration change history."""
        try:
            with self._get_connection() as conn:
                if key:
                    cursor = conn.execute("""
                    SELECT * FROM configuration_history 
                    WHERE config_key = ? AND changed_at >= datetime('now', '-{} days')
                    ORDER BY changed_at DESC
                    """.format(days), (key,))
                else:
                    cursor = conn.execute("""
                    SELECT * FROM configuration_history 
                    WHERE changed_at >= datetime('now', '-{} days')
                    ORDER BY changed_at DESC
                    """.format(days))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'config_key': row['config_key'],
                        'old_value': row['old_value'],
                        'new_value': row['new_value'],
                        'changed_by': row['changed_by'],
                        'changed_at': row['changed_at'],
                        'change_reason': row['change_reason']
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting configuration history: {e}")
            return []
```

### Maintenance Panel Component

Create `app/components/admin_dashboard/maintenance_panel.py`:

```python
"""
Maintenance Panel Component for Admin Dashboard

Provides user interface for maintenance operations, scheduling,
and system configuration.

Sprint 3.1 Features:
- One-click maintenance operations
- Maintenance scheduling interface
- Progress tracking and results
- System configuration management
"""

import panel as pn
import asyncio
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta

from app.services.maintenance_service import MaintenanceService, MaintenanceSchedule
from app.services.configuration_service import ConfigurationService, AlertRule

logger = logging.getLogger(__name__)

pn.extension('bokeh', 'tabulator')


class MaintenancePanel:
    """Panel for maintenance operations and configuration."""
    
    def __init__(self, maintenance_service: Optional[MaintenanceService] = None, 
                 config_service: Optional[ConfigurationService] = None):
        """Initialize the maintenance panel.
        
        Args:
            maintenance_service: Optional maintenance service (for testing)
            config_service: Optional configuration service (for testing)
        """
        self.maintenance_service = maintenance_service or MaintenanceService()
        self.config_service = config_service or ConfigurationService()
        
        # Create UI components
        self._create_components()
    
    def _create_components(self):
        """Create all UI components."""
        # Maintenance operations section
        self._create_maintenance_components()
        
        # Configuration section
        self._create_configuration_components()
        
        # Alert management section
        self._create_alert_components()
    
    def _create_maintenance_components(self):
        """Create maintenance operation components."""
        # Available operations
        operations = self.maintenance_service.get_available_operations()
        
        # Operation selector
        self.operation_selector = pn.widgets.CheckBoxGroup(
            name="Select Operations",
            value=[],
            options={op.name: op.operation_id for op in operations},
            inline=False,
            width=400
        )
        
        # Quick maintenance buttons
        self.quick_maintenance_buttons = pn.Row(
            pn.widgets.Button(
                name="🗄️ Database Cleanup",
                button_type='primary',
                width=150
            ),
            pn.widgets.Button(
                name="🧹 Cache Cleanup", 
                button_type='primary',
                width=150
            ),
            pn.widgets.Button(
                name="📝 Log Rotation",
                button_type='primary', 
                width=150
            ),
            pn.widgets.Button(
                name="⚡ Full Optimization",
                button_type='success',
                width=150
            )
        )
        
        # Bind quick maintenance buttons
        self.quick_maintenance_buttons[0].on_click(lambda event: self._run_quick_maintenance(['db_vacuum', 'db_analyze']))
        self.quick_maintenance_buttons[1].on_click(lambda event: self._run_quick_maintenance(['cache_cleanup']))
        self.quick_maintenance_buttons[2].on_click(lambda event: self._run_quick_maintenance(['log_rotation', 'log_cleanup']))
        self.quick_maintenance_buttons[3].on_click(lambda event: self._run_quick_maintenance(['db_vacuum', 'db_analyze', 'cache_cleanup', 'performance_optimization']))
        
        # Custom maintenance button
        self.run_maintenance_button = pn.widgets.Button(
            name="Run Selected Operations",
            button_type='primary',
            width=200
        )
        self.run_maintenance_button.on_click(self._on_run_maintenance)
        
        # Progress and status
        self.maintenance_status = pn.pane.HTML(
            "<p>Ready to run maintenance operations</p>",
            width=600
        )
        
        self.maintenance_progress = pn.indicators.Progress(
            name='Maintenance Progress',
            value=0,
            width=600,
            visible=False
        )
        
        # Results display
        self.maintenance_results = pn.Column(width=800)
        
        # Maintenance history
        self.maintenance_history_table = pn.widgets.Tabulator(
            value=self._get_maintenance_history_data(),
            pagination='remote',
            page_size=10,
            width=800,
            height=300
        )
        
        # Schedule maintenance
        self.schedule_name_input = pn.widgets.TextInput(
            name="Schedule Name",
            placeholder="Enter schedule name",
            width=200
        )
        
        self.schedule_type_selector = pn.widgets.Select(
            name="Schedule Type",
            value='weekly',
            options=['daily', 'weekly', 'monthly'],
            width=150
        )
        
        self.create_schedule_button = pn.widgets.Button(
            name="Create Schedule",
            button_type='success',
            width=150
        )
        self.create_schedule_button.on_click(self._on_create_schedule)
    
    def _create_configuration_components(self):
        """Create configuration management components."""
        # Configuration category selector
        categories = self.config_service.get_all_categories()
        self.config_category_selector = pn.widgets.Select(
            name="Configuration Category",
            value=categories[0] if categories else '',
            options=categories,
            width=200
        )
        self.config_category_selector.param.watch(self._on_config_category_change, 'value')
        
        # Configuration table
        self.config_table = pn.widgets.Tabulator(
            value=self._get_config_data(),
            pagination='local',
            page_size=15,
            width=800,
            height=400,
            editors={
                'value': {'type': 'input'},
                'description': None  # Read-only
            }
        )
        
        # Configuration save button
        self.save_config_button = pn.widgets.Button(
            name="Save Configuration",
            button_type='primary',
            width=150
        )
        self.save_config_button.on_click(self._on_save_config)
        
        # Configuration status
        self.config_status = pn.pane.HTML(
            "<p>Configuration ready for editing</p>",
            width=600
        )
    
    def _create_alert_components(self):
        """Create alert management components."""
        # Alert rule form
        self.alert_name_input = pn.widgets.TextInput(
            name="Alert Name",
            placeholder="Enter alert name",
            width=200
        )
        
        self.alert_metric_selector = pn.widgets.Select(
            name="Metric",
            options=[
                'db_response_time_ms',
                'cache_hit_rate',
                'error_rate',
                'memory_usage_percent',
                'disk_usage_percent'
            ],
            width=200
        )
        
        self.alert_condition_selector = pn.widgets.Select(
            name="Condition",
            options=[
                ('Greater than', 'greater_than'),
                ('Less than', 'less_than'),
                ('Equals', 'equals'),
                ('Not equals', 'not_equals')
            ],
            width=150
        )
        
        self.alert_threshold_input = pn.widgets.FloatInput(
            name="Threshold",
            value=0.0,
            width=100
        )
        
        self.alert_severity_selector = pn.widgets.Select(
            name="Severity",
            options=['info', 'warning', 'error', 'critical'],
            value='warning',
            width=100
        )
        
        self.create_alert_button = pn.widgets.Button(
            name="Create Alert Rule",
            button_type='primary',
            width=150
        )
        self.create_alert_button.on_click(self._on_create_alert)
        
        # Alert rules table
        self.alert_rules_table = pn.widgets.Tabulator(
            value=self._get_alert_rules_data(),
            pagination='local',
            page_size=10,
            width=800,
            height=300
        )
    
    def _run_quick_maintenance(self, operation_ids: List[str]):
        """Run quick maintenance operations."""
        self.maintenance_status.object = f"<p>🔄 Running {len(operation_ids)} maintenance operations...</p>"
        self.maintenance_progress.visible = True
        self.maintenance_progress.value = 0
        
        # Run maintenance in background
        asyncio.create_task(self._execute_maintenance_suite(operation_ids))
    
    def _on_run_maintenance(self, event):
        """Handle run maintenance button click."""
        selected_operations = self.operation_selector.value
        if not selected_operations:
            self.maintenance_status.object = "<p>⚠️ Please select at least one operation</p>"
            return
        
        self._run_quick_maintenance(selected_operations)
    
    async def _execute_maintenance_suite(self, operation_ids: List[str]):
        """Execute maintenance operations asynchronously."""
        try:
            total_operations = len(operation_ids)
            
            for i, operation_id in enumerate(operation_ids):
                # Update progress
                progress = (i / total_operations) * 100
                self.maintenance_progress.value = int(progress)
                
                # Execute operation
                result = await self.maintenance_service.execute_maintenance_operation(operation_id)
                
                # Add result to display
                result_card = self._create_result_card(result)
                self.maintenance_results.append(result_card)
                
                # Keep only last 5 results
                if len(self.maintenance_results) > 5:
                    self.maintenance_results.pop(0)
            
            # Complete
            self.maintenance_progress.value = 100
            self.maintenance_status.object = f"<p>✅ Maintenance completed successfully! {total_operations} operations executed.</p>"
            
            # Hide progress after delay
            await asyncio.sleep(2)
            self.maintenance_progress.visible = False
            
            # Refresh history table
            self.maintenance_history_table.value = self._get_maintenance_history_data()
            
        except Exception as e:
            logger.error(f"Error executing maintenance suite: {e}")
            self.maintenance_status.object = f"<p>❌ Maintenance failed: {str(e)}</p>"
            self.maintenance_progress.visible = False
    
    def _create_result_card(self, result) -> pn.pane.HTML:
        """Create a result card for maintenance operation."""
        status_icon = "✅" if result.success else "❌"
        status_color = "#d4edda" if result.success else "#f8d7da"
        
        duration = ""
        if result.completed_at and result.started_at:
            duration_seconds = (result.completed_at - result.started_at).total_seconds()
            duration = f"Duration: {duration_seconds:.1f}s"
        
        recommendations_html = ""
        if result.recommendations:
            recommendations_html = "<br><strong>Recommendations:</strong><ul>"
            for rec in result.recommendations[:3]:  # Show first 3
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul>"
        
        card_html = f"""
        <div style="background: {status_color}; padding: 15px; border-radius: 8px; margin: 5px 0; border-left: 4px solid {'#28a745' if result.success else '#dc3545'};">
            <h4 style="margin: 0 0 5px 0;">{status_icon} {result.operation_name}</h4>
            <p style="margin: 0; color: #666;">
                {duration} | Started: {result.started_at.strftime('%H:%M:%S')}
            </p>
            {recommendations_html}
        </div>
        """
        
        return pn.pane.HTML(card_html, width=780)
    
    def _get_maintenance_history_data(self) -> List[Dict[str, Any]]:
        """Get maintenance history data for table."""
        try:
            history = self.maintenance_service.get_maintenance_history(30)
            
            data = []
            for result in history:
                duration = ""
                if result.completed_at and result.started_at:
                    duration_seconds = (result.completed_at - result.started_at).total_seconds()
                    duration = f"{duration_seconds:.1f}s"
                
                data.append({
                    'operation': result.operation_name,
                    'status': '✅ Success' if result.success else '❌ Failed',
                    'started_at': result.started_at.strftime('%Y-%m-%d %H:%M'),
                    'duration': duration,
                    'recommendations': len(result.recommendations)
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting maintenance history data: {e}")
            return []
    
    def _on_create_schedule(self, event):
        """Handle create schedule button click."""
        try:
            if not self.schedule_name_input.value:
                self.maintenance_status.object = "<p>⚠️ Please enter a schedule name</p>"
                return
            
            selected_operations = self.operation_selector.value
            if not selected_operations:
                self.maintenance_status.object = "<p>⚠️ Please select operations for the schedule</p>"
                return
            
            # Create schedule
            schedule = MaintenanceSchedule(
                schedule_id=f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=self.schedule_name_input.value,
                operations=selected_operations,
                schedule_type=self.schedule_type_selector.value,
                schedule_config={},
                enabled=True,
                last_run=None,
                next_run=datetime.now() + timedelta(days=1),  # Start tomorrow
                notification_settings={}
            )
            
            success = self.maintenance_service.create_maintenance_schedule(schedule)
            
            if success:
                self.maintenance_status.object = f"<p>✅ Schedule '{schedule.name}' created successfully!</p>"
                self.schedule_name_input.value = ""
                self.operation_selector.value = []
            else:
                self.maintenance_status.object = "<p>❌ Failed to create schedule</p>"
                
        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            self.maintenance_status.object = f"<p>❌ Error creating schedule: {str(e)}</p>"
    
    def _get_config_data(self) -> List[Dict[str, Any]]:
        """Get configuration data for table."""
        try:
            category = self.config_category_selector.value
            if not category:
                return []
            
            configs = self.config_service.get_configuration_by_category(category)
            
            data = []
            for config in configs:
                data.append({
                    'key': config.key,
                    'value': str(config.value),
                    'type': config.config_type,
                    'description': config.description,
                    'requires_restart': '⚠️' if config.requires_restart else ''
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting config data: {e}")
            return []
    
    def _on_config_category_change(self, event):
        """Handle configuration category change."""
        self.config_table.value = self._get_config_data()
    
    def _on_save_config(self, event):
        """Handle save configuration button click."""
        try:
            # Get modified data from table
            modified_data = self.config_table.value
            
            saved_count = 0
            for row in modified_data:
                key = row['key']
                new_value = row['value']
                
                # Parse value based on type
                config_type = row['type']
                if config_type == 'boolean':
                    parsed_value = new_value.lower() in ('true', '1', 'yes', 'on')
                elif config_type == 'integer':
                    parsed_value = int(new_value)
                elif config_type == 'float':
                    parsed_value = float(new_value)
                else:
                    parsed_value = new_value
                
                # Save configuration
                if self.config_service.set_configuration(key, parsed_value, 'admin_dashboard', 'Updated via dashboard'):
                    saved_count += 1
            
            self.config_status.object = f"<p>✅ Saved {saved_count} configuration changes</p>"
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            self.config_status.object = f"<p>❌ Error saving configuration: {str(e)}</p>"
    
    def _get_alert_rules_data(self) -> List[Dict[str, Any]]:
        """Get alert rules data for table."""
        try:
            rules = self.config_service.get_alert_rules()
            
            data = []
            for rule in rules:
                data.append({
                    'name': rule.rule_name,
                    'metric': rule.metric_name,
                    'condition': f"{rule.condition_type} {rule.threshold_value}",
                    'severity': rule.severity,
                    'enabled': '✅' if rule.enabled else '❌',
                    'rule_id': rule.rule_id
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting alert rules data: {e}")
            return []
    
    def _on_create_alert(self, event):
        """Handle create alert button click."""
        try:
            if not self.alert_name_input.value:
                return
            
            # Create alert rule
            rule = AlertRule(
                rule_id=f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                rule_name=self.alert_name_input.value,
                metric_name=self.alert_metric_selector.value,
                condition_type=self.alert_condition_selector.value,
                threshold_value=self.alert_threshold_input.value,
                severity=self.alert_severity_selector.value,
                enabled=True,
                escalation_rules={},
                notification_channels=['dashboard'],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            success = self.config_service.create_alert_rule(rule)
            
            if success:
                # Clear form
                self.alert_name_input.value = ""
                self.alert_threshold_input.value = 0.0
                
                # Refresh table
                self.alert_rules_table.value = self._get_alert_rules_data()
                
        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
    
    def get_panel(self):
        """Get the complete maintenance panel."""
        return pn.Tabs(
            ("🔧 Maintenance Operations", pn.Column(
                pn.pane.HTML("<h2>🔧 Maintenance Operations</h2>"),
                
                # Quick maintenance
                pn.pane.HTML("<h3>⚡ Quick Maintenance</h3>"),
                self.quick_maintenance_buttons,
                
                pn.Divider(),
                
                # Custom maintenance
                pn.pane.HTML("<h3>🛠️ Custom Maintenance</h3>"),
                pn.Row(
                    self.operation_selector,
                    pn.Spacer(width=50),
                    pn.Column(
                        self.run_maintenance_button,
                        pn.pane.HTML("<h4>📅 Schedule Maintenance</h4>"),
                        pn.Row(
                            self.schedule_name_input,
                            self.schedule_type_selector,
                            self.create_schedule_button
                        )
                    )
                ),
                
                pn.Divider(),
                
                # Status and progress
                self.maintenance_status,
                self.maintenance_progress,
                
                # Results
                pn.pane.HTML("<h3>📊 Recent Results</h3>"),
                self.maintenance_results,
                
                # History
                pn.pane.HTML("<h3>📋 Maintenance History</h3>"),
                self.maintenance_history_table,
                
                width=900
            )),
            
            ("⚙️ System Configuration", pn.Column(
                pn.pane.HTML("<h2>⚙️ System Configuration</h2>"),
                
                pn.Row(
                    self.config_category_selector,
                    pn.Spacer(width=50),
                    self.save_config_button
                ),
                
                self.config_status,
                self.config_table,
                
                width=900
            )),
            
            ("🚨 Alert Management", pn.Column(
                pn.pane.HTML("<h2>🚨 Alert Management</h2>"),
                
                pn.pane.HTML("<h3>Create New Alert Rule</h3>"),
                pn.Row(
                    self.alert_name_input,
                    self.alert_metric_selector,
                    self.alert_condition_selector,
                    self.alert_threshold_input,
                    self.alert_severity_selector,
                    self.create_alert_button
                ),
                
                pn.Divider(),
                
                pn.pane.HTML("<h3>Existing Alert Rules</h3>"),
                self.alert_rules_table,
                
                width=900
            ))
        )
```

## TESTING REQUIREMENTS

### Unit Tests

Create `tests/services/test_maintenance_service.py`:

```python
"""
Tests for Maintenance Service

Sprint 3.1 Testing:
- Maintenance operation execution
- Performance impact calculation
- Scheduling functionality
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from app.services.maintenance_service import MaintenanceService, MaintenanceResult, MaintenanceSchedule


class TestMaintenanceService:
    """Test cases for MaintenanceService."""
    
    @pytest.fixture
    def maintenance_service(self, tmp_path):
        """Create maintenance service with test database."""
        db_path = tmp_path / "test_maintenance.db"
        return MaintenanceService(str(db_path))
    
    @pytest.mark.asyncio
    async def test_execute_maintenance_operation(self, maintenance_service):
        """Test executing a single maintenance operation."""
        result = await maintenance_service.execute_maintenance_operation('db_vacuum')
        
        assert result is not None
        assert result.operation_id == 'db_vacuum'
        assert result.operation_name == 'Database Vacuum'
        assert result.started_at is not None
        assert result.completed_at is not None
        assert isinstance(result.success, bool)
        assert isinstance(result.details, dict)
        assert isinstance(result.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_execute_maintenance_suite(self, maintenance_service):
        """Test executing multiple maintenance operations."""
        operation_ids = ['db_vacuum', 'cache_cleanup']
        results = await maintenance_service.execute_maintenance_suite(operation_ids)
        
        assert len(results) == 2
        assert all(isinstance(r, MaintenanceResult) for r in results)
        assert results[0].operation_id == 'db_vacuum'
        assert results[1].operation_id == 'cache_cleanup'
    
    def test_get_available_operations(self, maintenance_service):
        """Test getting available maintenance operations."""
        operations = maintenance_service.get_available_operations()
        
        assert len(operations) > 0
        assert any(op.operation_id == 'db_vacuum' for op in operations)
        assert any(op.operation_id == 'cache_cleanup' for op in operations)
        
        # Check operation structure
        for op in operations:
            assert hasattr(op, 'operation_id')
            assert hasattr(op, 'name')
            assert hasattr(op, 'description')
            assert hasattr(op, 'category')
            assert hasattr(op, 'risk_level')
    
    def test_vacuum_database(self, maintenance_service):
        """Test database vacuum operation."""
        result = maintenance_service._vacuum_database()
        
        assert isinstance(result, dict)
        assert 'size_before_mb' in result
        assert 'size_after_mb' in result
        assert 'space_reclaimed_mb' in result
        assert result['size_before_mb'] >= result['size_after_mb']
    
    def test_analyze_database(self, maintenance_service):
        """Test database analysis operation."""
        result = maintenance_service._analyze_database()
        
        assert isinstance(result, dict)
        assert 'tables_analyzed' in result
        assert 'analysis_completed' in result
        assert result['analysis_completed'] is True
    
    def test_check_database_integrity(self, maintenance_service):
        """Test database integrity check."""
        result = maintenance_service._check_database_integrity()
        
        assert isinstance(result, dict)
        assert 'integrity_ok' in result
        assert 'check_results' in result
        assert isinstance(result['integrity_ok'], bool)
        assert isinstance(result['check_results'], list)
    
    def test_cleanup_cache(self, maintenance_service):
        """Test cache cleanup operation."""
        result = maintenance_service._cleanup_cache()
        
        assert isinstance(result, dict)
        assert 'cache_entries_before' in result
        assert 'cache_entries_after' in result
        assert 'entries_removed' in result
    
    def test_performance_baseline(self, maintenance_service):
        """Test performance baseline measurement."""
        baseline = maintenance_service._get_performance_baseline()
        
        assert isinstance(baseline, dict)
        assert 'db_response_time_ms' in baseline
        assert 'timestamp' in baseline
        assert baseline['db_response_time_ms'] >= 0
    
    def test_calculate_performance_impact(self, maintenance_service):
        """Test performance impact calculation."""
        before = {
            'db_response_time_ms': 100.0,
            'cache_performance': 0.8,
            'error_rate': 0.05
        }
        
        after = {
            'db_response_time_ms': 80.0,
            'cache_performance': 0.9,
            'error_rate': 0.03
        }
        
        impact = maintenance_service._calculate_performance_impact(before, after)
        
        assert isinstance(impact, dict)
        assert 'db_response_time_ms_change_percent' in impact
        assert impact['db_response_time_ms_change_percent'] < 0  # Should be negative (improvement)
    
    def test_generate_recommendations(self, maintenance_service):
        """Test recommendation generation."""
        details = {'space_reclaimed_percent': 15.0}
        impact = {'db_response_time_ms_change_percent': -20.0}
        
        recommendations = maintenance_service._generate_maintenance_recommendations(
            'db_vacuum', details, impact
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)
    
    def test_create_maintenance_schedule(self, maintenance_service):
        """Test creating maintenance schedule."""
        schedule = MaintenanceSchedule(
            schedule_id='test_schedule',
            name='Test Schedule',
            operations=['db_vacuum', 'cache_cleanup'],
            schedule_type='daily',
            schedule_config={},
            enabled=True,
            last_run=None,
            next_run=datetime.now() + timedelta(days=1),
            notification_settings={}
        )
        
        success = maintenance_service.create_maintenance_schedule(schedule)
        assert success is True
    
    def test_get_maintenance_history(self, maintenance_service):
        """Test getting maintenance history."""
        # Initially should be empty
        history = maintenance_service.get_maintenance_history(30)
        assert isinstance(history, list)
        # History might be empty for new database
    
    def test_scheduler_start_stop(self, maintenance_service):
        """Test scheduler start and stop."""
        # Start scheduler
        maintenance_service.start_scheduler()
        assert maintenance_service._scheduler_running is True
        assert maintenance_service._scheduler_thread is not None
        
        # Stop scheduler
        maintenance_service.stop_scheduler()
        assert maintenance_service._scheduler_running is False
```

### Integration Tests

Create `tests/services/test_configuration_service.py`:

```python
"""
Tests for Configuration Service

Sprint 3.1 Testing:
- Configuration management
- Alert rule creation
- User preferences
- Configuration history
"""

import pytest
import json
from datetime import datetime

from app.services.configuration_service import ConfigurationService, AlertRule


class TestConfigurationService:
    """Test cases for ConfigurationService."""
    
    @pytest.fixture
    def config_service(self, tmp_path):
        """Create configuration service with test database."""
        db_path = tmp_path / "test_config.db"
        return ConfigurationService(str(db_path))
    
    def test_get_configuration(self, config_service):
        """Test getting configuration values."""
        # Should have default configurations
        config = config_service.get_configuration('dashboard.refresh_interval')
        
        assert config is not None
        assert config.key == 'dashboard.refresh_interval'
        assert config.value == 30  # Default value
        assert config.config_type == 'integer'
        assert config.category == 'dashboard'
    
    def test_set_configuration(self, config_service):
        """Test setting configuration values."""
        # Set a new value
        success = config_service.set_configuration(
            'dashboard.refresh_interval', 
            60, 
            'test_user', 
            'Testing configuration update'
        )
        
        assert success is True
        
        # Verify the value was set
        config = config_service.get_configuration('dashboard.refresh_interval')
        assert config.value == 60
        assert config.updated_by == 'test_user'
    
    def test_get_configuration_by_category(self, config_service):
        """Test getting configuration by category."""
        dashboard_configs = config_service.get_configuration_by_category('dashboard')
        
        assert len(dashboard_configs) > 0
        assert all(config.category == 'dashboard' for config in dashboard_configs)
        
        # Check for expected dashboard configurations
        config_keys = [config.key for config in dashboard_configs]
        assert 'dashboard.refresh_interval' in config_keys
        assert 'dashboard.theme' in config_keys
    
    def test_get_all_categories(self, config_service):
        """Test getting all configuration categories."""
        categories = config_service.get_all_categories()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert 'dashboard' in categories
        assert 'performance' in categories
        assert 'alerts' in categories
    
    def test_parse_config_value(self, config_service):
        """Test configuration value parsing."""
        # Boolean values
        assert config_service._parse_config_value('true', 'boolean') is True
        assert config_service._parse_config_value('false', 'boolean') is False
        assert config_service._parse_config_value('1', 'boolean') is True
        assert config_service._parse_config_value('0', 'boolean') is False
        
        # Integer values
        assert config_service._parse_config_value('42', 'integer') == 42
        assert config_service._parse_config_value('-10', 'integer') == -10
        
        # Float values
        assert config_service._parse_config_value('3.14', 'float') == 3.14
        assert config_service._parse_config_value('-2.5', 'float') == -2.5
        
        # JSON values
        json_value = config_service._parse_config_value('{"key": "value"}', 'json')
        assert isinstance(json_value, dict)
        assert json_value['key'] == 'value'
        
        # String values
        assert config_service._parse_config_value('test', 'string') == 'test'
    
    def test_create_alert_rule(self, config_service):
        """Test creating alert rules."""
        rule = AlertRule(
            rule_id='test_rule',
            rule_name='Test Alert',
            metric_name='db_response_time_ms',
            condition_type='greater_than',
            threshold_value=1000.0,
            severity='warning',
            enabled=True,
            escalation_rules={},
            notification_channels=['email'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        success = config_service.create_alert_rule(rule)
        assert success is True
        
        # Verify the rule was created
        rules = config_service.get_alert_rules()
        assert len(rules) > 0
        
        created_rule = next((r for r in rules if r.rule_id == 'test_rule'), None)
        assert created_rule is not None
        assert created_rule.rule_name == 'Test Alert'
        assert created_rule.threshold_value == 1000.0
    
    def test_get_alert_rules(self, config_service):
        """Test getting alert rules."""
        # Create a test rule first
        rule = AlertRule(
            rule_id='test_rule_2',
            rule_name='Another Test Alert',
            metric_name='error_rate',
            condition_type='greater_than',
            threshold_value=0.1,
            severity='error',
            enabled=True,
            escalation_rules={},
            notification_channels=['dashboard'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        config_service.create_alert_rule(rule)
        
        # Get all rules
        rules = config_service.get_alert_rules()
        
        assert isinstance(rules, list)
        assert len(rules) > 0
        
        # Check rule structure
        for rule in rules:
            assert hasattr(rule, 'rule_id')
            assert hasattr(rule, 'rule_name')
            assert hasattr(rule, 'metric_name')
            assert hasattr(rule, 'threshold_value')
            assert hasattr(rule, 'severity')
    
    def test_delete_alert_rule(self, config_service):
        """Test deleting alert rules."""
        # Create a rule to delete
        rule = AlertRule(
            rule_id='delete_test_rule',
            rule_name='Rule to Delete',
            metric_name='memory_usage',
            condition_type='greater_than',
            threshold_value=90.0,
            severity='critical',
            enabled=True,
            escalation_rules={},
            notification_channels=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        config_service.create_alert_rule(rule)
        
        # Verify it exists
        rules_before = config_service.get_alert_rules()
        rule_exists = any(r.rule_id == 'delete_test_rule' for r in rules_before)
        assert rule_exists is True
        
        # Delete the rule
        success = config_service.delete_alert_rule('delete_test_rule')
        assert success is True
        
        # Verify it's gone
        rules_after = config_service.get_alert_rules()
        rule_exists = any(r.rule_id == 'delete_test_rule' for r in rules_after)
        assert rule_exists is False
    
    def test_user_preferences(self, config_service):
        """Test user preference management."""
        user_id = 'test_user'
        
        # Set preferences
        success1 = config_service.set_user_preference(user_id, 'theme', 'dark')
        success2 = config_service.set_user_preference(user_id, 'notifications', True)
        success3 = config_service.set_user_preference(user_id, 'dashboard_layout', {'columns': 2})
        
        assert success1 is True
        assert success2 is True
        assert success3 is True
        
        # Get preferences
        preferences = config_service.get_user_preferences(user_id)
        
        assert isinstance(preferences, dict)
        assert preferences['theme'] == 'dark'
        assert preferences['notifications'] is True
        assert preferences['dashboard_layout']['columns'] == 2
    
    def test_configuration_history(self, config_service):
        """Test configuration change history."""
        # Make some configuration changes
        config_service.set_configuration('test.setting1', 'value1', 'user1', 'Initial setup')
        config_service.set_configuration('test.setting1', 'value2', 'user2', 'Updated value')
        config_service.set_configuration('test.setting2', 'another_value', 'user1', 'New setting')
        
        # Get history for specific key
        history = config_service.get_configuration_history('test.setting1', 30)
        
        assert isinstance(history, list)
        assert len(history) >= 2  # Should have at least 2 changes
        
        # Check history structure
        for change in history:
            assert 'config_key' in change
            assert 'old_value' in change
            assert 'new_value' in change
            assert 'changed_by' in change
            assert 'changed_at' in change
        
        # Get all history
        all_history = config_service.get_configuration_history(None, 30)
        assert len(all_history) >= 3  # Should have at least 3 changes
```

## SUCCESS CRITERIA

### Functional Requirements
- [ ] **Maintenance Service**: 9+ automated maintenance operations with progress tracking
- [ ] **One-Click Maintenance**: Quick maintenance buttons for common operations
- [ ] **Maintenance Scheduling**: Automated scheduling with daily/weekly/monthly options
- [ ] **System Configuration**: Comprehensive configuration management with categories
- [ ] **Alert Management**: Advanced alert rules with escalation and notifications
- [ ] **Performance Optimization**: Automated performance tuning and recommendations

### Technical Requirements
- [ ] **Operation Reliability**: All maintenance operations execute successfully with proper error handling
- [ ] **Performance Impact**: Accurate measurement and reporting of performance improvements
- [ ] **Configuration Persistence**: Reliable storage and retrieval of configuration changes
- [ ] **Scheduler Accuracy**: Precise scheduling and execution of automated maintenance
- [ ] **Data Integrity**: Safe maintenance operations that preserve data integrity

### User Experience Requirements
- [ ] **Intuitive Interface**: Easy-to-use maintenance and configuration panels
- [ ] **Progress Feedback**: Real-time progress tracking for maintenance operations
- [ ] **Clear Results**: Comprehensive reporting of maintenance results and recommendations
- [ ] **Configuration Management**: User-friendly configuration editing with validation
- [ ] **Alert Configuration**: Simple alert rule creation and management

### Testing Requirements
- [ ] **Unit Test Coverage**: ≥85% coverage for maintenance and configuration services
- [ ] **Integration Tests**: Complete testing of maintenance workflows and configuration management
- [ ] **Performance Tests**: Validation of maintenance operation performance impact
- [ ] **Scheduler Tests**: Testing of automated scheduling functionality
- [ ] **Error Handling Tests**: Comprehensive error handling and recovery testing

## DEVELOPMENT WORKFLOW

### Phase 1: Maintenance Service (Days 1-3)
1. **Create Maintenance Service**
   - Implement 9 maintenance operations
   - Add performance impact measurement
   - Build recommendation engine
   - Add scheduling framework

2. **Testing & Validation**
   - Unit tests for all operations
   - Performance impact validation
   - Scheduler testing

### Phase 2: Configuration Service (Days 4-5)
1. **Create Configuration Service**
   - System configuration management
   - Alert rule management
   - User preferences
   - Configuration history

2. **Integration Testing**
   - Configuration persistence testing
   - Alert rule functionality
   - User preference management

### Phase 3: UI Integration (Days 6-7)
1. **Maintenance Panel**
   - One-click maintenance interface
   - Progress tracking and results
   - Maintenance scheduling UI
   - History display

2. **Configuration Panel**
   - Configuration editing interface
   - Alert rule management
   - User preference settings

## VALIDATION STEPS

### Pre-Development Validation
- [ ] Review maintenance operation requirements and safety
- [ ] Confirm configuration management specifications
- [ ] Validate alert management requirements
- [ ] Ensure scheduler framework design

### Development Validation
- [ ] **Maintenance Validation**: Test all maintenance operations in safe environment
- [ ] **Configuration Validation**: Verify configuration changes take effect properly
- [ ] **Alert Validation**: Test alert rule creation and triggering
- [ ] **Integration Testing**: Ensure seamless integration with existing dashboard

### Post-Development Validation
- [ ] **User Testing**: Healthcare administrators test maintenance and configuration features
- [ ] **Performance Testing**: Verify maintenance operations improve system performance
- [ ] **Safety Testing**: Ensure maintenance operations don't cause data loss or corruption
- [ ] **Documentation Review**: Ensure comprehensive documentation for all features

## IMPORTANT NOTES

### Safety Considerations
- **Data Backup**: Ensure critical operations have backup/rollback capabilities
- **Operation Safety**: Validate that maintenance operations are safe for production
- [ ] **Downtime Prevention**: Minimize or eliminate downtime during maintenance
- [ ] **Error Recovery**: Provide clear error messages and recovery procedures

### Performance Considerations
- [ ] **Maintenance Timing**: Schedule intensive operations during low-usage periods
- [ ] **Resource Usage**: Monitor resource consumption during maintenance operations
- [ ] **Concurrent Operations**: Handle multiple simultaneous maintenance requests safely
- [ ] **Progress Tracking**: Provide accurate progress feedback for long-running operations

### Security Considerations
- [ ] **Configuration Access**: Secure access to system configuration changes
- [ ] **Audit Trail**: Maintain complete audit trail of configuration changes
- [ ] **User Permissions**: Implement appropriate permissions for maintenance operations
- [ ] **Alert Security**: Secure alert notification channels and escalation

### Future Enhancements
- [ ] **Advanced Scheduling**: Add cron-like scheduling with complex patterns
- [ ] **Maintenance Automation**: AI-driven maintenance recommendations
- [ ] **Configuration Validation**: Advanced validation and dependency checking
- [ ] **Remote Maintenance**: Support for remote maintenance execution