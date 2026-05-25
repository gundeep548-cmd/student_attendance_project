from django.urls import path
from . import views

urlpatterns = [
    path('',views.started_page, name='startedpage'),
    path('homepage/', views.homepage, name='homepage'),
    path('login/', views.login_page, name='login'), 
    path('add-student/', views.add_student, name='add_student'), 
    path('save-student/', views.save_student, name='save_student'), 
    path('camera/', views.camera_page, name='camera'), 
    path('start-camera/', views.start_camera, name='start_camera'), 
    path('student-list/', views.attendance_report, name='attendance_report'), 
    path('attendance/', views.mark_attendance, name='mark_attendance'),
    path('view-attendance/', views.view_students_attendance, name='view_students_attendance'),
    path('attendance/manual/<int:student_id>/', views.mark_attendance_manual, name= 'mark_attendance_manual'),
    path('student-login-auth/', views.student_login_process, name= 'student_login_process'),
    path('student-profile/', views.student_profile, name= 'student_profile'),
    path('student-logout/', views.student_logout, name='student_logout'),
]