import pytest
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def sample_cv_text():
    """Sample CV text for testing."""
    return """
John Smith
john.smith@email.com | +1 555 123 4567 | New York, NY
LinkedIn: linkedin.com/in/johnsmith | GitHub: github.com/johnsmith

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years of experience in Python, JavaScript, and cloud technologies.
Passionate about building scalable applications and leading development teams.

EXPERIENCE

Senior Software Engineer | TechCorp Inc. | 2020 - Present
- Led development of microservices architecture serving 1M+ users
- Implemented CI/CD pipelines reducing deployment time by 60%
- Mentored junior developers and conducted code reviews

Software Engineer | StartupXYZ | 2018 - 2020
- Built REST APIs using Python and FastAPI
- Developed React frontend applications
- Managed AWS infrastructure using Terraform

EDUCATION

Master of Science in Computer Science | MIT | 2018
Bachelor of Science in Computer Science | Stanford University | 2016

SKILLS
Languages: Python, JavaScript, TypeScript, Go
Frameworks: React, FastAPI, Django, Node.js
Cloud: AWS, GCP, Docker, Kubernetes
Databases: PostgreSQL, MongoDB, Redis
Tools: Git, Jenkins, Terraform

CERTIFICATIONS
- AWS Solutions Architect Professional
- Google Cloud Professional Developer
"""


@pytest.fixture
def sample_cv_chunks():
    """Sample CV chunks for testing."""
    return [
        {
            "content": "John Smith - Senior Software Engineer with 5+ years of experience in Python",
            "metadata": {
                "cv_id": "cv_001",
                "filename": "john_smith.pdf",
                "candidate_name": "John Smith",
                "section_type": "summary",
            },
            "score": 0.92,
        },
        {
            "content": "Experience at TechCorp Inc. - Led development of microservices architecture",
            "metadata": {
                "cv_id": "cv_001",
                "filename": "john_smith.pdf",
                "candidate_name": "John Smith",
                "section_type": "experience",
            },
            "score": 0.88,
        },
    ]
