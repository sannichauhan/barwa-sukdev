from django.urls import path
from . import views
from .views import survey_view

urlpatterns = [
    path('', views.voter_list_view, name='voter_list'),    
    path('edit/<int:pk>/', views.voter_update_view, name='voter_update'),    
    path('vote/login/', views.voter_login, name='voter_login'),
    path('vote/panel/', views.voting_panel, name='voting_panel'),
    path('vote/results/', views.election_results, name='election_results'),
    path('vote/logout/', views.voter_logout, name='voter_logout'),
    path('survey/', survey_view, name='survey'),
]