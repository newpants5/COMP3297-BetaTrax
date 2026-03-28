from django.urls import path

from .models import DefectReport
from .views import DefectListView, DefectDetailView, AcceptDefectView, AssignDefectView, FixDefectView, \
    ResolveDefectView

urlpatterns = [
    path("defects/", DefectListView.as_view()),
    path("defects/<int:pk>/", DefectDetailView.as_view()),
    path("defects/<int:pk>/accept/", AcceptDefectView.as_view()),
    path("defects/<int:pk>/assign/", AssignDefectView.as_view()),
    path("defects/<int:pk>/fix/", FixDefectView.as_view()),
    path("defects/<int:pk>/resolve/", ResolveDefectView.as_view()),
]
