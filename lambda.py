import os
import json
import uuid
import time
import datetime
from decimal import Decimal

import boto3

# ===== Config =====
DDB_TABLE = os.environ.get("DDB_TABLE", "AirQReadings")
S3_BUCKET = os.environ.get("S3_BUCKET", "iot-airq-accountID-eu-central-1")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DDB_TABLE)
s3 = boto3.client("s3")

def clean_keys(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k is None: 
                continue
            if isinstance(k, str) and k.strip() == "":
                continue
            out[k] = clean_keys(v)
        return out
    if isinstance(obj, list):
        return [clean_keys(x) for x in obj]
    return obj

def convert_floats(obj):
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(v) for v in obj]
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def lambda_handler(event, context):
    print("Lambda triggered with event:", event)

    msg = event.get("message", event)
    if isinstance(msg, str):
        try:
            msg = json.loads(msg)
        except Exception:
            msg = {"raw": msg}

    msg = clean_keys(msg)
    device_id = str(msg.get("device_id", "unknown"))

    now = datetime.datetime.utcnow()
    epoch_ms = int(time.time() * 1000)

    # 1) DynamoDB
    ddb_data = convert_floats(msg)
    table.put_item(
        Item={
            "device_id": device_id,
            "ts": epoch_ms,
            "data": ddb_data
        }
    )

    # 2) S3
    s3_key = (
        f"airq/year={now:%Y}/month={now:%m}/day={now:%d}/"
        f"device_id={device_id}/{uuid.uuid4()}.json"
    )
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(msg).encode("utf-8"),
        ContentType="application/json",
    )

    print("Wrote to DynamoDB and S3:", {"ddb_pk": device_id, "s3_key": s3_key})
    return {"status": "ok", "ddb_written": True, "s3_written": True, "s3_key": s3_key}
