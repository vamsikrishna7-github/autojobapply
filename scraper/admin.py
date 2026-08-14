from django.contrib import admin
from .models import JobContact, JobPost


class JobContactInline(admin.TabularInline):
    model = JobContact
    extra = 0
    readonly_fields = ("discovered_at",)


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "site", "extracted_email", "email_sent", "date_scraped")
    list_filter = ("site", "email_sent")
    search_fields = ("title", "company", "extracted_email", "company_domain")
    inlines = (JobContactInline,)
