from rest_framework import serializers
from .models import Lesson, LessonProgress

class GenerateLessonRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=255)
    subject = serializers.CharField(max_length=100)
    level = serializers.CharField(max_length=50)

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'topic', 'subject', 'level', 'content', 'estimated_minutes', 'created_at']

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'user', 'lesson', 'is_completed', 'score', 'last_accessed']
        read_only_fields = ['user', 'lesson', 'last_accessed']