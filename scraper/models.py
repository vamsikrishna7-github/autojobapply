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
    
    # Automation Status tracking
    date_posted = models.DateField(blank=True, null=True)
    date_scraped = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} at {self.company}"