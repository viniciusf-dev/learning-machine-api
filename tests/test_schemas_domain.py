"""
Tests for src/domain/schemas.py

Covers: CrossSessionProfile dataclass fields and defaults.
"""

from src.domain.schemas import CrossSessionProfile


class TestCrossSessionProfile:
    def test_defaults_are_none(self):
        p = CrossSessionProfile(user_id="u1")
        assert p.preferred_channel is None
        assert p.language is None
        assert p.timezone is None
        assert p.role is None
        assert p.company is None
        assert p.department is None
        assert p.communication_style is None
        assert p.topics_of_interest is None

    def test_set_fields(self):
        p = CrossSessionProfile(
            user_id="u1",
            preferred_channel="slack",
            language="portuguese",
            timezone="America/Sao_Paulo",
            role="Backend Engineer",
            company="OpenClaw",
            department="engineering",
            communication_style="casual",
            topics_of_interest=["python", "fastapi"],
        )
        assert p.preferred_channel == "slack"
        assert p.language == "portuguese"
        assert p.timezone == "America/Sao_Paulo"
        assert p.role == "Backend Engineer"
        assert p.company == "OpenClaw"
        assert p.department == "engineering"
        assert p.communication_style == "casual"
        assert p.topics_of_interest == ["python", "fastapi"]

    def test_metadata_descriptions_exist(self):
        """Every field must have a description metadata — Agno uses these for schema introspection."""
        import dataclasses

        for f in dataclasses.fields(CrossSessionProfile):
            if f.name in ("preferred_channel", "language", "timezone", "role",
                          "company", "department", "communication_style",
                          "topics_of_interest"):
                assert "description" in f.metadata, f"Field {f.name} missing description"
                assert len(f.metadata["description"]) > 5
