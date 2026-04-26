from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    DefectListView, DefectDetailView, AcceptDefectView, AssignDefectView,
    FixDefectView, ResolveDefectView,
    ProductListCreateView, RejectDefectView, ReopenDefectView,
    ReassignDefectView, LogoutView, DefectCommentListCreateView,
    CommentRetrieveUpdateDestroyView, MarkDuplicateView, CannotReproduceView,
    DeveloperEffectivenessView, DeveloperListView
)

urlpatterns = [
    path("login/", obtain_auth_token),
    path("logout/", LogoutView.as_view()),
    
    path("products/", ProductListCreateView.as_view()),
    path("developers/", DeveloperListView.as_view()),
    path("developers/<int:pk>/effectiveness/", DeveloperEffectivenessView.as_view()),
    
    path("defects/", DefectListView.as_view()),
    path("defects/<int:pk>/", DefectDetailView.as_view()),
    path("defects/<int:pk>/accept/", AcceptDefectView.as_view()),
    path("defects/<int:pk>/assign/", AssignDefectView.as_view()),
    path("defects/<int:pk>/fix/", FixDefectView.as_view()),
    path("defects/<int:pk>/resolve/", ResolveDefectView.as_view()),
    
    path("defects/<int:pk>/reject/", RejectDefectView.as_view()),
    path("defects/<int:pk>/reopen/", ReopenDefectView.as_view()),
    path("defects/<int:pk>/reassign/", ReassignDefectView.as_view()),
    path("defects/<int:pk>/comments/", DefectCommentListCreateView.as_view()),
    path("comments/<int:pk>/", CommentRetrieveUpdateDestroyView.as_view()),
    path("defects/<int:pk>/mark-duplicate/", MarkDuplicateView.as_view()),
    path("defects/<int:pk>/cannot-reproduce/", CannotReproduceView.as_view()),
]
