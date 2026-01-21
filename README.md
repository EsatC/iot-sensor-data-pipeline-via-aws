## IoT Sensor Data Pipeline and Real-Time Dashboard using AWS IoT Core and AWS Lambda

### Description

This project demonstrates a complete IoT data ingestion and visualization pipeline using AWS services and open-source tools. It simulates real-time sensor data publishing, processing through AWS Lambda, storing in DynamoDB and S3, and visualizing via Grafana dashboards through Athena.

### Technologies Used

- **IoT Core**: Secure device connectivity and message routing.
- **AWS Lambda**: Serverless processing of incoming MQTT messages.
- **DynamoDB**: NoSQL storage of the latest device state.
- **Amazon S3**: Archival of time-partitioned sensor data.
- **AWS Glue**: Schema inference and Data Catalog creation.
- **Amazon Athena**: SQL-based querying on JSON-formatted data.
- **Grafana**: Dashboarding and visual monitoring using Athena as a data source.
- **Python**: Language used for publisher simulation and Lambda functions.

### Architecture Overview

```text
[publisher.py] --> [IoT Core MQTT] --> [Lambda] --> [DynamoDB (latest)]
                                         |
                                         v
                                      [S3 Bucket (raw JSON)]
                                         |
                                [Glue Crawler / Catalog]
                                         |
                                   [Athena Queries]
                                         |
                                   [Grafana Dashboard]
```

### Setup Steps

1. **IoT Core**
   - Create Thing, generate certificates, attach policy allowing MQTT connect/publish.

2. **Lambda Function**
   - Parses incoming JSON, writes to DynamoDB and to S3 with `year/month/day/device_id` partitioned folder structure.
   - Lambda Role has permissions for DynamoDB PutItem and S3 PutObject.

3. **DynamoDB Table**
   - Partition key: DeviceID.
   - Holds the latest record per device.

4. **S3 Bucket**
   - Receives raw JSON data from Lambda.
   - Partitioned by `year/month/day/device_id`.

5. **AWS Glue**
   - Crawler scans S3 data, registers schema into Data Catalog.
   - SerDe mapping used to handle keys like `CO(GT)` to `co_gt`.

6. **Athena**
   - Queries JSON data using SQL.
   - Uses Glue Data Catalog and partitions for performance.
   - Output directed to designated S3 folder.

7. **Grafana**
   - Connects to Athena with plugin.
   - Runs timestamp-based queries like:
     ```sql
     SELECT from_iso8601_timestamp(curr_timestamp) as time, co_gt as value
     FROM airqdb.clean_airq_data
     WHERE $__timeFilter(time)
     ```
   - Panels for: CO, NO2, Temperature, Humidity, etc.
   - Grafana panel screenshot: 
   <img width="1600" height="785" alt="image" src="https://github.com/user-attachments/assets/661b0f75-a085-415b-be61-2ff464268752" />


8. **Publisher Script**
   - Publishes lines from `AirQualityUCI.csv` over MQTT.
   - Requires certs and endpoint config.

### Notes

- `-200` values in dataset represent missing data; handled by publisher and mapped to `None`.
- Athena queries rely on valid timestamp parsing and correct field name mapping.
- For multi-device support, device_id is included in partitions and queries.
- Real-time visibility depends on Athena’s query interval and S3 write speed.
- Lambda logs can be inspected via CloudWatch.

### Sample Query (Grafana Panel)

```sql
WITH src AS (
  SELECT from_iso8601_timestamp(curr_timestamp) AS time,
         co_gt AS value
  FROM airqdb.clean_airq_data
)
SELECT time, value
FROM src
WHERE $__timeFilter(time)
ORDER BY time DESC
LIMIT 500;
```

