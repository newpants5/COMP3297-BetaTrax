from django.urls import path
from .views import DefectListView, DefectDetailView, AcceptDefectView, AssignDefectView, FixDefectView

urlpatterns = [
    path("defects/", DefectListView.as_view()),
    path("defects/<int:pk>/", DefectDetailView.as_view()),
    path("defects/<int:pk>/accept/", AcceptDefectView.as_view()),
    path("defects/<int:pk>/assign/", AssignDefectView.as_view()),
    path("defects/<int:pk>/fix/", FixDefectView.as_view()),
]
