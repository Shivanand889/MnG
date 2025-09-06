from django.urls import path
from . import views

urlpatterns = [
    # POST endpoints (send access_token in request body)
    path('threads/<int:thread_id>/messages/', views.get_thread_messages, name='thread_messages'),
    path('threads/', views.get_user_threads, name='user_threads'),
    
    # Alternative GET endpoint using Authorization header
    # path('threads/header-auth/', views.get_user_threads_header_auth, name='user_threads_header'),
]