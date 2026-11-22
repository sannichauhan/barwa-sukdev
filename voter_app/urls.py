from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import survey_view, CandidateViewSet, NewVoteViewSet, VoterViewSet


router = DefaultRouter()
router.register(r"voters", VoterViewSet, basename="voter")
router.register(r"candidates", CandidateViewSet, basename="candidate")
router.register(r"votes", NewVoteViewSet, basename="newvote")

urlpatterns = [
    path('', views.voter_list_view, name='voter_list'),    
    path('edit/<int:pk>/', views.voter_update_view, name='voter_update'),    
    path('vote/login/', views.voter_login, name='voter_login'),
    path('vote/panel/', views.voting_panel, name='voting_panel'),
    path('vote/results/', views.election_results, name='election_results'),
    path('vote/logout/', views.voter_logout, name='voter_logout'),
    path('survey/', survey_view, name='survey'),
    path("api/", include(router.urls)),
]