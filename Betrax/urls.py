from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    DefectListView, DefectDetailView, AcceptDefectView, AssignDefectView, 
    FixDefectView, ResolveDefectView, 
    ProductListCreateView, RejectDefectView, ReopenDefectView, ReassignDefectView # <-- Added new views
)

urlpatterns = [
    path("login/", obtain_auth_token),
    
    path("products/", ProductListCreateView.as_view()),
    
    path("defects/", DefectListView.as_view()),
    path("defects/<int:pk>/", DefectDetailView.as_view()),
    path("defects/<int:pk>/accept/", AcceptDefectView.as_view()),
    path("defects/<int:pk>/assign/", AssignDefectView.as_view()),
    path("defects/<int:pk>/fix/", FixDefectView.as_view()),
    path("defects/<int:pk>/resolve/", ResolveDefectView.as_view()),
    
    path("defects/<int:pk>/reject/", RejectDefectView.as_view()),
    path("defects/<int:pk>/reopen/", ReopenDefectView.as_view()),
    path("defects/<int:pk>/reassign/", ReassignDefectView.as_view()),
]