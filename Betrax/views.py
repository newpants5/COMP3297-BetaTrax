from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from rest_framework.permissions import IsAuthenticated

from .models import DefectReport, Product, Developer, Comment
from .serializers import (
    DefectListSerializer,
    DefectDetailSerializer,
    DefectAcceptSerializer,
    DefectAssignSerializer,
    ProductSerializer,
    CommentSerializer,
)
from .permissions import IsProductOwner, IsDeveloper, IsBetaTester, IsProductOwnerOrDeveloper


def send_status_notification(defect, old_status):
    if not defect.tester_email:
        return

    subject = f"BetaTrax: Defect #{defect.id} status changed to {defect.status}"
    body = (
        f"Hello,\n\n"
        f'The status of defect "{defect.title}" (ID: {defect.id}) '
        f"has changed\nfrom {old_status} to {defect.status}.\n\n"
        f"BetaTrax"
    )
    send_mail(subject, body, None, [defect.tester_email])


class DefectListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DefectReport.objects.all()

        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        product_id = self.request.query_params.get("product")
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DefectDetailSerializer
        return DefectListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsBetaTester()]
        return [IsAuthenticated()]


class DefectDetailView(generics.RetrieveAPIView):
    queryset = DefectReport.objects.all()
    serializer_class = DefectDetailSerializer
    permission_classes = [IsAuthenticated]


class AcceptDefectView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.NEW:
            return Response(
                {"error": "Only NEW defects can be accepted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DefectAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = defect.status
        defect.severity = serializer.validated_data["severity"]
        defect.priority = serializer.validated_data["priority"]
        defect.status = DefectReport.Status.OPEN
        defect.save()

        send_status_notification(defect, old_status)

        return Response(
            {
                "id": defect.id,
                "status": defect.status,
                "severity": defect.severity,
                "priority": defect.priority,
            }
        )


class AssignDefectView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.OPEN:
            return Response(
                {"error": "Only OPEN defects can be assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DefectAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = defect.status
        developer = get_object_or_404(
            Developer, pk=serializer.validated_data["developer_id"]
        )
        defect.assigned_developer = developer
        defect.status = DefectReport.Status.ASSIGNED
        defect.save()

        send_status_notification(defect, old_status)

        return Response(
            {
                "id": defect.id,
                "status": defect.status,
                "assigned_developer": defect.assigned_developer.id,
            }
        )


class FixDefectView(APIView):
    permission_classes = [IsDeveloper]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.ASSIGNED:
            return Response(
                {"error": "Only ASSIGNED defects can be marked as Fixed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = defect.status
        defect.status = DefectReport.Status.FIXED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({"id": defect.id, "status": defect.status})


class ResolveDefectView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.FIXED:
            return Response(
                {"error": "Only FIXED defects can be marked as Resolved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = defect.status
        defect.status = DefectReport.Status.RESOLVED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({"id": defect.id, "status": defect.status})


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsProductOwner()]
        return [IsAuthenticated()]


class RejectDefectView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.NEW:
            return Response(
                {"error": "Only NEW defects can be rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = defect.status
        defect.status = DefectReport.Status.REJECTED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({"id": defect.id, "status": defect.status})


class ReopenDefectView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.RESOLVED:
            return Response(
                {"error": "Only RESOLVED defects can be reopened"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = defect.status
        defect.status = DefectReport.Status.REOPENED
        defect.save()

        send_status_notification(defect, old_status)

        return Response({"id": defect.id, "status": defect.status})


class ReassignDefectView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status not in [DefectReport.Status.OPEN, DefectReport.Status.ASSIGNED]:
            return Response(
                {"error": "Only OPEN or ASSIGNED defects can be reassigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DefectAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = defect.status
        developer = get_object_or_404(
            Developer, pk=serializer.validated_data["developer_id"]
        )

        defect.assigned_developer = developer
        defect.status = DefectReport.Status.ASSIGNED
        defect.save()

        send_status_notification(defect, old_status)

        return Response(
            {
                "id": defect.id,
                "status": defect.status,
                "assigned_developer": defect.assigned_developer.id,
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )
    
class DefectCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsProductOwnerOrDeveloper]

    def get_queryset(self):
        defect = get_object_or_404(DefectReport, pk=self.kwargs["pk"])
        return Comment.objects.filter(defect=defect).order_by("creation_date")

    def perform_create(self, serializer):
        defect = get_object_or_404(DefectReport, pk=self.kwargs["pk"])
        serializer.save(defect=defect)

class CommentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsProductOwnerOrDeveloper]

class MarkDuplicateView(APIView):
    permission_classes = [IsProductOwner]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)
        
        parent_id = request.data.get('duplicate_of')

        if defect.status != DefectReport.Status.NEW:
            return Response(
                {"error": "Only NEW defects can be marked as duplicates"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if not parent_id:
            return Response(
                {"error": "The ID of the parent defect (duplicate_of) is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parent_defect = get_object_or_404(DefectReport, pk=parent_id)

        old_status = defect.status
        defect.duplicate_of = parent_defect
        defect.status = DefectReport.Status.DUPLICATE
        defect.save()

        send_status_notification(defect, old_status)

        return Response({
            "id": defect.id, 
            "status": defect.status, 
            "duplicate_of": parent_defect.id
        })
    
class CannotReproduceView(APIView):
    permission_classes = [IsDeveloper]

    def patch(self, request, pk):
        defect = get_object_or_404(DefectReport, pk=pk)

        if defect.status != DefectReport.Status.ASSIGNED:
            return Response(
                {"error": "Only ASSIGNED defects can be marked as Cannot Reproduce"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = defect.status
        defect.status = DefectReport.Status.CANNOT_REPRODUCE
        defect.save()

        send_status_notification(defect, old_status)

        return Response({"id": defect.id, "status": defect.status})