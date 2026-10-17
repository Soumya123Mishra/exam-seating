from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('redirect-after-login/', views.redirect_after_login,name='redirect_after_login'),
    path("", views.dashboard,name='dashboard'),
    path("add-student/", views.add_student,name='add_student'),
    path("update-student/<str:student_id>/", views.update_student, name="update_student"),
    path("delete-student/<str:student_id>/", views.delete_student, name="delete_student"),
    path("update-room/<str:room_id>/", views.update_room, name="update_room"),
    path("delete-room/<str:room_id>/", views.delete_room, name="delete_room"),
    path("add-room/", views.add_room,name='add_room'),
    path("generate/", views.generate,name='generate'),
    path("download-pdf/", views.download_pdf, name="download_pdf"),
    path("view_seating/", views.view_seating,name='view_seating'),
    path('upload-students/', views.upload_students, name='upload_students'),
    path('school-settings/', views.school_settings, name='school_settings'),
    
]