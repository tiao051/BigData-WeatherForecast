# HDFS Setup Guide

## Quick Start

### 1. Start HDFS Cluster + All Services

```powershell
# Start all services (HDFS + Kafka + MongoDB + Webapp)
docker-compose up -d

# Check HDFS status
docker-compose logs namenode datanode1 datanode2 datanode3
```

### 2. Initialize HDFS (Upload dataset & models)

Wait ~60 seconds for HDFS to be fully ready, then:

```powershell
# Run initialization script
.\scripts\init_hdfs.ps1
```

This script will:
- Create HDFS directories (`/dataset`, `/models`, `/predictions`)
- Upload `weather_dataset.csv` to HDFS
- Upload ML models to HDFS
- Verify files are uploaded correctly

### 3. Verify HDFS Web UI

Open browser: **http://localhost:9870**

Navigate to: **Utilities → Browse the file system**

You should see:
```
/dataset/
  └── weather_dataset.csv

/models/
  ├── weather/
  │   └── random_forest_model/
  └── amount_of_rain/
      └── logistic_regression_model/

/predictions/
  └── (empty, will be populated by consumer)
```

### 4. Start Producer

```powershell
docker-compose --profile producer up -d
```

### 5. Check Consumer Logs

```powershell
docker-compose logs webapp -f
```

Look for:
```
Loading weather model from HDFS: hdfs://namenode:9000/models/weather/random_forest_model
Loading rain model from HDFS: hdfs://namenode:9000/models/amount_of_rain/logistic_regression_model
HDFS: Saved 100 predictions to hdfs://namenode:9000/predictions/2025/10/25
```

---

## Manual HDFS Commands

### Browse files
```bash
docker exec namenode hdfs dfs -ls /
docker exec namenode hdfs dfs -ls /dataset
docker exec namenode hdfs dfs -ls /models
docker exec namenode hdfs dfs -ls /predictions
```

### Check file size
```bash
docker exec namenode hdfs dfs -du -h /dataset
docker exec namenode hdfs dfs -du -h /models
```

### Read file content (first 10 lines)
```bash
docker exec namenode hdfs dfs -cat /dataset/weather_dataset.csv | head -10
```

### Check HDFS health
```bash
docker exec namenode hdfs dfsadmin -report
```

### View replication status
```bash
docker exec namenode hdfs fsck / -files -blocks -locations
```

---

## Troubleshooting

### Issue: Models not loading from HDFS

**Solution 1: Disable HDFS temporarily**
```bash
# In .env file, change:
USE_HDFS=false

# Restart webapp
docker-compose restart webapp
```

**Solution 2: Re-upload models**
```powershell
# Delete old models
docker exec namenode hdfs dfs -rm -r /models

# Re-run init script
.\scripts\init_hdfs.ps1
```

### Issue: HDFS Web UI not accessible

```bash
# Check NameNode logs
docker logs namenode

# Check if port 9870 is open
netstat -ano | findstr 9870

# Restart NameNode
docker-compose restart namenode
```

### Issue: DataNode not connecting

```bash
# Check DataNode logs
docker logs datanode1
docker logs datanode2  
docker logs datanode3

# Restart all DataNodes
docker-compose restart datanode1 datanode2 datanode3
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│         HDFS CLUSTER (3 nodes)          │
│                                         │
│  NameNode (namenode:9000)               │
│  ├── DataNode1 (replica 1)              │
│  ├── DataNode2 (replica 2)              │
│  └── DataNode3 (replica 3)              │
│                                         │
│  Replication Factor: 2                  │
│  Block Size: 128MB                      │
└─────────────────────────────────────────┘
            ▲
            │ hdfs://namenode:9000
            │
    ┌───────┴───────┬────────────┐
    │               │            │
┌───▼────┐    ┌────▼───┐   ┌───▼────┐
│Producer│    │Consumer│   │ Webapp │
│(future)│    │ Loads  │   │(future)│
│        │    │ models │   │        │
│        │    │ Saves  │   │        │
│        │    │ preds  │   │        │
└────────┘    └────────┘   └────────┘
```

---

## Benefits of HDFS

- **Distributed Storage**: Data split across 3 DataNodes
- **Fault Tolerance**: Each file replicated 2x
- **Scalability**: Add more DataNodes = more capacity
- **Centralized Models**: 1 source of truth for ML models
- **Easy Updates**: Update model without Docker rebuild
- **Analytics Ready**: Predictions saved as Parquet for Spark queries

---

## Next Steps (Optional Improvements)

1. **Upload dataset from Producer via HDFS**
   - Read CSV from HDFS instead of local file
   
2. **Webapp analytics from HDFS**
   - Query predictions from HDFS Parquet files
   - Use Spark SQL for aggregations

3. **Increase replication**
   - Change `HDFS_CONF_dfs_replication=3` for 3x redundancy

4. **Add more DataNodes**
   - Scale horizontally with more nodes
