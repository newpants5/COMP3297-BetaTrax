from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import tenant_context

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
    help = (
        "Create comparison metric data for two existing developers in a tenant: "
        "one with a low reopened/fixed ratio and one with a high reopened/fixed ratio."
    )

    def add_arguments(self, parser):
        parser.add_argument("--schema", default="demo")
        parser.add_argument("--good-dev", default="DEV-001")
        parser.add_argument("--poor-dev", default="DEV-002")

    def handle(self, *args, **options):
        schema_name = options["schema"]
        good_employee_id = options["good_dev"]
        poor_employee_id = options["poor_dev"]

        try:
            tenant = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist as exc:
            raise CommandError(
                f'Tenant schema "{schema_name}" does not exist.'
            ) from exc

        domain = Domain.objects.filter(tenant=tenant).order_by("-is_primary", "domain").first()

        with tenant_context(tenant):
            good_dev = self._get_developer(good_employee_id)
            poor_dev = self._get_developer(poor_employee_id)

            owner_employee, _ = Employee.objects.get_or_create(
                employee_id="PO200",
                defaults={"name": "Metrics Owner", "email": "metrics-owner@example.com"},
            )
            product_owner, _ = ProductOwner.objects.get_or_create(employee=owner_employee)
            product, _ = Product.objects.get_or_create(
                productId="MTRX002",
                defaults={"name": "Metric Comparison Product", "owner": product_owner},
            )
            if product.owner_id != product_owner.pk:
                product.owner = product_owner
                product.save(update_fields=["owner"])

            self._seed_good_scenario(product, good_dev)
            self._seed_poor_scenario(product, poor_dev)

            good_summary = good_dev.effectiveness_summary()
            poor_summary = poor_dev.effectiveness_summary()

        self.stdout.write(self.style.SUCCESS("Comparison metric data is ready."))
        self.stdout.write(f"Tenant schema: {tenant.schema_name}")
        if domain:
            self.stdout.write(f"Tenant domain: {domain.domain}")
        self.stdout.write("")
        self.stdout.write(
            f"{good_employee_id}: fixed={good_summary['fixed_count']}, "
            f"reopened={good_summary['reopened_count']}, "
            f"classification={good_summary['classification_label']}"
        )
        self.stdout.write(
            f"{poor_employee_id}: fixed={poor_summary['fixed_count']}, "
            f"reopened={poor_summary['reopened_count']}, "
            f"classification={poor_summary['classification_label']}"
        )
        self.stdout.write("")
        self.stdout.write("Check their ratios from the API using their developer primary keys:")
        self.stdout.write(f"- {good_employee_id} -> developer pk {good_dev.pk}")
        self.stdout.write(f"- {poor_employee_id} -> developer pk {poor_dev.pk}")
        if domain:
            self.stdout.write("")
            self.stdout.write("Example requests:")
            self.stdout.write(
                f'curl -H "Authorization: Token <your-token>" -H "Host: {domain.domain}" '
                f'http://127.0.0.1:8001/api/developers/{good_dev.pk}/effectiveness/'
            )
            self.stdout.write(
                f'curl -H "Authorization: Token <your-token>" -H "Host: {domain.domain}" '
                f'http://127.0.0.1:8001/api/developers/{poor_dev.pk}/effectiveness/'
            )

    def _get_developer(self, employee_id):
        try:
            employee = Employee.objects.get(employee_id=employee_id)
        except Employee.DoesNotExist as exc:
            raise CommandError(
                f'No Employee with employee_id "{employee_id}" exists in this tenant.'
            ) from exc

        try:
            return Developer.objects.get(employee=employee)
        except Developer.DoesNotExist as exc:
            raise CommandError(
                f'Employee "{employee_id}" exists but is not linked to a Developer role.'
            ) from exc

    def _seed_good_scenario(self, product, developer):
        # 32 fixed, 0 reopened -> ratio 0.0 -> Good
        for index in range(1, 33):
            defect = self._upsert_defect(
                title=f"Metric Good Demo #{index} for {developer.employee.employee_id}",
                product=product,
                developer=developer,
                status=DefectReport.Status.RESOLVED,
            )
            self._ensure_metric_event(defect, developer, DeveloperMetricEvent.EventType.FIXED)

    def _seed_poor_scenario(self, product, developer):
        # 24 fixed, 6 reopened -> ratio 0.25 -> Poor
        for index in range(1, 19):
            defect = self._upsert_defect(
                title=f"Metric Poor Fixed #{index} for {developer.employee.employee_id}",
                product=product,
                developer=developer,
                status=DefectReport.Status.RESOLVED,
            )
            self._ensure_metric_event(defect, developer, DeveloperMetricEvent.EventType.FIXED)

        for index in range(1, 7):
            defect = self._upsert_defect(
                title=f"Metric Poor Reopened #{index} for {developer.employee.employee_id}",
                product=product,
                developer=developer,
                status=DefectReport.Status.REOPENED,
            )
            self._ensure_metric_event(defect, developer, DeveloperMetricEvent.EventType.FIXED)
            self._ensure_metric_event(defect, developer, DeveloperMetricEvent.EventType.REOPENED)

    def _upsert_defect(self, title, product, developer, status):
        defect, _ = DefectReport.objects.get_or_create(
            title=title,
            defaults={
                "product": product,
                "product_version": "1.0",
                "description": "Seeded defect for metric comparison demo.",
                "steps_to_reproduce": "1. Open the app\n2. Observe the issue",
                "tester_id": "BT200",
                "tester_email": "tester@example.com",
                "status": status,
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
        if defect.status != status:
            defect.status = status
            changed_fields.append("status")
        if changed_fields:
            defect.save(update_fields=changed_fields)

        return defect

    def _ensure_metric_event(self, defect, developer, event_type):
        if not defect.metric_events.filter(
            developer=developer,
            event_type=event_type,
        ).exists():
            DeveloperMetricEvent.objects.create(
                developer=developer,
                defect=defect,
                event_type=event_type,
            )
