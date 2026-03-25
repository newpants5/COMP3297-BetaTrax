from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import DefectReport
from .serializers import DefectListSerializer, DefectDetailSerializer, DefectAcceptSerializer

from rest_framework import generics

class DefectListView(generics.ListAPIView):
    serializer_class = DefectListSerializer

    def get_queryset(self):
        queryset = DefectReport.objects.all()
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset
    
class DefectDetailView(generics.RetrieveAPIView):
    queryset = DefectReport.objects.all()
    serializer_class = DefectDetailSerializer

class AcceptDefectView(APIView):
    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.NEW:
            return Response(
                {"error": "Only NEW defects can be accepted"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DefectAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        defect.severity = serializer.validated_data["severity"]
        defect.priority = serializer.validated_data["priority"]
        defect.status = DefectReport.Status.OPEN
        defect.save()

        return Response({
            "id": defect.id,
            "status": defect.status,
            "severity": defect.severity,
            "priority": defect.priority
        })