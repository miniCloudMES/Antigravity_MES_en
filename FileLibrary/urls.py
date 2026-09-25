from django.urls import path
from . import views

app_name = 'filelibrary'

urlpatterns = [
    path('', views.file_library_list, name='file-library-list'),
    path('upload/', views.file_upload, name='file-upload'),
    path('chunk-status/', views.chunk_status, name='chunk-status'),
    path('chunk-upload/', views.chunk_upload, name='chunk-upload'),
    path('categories/create-ajax/', views.category_create_ajax, name='file-category-create-ajax'),
    path('<int:pk>/edit/', views.file_edit, name='file-edit'),
    path('<int:pk>/delete/', views.file_delete, name='file-delete'),
    path('retry-transcode/', views.retry_transcode, name='retry-transcode'),
    path('retry-transcode/<int:pk>/', views.retry_transcode, name='retry-transcode-one'),
    path('<int:pk>/download/', views.file_download, name='file-download'),
    path('<int:pk>/standard-download/', views.file_standard_download, name='file-standard-download'),
    path('<int:pk>/play/', views.file_video_play, name='file-video-play'),
    path('<int:pk>/preview/', views.file_preview, name='file-preview'),
    path('categories/', views.category_list, name='file-category-list'),
    path('categories/create/', views.category_create, name='file-category-create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='file-category-edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='file-category-delete'),
]
