"""
Tests for HealthReport model.
"""
import pytest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import User, HealthReport


class TestHealthReportModel:
    """Test HealthReport model."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user."""
        user = User(
            name="Test User",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        return user

    def test_create_health_report(self, db_session, test_user):
        """Should create a health report."""
        report = HealthReport(
            user_id=test_user.id,
            report_date=date(2026, 3, 1),
            report_type="morning",
            content="# 晨间报告\n\n测试内容"
        )
        db_session.add(report)
        db_session.commit()

        assert report.id is not None
        assert report.user_id == test_user.id
        assert report.report_type == "morning"

    def test_unique_constraint(self, db_session, test_user):
        """Should enforce unique constraint on user_id + date + type."""
        report1 = HealthReport(
            user_id=test_user.id,
            report_date=date(2026, 3, 1),
            report_type="morning",
            content="Report 1"
        )
        db_session.add(report1)
        db_session.commit()

        report2 = HealthReport(
            user_id=test_user.id,
            report_date=date(2026, 3, 1),
            report_type="morning",
            content="Report 2"
        )
        db_session.add(report2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_different_types_same_date(self, db_session, test_user):
        """Should allow morning and evening reports on same date."""
        morning = HealthReport(
            user_id=test_user.id,
            report_date=date(2026, 3, 1),
            report_type="morning",
            content="Morning report"
        )
        evening = HealthReport(
            user_id=test_user.id,
            report_date=date(2026, 3, 1),
            report_type="evening",
            content="Evening report"
        )
        db_session.add_all([morning, evening])
        db_session.commit()

        assert morning.id != evening.id

    def test_default_values(self, db_session, test_user):
        """Should set default values."""
        report = HealthReport(
            user_id=test_user.id,
            report_date=date(2026, 3, 1),
            report_type="morning",
            content="Test"
        )
        db_session.add(report)
        db_session.commit()

        assert report.retry_count == 0
        assert report.generated_at is not None


class TestUserProfileFields:
    """Test User model profile fields."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_user_profile_fields(self, db_session):
        """User should have profile fields."""
        user = User(
            name="Test User",
            email="test2@example.com",
            hashed_password="hashed",
            age=30,
            gender="male",
            weight_kg=70.5
        )
        db_session.add(user)
        db_session.commit()

        assert user.age == 30
        assert user.gender == "male"
        assert user.weight_kg == 70.5
