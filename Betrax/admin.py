from django.contrib import admin

# Register your models here.
from .models import Product, DefectReport, Comment, EmailMessage

class DefectReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'severity', 'priority', 'tester_id', 'submission_date', 'assigned_developer')
    list_filter = ('status', 'severity', 'priority')

admin.site.register(Product)
admin.site.register(DefectReport, DefectReportAdmin)
admin.site.register(Comment)
admin.site.register(EmailMessage)