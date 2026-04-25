from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework.authtoken.models import Token

from Betrax.models import (
    DefectReport,
    Developer,
    DeveloperMetricEvent,
    Employee,
    Product,
    ProductOwner,
)
from customers.models import Client, Domain


class Command(BaseCommand):
    help = "Create sample data for the developer effectiveness metric."

    def handle(self, *args, **options):
        for group_name in ["Product Owner", "Developer", "Beta Tester"]:
            Group.objects.get_or_create(name=group_name)

        user_model = get_user_model()
        api_user, created = user_model.objects.get_or_create(
            username="metricdemo",
            defaults={"email": "metricdemo@example.com"},
        )
        if created:
            api_user.set_password("betrax-demo-123")
            api_user.save()
        api_user.groups.add(Group.objects.get(name="Product Owner"))
        token, _ = Token.objects.get_or_create(user=api_user)

        tenant, created = Client.objects.get_or_create(
            schema_name="demo",
            defaults={
                "name": "Metric Demo Tenant",
                "paid_until": timezone.now().date(),
                "on_trial": True,
            },
        )
        if created and not tenant.name:
            tenant.name = "Metric Demo Tenant"
            tenant.save(update_fields=["name"])

        domain, _ = Domain.objects.get_or_create(
            domain="demo.localhost",
            defaults={"tenant": tenant, "is_primary": True},
        )
        if domain.tenant_id != tenant.pk or not domain.is_primary:
            domain.tenant = tenant
            domain.is_primary = True
            domain.save(update_fields=["tenant", "is_primary"])

        with tenant_context(tenant):
            owner_employee, _ = Employee.objects.get_or_create(
                employee_id="PO100",
                defaults={"name": "Metric Product Owner", "email": "owner@example.com"},
            )
            developer_employee, _ = Employee.objects.get_or_create(
                employee_id="DEV100",
                defaults={"name": "Metric Developer", "email": "developer@example.com"},
            )

            product_owner, _ = ProductOwner.objects.get_or_create(employee=owner_employee)
            developer, _ = Developer.objects.get_or_create(employee=developer_employee)

            product, _ = Product.objects.get_or_create(
                productId="METRIC1",
                defaults={"name": "Sprint 3 Metric Demo Product", "owner": product_owner},
            )
            if product.owner_id != product_owner.pk:
                product.owner = product_owner
                product.save(update_fields=["owner"])

            fixed_only_count = 23
            for index in range(1, fixed_only_count + 1):
                defect, _ = DefectReport.objects.get_or_create(
                    title=f"Sprint 3 Metric Demo Fixed #{index}",
                    defaults={
                        "product": product,
                        "product_version": "1.0",
                        "description": "Seeded defect for metric demo data.",
                        "steps_to_reproduce": "1. Open the app\n2. Observe the issue",
                        "tester_id": "BT100",
                        "tester_email": "tester@example.com",
                        "status": DefectReport.Status.RESOLVED,
                        "severity": DefectReport.Severity.MAJOR,
                        "priority": DefectReport.Priority.HIGH,
                        "assigned_developer": developer,
                    },
                )
                changed_fields = []
                if defect.product_id != product.pk:
                    defect.product = product
                    changed_fields.append("product")
                if defect.assigned_developer_id != developer.pk:
                    defect.assigned_developer = developer
                    changed_fields.append("assigned_developer")
                if defect.status != DefectReport.Status.RESOLVED:
                    defect.status = DefectReport.Status.RESOLVED
                    changed_fields.append("status")
                if changed_fields:
                    defect.save(update_fields=changed_fields)

                if not defect.metric_events.filter(
                    event_type=DeveloperMetricEvent.EventType.FIXED,
                    developer=developer,
                ).exists():
                    DeveloperMetricEvent.objects.create(
                        developer=developer,
                        defect=defect,
                        event_type=DeveloperMetricEvent.EventType.FIXED,
                    )

            reopened_defect, _ = DefectReport.objects.get_or_create(
                title="Sprint 3 Metric Demo Reopened",
                defaults={
                    "product": product,
                    "product_version": "1.0",
                    "description": "Seeded reopened defect for metric demo data.",
                    "steps_to_reproduce": "1. Open the app\n2. Observe the issue",
                    "tester_id": "BT100",
                    "tester_email": "tester@example.com",
                    "status": DefectReport.Status.REOPENED,
                    "severity": DefectReport.Severity.MAJOR,
                    "priority": DefectReport.Priority.HIGH,
                    "assigned_developer": developer,
                },
            )
            changed_fields = []
            if reopened_defect.product_id != product.pk:
                reopened_defect.product = product
                changed_fields.append("product")
            if reopened_defect.assigned_developer_id != developer.pk:
                reopened_defect.assigned_developer = developer
                changed_fields.append("assigned_developer")
            if reopened_defect.status != DefectReport.Status.REOPENED:
                reopened_defect.status = DefectReport.Status.REOPENED
                changed_fields.append("status")
            if changed_fields:
                reopened_defect.save(update_fields=changed_fields)

            for event_type in [
                DeveloperMetricEvent.EventType.FIXED,
                DeveloperMetricEvent.EventType.REOPENED,
            ]:
                if not reopened_defect.metric_events.filter(
                    event_type=event_type,
                    developer=developer,
                ).exists():
                    DeveloperMetricEvent.objects.create(
                        developer=developer,
                        defect=reopened_defect,
                        event_type=event_type,
                    )

            summary = developer.effectiveness_summary()

        self.stdout.write(self.style.SUCCESS("Metric demo data is ready."))
        self.stdout.write(f"Tenant schema: {tenant.schema_name}")
        self.stdout.write(f"Tenant domain: {domain.domain}")
        self.stdout.write(f"API user: metricdemo")
        self.stdout.write("Password: betrax-demo-123")
        self.stdout.write(f"Token: {token.key}")
        self.stdout.write(f"Developer id: {developer.pk}")
        self.stdout.write(
            "Endpoint: /api/developers/"
            f"{developer.pk}/effectiveness/"
        )
        self.stdout.write(
            "Summary: "
            f"fixed={summary['fixed_count']}, "
            f"reopened={summary['reopened_count']}, "
            f"classification={summary['classification_label']}"
        )
        self.stdout.write(
            'curl example: curl -H "Authorization: Token '
            f'{token.key}" -H "Host: {domain.domain}" '
            f"http://127.0.0.1:8000/api/developers/{developer.pk}/effectiveness/"
        )
