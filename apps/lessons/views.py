from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Lesson, LessonProgress
from .serializers import (
    LessonSerializer, 
    GenerateLessonRequestSerializer, 
    LessonProgressSerializer
)
from apps.lessons.services.ai_services import AIService

class LessonListView(generics.ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

class LessonDetailView(generics.RetrieveDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

class GenerateLessonView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GenerateLessonRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        topic = serializer.validated_data['topic'].strip().title()
        subject = serializer.validated_data['subject'].strip().title()
        level = serializer.validated_data['level'].strip().upper()

        # Smart Caching Logic
        lesson, created = Lesson.objects.get_or_create(
            topic=topic,
            subject=subject,
            level=level,
            defaults={'content': {}}
        )

        if created or not lesson.content:
            ai_content = AIService.generate_lesson_content(topic, subject, level)
            
            if "error" in ai_content:
                lesson.delete()
                return Response(ai_content, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            lesson.content = ai_content
            lesson.estimated_minutes = ai_content.get('estimated_minutes', 15)
            lesson.save()

        # Initialize progress tracking
        LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        return Response(LessonSerializer(lesson).data, status=status.HTTP_201_CREATED)

class UpdateLessonProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, id):
        lesson = get_object_or_404(Lesson, id=id)
        progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        
        progress.is_completed = request.data.get('is_completed', progress.is_completed)
        progress.score = request.data.get('score', progress.score)
        progress.save()
        
        return Response(LessonProgressSerializer(progress).data, status=status.HTTP_200_OK)