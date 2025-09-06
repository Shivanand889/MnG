"""
URL configuration for Mng project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Users.views import *
from UserData.views import *
from groups.views import *
from Chat.views import chat, thread_messages
# from Chat.views import chat, thread_messages


urlpatterns = [
    path('admin/', admin.site.urls),
    path('generateOTP',generateOTP, name = 'generateOTP'),
    path('verifyOTP',verifyOTP, name = 'verifyOTP'),
    path('createUser',createUser, name = 'createUser'),
    path('addInterests/',addInterests, name = 'addInterests'),
    path('getInterest',getInterest, name = 'getInterest'),
    path('login',login, name = 'login'),
    path('loginByMobile',loginByMobile, name = 'loginByMobile'),
    path('profilePhoto',profilePhoto, name = 'profilePhoto'),
    path('updatePhoto',updatePhoto, name = 'updatePhoto'),
    path('getProfileData',getProfileData, name = 'getProfileData'),
    path('addInterest',addInterest, name = 'addInterest'),
    path('removeInterest',removeInterest, name = 'removeInterest'),
    path('getProfiles',getProfiles, name = 'getProfiles'),
    path('connect',connect, name = 'connect'),
    path('accept',accept, name = 'accept'),
    path("chat/<int:thread_id>/messages", thread_messages, name="thread_messages"),
    path('api/chat/', include('Chat.urls')),
    
    path('groups/', include('groups.urls')),
    path('interests/', get_interests, name='get_interests'),
    path('interests/create/', create_interest, name='create_interest'),
    
]
