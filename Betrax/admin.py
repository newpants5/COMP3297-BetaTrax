from django.contrib import admin

# Register your models here.
from .models import Product, DefectReport, Comment, Email

admin.site.register(Product)
admin.site.register(DefectReport)
admin.site.register(Comment)
admin.site.register(Email)