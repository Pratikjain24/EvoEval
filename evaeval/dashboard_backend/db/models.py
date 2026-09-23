"""FastAPI backend database models and DuckDB query adapter."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Run(Base):
    """Experiment run record."""
    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="completed")
    total_cycles = Column(Integer, default=5)
    mean_drift = Column(Float, default=0.0)
    mean_success_rate = Column(Float, default=0.0)
    mean_proxy_gap = Column(Float, default=0.0)
    total_cost_usd = Column(Float, default=0.0)
    run_dir = Column(String, nullable=False)


class CycleMetrics(Base):
    """Cycle-level metric aggregation per seed and group."""
    __tablename__ = "cycle_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, index=True, nullable=False)
    cycle = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    group = Column(String, index=True, nullable=False)
    success_rate = Column(Float, default=0.0)
    proxy_gap = Column(Float, default=0.0)
    safety_drift = Column(Float, default=0.0)
    violations_count = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)


class AuditLabel(Base):
    """Human double-blind annotation on sampled trajectory."""
    __tablename__ = "audit_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String, unique=True, index=True, nullable=False)
    run_id = Column(String, index=True, nullable=False)
    annotator_id = Column(String, nullable=False)
    is_violation = Column(Boolean, default=False)
    is_reward_hacked = Column(Boolean, default=False)
    failure_severity = Column(String, default="none")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Database session setup
DB_FILE = Path("experiments/dashboard.db")
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_FILE.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DuckDBTrajectoryQuery:
    """High-speed DuckDB analytics engine reading directly over trajectory JSONL files."""

    @staticmethod
    def query_events(
        jsonl_path: Path,
        event_type: Optional[str] = None,
        task_id: Optional[str] = None,
        group: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        if not jsonl_path.exists():
            return []
        con = duckdb.connect()
        try:
            # DuckDB read_json_auto handles JSONL streaming
            query = f"SELECT * FROM read_json_auto('{jsonl_path.as_posix()}') WHERE 1=1"
            if event_type:
                query += f" AND event_type = '{event_type}'"
            if task_id:
                query += f" AND task_id = '{task_id}'"
            if group:
                query += f" AND \"group\" = '{group}'"
            query += f" LIMIT {limit} OFFSET {offset}"

            df = con.execute(query).fetchdf()
            return df.to_dict(orient="records")
        except Exception:
            return []
        finally:
            con.close()
