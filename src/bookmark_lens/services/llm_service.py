"""
LLM service for Smart Mode enhancements.

Uses LiteLLM to generate summaries, tags, and topics.
"""

import logging
import json
from typing import Optional, List
from dataclasses import dataclass

from litellm import completion

from ..config import Config

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result from summary generation."""
    short: str  # 1-2 sentences, ~50 words
    long: str   # 1 paragraph, ~150 words


class LLMService:
    """Service for LLM-powered enhancements."""
    
    def __init__(self, config: Config):
        """
        Initialize LLM service.
        
        Args:
            config: Application configuration with LLM settings
        """
        self.model = config.llm_model
        self.api_key = config.llm_api_key
        self.api_base = config.llm_api_base
        self.temperature = config.llm_temperature
        
        logger.info(f"LLM service initialized with model: {self.model}")
    
    def summarize(self, text: str, title: Optional[str] = None) -> SummaryResult:
        """
        Generate short and long summaries of content.
        
        Args:
            text: Content to summarize (will be truncated to 3000 chars)
            title: Optional title for context
        
        Returns:
            SummaryResult with short and long summaries
        
        Raises:
            Exception: If LLM call fails
        """
        # Truncate text to save tokens
        truncated_text = text[:3000] if text else ""
        
        # Build prompt
        prompt = f"""Summarize this article in two formats.

Title: {title or "No title"}

Content (Markdown format):
{truncated_text}

The content is in Markdown format with headings (#), lists, and code blocks.

Provide:
1. SHORT: 1-2 sentences, maximum 50 words
2. LONG: 1 paragraph, maximum 150 words

Return ONLY valid JSON in this exact format:
{{"short": "...", "long": "..."}}"""
        
        # Call LLM
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            api_key=self.api_key,
            api_base=self.api_base
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Extract JSON (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        return SummaryResult(
            short=result["short"],
            long=result["long"]
        )
    
    def generate_tags(self, text: str, title: Optional[str] = None) -> List[str]:
        """
        Generate 3-5 relevant tags for content.
        
        Args:
            text: Content to analyze (will be truncated to 2000 chars)
            title: Optional title for context
        
        Returns:
            List of 3-5 lowercase tags
        
        Raises:
            Exception: If LLM call fails
        """
        # Truncate text to save tokens
        truncated_text = text[:2000] if text else ""
        
        # Build prompt
        prompt = f"""Generate 3-5 relevant tags for this article.

Title: {title or "No title"}

Content (Markdown format):
{truncated_text}

The content is in Markdown format. Pay attention to headings and code blocks.

Requirements:
- Return 3-5 tags only
- Tags should be lowercase
- Tags should be single words or short phrases (max 2 words)
- Focus on main topics and technologies mentioned

Return ONLY valid JSON array:
["tag1", "tag2", "tag3"]"""
        
        # Call LLM
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            api_key=self.api_key,
            api_base=self.api_base
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Extract JSON (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        tags = json.loads(content)
        
        # Normalize tags (lowercase, strip whitespace)
        return [tag.lower().strip() for tag in tags if tag.strip()]
    
    def classify_topic(self, text: str, title: Optional[str] = None) -> str:
        """
        Classify content into a high-level topic.
        
        Args:
            text: Content to classify (will be truncated to 1000 chars)
            title: Optional title for context
        
        Returns:
            Single topic string (e.g., "AI", "Programming", "Cloud")
        
        Raises:
            Exception: If LLM call fails
        """
        # Truncate text to save tokens (topic needs less context)
        truncated_text = text[:1000] if text else ""
        
        # Build prompt with predefined topics
        prompt = f"""Classify this article into ONE high-level topic.

Title: {title or "No title"}

Content (Markdown format):
{truncated_text}

The content is in Markdown format. Use headings to understand the main topic.

Choose the MOST relevant topic from this list:
- AI (artificial intelligence, machine learning, neural networks)
- Cloud (AWS, Azure, GCP, cloud computing, infrastructure)
- Programming (coding, software development, algorithms)
- Data (databases, data science, analytics, big data)
- Security (cybersecurity, encryption, authentication)
- DevOps (CI/CD, deployment, containers, kubernetes)
- Design (UI/UX, graphics, web design)
- Business (management, strategy, entrepreneurship)
- Science (research, physics, biology, chemistry)
- Other (if none of the above fit well)

Return ONLY the topic word (e.g., "AI" or "Programming")."""
        
        # Call LLM
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            api_key=self.api_key,
            api_base=self.api_base
        )
        
        # Parse response (just extract the topic word)
        content = response.choices[0].message.content.strip()
        
        # Clean up response (remove quotes, extra text)
        topic = content.replace('"', '').replace("'", "").strip()
        
        # If response is too long, take first word
        if len(topic.split()) > 2:
            topic = topic.split()[0]
        
        return topic
