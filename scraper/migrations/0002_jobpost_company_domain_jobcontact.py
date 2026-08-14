from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("scraper", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="jobpost",
            name="company_domain",
            field=models.CharField(blank=True, max_length=253, null=True),
        ),
        migrations.CreateModel(
            name="JobContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("source", models.CharField(choices=[("description", "Job description"), ("job_page", "Job page")], max_length=20)),
                ("contact_type", models.CharField(choices=[("recruiter", "Recruiter"), ("hiring_manager", "Hiring manager"), ("hr", "HR"), ("company", "Company contact"), ("other", "Other")], default="other", max_length=20)),
                ("confidence", models.PositiveSmallIntegerField(default=0)),
                ("context", models.CharField(blank=True, max_length=500)),
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contacts", to="scraper.jobpost")),
            ],
            options={"ordering": ["-confidence", "email"]},
        ),
        migrations.AddConstraint(
            model_name="jobcontact",
            constraint=models.UniqueConstraint(fields=("job", "email"), name="unique_job_contact_email"),
        ),
    ]
