"""
Database models for Orcanos Performance Testing Tool
Using SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Account(Base):
    """Account model for storing Orcanos account details"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    url = Column(String(512), nullable=False)
    encrypted_password = Column(String(512), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    step_results = relationship("StepResult", back_populates="account")


class Scenario(Base):
    """Test scenario model"""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(1024))
    steps = Column(JSON, nullable=False)  # Array of step definitions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TestRun(Base):
    """Test run model"""
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, default=0)
    scenario_name = Column(String(255))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50))  # 'pass', 'warning', 'critical'

    step_results = relationship("StepResult", back_populates="test_run")


class StepResult(Base):
    """Step result model"""
    __tablename__ = "step_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    step_name = Column(String(255), nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    status = Column(String(50))  # 'pass', 'warning', 'critical'
    error_message = Column(String(1024))

    # Relationships
    test_run = relationship("TestRun", back_populates="step_results")
    account = relationship("Account", back_populates="step_results")
