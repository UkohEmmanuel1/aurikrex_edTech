from google import genai
from google.genai import types
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

class AIService:
    @staticmethod
    def generate_lesson_content(topic: str, subject: str, level: str) -> dict:
        try:
            # 1. Check for the API Key
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                logger.error("FalkeAI Service Error: GEMINI_API_KEY is missing in settings.py")
                return {"error": "AI Service unavailable. Please check server configuration."}
            
            # 2. Initialize the modern client
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            system_instruction = "You are FalkeAI, a context-aware academic curriculum designer. Your goal is Mastery."
            
            prompt = f"""
            Task: Generate a structured lesson resource.
            Subject: {subject}
            Topic: {topic.strip()}
            Target Level: {level}
            
            Requirements:
            1. Content must be academic and strictly educational.
            2. "retrieval_checkpoints" must be questions that force active recall.
            3. "prerequisites" must list concepts a student needs BEFORE this lesson.
            
            REQUIRED JSON STRUCTURE:
            {{
                "title": "Lesson Title",
                "subject": "{subject}",
                "topic": "{topic.strip()}",
                "level": "{level}",
                "objectives": ["obj1", "obj2"],
                "prerequisites": ["concept1", "concept2"],
                "core_concepts": ["key_term1", "key_term2"],
                "content_sections": [
                    {{
                        "heading": "Section 1",
                        "body_markdown": "Explanation...",
                        "key_takeaway": "Summary"
                    }}
                ],
                "examples": [
                    {{ "problem": "...", "solution": "...", "explanation": "..." }}
                ],
                "exercises": [
                    {{ "question": "...", "hint": "...", "answer": "..." }}
                ],
                "retrieval_checkpoints": ["Question 1?", "Question 2?"],
                "estimated_minutes": 20
            }}
            """

            # 3. Call the API with strict JSON formatting and System Instructions
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.7, # 0.7 gives a good balance of creativity and structure
                )
            )
            
            # 4. Parse the guaranteed JSON
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                logger.error(f"FalkeAI JSON Error: {response.text}")
                return {"error": "Failed to generate structured lesson."}

        except Exception as e:
            logger.error(f"FalkeAI Service Error: {str(e)}")
            return {"error": "AI Service unavailable. Please try again."}