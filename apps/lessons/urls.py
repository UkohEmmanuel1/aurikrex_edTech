from django.urls import path
from .views import (
    LessonListView, 
    LessonDetailView, 
    GenerateLessonView, 
    UpdateLessonProgressView
)

urlpatterns = [
    path('', LessonListView.as_view(), name='lesson-list'),
    path('<uuid:id>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('generate/', GenerateLessonView.as_view(), name='lesson-generate'),
    path('<uuid:id>/progress/', UpdateLessonProgressView.as_view(), name='lesson-progress'),
]