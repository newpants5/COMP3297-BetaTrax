from rest_framework import serializers
from .models import DefectReport, Product, Developer, Comment

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "defect", "author", "text", "creation_date"]
        read_only_fields = ["id", "creation_date", "defect"]
        
class DefectListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = ["id", "title", "status", "submission_date", "tester_id", "assigned_developer"]


class DefectDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    class Meta:
        model = DefectReport
        fields = "__all__"


class DefectAcceptSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(choices=DefectReport.Severity.choices)
    priority = serializers.ChoiceField(choices=DefectReport.Priority.choices)


class DefectAssignSerializer(serializers.Serializer):
    developer_id = serializers.IntegerField()

    def validate_developer_id(self, value):
        if not Developer.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Developer not found.")
        return value


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "productId", "name", "owner"]

