"""
AAA Admin Dashboard Deployment Script

Automated deployment script for the Admin Monitoring Dashboard,
including environment setup, database initialization, and service configuration.

Sprint 3.2 Features:
- Automated deployment process
- Environment validation
- Database setup and migration
- Service configuration
- Health check validation
"""

import sys
import subprocess
import sqlite3
import json
from pathlib import Path
from typing import Dict
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.utils.db_migrations import apply_pending_migrations
    from app.services.dashboard_service import DashboardService
    from app.services.production_monitor import ProductionMonitor
except ImportError:
    # For testing without full app setup
    apply_pending_migrations = None
    DashboardService = None
    ProductionMonitor = None


class DeploymentManager:
    """Manages the deployment process for the Admin Dashboard."""

    def __init__(self, environment: str = "production"):
        """Initialize deployment manager.

        Args:
            environment: Deployment environment ('development', 'staging', 'production')
        """
        self.environment = environment
        self.project_root = project_root
        self.deployment_config = self._load_deployment_config()

    def _load_deployment_config(self) -> Dict:
        """Load deployment configuration."""
        config_file = self.project_root / "deployment" / f"{self.environment}.json"

        if config_file.exists():
            with open(config_file, "r") as f:
                return json.load(f)

        # Default configuration
        return {
            "database_path": str(self.project_root / "patient_data.db"),
            "log_level": "INFO",
            "monitoring_enabled": True,
            "backup_enabled": True,
            "alert_email_enabled": False,
            "maintenance_schedule_enabled": True,
        }

    def deploy(self):
        """Execute complete deployment process."""
        print(
            f"Starting AAA Admin Dashboard deployment for {self.environment} environment..."
        )

        try:
            # Step 1: Validate environment
            print("1. Validating environment...")
            self._validate_environment()

            # Step 2: Setup directories
            print("2. Setting up directories...")
            self._setup_directories()

            # Step 3: Install dependencies
            print("3. Installing dependencies...")
            self._install_dependencies()

            # Step 4: Setup database
            print("4. Setting up database...")
            self._setup_database()

            # Step 5: Configure services
            print("5. Configuring services...")
            self._configure_services()

            # Step 6: Initialize monitoring
            print("6. Initializing monitoring...")
            self._initialize_monitoring()

            # Step 7: Run health checks
            print("7. Running health checks...")
            self._run_health_checks()

            # Step 8: Setup backup
            print("8. Setting up backup...")
            self._setup_backup()

            print("\n✅ Deployment completed successfully!")
            print(f"Environment: {self.environment}")
            print(f"Database: {self.deployment_config['database_path']}")
            print(
                f"Monitoring: {'Enabled' if self.deployment_config['monitoring_enabled'] else 'Disabled'}"
            )

            self._print_next_steps()

        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            sys.exit(1)

    def _validate_environment(self):
        """Validate deployment environment."""
        # Check Python version
        if sys.version_info < (3, 8):
            raise Exception("Python 3.8 or higher is required")

        # Check required directories
        required_dirs = ["app", "migrations", "tests"]
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                raise Exception(f"Required directory not found: {dir_name}")

        # Check required files
        required_files = ["requirements.txt", "run.py"]
        for file_name in required_files:
            if not (self.project_root / file_name).exists():
                raise Exception(f"Required file not found: {file_name}")

        print("   ✓ Environment validation passed")

    def _setup_directories(self):
        """Setup required directories."""
        directories = ["logs", "backups", "exports", "temp"]

        for dir_name in directories:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"   ✓ Created directory: {dir_name}")

    def _install_dependencies(self):
        """Install Python dependencies."""
        requirements_file = self.project_root / "requirements.txt"

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True,
            )
            print("   ✓ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install dependencies: {e}")

    def _setup_database(self):
        """Setup and initialize database."""
        db_path = self.deployment_config["database_path"]

        # Create database directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Apply migrations
        try:
            if apply_pending_migrations:
                apply_pending_migrations(db_path)
                print(f"   ✓ Database initialized: {db_path}")
            else:
                print("   ⚠ Database migrations skipped (app not available)")
        except Exception as e:
            raise Exception(f"Database setup failed: {e}")

        # Verify database structure
        self._verify_database_structure(db_path)

    def _verify_database_structure(self, db_path: str):
        """Verify database has all required tables."""
        required_tables = [
            "dashboard_metrics_history",
            "alert_configurations",
            "dashboard_preferences",
            "maintenance_logs",
            "benchmark_results",
            "learning_metrics",
            "maintenance_history",
            "system_configuration",
        ]

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )
            existing_tables = [row[0] for row in cursor.fetchall()]

        missing_tables = [
            table for table in required_tables if table not in existing_tables
        ]
        if missing_tables:
            raise Exception(f"Missing required tables: {missing_tables}")

        print("   ✓ Database structure verified")

    def _configure_services(self):
        """Configure dashboard services."""
        # Create environment configuration file
        env_config = {
            "LOG_LEVEL": self.deployment_config["log_level"],
            "DATABASE_PATH": self.deployment_config["database_path"],
            "MONITORING_ENABLED": str(self.deployment_config["monitoring_enabled"]),
            "ALERT_EMAIL_ENABLED": str(self.deployment_config["alert_email_enabled"]),
            "MAINTENANCE_SCHEDULE_ENABLED": str(
                self.deployment_config["maintenance_schedule_enabled"]
            ),
        }

        env_file = self.project_root / ".env.deployment"
        with open(env_file, "w") as f:
            for key, value in env_config.items():
                f.write(f"{key}={value}\n")

        print("   ✓ Service configuration created")

    def _initialize_monitoring(self):
        """Initialize production monitoring."""
        if not self.deployment_config["monitoring_enabled"]:
            print("   ⚠ Monitoring disabled in configuration")
            return

        if not ProductionMonitor:
            print("   ⚠ Monitoring skipped (app not available)")
            return

        try:
            # Initialize production monitor
            monitor = ProductionMonitor(self.deployment_config["database_path"])

            # Start monitoring (will run in background)
            monitor.start_monitoring()

            print("   ✓ Production monitoring initialized")
        except Exception as e:
            print(f"   ⚠ Monitoring initialization failed: {e}")

    def _run_health_checks(self):
        """Run comprehensive health checks."""
        if not DashboardService:
            print("   ⚠ Health checks skipped (app not available)")
            return

        try:
            dashboard_service = DashboardService(
                self.deployment_config["database_path"]
            )

            # Get health status
            health = dashboard_service.get_health_status()

            if health.overall_status == "critical":
                raise Exception(f"Health check failed: {health.overall_status}")

            print(f"   ✓ Health check passed: {health.overall_status}")

            # Test basic functionality
            performance_metrics = dashboard_service.get_performance_metrics()
            if not performance_metrics:
                print("   ⚠ No performance metrics available")
            else:
                print("   ✓ Metrics collection working")

        except Exception as e:
            raise Exception(f"Health check failed: {e}")

    def _setup_backup(self):
        """Setup automated backup."""
        if not self.deployment_config["backup_enabled"]:
            print("   ⚠ Backup disabled in configuration")
            return

        # Create backup script
        backup_script = self.project_root / "scripts" / "backup.py"
        backup_script.parent.mkdir(exist_ok=True)

        backup_code = f'''#!/usr/bin/env python3
"""Automated backup script for AAA Admin Dashboard."""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

def backup_database():
    """Backup the main database."""
    db_path = "{self.deployment_config['database_path']}"
    backup_dir = Path("{self.project_root}") / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"database_backup_{{timestamp}}.db"
    
    # Create backup
    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(str(backup_path)) as backup:
            source.backup(backup)
    
    print(f"Database backed up to: {{backup_path}}")
    
    # Cleanup old backups (keep last 7 days)
    import glob
    import os
    backup_files = glob.glob(str(backup_dir / "database_backup_*.db"))
    backup_files.sort()
    
    if len(backup_files) > 7:
        for old_backup in backup_files[:-7]:
            os.remove(old_backup)
            print(f"Removed old backup: {{old_backup}}")

if __name__ == "__main__":
    backup_database()
'''

        with open(backup_script, "w") as f:
            f.write(backup_code)

        backup_script.chmod(0o755)
        print("   ✓ Backup script created")

    def _print_next_steps(self):
        """Print next steps for the user."""
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Start the application:")
        print(f"   cd {self.project_root}")
        print("   python run.py")
        print()
        print("2. Access the Admin Dashboard:")
        print("   Open your web browser and navigate to the Panel application")
        print("   Click on the 'Admin Dashboard' tab")
        print()
        print("3. Configure alerts (optional):")
        print("   Set environment variables for email/Slack notifications:")
        print("   - ALERT_EMAIL_ENABLED=true")
        print("   - ALERT_SMTP_SERVER=your.smtp.server")
        print("   - ALERT_EMAIL_USERNAME=your.email@domain.com")
        print("   - ALERT_EMAIL_PASSWORD=your.password")
        print("   - ALERT_EMAIL_TO=admin1@domain.com,admin2@domain.com")
        print()
        print("4. Schedule regular backups:")
        print(f"   Add to crontab: 0 2 * * * {self.project_root}/scripts/backup.py")
        print()
        print("5. Monitor system health:")
        print("   Check the dashboard regularly for alerts and performance metrics")
        print("=" * 60)


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy AAA Admin Dashboard")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="production",
        help="Deployment environment",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate environment, do not deploy",
    )

    args = parser.parse_args()

    deployment_manager = DeploymentManager(args.environment)

    if args.validate_only:
        print("Validating environment only...")
        deployment_manager._validate_environment()
        print("✅ Environment validation passed")
    else:
        deployment_manager.deploy()


if __name__ == "__main__":
    main()
