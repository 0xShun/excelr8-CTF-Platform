from django.urls import path
from . import views

app_name = 'ctf'

urlpatterns = [
    # Home and auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Teams
    path('team/register/', views.team_register, name='team_register'),
    path('team/join/', views.team_join, name='team_join'),
    path('team/leave/', views.leave_team, name='leave_team'),
    
    # Challenges
    path('challenges/', views.challenge_list, name='challenge_list'),
    path('challenges/<int:pk>/', views.challenge_detail, name='challenge_detail'),
    
    # Hints
    path('hints/unlock/<int:hint_id>/', views.unlock_hint, name='unlock_hint'),
    
    # Files
    path('files/download/<int:file_id>/', views.download_file, name='download_file'),
    
    # Scoreboard and stats
    path('scoreboard/', views.scoreboard, name='scoreboard'),
    path('scoreboard/json/', views.scoreboard_json, name='scoreboard_json'),
    path('scoreboard/timeseries/', views.scoreboard_timeseries_json, name='scoreboard_timeseries_json'),
    path('stats/', views.user_stats, name='user_stats'),
    
    # AJAX endpoints
    path('ajax/submit-flag/', views.submit_flag_ajax, name='submit_flag_ajax'),
    path('ajax/challenge-stats/<int:pk>/', views.challenge_stats_json, name='challenge_stats_json'),
] 