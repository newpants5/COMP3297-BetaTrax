from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Product(models.Model):
  productId = models.CharField(max_length=10)
  name = models.CharField(max_length=200)

  def __str__(self):
    return  self.name

class DefectReport(models.Model):
  class Status(models.TextChoices):
    NEW = 'New', 'New'
    OPEN = 'Open', 'Open'
    ASSIGNED = 'Assigned', 'Assigned'
    FIXED    = 'Fixed',    'Fixed'
    RESOLVED = 'Resolved', 'Resolved'

  class Severity(models.TextChoices):
    CRITICAL = 'Critical', 'Critical'
    MAJOR    = 'Major',    'Major'
    MINOR    = 'Minor',    'Minor'
    LOW      = 'Low',      'Low'

  class Priority(models.TextChoices):
    CRITICAL = 'Critical', 'Critical'
    HIGH     = 'High',     'High'
    MEDIUM   = 'Medium',   'Medium'
    LOW      = 'Low',      'Low'

  product = models.ForeignKey(Product, on_delete=models.CASCADE)
  defect_id = models.CharField(max_length=10)
  product_version = models.CharField(max_length=50)
  title = models.CharField(max_length=200)
  description = models.TextField()
  steps_to_reproduce = models.TextField()
  tester_id = models.CharField(max_length=10)
  tester_email = models.EmailField(blank=True, null=True)
  submission_date = models.DateTimeField(auto_now_add=True)
  status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
  severity = models.CharField(max_length=20, choices=Severity.choices, blank=True)
  priority = models.CharField(max_length=20, choices=Priority.choices, blank=True)
  assigned_developer = models.ForeignKey(
    User, null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='assignedDefect'
  )

class Comment(models.Model):
  defect = models.ForeignKey(DefectReport, on_delete=models.CASCADE, related_name='comments')
  author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='comment_authored')
  comment_id = models.CharField(max_length=10)
  text = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)

class Email(models.Model):
  defect = models.ForeignKey(DefectReport, on_delete=models.CASCADE, related_name='emails')
  author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='email_sent')
  email_id = models.CharField(max_length=10)
  subject = models.CharField(max_length=200)
  body = models.TextField()
  date_sent = models.DateTimeField(auto_now_add=True)