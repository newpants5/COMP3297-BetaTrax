from django.contrib.auth.models import AnonymousUser, Group, User
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from .models import Comment, DefectReport, Developer, DeveloperMetricEvent, Employee, Product, ProductOwner
from .permissions import (
	IsBetaTester,
	IsDeveloper,
	IsProductOwner,
	IsProductOwnerOrDeveloper,
)
from .serializers import DefectAssignSerializer
from .views import send_status_notification


@override_settings(
	PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
	ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1", "tenant.test.com"],
)
class BetaTraxAPITestCase(TenantTestCase):
	client_class = APIClient

	@classmethod
	def setup_tenant(cls, tenant):
		tenant.name = "Test Tenant"
		tenant.paid_until = timezone.now().date()
		tenant.on_trial = False

	def setUp(self):
		from django.db import connection
		connection.set_tenant(type(self).tenant)
		super().setUp()
		for group_name in ["Product Owner", "Developer", "Beta Tester"]:
			Group.objects.get_or_create(name=group_name)
		self.client.defaults["SERVER_NAME"] = "tenant.test.com"

	def create_user(self, username, password, group_name):
		user = User.objects.create_user(username=username, password=password)
		user.groups.add(Group.objects.get(name=group_name))
		return user

	def api_client_for(self, user):
		client = APIClient()
		client.force_authenticate(user=user)
		client.defaults["SERVER_NAME"] = "tenant.test.com"
		return client

	def create_employee(self, label):
		index = Employee.objects.count() + 1
		return Employee.objects.create(
			employee_id=f"E{index:03d}",
			name=f"{label} {index}",
			email=f"{label.lower()}{index}@example.com",
		)

	def create_product_owner(self, label="Owner"):
		return ProductOwner.objects.create(employee=self.create_employee(label))

	def create_developer(self, label="Developer"):
		return Developer.objects.create(employee=self.create_employee(label))

	def create_product(self, owner=None, name="Product"):
		index = Product.objects.count() + 1
		return Product.objects.create(
			productId=f"P{index:03d}",
			name=f"{name} {index}",
			owner=owner or self.create_product_owner(),
		)

	def create_defect(self, **overrides):
		product = overrides.pop("product", self.create_product())
		defaults = {
			"product": product,
			"product_version": "1.0.0",
			"title": f"Defect {DefectReport.objects.count() + 1}",
			"description": "Something went wrong.",
			"steps_to_reproduce": "1. Open the page\n2. Click save",
			"tester_id": "TEST-001",
			"tester_email": "tester@example.com",
			"status": DefectReport.Status.NEW,
		}
		defaults.update(overrides)
		return DefectReport.objects.create(**defaults)

	def create_comment(self, **overrides):
		defect = overrides.pop("defect", self.create_defect())
		author = overrides.pop("author", self.create_developer())
		defaults = {
			"defect": defect,
			"author": author,
			"text": "Initial comment",
		}
		defaults.update(overrides)
		return Comment.objects.create(**defaults)


class AuthenticationEndpointTests(BetaTraxAPITestCase):
	def test_login_returns_auth_token(self):
		self.create_user("owner", "password123", "Product Owner")

		response = self.client.post(
			"/api/login/",
			{"username": "owner", "password": "password123"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("token", response.data)

	def test_logout_deletes_auth_token(self):
		user = self.create_user("developer", "password123", "Developer")
		token = Token.objects.create(user=user)
		self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

		response = self.client.post("/api/logout/", format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertFalse(Token.objects.filter(key=token.key).exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ProductEndpointTests(BetaTraxAPITestCase):
	def setUp(self):
		super().setUp()
		self.owner_user = self.create_user("owner", "password123", "Product Owner")
		self.owner_role = self.create_product_owner()
		self.product = self.create_product(owner=self.owner_role)

	def test_product_list_returns_registered_products(self):
		client = self.api_client_for(self.owner_user)

		response = client.get("/api/products/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], self.product.id)

	def test_product_create_allows_product_owner(self):
		client = self.api_client_for(self.owner_user)

		response = client.post(
			"/api/products/",
			{
				"productId": "P999",
				"name": "BetaTrax Release 2",
				"owner": self.owner_role.id,
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(Product.objects.filter(productId="P999").exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DefectEndpointTests(BetaTraxAPITestCase):
	def setUp(self):
		super().setUp()
		self.owner_user = self.create_user("owner", "password123", "Product Owner")
		self.developer_user = self.create_user("dev", "password123", "Developer")
		self.tester_user = self.create_user("tester", "password123", "Beta Tester")
		self.owner_role = self.create_product_owner()
		self.developer_role = self.create_developer()
		self.second_developer_role = self.create_developer("DeveloperTwo")
		self.product = self.create_product(owner=self.owner_role)

	def test_defect_list_returns_filtered_results(self):
		open_defect = self.create_defect(product=self.product, status=DefectReport.Status.OPEN)
		self.create_defect(status=DefectReport.Status.NEW)
		client = self.api_client_for(self.developer_user)

		response = client.get(
			f"/api/defects/?status={DefectReport.Status.OPEN}&product={self.product.id}"
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], open_defect.id)

	def test_defect_create_allows_beta_tester(self):
		client = self.api_client_for(self.tester_user)

		response = client.post(
			"/api/defects/",
			{
				"product": self.product.id,
				"product_version": "1.0.1",
				"title": "Save button fails",
				"description": "Saving throws an error.",
				"steps_to_reproduce": "1. Open draft\n2. Click save",
				"tester_id": "BT-007",
				"tester_email": "notify@example.com",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(DefectReport.objects.count(), 1)
		self.assertEqual(DefectReport.objects.get().status, DefectReport.Status.NEW)

	def test_defect_detail_returns_single_report(self):
		defect = self.create_defect(product=self.product)
		client = self.api_client_for(self.owner_user)

		response = client.get(f"/api/defects/{defect.id}/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["id"], defect.id)
		self.assertEqual(response.data["product_name"], self.product.name)

	def test_accept_defect_updates_status_and_fields(self):
		defect = self.create_defect(product=self.product)
		client = self.api_client_for(self.owner_user)

		response = client.patch(
			f"/api/defects/{defect.id}/accept/",
			{"severity": "MAJOR", "priority": "HIGH"},
			format="json",
		)

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.OPEN)
		self.assertEqual(defect.severity, DefectReport.Severity.MAJOR)
		self.assertEqual(defect.priority, DefectReport.Priority.HIGH)

	def test_assign_defect_sets_responsible_developer(self):
		defect = self.create_defect(product=self.product, status=DefectReport.Status.OPEN)
		client = self.api_client_for(self.owner_user)

		response = client.patch(
			f"/api/defects/{defect.id}/assign/",
			{"developer_id": self.developer_role.id},
			format="json",
		)

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.ASSIGNED)
		self.assertEqual(defect.assigned_developer_id, self.developer_role.id)

	def test_developer_can_self_assign_open_defect(self):
		# Link the developer user's email to the employee record so the
		# self-assign check can match request.user to a Developer row.
		self.developer_user.email = self.developer_role.employee.email
		self.developer_user.save()
		defect = self.create_defect(product=self.product, status=DefectReport.Status.OPEN)
		client = self.api_client_for(self.developer_user)

		response = client.patch(
			f"/api/defects/{defect.id}/assign/",
			{"developer_id": self.developer_role.id},
			format="json",
		)

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.ASSIGNED)
		self.assertEqual(defect.assigned_developer_id, self.developer_role.id)

	def test_developer_cannot_assign_defect_to_another_developer(self):
		self.developer_user.email = self.developer_role.employee.email
		self.developer_user.save()
		defect = self.create_defect(product=self.product, status=DefectReport.Status.OPEN)
		client = self.api_client_for(self.developer_user)

		response = client.patch(
			f"/api/defects/{defect.id}/assign/",
			{"developer_id": self.second_developer_role.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		defect.refresh_from_db()
		self.assertIsNone(defect.assigned_developer)

	def test_fix_defect_marks_assigned_defect_as_fixed(self):
		defect = self.create_defect(
			product=self.product,
			status=DefectReport.Status.ASSIGNED,
			assigned_developer=self.developer_role,
		)
		client = self.api_client_for(self.developer_user)

		response = client.patch(f"/api/defects/{defect.id}/fix/", {}, format="json")

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.FIXED)

	def test_resolve_defect_marks_fixed_defect_as_resolved(self):
		defect = self.create_defect(product=self.product, status=DefectReport.Status.FIXED)
		client = self.api_client_for(self.owner_user)

		response = client.patch(f"/api/defects/{defect.id}/resolve/", {}, format="json")

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.RESOLVED)

	def test_reject_defect_marks_new_defect_as_rejected(self):
		defect = self.create_defect(product=self.product)
		client = self.api_client_for(self.owner_user)

		response = client.patch(f"/api/defects/{defect.id}/reject/", {}, format="json")

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.REJECTED)

	def test_reopen_defect_marks_fixed_defect_as_reopened(self):
		defect = self.create_defect(product=self.product, status=DefectReport.Status.FIXED)
		client = self.api_client_for(self.owner_user)

		response = client.patch(f"/api/defects/{defect.id}/reopen/", {}, format="json")

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.REOPENED)

	def test_reassign_defect_updates_assigned_developer(self):
		defect = self.create_defect(
			product=self.product,
			status=DefectReport.Status.ASSIGNED,
			assigned_developer=self.developer_role,
		)
		client = self.api_client_for(self.owner_user)

		response = client.patch(
			f"/api/defects/{defect.id}/reassign/",
			{"developer_id": self.second_developer_role.id},
			format="json",
		)

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.assigned_developer_id, self.second_developer_role.id)
		self.assertEqual(defect.status, DefectReport.Status.ASSIGNED)

	def test_mark_duplicate_links_duplicate_to_parent(self):
		parent = self.create_defect(product=self.product)
		duplicate = self.create_defect(product=self.product)
		client = self.api_client_for(self.owner_user)

		response = client.patch(
			f"/api/defects/{duplicate.id}/mark-duplicate/",
			{"duplicate_of": parent.id},
			format="json",
		)

		duplicate.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(duplicate.status, DefectReport.Status.DUPLICATE)
		self.assertEqual(duplicate.duplicate_of_id, parent.id)

	def test_cannot_reproduce_marks_assigned_defect(self):
		defect = self.create_defect(
			product=self.product,
			status=DefectReport.Status.ASSIGNED,
			assigned_developer=self.developer_role,
		)
		client = self.api_client_for(self.developer_user)

		response = client.patch(
			f"/api/defects/{defect.id}/cannot-reproduce/",
			{},
			format="json",
		)

		defect.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(defect.status, DefectReport.Status.CANNOT_REPRODUCE)


class CommentEndpointTests(BetaTraxAPITestCase):
	def setUp(self):
		super().setUp()
		self.owner_user = self.create_user("owner", "password123", "Product Owner")
		self.developer_user = self.create_user("dev", "password123", "Developer")
		self.author_role = self.create_developer()
		self.product = self.create_product(owner=self.create_product_owner())
		self.defect = self.create_defect(product=self.product, status=DefectReport.Status.OPEN)

	def test_comment_list_returns_comments_for_defect(self):
		first_comment = self.create_comment(defect=self.defect, author=self.author_role, text="First")
		second_comment = self.create_comment(defect=self.defect, author=self.author_role, text="Second")
		client = self.api_client_for(self.owner_user)

		response = client.get(f"/api/defects/{self.defect.id}/comments/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual([item["id"] for item in response.data], [first_comment.id, second_comment.id])

	def test_comment_create_allows_product_owner_or_developer(self):
		client = self.api_client_for(self.developer_user)

		response = client.post(
			f"/api/defects/{self.defect.id}/comments/",
			{"author": self.author_role.id, "text": "Investigating now."},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(Comment.objects.get().defect_id, self.defect.id)

	def test_comment_detail_returns_single_comment(self):
		comment = self.create_comment(defect=self.defect, author=self.author_role)
		client = self.api_client_for(self.owner_user)

		response = client.get(f"/api/comments/{comment.id}/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["id"], comment.id)

	def test_comment_put_replaces_comment_text(self):
		comment = self.create_comment(defect=self.defect, author=self.author_role)
		client = self.api_client_for(self.owner_user)

		response = client.put(
			f"/api/comments/{comment.id}/",
			{"author": self.author_role.id, "text": "Updated via PUT."},
			format="json",
		)

		comment.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(comment.text, "Updated via PUT.")

	def test_comment_patch_updates_comment_text(self):
		comment = self.create_comment(defect=self.defect, author=self.author_role)
		client = self.api_client_for(self.owner_user)

		response = client.patch(
			f"/api/comments/{comment.id}/",
			{"text": "Updated via PATCH."},
			format="json",
		)

		comment.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(comment.text, "Updated via PATCH.")

	def test_comment_delete_removes_comment(self):
		comment = self.create_comment(defect=self.defect, author=self.author_role)
		client = self.api_client_for(self.owner_user)

		response = client.delete(f"/api/comments/{comment.id}/")

		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertFalse(Comment.objects.filter(pk=comment.id).exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationAndValidationTests(BetaTraxAPITestCase):
	def test_send_status_notification_sends_email_when_address_exists(self):
		defect = self.create_defect(status=DefectReport.Status.OPEN, tester_email="notify@example.com")

		send_status_notification(defect, DefectReport.Status.NEW)

		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("status changed to OPEN", mail.outbox[0].subject)
		self.assertEqual(mail.outbox[0].to, ["notify@example.com"])

	def test_send_status_notification_skips_when_no_email(self):
		defect = self.create_defect(status=DefectReport.Status.OPEN, tester_email="")

		send_status_notification(defect, DefectReport.Status.NEW)

		self.assertEqual(len(mail.outbox), 0)

	def test_defect_clean_requires_duplicate_parent_for_duplicate_status(self):
		defect = self.create_defect(status=DefectReport.Status.DUPLICATE, duplicate_of=None)

		with self.assertRaises(ValidationError):
			defect.full_clean()

	def test_defect_clean_rejects_self_duplicate(self):
		defect = self.create_defect()
		defect.duplicate_of = defect

		with self.assertRaises(ValidationError):
			defect.full_clean()

	def test_assign_serializer_rejects_unknown_developer(self):
		serializer = DefectAssignSerializer(data={"developer_id": 999999})

		self.assertFalse(serializer.is_valid())
		self.assertIn("developer_id", serializer.errors)


class PermissionTests(BetaTraxAPITestCase):
	def setUp(self):
		super().setUp()
		self.factory = APIRequestFactory()
		self.owner_user = self.create_user("owner", "password123", "Product Owner")
		self.developer_user = self.create_user("dev", "password123", "Developer")
		self.tester_user = self.create_user("tester", "password123", "Beta Tester")

	def test_is_product_owner_recognizes_product_owner_group(self):
		request = self.factory.get("/api/products/")
		request.user = self.owner_user

		self.assertTrue(IsProductOwner().has_permission(request, None))

	def test_is_developer_recognizes_developer_group(self):
		request = self.factory.get("/api/defects/")
		request.user = self.developer_user

		self.assertTrue(IsDeveloper().has_permission(request, None))

	def test_is_beta_tester_recognizes_beta_tester_group(self):
		request = self.factory.post("/api/defects/")
		request.user = self.tester_user

		self.assertTrue(IsBetaTester().has_permission(request, None))

	def test_is_product_owner_or_developer_rejects_anonymous_user(self):
		request = self.factory.get("/api/defects/1/comments/")
		request.user = AnonymousUser()

		self.assertFalse(IsProductOwnerOrDeveloper().has_permission(request, None))

	def test_is_product_owner_or_developer_accepts_developer(self):
		request = self.factory.get("/api/defects/1/comments/")
		request.user = self.developer_user

		self.assertTrue(IsProductOwnerOrDeveloper().has_permission(request, None))


class DeveloperEffectivenessClassificationTests(BetaTraxAPITestCase):
	"""Unit tests for Developer.effectiveness_summary() — all branches covered."""

	def _make_events(self, developer, fixed_count, reopened_count):
		defect = self.create_defect(
			assigned_developer=developer,
			status=DefectReport.Status.ASSIGNED,
		)
		for _ in range(fixed_count):
			DeveloperMetricEvent.objects.create(
				developer=developer,
				defect=defect,
				event_type=DeveloperMetricEvent.EventType.FIXED,
			)
		for _ in range(reopened_count):
			DeveloperMetricEvent.objects.create(
				developer=developer,
				defect=defect,
				event_type=DeveloperMetricEvent.EventType.REOPENED,
			)

	def test_insufficient_data_when_fixed_count_below_20(self):
		developer = self.create_developer()
		self._make_events(developer, fixed_count=19, reopened_count=0)

		result = developer.effectiveness_summary()

		self.assertEqual(result["classification"], Developer.Effectiveness.INSUFFICIENT_DATA)
		self.assertIsNone(result["ratio"])

	def test_good_when_ratio_below_1_over_32(self):
		# 20 fixed, 0 reopened → ratio 0.0 < 1/32
		developer = self.create_developer()
		self._make_events(developer, fixed_count=20, reopened_count=0)

		result = developer.effectiveness_summary()

		self.assertEqual(result["classification"], Developer.Effectiveness.GOOD)

	def test_fair_when_ratio_between_1_over_32_and_1_over_8(self):
		# 32 fixed, 1 reopened → ratio 1/32 = 0.03125 (not < 1/32, but < 1/8)
		developer = self.create_developer()
		self._make_events(developer, fixed_count=32, reopened_count=1)

		result = developer.effectiveness_summary()

		self.assertEqual(result["classification"], Developer.Effectiveness.FAIR)

	def test_poor_when_ratio_at_or_above_1_over_8(self):
		# 8 fixed but we need >= 20; use 24 fixed, 3 reopened → ratio 3/24 = 0.125 (not < 1/8)
		developer = self.create_developer()
		self._make_events(developer, fixed_count=24, reopened_count=3)

		result = developer.effectiveness_summary()

		self.assertEqual(result["classification"], Developer.Effectiveness.POOR)

	def test_developer_list_returns_all_developers(self):
		developer = self.create_developer()
		client = self.api_client_for(self.create_user("auth", "password123", "Product Owner"))

		response = client.get("/api/developers/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], developer.pk)

	def test_effectiveness_endpoint_returns_classification(self):
		developer = self.create_developer()
		self._make_events(developer, fixed_count=19, reopened_count=0)
		client = self.api_client_for(self.create_user("auth", "password123", "Product Owner"))

		response = client.get(f"/api/developers/{developer.pk}/effectiveness/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("classification", response.data)
		self.assertIn("fixed_count", response.data)
