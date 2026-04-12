from django.db import models
from django.core.exceptions import ValidationError


class Employee(models.Model):
    employee_id = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name


class EmployeeRole(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='roles',
    )

    def __str__(self):
        return f"{self.__class__.__name__}: {self.employee.name}"


class Developer(EmployeeRole):
    pass


class ProductOwner(EmployeeRole):
    pass


class Product(models.Model):
    productId = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        ProductOwner,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='owned_products',
    )

    def __str__(self):
        return self.name


class DefectReport(models.Model):
    class Status(models.TextChoices):
        NEW              = 'NEW',              'New'
        OPEN             = 'OPEN',             'Open'
        REJECTED         = 'REJECTED',         'Rejected'
        DUPLICATE        = 'DUPLICATE',        'Duplicate'
        ASSIGNED         = 'ASSIGNED',         'Assigned'
        CANNOT_REPRODUCE = 'CANNOT_REPRODUCE', 'Cannot Reproduce'
        FIXED            = 'FIXED',            'Fixed'
        REOPENED         = 'REOPENED',         'Reopened'
        RESOLVED         = 'RESOLVED',         'Resolved'

    class Severity(models.TextChoices):
        CRITICAL = 'CRITICAL', 'Critical'
        MAJOR    = 'MAJOR',    'Major'
        MINOR    = 'MINOR',    'Minor'
        LOW      = 'LOW',      'Low'

    class Priority(models.TextChoices):
        CRITICAL = 'CRITICAL', 'Critical'
        HIGH     = 'HIGH',     'High'
        MEDIUM   = 'MEDIUM',   'Medium'
        LOW      = 'LOW',      'Low'

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='defect_reports',
    )
    product_version = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField()
    steps_to_reproduce = models.TextField()
    tester_id = models.CharField(max_length=50)
    tester_email = models.EmailField(blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )
    severity = models.CharField(max_length=20, choices=Severity.choices, blank=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, blank=True)
    duplicate_of = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicates',
    )
    assigned_developer = models.ForeignKey(
        Developer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_defects',
    )

    def clean(self):
        if self.status == self.Status.DUPLICATE and self.duplicate_of is None:
            raise ValidationError(
                {'duplicate_of': 'duplicate_of must be set when status is DUPLICATE.'}
            )
        if self.duplicate_of is not None and self.duplicate_of == self:
            raise ValidationError(
                {'duplicate_of': 'A defect report cannot be a duplicate of itself.'}
            )

    def __str__(self):
        return self.title


class Comment(models.Model):
    defect = models.ForeignKey(
        DefectReport, on_delete=models.CASCADE, related_name='comments'
    )
    author = models.ForeignKey(
        EmployeeRole, on_delete=models.CASCADE, related_name='comments'
    )
    text = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on '{self.defect}' by {self.author}"


class EmailMessage(models.Model):
    defect = models.ForeignKey(
        DefectReport, on_delete=models.CASCADE, related_name='email_messages'
    )
    author = models.ForeignKey(
        EmployeeRole, on_delete=models.CASCADE, related_name='email_messages'
    )
    recipient_address = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject