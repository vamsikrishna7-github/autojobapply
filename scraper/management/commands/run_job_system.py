from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import DatabaseError
from django.db.migrations.executor import MigrationExecutor
from scraper.utils import run_job_scraper
from scraper.outreach import auto_apply_via_email

class Command(BaseCommand):
    help = 'Runs the JobSpy scraping engine and triggers auto outreach emails.'

    def handle(self, *args, **options):
        connection = connections["default"]
        try:
            connection.ensure_connection()
            executor = MigrationExecutor(connection)
        except DatabaseError as exc:
            engine = connection.settings_dict["ENGINE"]
            host = connection.settings_dict.get("HOST") or "local SQLite"
            raise CommandError(
                f"Cannot connect to the configured database ({engine}, {host}). "
                "For Supabase, copy the current host, port, database, user, and password "
                "from Project Settings → Database → Connection string into .env. "
                "For local development, set USE_SQLITE=true in .env and run `python manage.py migrate`."
            ) from exc
        pending_migrations = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if pending_migrations:
            raise CommandError(
                "Database tables are not ready. Run `python manage.py migrate` "
                "before starting the job scraper."
            )

        self.stdout.write("Starting JobSpy Scraping Routine...")
        run_job_scraper()
        self.stdout.write("Scraping completed. Initiating direct outreach actions...")
        # auto_apply_via_email()
        self.stdout.write("System execution completed successfully.")
