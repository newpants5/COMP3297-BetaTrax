from rest_framework import serializers
from .models import DefectReport

class DefectListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = ["id", "title", "status", "submission_date", "tester_id"]

class DefectDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = "__all__"

class DefectAcceptSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(choices=DefectReport.Severity.choices)
    priority = serializers.ChoiceField(choices=DefectReport.Priority.choices)
