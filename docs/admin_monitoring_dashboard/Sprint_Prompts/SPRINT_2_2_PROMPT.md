# SPRINT 2.2 PROMPT - Learning System Analytics

## PROJECT CONTEXT

You are working on the **Admin Monitoring Dashboard Project** - creating a web-based monitoring interface for the AAA (Ask Anything AI Assistant) Learning System. This is Sprint 2.2 of an 8-sprint project across 3 phases.

### Project Overview
The AAA is a healthcare data analysis assistant with a recently deployed Learning Enhancement system. We're building a modern, visual dashboard that allows non-technical healthcare administrators to monitor system health, performance, and learning metrics through a web interface.

### Current System Status (After Sprint 2.1)
The AAA now has:
- **Complete Phase 1**: Basic dashboard with health status, interactive features, and user testing
- **Historical Trends**: Time-series charts showing system performance over time
- **MetricsCollector**: Automated background data collection
- **TimeSeriesChart**: Interactive Bokeh visualizations with time period selectors
- **Data Retention**: Automated cleanup and performance optimization

### Sprint 2.2 Focus
This sprint focuses on **Learning System Analytics** - providing deep insights into the effectiveness of the learning system, pattern performance, and correction success rates.

## SPRINT 2.2 OBJECTIVES

**Goal**: Implement comprehensive learning system analytics with pattern effectiveness tracking, correction success analysis, and learning progress visualization.

**Key Deliverables**:
1. Learning Analytics Service for pattern effectiveness tracking
2. Pattern Performance Charts showing success rates and trends
3. Correction Success Analysis with detailed metrics
4. User Feedback Analytics and sentiment tracking
5. Learning Progress Indicators and milestone tracking
6. Advanced Learning Metrics Dashboard panel

**User Impact**: Healthcare administrators can understand how well the AI is learning from corrections and improving over time.

## TECHNICAL REQUIREMENTS

### Learning Analytics Service

Create `app/services/learning_analytics.py`:

```python
"""
Learning Analytics Service for AAA Admin Monitoring

This service provides comprehensive analytics for the learning system,
tracking pattern effectiveness, correction success rates, and learning progress.

Sprint 2.2 Features:
- Pattern effectiveness analysis
- Correction success tracking
- User feedback analytics
- Learning progress metrics
- Pattern lifecycle management
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

from app.utils.saved_questions_db import DB_FILE
from app.utils.learning_metrics import LearningSystemMonitor
from app.services.correction_service import CorrectionService

logger = logging.getLogger(__name__)


@dataclass
class PatternEffectiveness:
    """Pattern effectiveness metrics."""
    pattern_id: str
    pattern_type: str
    success_rate: float
    total_applications: int
    successful_applications: int
    failed_applications: int
    avg_confidence: float
    last_used: str
    trend: str  # "improving", "declining", "stable"


@dataclass
class CorrectionAnalysis:
    """Correction success analysis."""
    total_corrections: int
    successful_corrections: int
    success_rate: float
    avg_time_to_success: float
    common_correction_types: List[Dict[str, Any]]
    correction_trends: Dict[str, float]


@dataclass
class LearningProgress:
    """Learning progress metrics."""
    overall_learning_rate: float
    patterns_learned: int
    patterns_improved: int
    patterns_deprecated: int
    learning_velocity: float  # patterns per day
    confidence_improvement: float
    milestone_progress: Dict[str, Any]


class LearningAnalyticsService:
    """Service for learning system analytics."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the learning analytics service.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.monitor = LearningSystemMonitor(db_path)
        self.correction_service = CorrectionService(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_pattern_effectiveness(self, days: int = 30) -> List[PatternEffectiveness]:
        """Get pattern effectiveness metrics for the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of pattern effectiveness metrics
        """
        try:
            with self._get_connection() as conn:
                # Get pattern usage and success data
                query = """
                SELECT 
                    p.pattern_id,
                    p.pattern_type,
                    p.confidence_score,
                    p.created_at,
                    COUNT(pa.id) as total_applications,
                    SUM(CASE WHEN pa.success = 1 THEN 1 ELSE 0 END) as successful_applications,
                    AVG(pa.confidence_score) as avg_confidence,
                    MAX(pa.applied_at) as last_used
                FROM learned_patterns p
                LEFT JOIN pattern_applications pa ON p.pattern_id = pa.pattern_id
                WHERE p.created_at >= datetime('now', '-{} days')
                GROUP BY p.pattern_id, p.pattern_type, p.confidence_score, p.created_at
                ORDER BY total_applications DESC
                """.format(days)
                
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                
                effectiveness_list = []
                for row in rows:
                    total_apps = row['total_applications'] or 0
                    successful_apps = row['successful_applications'] or 0
                    success_rate = (successful_apps / total_apps) if total_apps > 0 else 0.0
                    
                    # Calculate trend
                    trend = self._calculate_pattern_trend(conn, row['pattern_id'], days)
                    
                    effectiveness = PatternEffectiveness(
                        pattern_id=row['pattern_id'],
                        pattern_type=row['pattern_type'],
                        success_rate=success_rate,
                        total_applications=total_apps,
                        successful_applications=successful_apps,
                        failed_applications=total_apps - successful_apps,
                        avg_confidence=row['avg_confidence'] or 0.0,
                        last_used=row['last_used'] or 'Never',
                        trend=trend
                    )
                    effectiveness_list.append(effectiveness)
                
                return effectiveness_list
                
        except Exception as e:
            logger.error(f"Error getting pattern effectiveness: {e}")
            return []
    
    def _calculate_pattern_trend(self, conn: sqlite3.Connection, pattern_id: str, days: int) -> str:
        """Calculate trend for a specific pattern."""
        try:
            # Get success rates for first and second half of the period
            half_days = days // 2
            
            query_recent = """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM pattern_applications 
            WHERE pattern_id = ? AND applied_at >= datetime('now', '-{} days')
            """.format(half_days)
            
            query_older = """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM pattern_applications 
            WHERE pattern_id = ? 
            AND applied_at >= datetime('now', '-{} days')
            AND applied_at < datetime('now', '-{} days')
            """.format(days, half_days)
            
            recent_rate = conn.execute(query_recent, (pattern_id,)).fetchone()['success_rate'] or 0
            older_rate = conn.execute(query_older, (pattern_id,)).fetchone()['success_rate'] or 0
            
            if recent_rate > older_rate + 0.1:
                return "improving"
            elif recent_rate < older_rate - 0.1:
                return "declining"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"Error calculating pattern trend: {e}")
            return "unknown"
    
    def get_correction_analysis(self, days: int = 30) -> CorrectionAnalysis:
        """Get correction success analysis for the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Correction analysis metrics
        """
        try:
            with self._get_connection() as conn:
                # Get correction statistics
                query = """
                SELECT 
                    COUNT(*) as total_corrections,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_corrections,
                    AVG(CASE WHEN status = 'completed' 
                        THEN (julianday(updated_at) - julianday(created_at)) * 24 * 60 
                        ELSE NULL END) as avg_time_to_success_minutes,
                    correction_type,
                    COUNT(*) as type_count
                FROM user_corrections 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY correction_type
                ORDER BY type_count DESC
                """.format(days)
                
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                
                if not rows:
                    return CorrectionAnalysis(
                        total_corrections=0,
                        successful_corrections=0,
                        success_rate=0.0,
                        avg_time_to_success=0.0,
                        common_correction_types=[],
                        correction_trends={}
                    )
                
                # Aggregate totals
                total_corrections = sum(row['total_corrections'] for row in rows)
                successful_corrections = sum(row['successful_corrections'] for row in rows)
                success_rate = (successful_corrections / total_corrections) if total_corrections > 0 else 0.0
                
                # Get average time to success
                avg_time_query = """
                SELECT AVG(CASE WHEN status = 'completed' 
                    THEN (julianday(updated_at) - julianday(created_at)) * 24 * 60 
                    ELSE NULL END) as avg_time_minutes
                FROM user_corrections 
                WHERE created_at >= datetime('now', '-{} days')
                AND status = 'completed'
                """.format(days)
                
                avg_time_result = conn.execute(avg_time_query).fetchone()
                avg_time_to_success = avg_time_result['avg_time_minutes'] or 0.0
                
                # Build common correction types
                common_types = [
                    {
                        'type': row['correction_type'],
                        'count': row['type_count'],
                        'percentage': (row['type_count'] / total_corrections) * 100 if total_corrections > 0 else 0
                    }
                    for row in rows[:5]  # Top 5 types
                ]
                
                # Get correction trends (weekly comparison)
                trends = self._get_correction_trends(conn, days)
                
                return CorrectionAnalysis(
                    total_corrections=total_corrections,
                    successful_corrections=successful_corrections,
                    success_rate=success_rate,
                    avg_time_to_success=avg_time_to_success,
                    common_correction_types=common_types,
                    correction_trends=trends
                )
                
        except Exception as e:
            logger.error(f"Error getting correction analysis: {e}")
            return CorrectionAnalysis(
                total_corrections=0,
                successful_corrections=0,
                success_rate=0.0,
                avg_time_to_success=0.0,
                common_correction_types=[],
                correction_trends={}
            )
    
    def _get_correction_trends(self, conn: sqlite3.Connection, days: int) -> Dict[str, float]:
        """Get correction trends over time."""
        try:
            # Compare current week vs previous week
            current_week_query = """
            SELECT COUNT(*) as count
            FROM user_corrections 
            WHERE created_at >= datetime('now', '-7 days')
            """
            
            previous_week_query = """
            SELECT COUNT(*) as count
            FROM user_corrections 
            WHERE created_at >= datetime('now', '-14 days')
            AND created_at < datetime('now', '-7 days')
            """
            
            current_count = conn.execute(current_week_query).fetchone()['count']
            previous_count = conn.execute(previous_week_query).fetchone()['count']
            
            if previous_count > 0:
                weekly_change = ((current_count - previous_count) / previous_count) * 100
            else:
                weekly_change = 0.0
            
            return {
                'weekly_change_percent': weekly_change,
                'current_week_count': current_count,
                'previous_week_count': previous_count
            }
            
        except Exception as e:
            logger.error(f"Error getting correction trends: {e}")
            return {}
    
    def get_learning_progress(self, days: int = 30) -> LearningProgress:
        """Get overall learning progress metrics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Learning progress metrics
        """
        try:
            with self._get_connection() as conn:
                # Get pattern statistics
                pattern_stats_query = """
                SELECT 
                    COUNT(*) as total_patterns,
                    SUM(CASE WHEN created_at >= datetime('now', '-{} days') THEN 1 ELSE 0 END) as new_patterns,
                    AVG(confidence_score) as avg_confidence
                FROM learned_patterns
                """.format(days)
                
                pattern_stats = conn.execute(pattern_stats_query).fetchone()
                
                # Get improved patterns (those with increasing success rates)
                improved_patterns = self._count_improved_patterns(conn, days)
                
                # Get deprecated patterns
                deprecated_query = """
                SELECT COUNT(*) as count
                FROM learned_patterns 
                WHERE status = 'deprecated' 
                AND updated_at >= datetime('now', '-{} days')
                """.format(days)
                
                deprecated_count = conn.execute(deprecated_query).fetchone()['count']
                
                # Calculate learning velocity (patterns per day)
                learning_velocity = pattern_stats['new_patterns'] / days if days > 0 else 0
                
                # Get confidence improvement
                confidence_improvement = self._calculate_confidence_improvement(conn, days)
                
                # Get milestone progress
                milestones = self._get_milestone_progress(conn)
                
                return LearningProgress(
                    overall_learning_rate=self._calculate_learning_rate(conn, days),
                    patterns_learned=pattern_stats['new_patterns'],
                    patterns_improved=improved_patterns,
                    patterns_deprecated=deprecated_count,
                    learning_velocity=learning_velocity,
                    confidence_improvement=confidence_improvement,
                    milestone_progress=milestones
                )
                
        except Exception as e:
            logger.error(f"Error getting learning progress: {e}")
            return LearningProgress(
                overall_learning_rate=0.0,
                patterns_learned=0,
                patterns_improved=0,
                patterns_deprecated=0,
                learning_velocity=0.0,
                confidence_improvement=0.0,
                milestone_progress={}
            )
    
    def _count_improved_patterns(self, conn: sqlite3.Connection, days: int) -> int:
        """Count patterns that have improved in the specified period."""
        try:
            # This is a simplified version - in practice, you'd track pattern performance over time
            query = """
            SELECT COUNT(DISTINCT pattern_id) as count
            FROM pattern_applications 
            WHERE applied_at >= datetime('now', '-{} days')
            AND success = 1
            """.format(days)
            
            result = conn.execute(query).fetchone()
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Error counting improved patterns: {e}")
            return 0
    
    def _calculate_confidence_improvement(self, conn: sqlite3.Connection, days: int) -> float:
        """Calculate average confidence improvement over the period."""
        try:
            # Compare average confidence of recent patterns vs older patterns
            recent_query = """
            SELECT AVG(confidence_score) as avg_confidence
            FROM learned_patterns 
            WHERE created_at >= datetime('now', '-{} days')
            """.format(days // 2)
            
            older_query = """
            SELECT AVG(confidence_score) as avg_confidence
            FROM learned_patterns 
            WHERE created_at >= datetime('now', '-{} days')
            AND created_at < datetime('now', '-{} days')
            """.format(days, days // 2)
            
            recent_confidence = conn.execute(recent_query).fetchone()['avg_confidence'] or 0
            older_confidence = conn.execute(older_query).fetchone()['avg_confidence'] or 0
            
            return recent_confidence - older_confidence
            
        except Exception as e:
            logger.error(f"Error calculating confidence improvement: {e}")
            return 0.0
    
    def _calculate_learning_rate(self, conn: sqlite3.Connection, days: int) -> float:
        """Calculate overall learning rate based on successful pattern applications."""
        try:
            query = """
            SELECT 
                COUNT(*) as total_applications,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_applications
            FROM pattern_applications 
            WHERE applied_at >= datetime('now', '-{} days')
            """.format(days)
            
            result = conn.execute(query).fetchone()
            total = result['total_applications'] or 0
            successful = result['successful_applications'] or 0
            
            return (successful / total) if total > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating learning rate: {e}")
            return 0.0
    
    def _get_milestone_progress(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get progress towards learning milestones."""
        try:
            # Define milestones and check progress
            milestones = {
                'patterns_milestone_100': {
                    'target': 100,
                    'current': 0,
                    'description': '100 learned patterns'
                },
                'success_rate_milestone_90': {
                    'target': 0.90,
                    'current': 0.0,
                    'description': '90% pattern success rate'
                },
                'corrections_milestone_50': {
                    'target': 50,
                    'current': 0,
                    'description': '50 successful corrections'
                }
            }
            
            # Get current pattern count
            pattern_count = conn.execute("SELECT COUNT(*) as count FROM learned_patterns").fetchone()['count']
            milestones['patterns_milestone_100']['current'] = pattern_count
            
            # Get current success rate
            success_rate_query = """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as rate
            FROM pattern_applications 
            WHERE applied_at >= datetime('now', '-30 days')
            """
            success_rate = conn.execute(success_rate_query).fetchone()['rate'] or 0.0
            milestones['success_rate_milestone_90']['current'] = success_rate
            
            # Get successful corrections count
            corrections_count = conn.execute(
                "SELECT COUNT(*) as count FROM user_corrections WHERE status = 'completed'"
            ).fetchone()['count']
            milestones['corrections_milestone_50']['current'] = corrections_count
            
            return milestones
            
        except Exception as e:
            logger.error(f"Error getting milestone progress: {e}")
            return {}
    
    def get_user_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get user feedback analytics and sentiment analysis.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            User feedback analytics
        """
        try:
            with self._get_connection() as conn:
                # Get feedback statistics
                feedback_query = """
                SELECT 
                    feedback_type,
                    rating,
                    COUNT(*) as count,
                    AVG(rating) as avg_rating
                FROM user_feedback 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY feedback_type, rating
                ORDER BY feedback_type, rating
                """.format(days)
                
                cursor = conn.execute(feedback_query)
                feedback_data = cursor.fetchall()
                
                # Process feedback data
                feedback_summary = defaultdict(lambda: {'total': 0, 'avg_rating': 0.0, 'ratings': {}})
                
                for row in feedback_data:
                    feedback_type = row['feedback_type']
                    rating = row['rating']
                    count = row['count']
                    
                    feedback_summary[feedback_type]['total'] += count
                    feedback_summary[feedback_type]['ratings'][rating] = count
                    feedback_summary[feedback_type]['avg_rating'] = row['avg_rating']
                
                return dict(feedback_summary)
                
        except Exception as e:
            logger.error(f"Error getting user feedback analytics: {e}")
            return {}
```

### Learning Charts Component

Create `app/components/admin_dashboard/learning_charts.py`:

```python
"""
Learning Charts Component for Admin Dashboard

Provides interactive charts and visualizations for learning system analytics.

Sprint 2.2 Features:
- Pattern effectiveness charts
- Correction success trend charts
- Learning progress indicators
- User feedback visualization
"""

import panel as pn
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource
from bokeh.palettes import Category10
from typing import Dict, List, Any, Optional
import logging

from app.services.learning_analytics import LearningAnalyticsService, PatternEffectiveness, CorrectionAnalysis, LearningProgress

logger = logging.getLogger(__name__)

pn.extension('bokeh')


class LearningChartsPanel:
    """Panel for learning system analytics charts."""
    
    def __init__(self, analytics_service: Optional[LearningAnalyticsService] = None):
        """Initialize the learning charts panel.
        
        Args:
            analytics_service: Optional analytics service (for testing)
        """
        self.analytics_service = analytics_service or LearningAnalyticsService()
        self.time_period = pn.Param(default=30, bounds=(7, 90))
        
        # Create UI components
        self._create_components()
    
    def _create_components(self):
        """Create all UI components."""
        # Time period selector
        self.time_selector = pn.widgets.IntSlider(
            name="Analysis Period (days)",
            value=30,
            start=7,
            end=90,
            step=7,
            width=300
        )
        
        # Chart containers
        self.pattern_effectiveness_chart = pn.pane.Bokeh(
            self._create_pattern_effectiveness_chart(),
            width=600,
            height=400
        )
        
        self.correction_trends_chart = pn.pane.Bokeh(
            self._create_correction_trends_chart(),
            width=600,
            height=400
        )
        
        self.learning_progress_chart = pn.pane.Bokeh(
            self._create_learning_progress_chart(),
            width=600,
            height=400
        )
        
        # Metrics cards
        self.metrics_cards = self._create_metrics_cards()
        
        # Bind update function to time selector
        self.time_selector.param.watch(self._update_charts, 'value')
    
    def _create_pattern_effectiveness_chart(self):
        """Create pattern effectiveness chart."""
        try:
            # Get pattern effectiveness data
            patterns = self.analytics_service.get_pattern_effectiveness(self.time_selector.value)
            
            if not patterns:
                # Create empty chart
                p = figure(
                    title="Pattern Effectiveness",
                    x_axis_label="Pattern ID",
                    y_axis_label="Success Rate",
                    width=580,
                    height=380
                )
                p.text([0.5], [0.5], text=["No pattern data available"], 
                       text_align="center", text_baseline="middle")
                return p
            
            # Prepare data
            pattern_ids = [p.pattern_id[:10] + "..." if len(p.pattern_id) > 10 else p.pattern_id for p in patterns]
            success_rates = [p.success_rate for p in patterns]
            total_apps = [p.total_applications for p in patterns]
            pattern_types = [p.pattern_type for p in patterns]
            trends = [p.trend for p in patterns]
            
            # Create chart
            p = figure(
                x_range=pattern_ids,
                title="Pattern Effectiveness by Success Rate",
                x_axis_label="Pattern ID",
                y_axis_label="Success Rate",
                width=580,
                height=380
            )
            
            # Color by trend
            colors = []
            for trend in trends:
                if trend == "improving":
                    colors.append("green")
                elif trend == "declining":
                    colors.append("red")
                else:
                    colors.append("blue")
            
            # Create bars
            source = ColumnDataSource(data=dict(
                pattern_ids=pattern_ids,
                success_rates=success_rates,
                total_apps=total_apps,
                pattern_types=pattern_types,
                trends=trends,
                colors=colors
            ))
            
            bars = p.vbar(
                x='pattern_ids',
                top='success_rates',
                width=0.8,
                color='colors',
                source=source
            )
            
            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Pattern ID", "@pattern_ids"),
                    ("Success Rate", "@success_rates{0.0%}"),
                    ("Total Applications", "@total_apps"),
                    ("Pattern Type", "@pattern_types"),
                    ("Trend", "@trends")
                ],
                renderers=[bars]
            )
            p.add_tools(hover)
            
            # Styling
            p.xgrid.grid_line_color = None
            p.xaxis.major_label_orientation = 45
            
            return p
            
        except Exception as e:
            logger.error(f"Error creating pattern effectiveness chart: {e}")
            # Return empty chart on error
            p = figure(title="Pattern Effectiveness", width=580, height=380)
            p.text([0.5], [0.5], text=[f"Error: {str(e)}"], 
                   text_align="center", text_baseline="middle")
            return p
    
    def _create_correction_trends_chart(self):
        """Create correction trends chart."""
        try:
            # Get correction analysis data
            analysis = self.analytics_service.get_correction_analysis(self.time_selector.value)
            
            # Create chart showing correction types
            if not analysis.common_correction_types:
                p = figure(title="Correction Types Distribution", width=580, height=380)
                p.text([0.5], [0.5], text=["No correction data available"], 
                       text_align="center", text_baseline="middle")
                return p
            
            # Prepare data for pie chart (using wedges)
            types = [ct['type'] for ct in analysis.common_correction_types]
            counts = [ct['count'] for ct in analysis.common_correction_types]
            percentages = [ct['percentage'] for ct in analysis.common_correction_types]
            
            # Create horizontal bar chart instead of pie chart for better readability
            p = figure(
                y_range=types,
                title="Most Common Correction Types",
                x_axis_label="Number of Corrections",
                y_axis_label="Correction Type",
                width=580,
                height=380
            )
            
            source = ColumnDataSource(data=dict(
                types=types,
                counts=counts,
                percentages=percentages
            ))
            
            bars = p.hbar(
                y='types',
                right='counts',
                height=0.8,
                color=Category10[len(types)] if len(types) <= 10 else Category10[10],
                source=source
            )
            
            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Correction Type", "@types"),
                    ("Count", "@counts"),
                    ("Percentage", "@percentages{0.0}%")
                ],
                renderers=[bars]
            )
            p.add_tools(hover)
            
            return p
            
        except Exception as e:
            logger.error(f"Error creating correction trends chart: {e}")
            p = figure(title="Correction Trends", width=580, height=380)
            p.text([0.5], [0.5], text=[f"Error: {str(e)}"], 
                   text_align="center", text_baseline="middle")
            return p
    
    def _create_learning_progress_chart(self):
        """Create learning progress chart."""
        try:
            # Get learning progress data
            progress = self.analytics_service.get_learning_progress(self.time_selector.value)
            
            # Create milestone progress chart
            milestones = progress.milestone_progress
            
            if not milestones:
                p = figure(title="Learning Progress Milestones", width=580, height=380)
                p.text([0.5], [0.5], text=["No milestone data available"], 
                       text_align="center", text_baseline="middle")
                return p
            
            # Prepare data
            milestone_names = []
            current_values = []
            target_values = []
            progress_percentages = []
            
            for milestone_id, milestone_data in milestones.items():
                milestone_names.append(milestone_data['description'])
                current_values.append(milestone_data['current'])
                target_values.append(milestone_data['target'])
                
                # Calculate progress percentage
                if milestone_data['target'] > 0:
                    progress_pct = min(100, (milestone_data['current'] / milestone_data['target']) * 100)
                else:
                    progress_pct = 0
                progress_percentages.append(progress_pct)
            
            # Create horizontal progress bars
            p = figure(
                y_range=milestone_names,
                title="Learning Progress Milestones",
                x_axis_label="Progress (%)",
                y_axis_label="Milestone",
                width=580,
                height=380
            )
            
            source = ColumnDataSource(data=dict(
                milestone_names=milestone_names,
                current_values=current_values,
                target_values=target_values,
                progress_percentages=progress_percentages
            ))
            
            # Background bars (targets)
            p.hbar(
                y='milestone_names',
                right=100,  # Full width
                height=0.6,
                color='lightgray',
                alpha=0.3,
                source=source
            )
            
            # Progress bars
            bars = p.hbar(
                y='milestone_names',
                right='progress_percentages',
                height=0.6,
                color='green',
                source=source
            )
            
            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Milestone", "@milestone_names"),
                    ("Current", "@current_values"),
                    ("Target", "@target_values"),
                    ("Progress", "@progress_percentages{0.0}%")
                ],
                renderers=[bars]
            )
            p.add_tools(hover)
            
            # Set x-axis range
            p.x_range.start = 0
            p.x_range.end = 100
            
            return p
            
        except Exception as e:
            logger.error(f"Error creating learning progress chart: {e}")
            p = figure(title="Learning Progress", width=580, height=380)
            p.text([0.5], [0.5], text=[f"Error: {str(e)}"], 
                   text_align="center", text_baseline="middle")
            return p
    
    def _create_metrics_cards(self):
        """Create metrics summary cards."""
        try:
            # Get current metrics
            progress = self.analytics_service.get_learning_progress(self.time_selector.value)
            analysis = self.analytics_service.get_correction_analysis(self.time_selector.value)
            
            # Create cards
            cards = pn.Row(
                pn.pane.HTML(f"""
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #2e7d32;">Learning Rate</h3>
                    <h2 style="margin: 5px 0; color: #1b5e20;">{progress.overall_learning_rate:.1%}</h2>
                    <p style="margin: 0; color: #388e3c;">Overall Success Rate</p>
                </div>
                """, width=180, height=120),
                
                pn.pane.HTML(f"""
                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #1976d2;">New Patterns</h3>
                    <h2 style="margin: 5px 0; color: #0d47a1;">{progress.patterns_learned}</h2>
                    <p style="margin: 0; color: #1565c0;">Last {self.time_selector.value} days</p>
                </div>
                """, width=180, height=120),
                
                pn.pane.HTML(f"""
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #f57c00;">Corrections</h3>
                    <h2 style="margin: 5px 0; color: #e65100;">{analysis.successful_corrections}</h2>
                    <p style="margin: 0; color: #ff9800;">Successful</p>
                </div>
                """, width=180, height=120),
                
                pn.pane.HTML(f"""
                <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #7b1fa2;">Learning Velocity</h3>
                    <h2 style="margin: 5px 0; color: #4a148c;">{progress.learning_velocity:.1f}</h2>
                    <p style="margin: 0; color: #8e24aa;">Patterns/day</p>
                </div>
                """, width=180, height=120)
            )
            
            return cards
            
        except Exception as e:
            logger.error(f"Error creating metrics cards: {e}")
            return pn.pane.HTML("<p>Error loading metrics</p>")
    
    def _update_charts(self, event):
        """Update all charts when time period changes."""
        try:
            # Update charts
            self.pattern_effectiveness_chart.object = self._create_pattern_effectiveness_chart()
            self.correction_trends_chart.object = self._create_correction_trends_chart()
            self.learning_progress_chart.object = self._create_learning_progress_chart()
            
            # Update metrics cards
            self.metrics_cards[:] = [self._create_metrics_cards()]
            
        except Exception as e:
            logger.error(f"Error updating charts: {e}")
    
    def get_panel(self):
        """Get the complete learning charts panel."""
        return pn.Column(
            pn.pane.HTML("<h2>🧠 Learning System Analytics</h2>"),
            self.time_selector,
            self.metrics_cards,
            pn.Row(
                self.pattern_effectiveness_chart,
                self.correction_trends_chart
            ),
            self.learning_progress_chart,
            width=1200
        )
```

### Integration with Admin Dashboard

Update `app/components/admin_dashboard/admin_dashboard_tab.py` to include learning analytics:

```python
# Add to imports
from app.components.admin_dashboard.learning_charts import LearningChartsPanel

# Add to AdminDashboardTab.__init__()
self.learning_charts = LearningChartsPanel()

# Add to the main layout in get_panel()
learning_section = pn.Column(
    pn.pane.HTML("<h2>📊 Learning Analytics</h2>"),
    self.learning_charts.get_panel(),
    margin=(10, 0)
)

# Include in the main tabs or accordion
main_content = pn.Tabs(
    ("Health Overview", health_section),
    ("Performance Metrics", performance_section),
    ("Learning Analytics", learning_section),  # New tab
    ("Historical Trends", trends_section)
)
```

## TESTING REQUIREMENTS

### Unit Tests

Create `tests/services/test_learning_analytics.py`:

```python
"""
Tests for Learning Analytics Service

Sprint 2.2 Testing:
- Pattern effectiveness calculation
- Correction analysis accuracy
- Learning progress metrics
- User feedback analytics
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.learning_analytics import (
    LearningAnalyticsService,
    PatternEffectiveness,
    CorrectionAnalysis,
    LearningProgress
)


class TestLearningAnalyticsService:
    """Test cases for LearningAnalyticsService."""
    
    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create a temporary test database."""
        db_path = tmp_path / "test_learning_analytics.db"
        
        # Create test database with sample data
        conn = sqlite3.connect(str(db_path))
        
        # Create tables
        conn.execute("""
        CREATE TABLE learned_patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_type TEXT,
            confidence_score REAL,
            status TEXT DEFAULT 'active',
            created_at DATETIME,
            updated_at DATETIME
        )
        """)
        
        conn.execute("""
        CREATE TABLE pattern_applications (
            id INTEGER PRIMARY KEY,
            pattern_id TEXT,
            success BOOLEAN,
            confidence_score REAL,
            applied_at DATETIME
        )
        """)
        
        conn.execute("""
        CREATE TABLE user_corrections (
            id INTEGER PRIMARY KEY,
            correction_type TEXT,
            status TEXT,
            created_at DATETIME,
            updated_at DATETIME
        )
        """)
        
        conn.execute("""
        CREATE TABLE user_feedback (
            id INTEGER PRIMARY KEY,
            feedback_type TEXT,
            rating INTEGER,
            created_at DATETIME
        )
        """)
        
        # Insert sample data
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Sample patterns
        patterns = [
            ('pattern_1', 'query_optimization', 0.85, 'active', month_ago, month_ago),
            ('pattern_2', 'data_validation', 0.92, 'active', week_ago, week_ago),
            ('pattern_3', 'error_handling', 0.78, 'deprecated', month_ago, week_ago)
        ]
        
        for pattern in patterns:
            conn.execute(
                "INSERT INTO learned_patterns VALUES (?, ?, ?, ?, ?, ?)",
                pattern
            )
        
        # Sample applications
        applications = [
            ('pattern_1', True, 0.88, now - timedelta(days=1)),
            ('pattern_1', True, 0.82, now - timedelta(days=2)),
            ('pattern_1', False, 0.75, now - timedelta(days=3)),
            ('pattern_2', True, 0.95, now - timedelta(days=1)),
            ('pattern_2', True, 0.90, now - timedelta(days=2))
        ]
        
        for app in applications:
            conn.execute(
                "INSERT INTO pattern_applications (pattern_id, success, confidence_score, applied_at) VALUES (?, ?, ?, ?)",
                app
            )
        
        # Sample corrections
        corrections = [
            ('data_format', 'completed', week_ago, now - timedelta(days=1)),
            ('query_syntax', 'completed', week_ago, now - timedelta(days=2)),
            ('validation_rule', 'pending', now - timedelta(days=1), now - timedelta(days=1))
        ]
        
        for correction in corrections:
            conn.execute(
                "INSERT INTO user_corrections (correction_type, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                correction
            )
        
        # Sample feedback
        feedback = [
            ('pattern_effectiveness', 4, week_ago),
            ('pattern_effectiveness', 5, now - timedelta(days=2)),
            ('correction_quality', 3, now - timedelta(days=1))
        ]
        
        for fb in feedback:
            conn.execute(
                "INSERT INTO user_feedback (feedback_type, rating, created_at) VALUES (?, ?, ?)",
                fb
            )
        
        conn.commit()
        conn.close()
        
        return str(db_path)
    
    @pytest.fixture
    def analytics_service(self, mock_db):
        """Create analytics service with test database."""
        return LearningAnalyticsService(mock_db)
    
    def test_get_pattern_effectiveness(self, analytics_service):
        """Test pattern effectiveness calculation."""
        effectiveness = analytics_service.get_pattern_effectiveness(30)
        
        assert len(effectiveness) >= 2
        
        # Check pattern_1 effectiveness
        pattern_1 = next((p for p in effectiveness if p.pattern_id == 'pattern_1'), None)
        assert pattern_1 is not None
        assert pattern_1.total_applications == 3
        assert pattern_1.successful_applications == 2
        assert pattern_1.success_rate == pytest.approx(2/3, rel=1e-2)
        
        # Check pattern_2 effectiveness
        pattern_2 = next((p for p in effectiveness if p.pattern_id == 'pattern_2'), None)
        assert pattern_2 is not None
        assert pattern_2.total_applications == 2
        assert pattern_2.successful_applications == 2
        assert pattern_2.success_rate == 1.0
    
    def test_get_correction_analysis(self, analytics_service):
        """Test correction analysis calculation."""
        analysis = analytics_service.get_correction_analysis(30)
        
        assert analysis.total_corrections >= 3
        assert analysis.successful_corrections >= 2
        assert analysis.success_rate > 0.5
        assert len(analysis.common_correction_types) > 0
        
        # Check that correction types are included
        correction_types = [ct['type'] for ct in analysis.common_correction_types]
        assert 'data_format' in correction_types or 'query_syntax' in correction_types
    
    def test_get_learning_progress(self, analytics_service):
        """Test learning progress calculation."""
        progress = analytics_service.get_learning_progress(30)
        
        assert progress.patterns_learned >= 0
        assert progress.overall_learning_rate >= 0.0
        assert progress.learning_velocity >= 0.0
        assert isinstance(progress.milestone_progress, dict)
    
    def test_get_user_feedback_analytics(self, analytics_service):
        """Test user feedback analytics."""
        feedback = analytics_service.get_user_feedback_analytics(30)
        
        assert isinstance(feedback, dict)
        if feedback:  # If there's feedback data
            assert 'pattern_effectiveness' in feedback or 'correction_quality' in feedback
    
    def test_empty_database(self, tmp_path):
        """Test analytics with empty database."""
        # Create empty database
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        
        # Create tables but no data
        conn.execute("CREATE TABLE learned_patterns (pattern_id TEXT, pattern_type TEXT, confidence_score REAL, created_at DATETIME)")
        conn.execute("CREATE TABLE pattern_applications (pattern_id TEXT, success BOOLEAN, applied_at DATETIME)")
        conn.execute("CREATE TABLE user_corrections (correction_type TEXT, status TEXT, created_at DATETIME, updated_at DATETIME)")
        conn.execute("CREATE TABLE user_feedback (feedback_type TEXT, rating INTEGER, created_at DATETIME)")
        conn.commit()
        conn.close()
        
        analytics_service = LearningAnalyticsService(str(db_path))
        
        # Should handle empty data gracefully
        effectiveness = analytics_service.get_pattern_effectiveness(30)
        assert effectiveness == []
        
        analysis = analytics_service.get_correction_analysis(30)
        assert analysis.total_corrections == 0
        assert analysis.success_rate == 0.0
        
        progress = analytics_service.get_learning_progress(30)
        assert progress.patterns_learned == 0
        assert progress.overall_learning_rate == 0.0
```

### Integration Tests

Create `tests/components/test_learning_charts.py`:

```python
"""
Tests for Learning Charts Component

Sprint 2.2 Testing:
- Chart creation and rendering
- Data visualization accuracy
- Interactive features
- Error handling
"""

import pytest
import panel as pn
from unittest.mock import Mock, patch

from app.components.admin_dashboard.learning_charts import LearningChartsPanel
from app.services.learning_analytics import PatternEffectiveness, CorrectionAnalysis, LearningProgress


class TestLearningChartsPanel:
    """Test cases for LearningChartsPanel."""
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Create mock analytics service."""
        service = Mock()
        
        # Mock pattern effectiveness data
        service.get_pattern_effectiveness.return_value = [
            PatternEffectiveness(
                pattern_id="test_pattern_1",
                pattern_type="query_optimization",
                success_rate=0.85,
                total_applications=20,
                successful_applications=17,
                failed_applications=3,
                avg_confidence=0.88,
                last_used="2024-01-15",
                trend="improving"
            ),
            PatternEffectiveness(
                pattern_id="test_pattern_2",
                pattern_type="data_validation",
                success_rate=0.92,
                total_applications=15,
                successful_applications=14,
                failed_applications=1,
                avg_confidence=0.91,
                last_used="2024-01-14",
                trend="stable"
            )
        ]
        
        # Mock correction analysis data
        service.get_correction_analysis.return_value = CorrectionAnalysis(
            total_corrections=50,
            successful_corrections=42,
            success_rate=0.84,
            avg_time_to_success=15.5,
            common_correction_types=[
                {'type': 'data_format', 'count': 20, 'percentage': 40.0},
                {'type': 'query_syntax', 'count': 15, 'percentage': 30.0},
                {'type': 'validation_rule', 'count': 10, 'percentage': 20.0}
            ],
            correction_trends={'weekly_change_percent': 5.2}
        )
        
        # Mock learning progress data
        service.get_learning_progress.return_value = LearningProgress(
            overall_learning_rate=0.87,
            patterns_learned=25,
            patterns_improved=18,
            patterns_deprecated=3,
            learning_velocity=1.2,
            confidence_improvement=0.05,
            milestone_progress={
                'patterns_milestone_100': {
                    'target': 100,
                    'current': 75,
                    'description': '100 learned patterns'
                },
                'success_rate_milestone_90': {
                    'target': 0.90,
                    'current': 0.87,
                    'description': '90% pattern success rate'
                }
            }
        )
        
        return service
    
    @pytest.fixture
    def charts_panel(self, mock_analytics_service):
        """Create charts panel with mock service."""
        return LearningChartsPanel(mock_analytics_service)
    
    def test_panel_initialization(self, charts_panel):
        """Test that panel initializes correctly."""
        assert charts_panel.time_selector is not None
        assert charts_panel.pattern_effectiveness_chart is not None
        assert charts_panel.correction_trends_chart is not None
        assert charts_panel.learning_progress_chart is not None
        assert charts_panel.metrics_cards is not None
    
    def test_pattern_effectiveness_chart_creation(self, charts_panel):
        """Test pattern effectiveness chart creation."""
        chart = charts_panel._create_pattern_effectiveness_chart()
        
        assert chart is not None
        assert chart.title.text == "Pattern Effectiveness by Success Rate"
        assert chart.xaxis.axis_label == "Pattern ID"
        assert chart.yaxis.axis_label == "Success Rate"
    
    def test_correction_trends_chart_creation(self, charts_panel):
        """Test correction trends chart creation."""
        chart = charts_panel._create_correction_trends_chart()
        
        assert chart is not None
        assert chart.title.text == "Most Common Correction Types"
        assert chart.xaxis.axis_label == "Number of Corrections"
        assert chart.yaxis.axis_label == "Correction Type"
    
    def test_learning_progress_chart_creation(self, charts_panel):
        """Test learning progress chart creation."""
        chart = charts_panel._create_learning_progress_chart()
        
        assert chart is not None
        assert chart.title.text == "Learning Progress Milestones"
        assert chart.xaxis.axis_label == "Progress (%)"
        assert chart.yaxis.axis_label == "Milestone"
    
    def test_metrics_cards_creation(self, charts_panel):
        """Test metrics cards creation."""
        cards = charts_panel._create_metrics_cards()
        
        assert cards is not None
        # Should be a Panel Row with multiple cards
        assert hasattr(cards, '__len__')
    
    def test_time_selector_update(self, charts_panel):
        """Test that time selector updates work."""
        # Change time period
        charts_panel.time_selector.value = 60
        
        # Trigger update
        charts_panel._update_charts(None)
        
        # Verify analytics service was called with new period
        charts_panel.analytics_service.get_pattern_effectiveness.assert_called_with(60)
        charts_panel.analytics_service.get_correction_analysis.assert_called_with(60)
        charts_panel.analytics_service.get_learning_progress.assert_called_with(60)
    
    def test_empty_data_handling(self, mock_analytics_service):
        """Test handling of empty data."""
        # Configure mock to return empty data
        mock_analytics_service.get_pattern_effectiveness.return_value = []
        mock_analytics_service.get_correction_analysis.return_value = CorrectionAnalysis(
            total_corrections=0,
            successful_corrections=0,
            success_rate=0.0,
            avg_time_to_success=0.0,
            common_correction_types=[],
            correction_trends={}
        )
        
        charts_panel = LearningChartsPanel(mock_analytics_service)
        
        # Should create charts without errors
        pattern_chart = charts_panel._create_pattern_effectiveness_chart()
        correction_chart = charts_panel._create_correction_trends_chart()
        
        assert pattern_chart is not None
        assert correction_chart is not None
    
    def test_get_panel_structure(self, charts_panel):
        """Test the complete panel structure."""
        panel = charts_panel.get_panel()
        
        assert panel is not None
        assert isinstance(panel, pn.Column)
        
        # Should contain all major components
        assert len(panel) >= 4  # Title, selector, metrics, charts
```

## SUCCESS CRITERIA

### Functional Requirements
- [ ] **Learning Analytics Service**: Comprehensive analytics for pattern effectiveness, correction success, and learning progress
- [ ] **Pattern Effectiveness Tracking**: Visual charts showing pattern success rates, trends, and performance metrics
- [ ] **Correction Success Analysis**: Detailed analysis of correction types, success rates, and trends
- [ ] **Learning Progress Indicators**: Milestone tracking and progress visualization
- [ ] **User Feedback Analytics**: Sentiment analysis and feedback trend tracking
- [ ] **Interactive Charts**: Time period selection and real-time data updates

### Technical Requirements
- [ ] **Database Integration**: Efficient queries for learning analytics data
- [ ] **Chart Performance**: Responsive visualizations with proper error handling
- [ ] **Data Accuracy**: Correct calculation of success rates, trends, and progress metrics
- [ ] **Memory Efficiency**: Optimized data processing for large datasets
- [ ] **Error Handling**: Graceful handling of missing or invalid data

### User Experience Requirements
- [ ] **Intuitive Interface**: Clear and understandable learning analytics dashboard
- [ ] **Visual Clarity**: Well-designed charts with appropriate colors and labels
- [ ] **Interactive Features**: Responsive time period selection and chart updates
- [ ] **Performance Feedback**: Quick loading and smooth interactions
- [ ] **Information Hierarchy**: Logical organization of learning metrics and insights

### Testing Requirements
- [ ] **Unit Test Coverage**: ≥85% coverage for learning analytics service
- [ ] **Integration Tests**: Complete testing of chart components and data flow
- [ ] **Performance Tests**: Chart rendering and data processing performance
- [ ] **Error Handling Tests**: Proper handling of edge cases and invalid data
- [ ] **User Interaction Tests**: Time selector and chart update functionality

## DEVELOPMENT WORKFLOW

### Phase 1: Service Development (Days 1-2)
1. **Create Learning Analytics Service**
   - Implement pattern effectiveness tracking
   - Add correction success analysis
   - Build learning progress metrics
   - Add user feedback analytics

2. **Database Integration**
   - Optimize queries for performance
   - Add proper indexing
   - Implement data validation

### Phase 2: Chart Development (Days 3-4)
1. **Create Learning Charts Component**
   - Pattern effectiveness charts
   - Correction trends visualization
   - Learning progress indicators
   - Metrics summary cards

2. **Interactive Features**
   - Time period selection
   - Chart updates and refresh
   - Hover tooltips and details

### Phase 3: Integration & Testing (Days 5-7)
1. **Dashboard Integration**
   - Add learning analytics tab
   - Integrate with existing dashboard
   - Ensure consistent styling

2. **Comprehensive Testing**
   - Unit tests for all components
   - Integration testing
   - Performance optimization
   - User acceptance testing

## VALIDATION STEPS

### Pre-Development Validation
- [ ] Review existing learning system data structure
- [ ] Confirm analytics requirements with stakeholders
- [ ] Validate chart design and user interface mockups
- [ ] Ensure database schema supports required analytics

### Development Validation
- [ ] **Code Review**: All learning analytics code reviewed for accuracy and performance
- [ ] **Data Validation**: Verify analytics calculations against known test data
- [ ] **Chart Validation**: Confirm visualizations accurately represent data
- [ ] **Integration Testing**: Ensure seamless integration with existing dashboard

### Post-Development Validation
- [ ] **User Testing**: Healthcare administrators test learning analytics features
- [ ] **Performance Testing**: Verify chart loading and interaction performance
- [ ] **Data Accuracy**: Validate analytics results against manual calculations
- [ ] **Documentation Review**: Ensure comprehensive documentation for learning analytics

## IMPORTANT NOTES

### Learning System Context
- **Pattern Lifecycle**: Understand how patterns are created, applied, and deprecated
- **Correction Process**: Familiarize with the correction workflow and success criteria
- **Feedback System**: Understand how user feedback is collected and categorized
- **Performance Metrics**: Know what constitutes successful learning and improvement

### Data Considerations
- **Historical Data**: Ensure sufficient historical data for meaningful analytics
- **Data Quality**: Validate data integrity before performing analytics
- **Performance Impact**: Optimize queries to avoid impacting system performance
- **Privacy Concerns**: Ensure analytics don't expose sensitive information

### Technical Considerations
- **Chart Performance**: Large datasets may require pagination or data sampling
- **Real-time Updates**: Consider caching strategies for frequently accessed analytics
- **Mobile Compatibility**: Ensure charts work well on different screen sizes
- **Accessibility**: Include proper labels and alternative text for charts

### Future Enhancements
- **Predictive Analytics**: Consider adding trend prediction and forecasting
- **Advanced Filtering**: Add filters for pattern types, time ranges, and user segments
- **Export Capabilities**: Enable export of analytics data and charts
- **Alert Integration**: Connect analytics insights to the alert system 