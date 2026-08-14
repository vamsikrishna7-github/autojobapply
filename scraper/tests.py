from django.test import TestCase

from .contact_discovery import discover_contacts, find_company_domain, merge_candidates
from .models import JobPost
from .utils import _save_contacts
from .utils import configured_sites


class ContactDiscoveryTests(TestCase):
    def test_default_job_sites_include_naukri(self):
        self.assertIn("naukri", configured_sites())
    def test_ranks_role_specific_public_email_and_keeps_all_addresses(self):
        contacts = discover_contacts(
            "For this role, email our recruiter Jane at jane.doe@acme.com. "
            "General applications: careers@acme.com. Ignore noreply@acme.com.",
            source="description",
            company_domain="acme.com",
        )

        self.assertEqual([contact.email for contact in contacts], ["jane.doe@acme.com", "careers@acme.com"])
        self.assertEqual(contacts[0].contact_type, "recruiter")
        self.assertGreater(contacts[0].confidence, contacts[1].confidence)

    def test_supports_bracket_obfuscation_without_rewriting_normal_prose(self):
        contacts = discover_contacts(
            "Ask our recruiter at the event, then send a CV to jobs [at] acme [dot] com.",
            source="description",
            company_domain="acme.com",
        )
        self.assertEqual([contact.email for contact in contacts], ["jobs@acme.com"])

    def test_only_uses_an_explicit_company_url_for_domain(self):
        self.assertEqual(find_company_domain({"company_url": "https://www.acme.com/about"}), "acme.com")
        self.assertIsNone(find_company_domain({}, "https://www.linkedin.com/jobs/view/123"))

    def test_persists_all_contacts_and_legacy_best_contact(self):
        job = JobPost.objects.create(
            job_id="test-1", site="google", title="Engineer", company="Acme", job_url="https://example.com/job"
        )
        contacts = merge_candidates(discover_contacts(
            "Contact our recruiter at recruiter@acme.com. General applications: careers@acme.com.",
            source="description", company_domain="acme.com",
        ))
        _save_contacts(job, contacts)
        job.refresh_from_db()

        self.assertEqual(job.contacts.count(), 2)
        self.assertEqual(job.extracted_email, "recruiter@acme.com")
