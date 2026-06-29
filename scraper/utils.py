import re
import traceback
from datetime import datetime, date
from jobspy import scrape_jobs
from .models import JobPost

def run_job_scraper():
    # keywords = [
    #     "Python Django", "React", "Next.js", "JavaScript", 
    #     "Full-stack Developer", "Frontend Developer", 
    #     "Backend Developer", "Software Engineer"
    # ]
    keywords = [
        "Software Engineer"
    ]
    
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Target platforms sequentially to handle their unique API parameters perfectly
    target_platforms = ["linkedin", "indeed", "google"]

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

                # Run Scraper
                jobs_df = scrape_jobs(**scrape_kwargs)
                
                if jobs_df is None or jobs_df.empty:
                    print(f"-> No items returned from {site} for '{query}'.")
                    continue

                # Process Row-Level Insertions
                for _, row in jobs_df.iterrows():
                    try:
                        job_id = str(row.get('id', ''))
                        if not job_id or job_id == 'nan' or JobPost.objects.filter(job_id=job_id).exists():
                            continue 

                        description = row.get('description', '') or ''
                        found_emails = re.findall(email_regex, description)
                        extracted_email = found_emails[0] if found_emails else None

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

                        # Save cleanly to your Django DB
                        JobPost.objects.create(
                            job_id=job_id,
                            site=row.get('site', site),
                            title=row.get('title', 'N/A'),
                            company=row.get('company', 'N/A'),
                            location=row.get('location', 'India'),
                            job_url=row.get('job_url', ''),
                            description=description,
                            extracted_email=extracted_email,
                            date_posted=sanitized_date
                        )
                    except Exception as row_err:
                        pass # Silently proceed over minor single row failures

                print(f" Successfully processed batch for '{query}' on {site}.")

            except Exception as e:
                print(f"Error scraping '{query}' on {site}: {str(e)}")