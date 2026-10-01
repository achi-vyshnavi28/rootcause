"""DynamoDB run index / answer cache and S3 run archive, on moto (no AWS account needed). Uses a real saved run."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from backend.cloud.aws_runs import RunArchive, RunIndex, create_table, question_hash

RUN = json.loads((Path(__file__).resolve().parents[1] / "frontend" / "example_run.json").read_text(encoding="utf-8"))
T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def aws(monkeypatch):
    for k, v in {"AWS_DEFAULT_REGION": "ap-south-1", "AWS_ACCESS_KEY_ID": "t", "AWS_SECRET_ACCESS_KEY": "t"}.items():
        monkeypatch.setenv(k, v)
    with mock_aws():
        create_table("rootcause-runs", boto3.client("dynamodb"))
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="rootcause-runs", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
        yield RunIndex(boto3.resource("dynamodb").Table("rootcause-runs")), RunArchive("rootcause-runs", s3), s3


def test_question_hash_ignores_case_spacing_and_question_mark():
    assert question_hash("Why did orders drop in April 2018?", "olist") == question_hash("  why did ORDERS drop in april 2018 ", "olist")
    assert question_hash("Why did orders drop?", "olist") != question_hash("Why did orders drop?", "olist_lab")


def test_same_question_hits_the_cache_until_it_expires(aws):
    index, _, _ = aws
    index.put(RUN, now=T0)
    hit = index.cached("why did the number of orders drop in april 2018 compared to march 2018", RUN["dataset"], now=T0 + timedelta(hours=3))
    assert hit and hit["run_id"] == RUN["run_id"] and hit["confidence"] == "high"
    assert index.cached(RUN["question"], RUN["dataset"], now=T0 + timedelta(days=2)) is None      # expired
    assert index.cached(RUN["question"], "olist", now=T0 + timedelta(hours=1)) is None              # other dataset


def test_recent_runs_newest_first(aws):
    index, _, _ = aws
    index.put({**RUN, "run_id": "older"}, now=T0)
    index.put({**RUN, "run_id": "newer"}, now=T0 + timedelta(minutes=5))
    assert [r["run_id"] for r in index.recent(RUN["dataset"])] == ["newer", "older"]


def test_uuid_run_ids_from_postgres_are_stored_as_strings(aws):
    import uuid
    index, archive, _ = aws
    rid = uuid.UUID(RUN["run_id"])
    index.put({**RUN, "run_id": rid}, now=T0)
    assert index.recent(RUN["dataset"])[0]["run_id"] == str(rid)
    assert archive.put({**RUN, "run_id": rid})["uri"].endswith(f"{rid}.json")


def test_failed_runs_are_not_served_from_cache(aws):
    index, _, _ = aws
    index.put({**RUN, "status": "error"}, now=T0)
    assert index.cached(RUN["question"], RUN["dataset"], now=T0) is None


def test_archive_is_encrypted_and_round_trips(aws):
    _, archive, s3 = aws
    out = archive.put(RUN)
    key = f"runs/{RUN['dataset']}/{RUN['run_id']}.json"
    assert out["uri"] == f"s3://rootcause-runs/{key}" and "Signature" in out["url"]
    assert s3.head_object(Bucket="rootcause-runs", Key=key)["ServerSideEncryption"] == "AES256"
    back = archive.get(RUN["dataset"], RUN["run_id"])
    assert back["report"]["summary"] == RUN["report"]["summary"] and len(back["queries"]) == len(RUN["queries"])
