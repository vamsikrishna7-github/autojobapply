import logging
import os
from datetime import datetime, date
from jobspy import scrape_jobs
from django.db import transaction
from .models import JobPost
from .contact_discovery import (
    discover_contacts,
    fetch_public_job_page,
    find_company_domain,
    merge_candidates,
)

logger = logging.getLogger(__name__)

SUPPORTED_SITES = {
    "linkedin",
    "indeed",
    "google",
    "naukri",
    "glassdoor",
    "zip_recruiter",
    "bayt",
    "bdjobs",
}
# The first four are the JobSpy sources suited to an India-based search. Other
# JobSpy sources are available through JOB_SITES for their supported regions.
DEFAULT_SITES = ("linkedin", "indeed", "google", "naukri")


def configured_sites() -> list[str]:
    """Return validated job boards selected through JOB_SITES in .env."""
    raw_sites = os.getenv("JOB_SITES", ",".join(DEFAULT_SITES))
    sites = [site.strip().lower() for site in raw_sites.split(",") if site.strip()]
    invalid_sites = sorted(set(sites) - SUPPORTED_SITES)
    if invalid_sites:
        raise ValueError(
            "Unsupported JOB_SITES value(s): "
            f"{', '.join(invalid_sites)}. Supported: {', '.join(sorted(SUPPORTED_SITES))}."
        )
    return list(dict.fromkeys(sites))

def _save_contacts(job: JobPost, candidates) -> None:
    """Persist every public address and maintain the legacy best-address field."""
    for candidate in candidates:
        job.contacts.update_or_create(
            email=candidate.email,
            defaults={
                "source": candidate.source,
                "contact_type": candidate.contact_type,
                "confidence": candidate.confidence,
                "context": candidate.context,
            },
        )
    best_contact = job.contacts.order_by("-confidence", "email").first()
    best_email = best_contact.email if best_contact else None
    if job.extracted_email != best_email:
        job.extracted_email = best_email
        job.save(update_fields=["extracted_email"])


def run_job_scraper(fetch_job_pages: bool = True):
    keywords = [
        "Python Django", "React", "Next.js", "JavaScript",
        "Full-stack Developer", "Frontend Developer",
        "Backend Developer", "Software Engineer"
    ]
    # keywords = [
    #     "Software Engineer"
    # ]
    
    target_platforms = configured_sites()

    for site in target_platforms:
        print(f"\n=========================================")
        print(f"Starting Scraper targeting: {site.upper()}")
        print(f"=========================================")

        for query in keywords:
            print(f"Scraping '{query}' on {site}...")
            try:
                # Core shared parameters
                scrape_kwargs = {
                    "site_name": [site],
                    "location": "India",
                    "results_wanted": 15,
                    "hours_old": 72,
                }

                # Site-Specific Fine Tuning
                if site == "linkedin":
                    scrape_kwargs["search_term"] = query
                    scrape_kwargs["linkedin_fetch_description"] = True
                
                elif site == "indeed":
                    scrape_kwargs["search_term"] = query
                    scrape_kwargs["country_indeed"] = "India" # CRITICAL: Tells Indeed where to look
                
                elif site == "google":
                    # CRITICAL: Google requires 'google_search_term' combined with standard location strings
                    scrape_kwargs["google_search_term"] = f"{query} jobs in India"
                else:
                    # Naukri and the optional JobSpy sources use the standard
                    # search term interface.
                    scrape_kwargs["search_term"] = query

                # Run Scraper
                jobs_df = scrape_jobs(**scrape_kwargs)
                
                if jobs_df is None or jobs_df.empty:
                    print(f"-> No items returned from {site} for '{query}'.")
                    continue

                # Process Row-Level Insertions
                for _, row in jobs_df.iterrows():
                    try:
                        job_id = str(row.get('id', ''))
                        if not job_id or job_id == 'nan':
                            logger.warning("Skipping a job without a stable ID from %s", site)
                            continue

                        description = row.get('description', '') or ''
                        job_url = row.get('job_url', '') or ''
                        company_domain = find_company_domain(row, job_url)

                        # Safe Date Validation
                        posted_date = row.get('date_posted')
                        sanitized_date = None
                        if isinstance(posted_date, (date, datetime)):
                            sanitized_date = posted_date
                        elif isinstance(posted_date, str) and posted_date.strip():
                            try:
                                sanitized_date = datetime.strptime(posted_date.strip(), "%Y-%m-%d").date()
                            except ValueError:
                                sanitized_date = None

                        # update_or_create lets later runs enrich jobs that were saved
                        # before their description/page exposed a contact address.
                        with transaction.atomic():
                            job, _created = JobPost.objects.update_or_create(
                                job_id=job_id,
                                defaults={
                                    "site": row.get('site', site),
                                    "title": row.get('title', 'N/A'),
                                    "company": row.get('company', 'N/A'),
                                    "location": row.get('location', 'India'),
                                    "job_url": job_url,
                                    "description": description,
                                    "company_domain": company_domain,
                                    "date_posted": sanitized_date,
                                },
                            )
                            description_contacts = discover_contacts(
                                description,
                                source="description",
                                company_domain=company_domain,
                            )
                            page_contacts = []
                            if fetch_job_pages:
                                page_text = fetch_public_job_page(job_url)
                                page_contacts = discover_contacts(
                                    page_text,
                                    source="job_page",
                                    company_domain=company_domain,
                                )
                            _save_contacts(job, merge_candidates(description_contacts, page_contacts))
                    except Exception as row_err:
                        logger.exception("Could not save or enrich job %r from %s: %s", row.get('id'), site, row_err)

                print(f" Successfully processed batch for '{query}' on {site}.")

            except Exception as e:
                print(f"Error scraping '{query}' on {site}: {str(e)}")
