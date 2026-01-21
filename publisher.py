import csv, json, time, datetime
from pathlib import Path
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

# =============================
#    CONFIG
# =============================
ENDPOINT  = "deviceID-ats.iot.eu-central-1.amazonaws.com"
CLIENT_ID = "dev1"
TOPIC     = "sensors/airq/dev1"
CSV_PATH  = Path(__file__).resolve().parent / "data" / "AirQualityUCI.csv"
SLEEP_SEC = 0.5
MAX_ROWS  = None   

BASE = Path(__file__).resolve().parents[1]
PATH_CERT = str(BASE / "certs" / "device.pem.crt")
PATH_KEY  = str(BASE / "certs" / "private.pem.key")
PATH_CA   = str(BASE / "certs" / "AmazonRootCA1.pem")


# =============================
#    HELPERS
# =============================
def parse_value(v):
    if v is None:
        return None

    s = str(v).strip()
    if s == "":
        return None

    
    s = s.replace(",", ".")

    try:
        f = float(s)
    except ValueError:
        return None  # if it not a number

    # sentinel -200 -> None 
    if abs(f + 200.0) < 1e-9:
        return None

    return f



# =============================
#    MAIN
# =============================
def main():
    # MQTT connection
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    mqtt_conn = mqtt_connection_builder.mtls_from_path(
        endpoint=ENDPOINT,
        cert_filepath=PATH_CERT,
        pri_key_filepath=PATH_KEY,
        client_bootstrap=client_bootstrap,
        ca_filepath=PATH_CA,
        client_id=CLIENT_ID,
        clean_session=True,
        keep_alive_secs=30
    )

    print("Connecting...")
    mqtt_conn.connect().result()
    print("Connected!")

    sent = 0
    with open(CSV_PATH, encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            now = datetime.datetime.utcnow()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            iso_ts  = now.isoformat() + "Z"

            record = {
                "device_id": CLIENT_ID,
                "date": date_str,
                "time": time_str,
                "timestamp": iso_ts,
            }

            for col, val in row.items():
                record[col] = parse_value(val)

            mqtt_conn.publish(
                topic=TOPIC,
                payload=json.dumps(record),
                qos=mqtt.QoS.AT_LEAST_ONCE
            )

            sent += 1
            if sent % 50 == 0:
                print(f"Sent {sent} rows...")

            if MAX_ROWS and sent >= MAX_ROWS:
                break

            time.sleep(SLEEP_SEC)

    mqtt_conn.disconnect().result()
    print(f"Disconnected. Total sent: {sent}")


if __name__ == "__main__":
    main()
