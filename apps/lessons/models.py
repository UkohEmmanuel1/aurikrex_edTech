from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Lesson(models.Model):
    """
    Stores the static AI-generated FalkeAI lesson content.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=255)
    subject = models.CharField(max_length=100)
    level = models.CharField(max_length=50)
    
    # FalkeAI JSON structure
    content = models.JSONField() 
    estimated_minutes = models.IntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('topic', 'subject', 'level')

    def __str__(self):
        return f"{self.subject} - {self.topic} ({self.level})"


class LessonProgress(models.Model):
    """
    Tracks a specific user's mastery and progress on a lesson.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')
    
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user.email} - {self.lesson.topic}"