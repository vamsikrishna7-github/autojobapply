from django.core.mail import EmailMessage
from .models import JobPost

def auto_apply_via_email():
    # Filter targets containing valid contact profiles that haven't been processed yet
    target_jobs = JobPost.objects.filter(extracted_email__isnull=False, email_sent=False)
    
    for job in target_jobs:
        subject = f"Application for {job.title} - Full-Stack Developer"
        
        body = f"""
Hi Hiring Team at {job.company},

I noticed your posting for a {job.title} on {job.site} and wanted to apply directly. 

I am a Full-Stack Software Engineer specializing in Python, Django, JavaScript, React, and Next.js. I build scalable web architectures and cleaner user experiences.

You can view my portfolio and resume link here: https://drive.google.com/file/d/1-ILaSceLgFTsseofXdSo9d3rVmXrPx3r/view?usp=drive_link
Job Reference: {job.job_url}

Looking forward to hearing from you.

Best regards,
Vamsi Krishna Nagidi
        """
        
        try:
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email='your_email@gmail.com',
                to=[job.extracted_email]
            )
            email.send()
            
            # Update status flag to prevent multiple spam actions
            job.email_sent = True
            job.save()
            print(f"Successfully applied to {job.company} for {job.title}")
            
        except Exception as e:
            print(f"Failed to send email to {job.extracted_email}: {str(e)}")