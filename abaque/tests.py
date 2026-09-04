import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import UserConfiguration, UserSavedJob
from .oidc_backend import AbaqueOIDCBackend
from .views import ACCESS_GROUP_NAME


def grant_access(user):
    group, _ = Group.objects.get_or_create(name=ACCESS_GROUP_NAME)
    user.groups.add(group)
    return user


class AuthRequiredTests(TestCase):
    """Unauthenticated requests should be redirected to the login page."""

    def test_index_redirects_to_login(self):
        response = self.client.get(reverse("abaque:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_configurations_redirects_to_login(self):
        response = self.client.get(reverse("abaque:api_configurations"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_saved_jobs_redirects_to_login(self):
        response = self.client.get(reverse("abaque:api_get_saved_jobs"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_apply_job_redirects_to_login(self):
        response = self.client.post(reverse("abaque:apply_job", args=[1]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_delete_job_redirects_to_login(self):
        response = self.client.delete(reverse("abaque:api_delete_job", args=[1]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class IndexViewTests(TestCase):
    def setUp(self):
        self.user = grant_access(User.objects.create_user(username="alice", password="pw12345"))
        self.client.force_login(self.user)

    def test_index_returns_200_for_logged_in_user(self):
        response = self.client.get(reverse("abaque:index"))
        self.assertEqual(response.status_code, 200)

    def test_option_decimal_data_attributes_not_localized(self):
        # The French locale renders 0.1 as "0,1", which parseFloat truncates to 0
        # in the cost formulas; data attributes must stay unlocalized.
        response = self.client.get(reverse("abaque:index"))
        self.assertContains(response, 'data-pourcentage_contribution="0.1"')
        self.assertNotContains(response, 'data-pourcentage_contribution="0,1"')


class ConfigurationsApiTests(TestCase):
    def setUp(self):
        self.user = grant_access(User.objects.create_user(username="bob", password="pw12345"))
        self.client.force_login(self.user)

    def test_post_then_get_round_trip(self):
        payload = {"1": [{"name": "Oui"}, {"name": "Non"}]}
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        get_response = self.client.get(reverse("abaque:api_configurations"))
        self.assertEqual(get_response.status_code, 200)
        data = get_response.json()
        self.assertEqual(data["1"], payload["1"])

        config = UserConfiguration.objects.get(user=self.user, group_id=1)
        self.assertEqual(config.options_json, payload["1"])

    def test_non_dict_body_rejected(self):
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_options_not_a_list_rejected(self):
        payload = {"1": {"name": "Oui"}}
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_option_missing_name_rejected(self):
        payload = {"1": [{"foo": "bar"}]}
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_rejected(self):
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_group_id_rejected(self):
        payload = {"42": [{"name": "Oui"}]}
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_property_key_with_unsafe_characters_rejected(self):
        # A key with a space could escape the data- attribute it is rendered into.
        payload = {"1": [{"name": "Oui", "x onmouseover=alert(1)": "y"}]}
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_accented_property_key_accepted(self):
        payload = {"2": [{"name": "PLA", "densité": 1.24}]}
        response = self.client.post(
            reverse("abaque:api_configurations"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)


class SavedJobsTests(TestCase):
    def setUp(self):
        self.user = grant_access(User.objects.create_user(username="carol", password="pw12345"))
        self.other_user = User.objects.create_user(username="dave", password="pw12345")
        self.client.force_login(self.user)

    def test_save_job_form_encoded_stores_dict(self):
        state = {"choices": {"1": "Oui"}, "rows": [], "numberOfCopies": "1"}
        response = self.client.post(
            reverse("abaque:api_get_saved_jobs"),
            data={"name": "My Job", "state": json.dumps(state)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "My Job")

        job = UserSavedJob.objects.get(id=data["id"])
        self.assertIsInstance(job.state_json, dict)
        self.assertEqual(job.state_json, state)

    def test_apply_job_returns_state_as_object(self):
        state = {"choices": {"2": "Non"}, "rows": [1, 2], "numberOfCopies": "3"}
        job = UserSavedJob.objects.create(user=self.user, name="Job A", state_json=state)

        response = self.client.post(reverse("abaque:apply_job", args=[job.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data["state"], dict)
        self.assertEqual(data["state"], state)

    def test_apply_job_on_legacy_string_row_returns_object(self):
        state = {"choices": {"3": "Yes"}, "rows": [], "numberOfCopies": "2"}
        job = UserSavedJob.objects.create(user=self.user, name="Legacy Job", state_json=json.dumps(state))
        # Confirm the row really was stored as a raw string (legacy bug reproduction).
        job.refresh_from_db()
        self.assertIsInstance(job.state_json, str)

        response = self.client.post(reverse("abaque:apply_job", args=[job.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data["state"], dict)
        self.assertEqual(data["state"], state)

    def test_long_name_truncated_and_empty_name_gets_default(self):
        response = self.client.post(
            reverse("abaque:api_get_saved_jobs"),
            data={"name": "x" * 300, "state": "{}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["name"]), 255)

        response = self.client.post(
            reverse("abaque:api_get_saved_jobs"),
            data={"name": "   ", "state": "{}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Projet sans nom")

    def test_oversized_state_rejected(self):
        big_state = json.dumps({"choices": {}, "rows": ["x" * (300 * 1024)]})
        response = self.client.post(
            reverse("abaque:api_get_saved_jobs"),
            data={"name": "Big", "state": big_state},
        )
        self.assertEqual(response.status_code, 400)

    def test_job_count_cap_enforced(self):
        from .views import MAX_SAVED_JOBS_PER_USER

        UserSavedJob.objects.bulk_create([
            UserSavedJob(user=self.user, name=f"Job {i}", state_json={})
            for i in range(MAX_SAVED_JOBS_PER_USER)
        ])
        response = self.client.post(
            reverse("abaque:api_get_saved_jobs"),
            data={"name": "One too many", "state": "{}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_job_works(self):
        job = UserSavedJob.objects.create(user=self.user, name="To Delete", state_json={})
        response = self.client.delete(reverse("abaque:api_delete_job", args=[job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserSavedJob.objects.filter(id=job.id).exists())

    def test_other_users_job_returns_404_on_apply(self):
        job = UserSavedJob.objects.create(user=self.other_user, name="Not Yours", state_json={})
        response = self.client.post(reverse("abaque:apply_job", args=[job.id]))
        self.assertEqual(response.status_code, 404)

    def test_other_users_job_returns_404_on_delete(self):
        job = UserSavedJob.objects.create(user=self.other_user, name="Not Yours", state_json={})
        response = self.client.delete(reverse("abaque:api_delete_job", args=[job.id]))
        self.assertEqual(response.status_code, 404)


class RegistrationTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "password1": "S0me-Strong-Pass",
            "password2": "S0me-Strong-Pass",
        })
        self.assertRedirects(response, reverse("abaque:index"), target_status_code=403)
        self.assertTrue(User.objects.filter(username="newuser").exists())

        user = User.objects.get(username="newuser")
        self.assertFalse(user.groups.filter(name=ACCESS_GROUP_NAME).exists())

    def test_register_requires_matching_passwords(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser2",
            "password1": "S0me-Strong-Pass",
            "password2": "does-not-match",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser2").exists())


class OIDCBackendTests(TestCase):
    def test_oidc_username_collision_gets_unique_suffix(self):
        User.objects.create_user(username="simons", email="local@example.com")
        claims = {
            "preferred_username": "simons",
            "email": "sso@example.com",
            "sub": "oidc-user-123",
        }

        user = AbaqueOIDCBackend().create_user(claims)

        self.assertNotEqual(user.username, "simons")
        self.assertEqual(user.email, "sso@example.com")


class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="frank", password="pw12345")
        self.client.force_login(self.user)

    def test_logout_requires_post(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_via_post_works(self):
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))


class PendingApprovalTests(TestCase):
    """Logged-in users without ACCESS_GROUP_NAME membership are gated."""

    def setUp(self):
        self.user = User.objects.create_user(username="eve", password="pw12345")
        self.client.force_login(self.user)

    def test_index_shows_pending_approval(self):
        response = self.client.get(reverse("abaque:index"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "en attente de validation", status_code=403)

    def test_api_configurations_blocked_until_approved(self):
        response = self.client.get(reverse("abaque:api_configurations"))
        self.assertEqual(response.status_code, 403)

    def test_index_accessible_once_granted_access(self):
        grant_access(self.user)
        response = self.client.get(reverse("abaque:index"))
        self.assertEqual(response.status_code, 200)
