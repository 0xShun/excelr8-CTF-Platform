from django.urls import path
from . import views

app_name = 'ctf'

urlpatterns = [
    path('register/team/', views.team_register, name='team_register'),
    path('challenges/', views.challenge_list, name='challenge_list'),
    path('challenges/<int:pk>/', views.challenge_detail, name='challenge_detail'),
    path('hints/unlock/<int:hint_id>/', views.unlock_hint, name='unlock_hint'),
] 