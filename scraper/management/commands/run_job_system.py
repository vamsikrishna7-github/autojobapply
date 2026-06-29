from django.core.management.base import BaseCommand
from scraper.utils import run_job_scraper
from scraper.outreach import auto_apply_via_email

class Command(BaseCommand):
    help = 'Runs the JobSpy scraping engine and triggers auto outreach emails.'

    def handle(self, *args, **options):
        self.stdout.write("Starting JobSpy Scraping Routine...")
        run_job_scraper()
        self.stdout.write("Scraping completed. Initiating direct outreach actions...")
        # auto_apply_via_email()
        self.stdout.write("System execution completed successfully.")