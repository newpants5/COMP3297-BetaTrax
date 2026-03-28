from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .models import DefectReport
from .serializers import DefectListSerializer, DefectDetailSerializer, DefectAcceptSerializer, DefectAssignSerializer

from rest_framework import generics

def send_status_notification(defect, old_status):
    if not defect.tester_email:
        return

    subject = f"BetaTrax: Defect #{defect.id} status changed to {defect.status}"
    body = (
        f"Hello,\n\n"
        f"The status of defect \"{defect.title}\" (ID: {defect.id}) "
        f"has changed from {old_status} to {defect.status}.\n\n"
        f"— BetaTrax"
    )
    send_mail(subject, body, None, [defect.tester_email])

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

        old_status = defect.status
        defect.severity = serializer.validated_data["severity"]
        defect.priority = serializer.validated_data["priority"]
        defect.status = DefectReport.Status.OPEN
        defect.save()

        send_status_notification(defect, old_status)

        return Response({
            "id": defect.id,
            "status": defect.status,
            "severity": defect.severity,
            "priority": defect.priority
        })


class AssignDefectView(APIView):
    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.OPEN:
            return Response(
                {"error": "Only OPEN defects can be assigned"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DefectAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = defect.status
        developer = get_object_or_404(User, pk=serializer.validated_data["developer_id"])
        defect.assigned_developer = developer
        defect.status = DefectReport.Status.ASSIGNED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({
            "id": defect.id,
            "status": defect.status,
            "assigned_developer": defect.assigned_developer.username
        })


class FixDefectView(APIView):
    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.ASSIGNED:
            return Response(
                {"error": "Only ASSIGNED defects can be marked as Fixed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = defect.status
        defect.status = DefectReport.Status.FIXED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({
            "id": defect.id,
            "status": defect.status
        })

class ResolveDefectView(APIView):
    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.FIXED:
            return Response(
                {"error": "Only FIXED defects can be marked as Resolved"},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = defect.status
        defect.status = DefectReport.Status.RESOLVED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({
            "id": defect.id,
            "status": defect.status,
        })