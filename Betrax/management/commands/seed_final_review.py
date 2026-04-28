import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework.authtoken.models import Token

from Betrax.models import (
    Comment,
    DefectReport,
    Developer,
    DeveloperMetricEvent,
    Employee,
    Product,
    ProductOwner,
)
from customers.models import Client, Domain

PASSWORD = "betrax-demo-123"


class Command(BaseCommand):
    help = "Seed demo data for the Final Review (SE Tenant 1 and SE Tenant 2)."

    def _get_or_create_user(self, User, username, email, group):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        if created:
            user.set_password(PASSWORD)
            user.save()
        if not user.groups.filter(pk=group.pk).exists():
            user.groups.add(group)
        return user

    def _ensure_tenant(self, schema_name, name, domain_name):
        tenant, _ = Client.objects.get_or_create(
            schema_name=schema_name,
            defaults={
                "name": name,
                "paid_until": timezone.now().date(),
                "on_trial": False,
            },
        )
        Domain.objects.get_or_create(
            domain=domain_name,
            defaults={"tenant": tenant, "is_primary": True},
        )
        return tenant

    def handle(self, *args, **options):
        for group_name in ["Product Owner", "Developer", "Beta Tester"]:
            Group.objects.get_or_create(name=group_name)

        po_group = Group.objects.get(name="Product Owner")
        dev_group = Group.objects.get(name="Developer")
        tester_group = Group.objects.get(name="Beta Tester")

        User = get_user_model()

        # ── Public-schema users ───────────────────────────────────────────────
        u1 = self._get_or_create_user(User, "user_1", "user1@se1.example.com", po_group)
        u2 = self._get_or_create_user(User, "user_2", "user2@se1.example.com", dev_group)
        self._get_or_create_user(User, "user_3", "user3@se1.example.com", tester_group)
        self._get_or_create_user(User, "user_4", "user4@se1.example.com", tester_group)
        self._get_or_create_user(User, "user_5", "user5@se1.example.com", tester_group)
        u6 = self._get_or_create_user(User, "user_6", "user6@se2.example.com", po_group)
        u7 = self._get_or_create_user(User, "user_7", "user7@se2.example.com", dev_group)
        u8 = self._get_or_create_user(User, "user_8", "user8@se2.example.com", dev_group)

        tokens = {}
        for username in [
            "user_1", "user_2", "user_3", "user_4", "user_5",
            "user_6", "user_7", "user_8",
        ]:
            u = User.objects.get(username=username)
            token, _ = Token.objects.get_or_create(user=u)
            tokens[username] = token.key

        # ── SE Tenant 1 ───────────────────────────────────────────────────────
        tenant1 = self._ensure_tenant("se1", "SE Tenant 1", "se1.localhost")

        with tenant_context(tenant1):
            emp1, _ = Employee.objects.get_or_create(
                employee_id="SE1PO001",
                defaults={"name": "User One", "email": u1.email},
            )
            emp2, _ = Employee.objects.get_or_create(
                employee_id="SE1DEV001",
                defaults={"name": "User Two", "email": u2.email},
            )
            po1, _ = ProductOwner.objects.get_or_create(employee=emp1)
            dev2, _ = Developer.objects.get_or_create(employee=emp2)

            product1, _ = Product.objects.get_or_create(
                productId="prod_1",
                defaults={"name": "SE1 Product", "owner": po1},
            )

            defect1, _ = DefectReport.objects.get_or_create(
                title="Unable to search",
                product=product1,
                defaults={
                    "product_version": "0.9.0",
                    "description": (
                        "Search button unresponsive after completing an initial search"
                    ),
                    "steps_to_reproduce": (
                        "1. Complete a search\n"
                        "2. Modify search criteria\n"
                        "3. Click Search button"
                    ),
                    "tester_id": "Tester_1",
                    "tester_email": "icyreward@gmail.com",
                    "status": DefectReport.Status.ASSIGNED,
                    "severity": DefectReport.Severity.MAJOR,
                    "priority": DefectReport.Priority.HIGH,
                    "assigned_developer": dev2,
                },
            )
            DefectReport.objects.filter(pk=defect1.pk).update(
                submission_date=datetime.datetime(
                    2026, 3, 25, 10, 53, 0, tzinfo=datetime.timezone.utc
                )
            )

        # ── SE Tenant 2 ───────────────────────────────────────────────────────
        tenant2 = self._ensure_tenant("se2", "SE Tenant 2", "se2.localhost")

        with tenant_context(tenant2):
            emp6, _ = Employee.objects.get_or_create(
                employee_id="SE2PO001",
                defaults={"name": "User Six", "email": u6.email},
            )
            emp7, _ = Employee.objects.get_or_create(
                employee_id="SE2DEV001",
                defaults={"name": "User Seven", "email": u7.email},
            )
            emp8, _ = Employee.objects.get_or_create(
                employee_id="SE2DEV002",
                defaults={"name": "User Eight", "email": u8.email},
            )

            po6, _ = ProductOwner.objects.get_or_create(employee=emp6)
            dev7, _ = Developer.objects.get_or_create(employee=emp7)
            dev8, _ = Developer.objects.get_or_create(employee=emp8)

            product2, _ = Product.objects.get_or_create(
                productId="prod_1",
                defaults={"name": "SE2 Product", "owner": po6},
            )

            defect2, _ = DefectReport.objects.get_or_create(
                title="Hit count incorrect",
                product=product2,
                defaults={
                    "product_version": "0.9.0",
                    "description": (
                        "Following a successful search, the hit count is different "
                        "to the number of matches displayed."
                    ),
                    "steps_to_reproduce": (
                        "1. Enter search criteria that ensure at least one match\n"
                        "2. Search\n"
                        "3. Compare matches displayed with the number of hits reported."
                    ),
                    "tester_id": "Tester_1",
                    "tester_email": "icyreward@gmail.com",
                    "status": DefectReport.Status.ASSIGNED,
                    "severity": DefectReport.Severity.MINOR,
                    "priority": DefectReport.Priority.HIGH,
                    "assigned_developer": dev7,
                },
            )
            DefectReport.objects.filter(pk=defect2.pk).update(
                submission_date=datetime.datetime(
                    2026, 4, 27, 15, 37, 0, tzinfo=datetime.timezone.utc
                )
            )

            # Comments on defect2
            comment1, created1 = Comment.objects.get_or_create(
                defect=defect2,
                author=dev7,
                text="Comment added by developer",
            )
            if created1:
                Comment.objects.filter(pk=comment1.pk).update(
                    creation_date=datetime.datetime(
                        2026, 4, 26, 20, 49, 0, tzinfo=datetime.timezone.utc
                    )
                )

            comment2, created2 = Comment.objects.get_or_create(
                defect=defect2,
                author=po6,
                text="Comment added by product owner",
            )
            if created2:
                Comment.objects.filter(pk=comment2.pk).update(
                    creation_date=datetime.datetime(
                        2026, 4, 26, 23, 27, 0, tzinfo=datetime.timezone.utc
                    )
                )

            # Clean up old helper defect if it exists from a previous seed run
            DefectReport.objects.filter(title="[Seeded] Metric base defect").delete()

            # Developer Metrics for user_7: fixed=8, reopened=1
            # Attach events to the real defect (defect2)
            existing_fixed = DeveloperMetricEvent.objects.filter(
                developer=dev7,
                event_type=DeveloperMetricEvent.EventType.FIXED,
            ).count()
            existing_reopened = DeveloperMetricEvent.objects.filter(
                developer=dev7,
                event_type=DeveloperMetricEvent.EventType.REOPENED,
            ).count()

            for _ in range(max(0, 8 - existing_fixed)):
                DeveloperMetricEvent.objects.create(
                    developer=dev7,
                    defect=defect2,
                    event_type=DeveloperMetricEvent.EventType.FIXED,
                )
            for _ in range(max(0, 1 - existing_reopened)):
                DeveloperMetricEvent.objects.create(
                    developer=dev7,
                    defect=defect2,
                    event_type=DeveloperMetricEvent.EventType.REOPENED,
                )

            dev7_summary = dev7.effectiveness_summary()

        # ── Print summary ─────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\n=== Final Review Demo Data Ready ===\n"))
        self.stdout.write(f"Password for all users: {PASSWORD}\n")

        self.stdout.write("SE Tenant 1  (se1.localhost)")
        for uname in ["user_1", "user_2", "user_3", "user_4", "user_5"]:
            self.stdout.write(f"  {uname:<8}  token: {tokens[uname]}")
        self.stdout.write(f"\n  Seeded defect id : {defect1.pk}")
        self.stdout.write(f"  Developer (user_2) id: {dev2.pk}\n")

        self.stdout.write("SE Tenant 2  (se2.localhost)")
        for uname in ["user_6", "user_7", "user_8"]:
            self.stdout.write(f"  {uname:<8}  token: {tokens[uname]}")
        self.stdout.write(f"\n  Seeded defect id : {defect2.pk}")
        self.stdout.write(f"  Developer (user_7) id: {dev7.pk}")
        self.stdout.write(f"  Developer (user_8) id: {dev8.pk}")
        self.stdout.write(
            f"  user_7 metrics  : fixed={dev7_summary['fixed_count']}, "
            f"reopened={dev7_summary['reopened_count']}, "
            f"classification={dev7_summary['classification_label']}"
        )
