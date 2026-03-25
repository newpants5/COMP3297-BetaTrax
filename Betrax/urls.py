from django.urls import path
from .views import DefectListView, DefectDetailView, AcceptDefectView

urlpatterns = [
    path("defects/", DefectListView.as_view()),
    path("defects/<int:pk>/", DefectDetailView.as_view()),
    path("defects/<int:pk>/accept/", AcceptDefectView.as_view()),
]
