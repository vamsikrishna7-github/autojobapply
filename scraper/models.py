from django.db import models

class JobPost(models.Model):
    # Core job properties
    job_id = models.CharField(max_length=255, unique=True) # ID from the job board
    site = models.CharField(max_length=50) # linkedin, indeed, etc.
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    job_url = models.URLField(max_length=1000)
    
    # Details & Extraction
    description = models.TextField(blank=True, null=True)
    extracted_email = models.EmailField(blank=True, null=True)
    company_domain = models.CharField(max_length=253, blank=True, null=True)
    
    # Automation Status tracking
    date_posted = models.DateField(blank=True, null=True)
    date_scraped = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} at {self.company}"


class JobContact(models.Model):
    """A publicly listed contact address associated with a job post."""

    class Source(models.TextChoices):
        DESCRIPTION = "description", "Job description"
        JOB_PAGE = "job_page", "Job page"

    class ContactType(models.TextChoices):
        RECRUITER = "recruiter", "Recruiter"
        HIRING_MANAGER = "hiring_manager", "Hiring manager"
        HR = "hr", "HR"
        COMPANY = "company", "Company contact"
        OTHER = "other", "Other"

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="contacts")
    email = models.EmailField()
    source = models.CharField(max_length=20, choices=Source.choices)
    contact_type = models.CharField(max_length=20, choices=ContactType.choices, default=ContactType.OTHER)
    confidence = models.PositiveSmallIntegerField(default=0)
    context = models.CharField(max_length=500, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "email"], name="unique_job_contact_email"),
        ]
        ordering = ["-confidence", "email"]

    def __str__(self):
        return f"{self.email} ({self.contact_type})"
