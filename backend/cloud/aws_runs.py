"""AWS for analysis runs: a DynamoDB run index that doubles as an answer cache, and an S3 archive of full run reports.

DynamoDB (NoSQL), single table:
    PK = DATASET#<dataset>   SK = RUN#<saved_at>#<run_id>   -> recent runs per dataset, newest first
    GSI1PK = Q#<question hash>  GSI1SK = <saved_at>         -> "was this exact question answered recently?"
    expires_at (TTL)                                         -> cache entries expire on their own
Asking the same question twice within the cache window returns the saved run instead of paying for new LLM calls.

S3: the full run (report, every SQL query, usage) as JSON at runs/<dataset>/<run_id>.json, server-side encrypted,
shared through short-lived presigned links. Enabled with ROOTCAUSE_DYNAMO_TABLE and ROOTCAUSE_S3_BUCKET.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Key


def question_hash(question: str, dataset: str) -> str:
    norm = re.sub(r"\s+", " ", question.strip().lower().rstrip("?"))
    return hashlib.sha256(f"{dataset}|{norm}".encode()).hexdigest()[:24]


def create_table(name, client):
    client.create_table(
        TableName=name, BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in ("PK", "SK", "GSI1PK", "GSI1SK")],
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        GlobalSecondaryIndexes=[{"IndexName": "GSI1", "Projection": {"ProjectionType": "ALL"},
                                 "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"},
                                               {"AttributeName": "GSI1SK", "KeyType": "RANGE"}]}])
    client.update_time_to_live(TableName=name, TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"})


class RunIndex:
    def __init__(self, table=None, cache_days: float = 1.0):
        self.table = table or boto3.resource("dynamodb").Table(os.environ["ROOTCAUSE_DYNAMO_TABLE"])
        self.cache_days = cache_days

    def put(self, run: dict, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        report = run.get("report") or {}
        run_id = str(run["run_id"])  # PostgreSQL returns UUID objects; DynamoDB stores strings
        self.table.put_item(Item={
            "PK": f"DATASET#{run['dataset']}", "SK": f"RUN#{now.isoformat()}#{run_id}",
            "GSI1PK": f"Q#{question_hash(run['question'], run['dataset'])}", "GSI1SK": now.isoformat(),
            "run_id": run_id, "question": run["question"], "dataset": run["dataset"], "status": run.get("status", "ok"),
            "summary": (report.get("summary") or "")[:1000], "confidence": report.get("confidence", "unknown"),
            "expires_at": int((now + timedelta(days=self.cache_days)).timestamp())})

    def recent(self, dataset: str, limit: int = 20) -> list[dict]:
        r = self.table.query(KeyConditionExpression=Key("PK").eq(f"DATASET#{dataset}") & Key("SK").begins_with("RUN#"),
                             ScanIndexForward=False, Limit=limit)
        return r["Items"]

    def cached(self, question: str, dataset: str, now: datetime | None = None) -> dict | None:
        """The newest successful run of the same question that has not expired (TTL deletion can lag, so check)."""
        now = now or datetime.now(timezone.utc)
        r = self.table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"Q#{question_hash(question, dataset)}"),
                             ScanIndexForward=False, Limit=5)
        for item in r["Items"]:
            if item["status"] == "ok" and int(item["expires_at"]) > now.timestamp():
                return item
        return None


class RunArchive:
    def __init__(self, bucket: str | None = None, client=None):
        self.bucket = bucket or os.environ["ROOTCAUSE_S3_BUCKET"]
        self.s3 = client or boto3.client("s3")

    def put(self, run: dict) -> dict:
        key = f"runs/{run['dataset']}/{str(run['run_id'])}.json"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=json.dumps(run, default=str).encode("utf-8"),
                           ContentType="application/json", ServerSideEncryption="AES256",
                           Metadata={"dataset": run["dataset"], "status": run.get("status", "ok")})
        return {"uri": f"s3://{self.bucket}/{key}", "url": self.link(key)}

    def link(self, key: str, seconds: int = 900) -> str:
        return self.s3.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=seconds)

    def get(self, dataset: str, run_id: str) -> dict:
        body = self.s3.get_object(Bucket=self.bucket, Key=f"runs/{dataset}/{run_id}.json")["Body"].read()
        return json.loads(body)
