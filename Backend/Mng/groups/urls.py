from django.urls import path
from . import views

urlpatterns = [
    path('gcreate/', views.create_group, name='create_group'),
    path('', views.get_groups, name='get_groups'),
    path('my/', views.get_user_groups, name='get_user_groups'),
    path('<int:group_id>/join/', views.join_group, name='join_group'),
    path('<int:group_id>/leave/', views.leave_group, name='leave_group'),
    path('<int:group_id>/messages/', views.get_group_messages, name='get_group_messages'),
    path('<int:group_id>/send/', views.send_group_message, name='send_group_message'),
    path('<int:group_id>/members/', views.get_group_members, name='get_group_members'),
]