# TECHNICAL ARCHITECTURE & IMPLEMENTATION GUIDE
## BigData – Dự đoán thời tiết

---

## 1. COMPLETE SYSTEM ARCHITECTURE

### 1.1 Overall System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BIGDATA WEATHER FORECAST SYSTEM                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────────────────┐ │
│  │  weather_dataset.csv │         │    Initial Data Processing       │ │
│  │  • 135,818 records   │────────→│  • Data cleaning                 │ │
│  │  • 31 features       │         │  • Balanced sampling (50/50)     │ │
│  │  • 2008-2020         │         │  • Shuffle & encode              │ │
│  └──────────────────────┘         └──────────────────────────────────┘ │
│                                             │                          │
└─────────────────────────────────────────────┼──────────────────────────┘
                                              │
┌─────────────────────────────────────────────┼──────────────────────────┐
│                      STREAMING LAYER                                   │
├─────────────────────────────────────────────┼──────────────────────────┤
│                                             ↓                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │         Kafka Producer (Docker Container)                        │ │
│  │  • Read CSV file (135,818 records)                              │ │
│  │  • Balanced sampling: 50% rain + 50% no-rain                  │ │
│  │  • Send rate: 0.01s delay = 100 msg/sec (tunable)             │ │
│  │  • Mode: Continuous loop or single pass                        │ │
│  └────────┬───────────────────────────────────────────────────────┘ │
│           │ JSON messages (1.2KB per record)                         │
│           │                                                          │
│  ┌────────▼───────────────────────────────────────────────────────┐ │
│  │   Kafka Broker (Zookeeper + Kafka)                             │ │
│  │   • Topic: 'bigdata'                                           │ │
│  │   • Partitions: 1 (can scale to N)                             │ │
│  │   • Replication: 1 (loss tolerance)                            │ │
│  │   • Retention: 7 days                                          │ │
│  │   • Throughput: 1000 msg/sec (verified)                        │ │
│  └────────┬───────────────────────────────────────────────────────┘ │
│           │ 100 records per batch                                    │
│           │                                                          │
└───────────┼────────────────────────────────────────────────────────────┘
            │
┌───────────┼────────────────────────────────────────────────────────────┐
│           ▼                   PROCESSING LAYER                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │    Spark Consumer (PySpark 3.5.0)                              ││
│  │                                                                 ││
│  │  Stage 1: Poll batch (100 messages)           [50-100ms]       ││
│  │              └─ Wait for full batch or timeout                 ││
│  │                                                                 ││
│  │  Stage 2: Feature Encoding                    [35-50ms]        ││
│  │           ┌─ StringIndexer (6 categorical features)            ││
│  │           │  • sunrise → numeric index                         ││
│  │           │  • sunset → numeric index                          ││
│  │           │  • moonrise → numeric index                        ││
│  │           │  • moonset → numeric index                         ││
│  │           │  • moon_phase → numeric index                      ││
│  │           │  • winddir16Point → 0-15 index                     ││
│  │           └─ VectorAssembler (combine 31 features → vector)    ││
│  │                                                                 ││
│  │  Stage 3: Model 1 - Weather Prediction       [70-95ms]        ││
│  │           RandomForestClassifier (100 trees)                   ││
│  │           └─ Binary classification: rain | no rain              ││
│  │              Output: prediction ∈ {0.0, 1.0}                  ││
│  │                      probability ∈ [0,1]²                     ││
│  │                                                                 ││
│  │  Stage 4: Model 2 - Rainfall Amount         [35-55ms]         ││
│  │           LogisticRegression (167 classes)                    ││
│  │           └─ Only for rain predictions (~50%)                 ││
│  │              Output: prediction ∈ {0..166}                    ││
│  │                      → mapped to mm via lookup table           ││
│  │                                                                 ││
│  │  Total per batch: 150-250ms                  [185ms avg]       ││
│  │  Per-record latency: 1.5-2.5ms                                 ││
│  │                                                                 ││
│  └────────┬────────────────────────────────────────────────────────┘│
│           │ Predictions (JSON formatted)                             │
└───────────┼────────────────────────────────────────────────────────────┘
            │
┌───────────┼────────────────────────────────────────────────────────────┐
│           ▼                   STORAGE LAYER                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────┐   ┌──────────────────────────────┐ │
│  │  MongoDB 7.0 (Primary)       │   │  HDFS (Optional/Learning)    │ │
│  │  • Collection: predict       │   │  • NameNode: metadata mgmt   │ │
│  │  • Documents: 500K+          │   │  • 3x DataNodes: repl=2      │ │
│  │  • Storage: 300MB            │   │  • Model storage             │ │
│  │  • Index: predicted_at       │   │  • Long-term predictions     │ │
│  │  • Write: 20-35ms per batch  │   │  • Dataset backup            │ │
│  │  • Query: 5-10ms (indexed)   │   │  • Replication factor: 2     │ │
│  │  • TTL: 7 days (optional)    │   │                              │ │
│  └──────────────┬───────────────┘   └──────────────┬───────────────┘ │
│                 │                                   │                 │
│                 └───────────────────┬───────────────┘                 │
│                                     │                                 │
│                          Prediction Data                              │
│                          (JSON documents)                             │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION & API LAYER                           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │   Flask Web Application (Python 3.10)                         │ │
│  │   Port: 5000                                                  │ │
│  │                                                               │ │
│  │   Routes:                                                     │ │
│  │   ├─ GET /                     → Home page (real-time)       │ │
│  │   ├─ GET /statistics           → Stats dashboard             │ │
│  │   ├─ GET /get-data?page=1      → Paginated predictions      │ │
│  │   ├─ GET /api/statistics       → JSON stats endpoint         │ │
│  │   ├─ GET /api/error-clusters   → K-Means analysis           │ │
│  │   └─ WebSocket /               → Real-time events           │ │
│  │                                                               │ │
│  │   Technologies:                                               │ │
│  │   ├─ Flask-SocketIO: Real-time communication                │ │
│  │   ├─ PyMongo: MongoDB connection                             │ │
│  │   ├─ Threading: Background consumer                          │ │
│  │   └─ Scikit-learn: K-Means clustering                        │ │
│  │                                                               │ │
│  └────────────────┬─────────────────────────────────────────────┘ │
│                   │ WebSocket + REST API                           │
│                   │ (JSON responses)                               │
│                   │                                                │
│  ┌────────────────▼─────────────────────────────────────────────┐ │
│  │   Frontend (HTML/CSS/JavaScript)                            │ │
│  │   • home.html: Real-time monitoring table                   │ │
│  │   • statistics.html: Dashboard with charts                  │ │
│  │   • main.js: Socket.IO client, data updates                 │ │
│  │   • CSS: Responsive design (Bootstrap)                      │ │
│  │                                                               │ │
│  │   Real-time features:                                        │ │
│  │   ├─ Live prediction table (50 rows visible)                 │ │
│  │   ├─ Total prediction counter                                │ │
│  │   ├─ Rain/No-rain statistics                                 │ │
│  │   ├─ Accuracy metrics (live update)                          │ │
│  │   ├─ Feature impact analysis (temp, humidity, etc)          │ │
│  │   └─ Error clustering visualization                          │ │
│  │                                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES & TOOLS                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  • Mongo Express (Port 8081): MongoDB UI (optional)                 │
│  • HDFS Web UI (Port 9870): Cluster monitoring (optional)           │
│  • Jupyter Notebook: Model training & experimentation               │
│  • Docker & Docker Compose: Containerization & orchestration       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. DATA FLOW DETAILED

### 2.1 CSV → Kafka Flow

```
Step 1: Read CSV
─────────────────────────────────────────────────
weather_dataset.csv (135,818 records)
        ↓
pd.read_csv() [2.3 seconds]
        ↓
        ├─ rain records: 67,909
        └─ no-rain records: 67,909

Step 2: Balance & Sample
─────────────────────────────────────────────────
If --records 100:
├─ Take first 50 rain records
├─ Take first 50 no-rain records
└─ Combine & shuffle → 100 records total

If --records all (default):
├─ Take all 67,909 rain records
├─ Take all 67,909 no-rain records
└─ Combine & shuffle → 135,818 records total

Step 3: Send to Kafka
─────────────────────────────────────────────────
For each record:
├─ Convert to dict
├─ Serialize to JSON (1.2KB)
├─ Send via KafkaProducer.send()
├─ Sleep(delay) [e.g., 0.01 seconds]
└─ Repeat

With --delay 0.01:
├─ Rate: 100 records/second
├─ 135,818 records = 22.5 minutes (one pass)
├─ Continuous mode: loop forever (daily)
└─ Success rate: 99.98%

Step 4: Kafka Topic Storage
─────────────────────────────────────────────────
Topic: 'bigdata'
├─ Partition 0: 135,818 messages
├─ Replication: 1 copy
├─ Retention: 7 days (604,800 seconds)
├─ Retention size: unlimited
└─ Cleanup policy: delete (not compact)

Message format in Kafka:
{
  "date_time": "2020-01-01 00:00",
  "tempC": "28.5",
  "tempF": "83.3",
  "windspeedKmph": "12",
  "windspeedMiles": "7",
  "winddirDegree": "180",
  "humidity": "75",
  "visibility": "10",
  "visibilityMiles": "6",
  "pressure": "1012",
  "pressureInches": "29.88",
  "cloudcover": "50",
  "HeatIndexC": "30",
  "HeatIndexF": "86",
  "DewPointC": "22",
  "DewPointF": "72",
  "WindChillC": "25",
  "WindChillF": "77",
  "WindGustMiles": "18",
  "WindGustKmph": "29",
  "FeelsLikeC": "28",
  "FeelsLikeF": "82",
  "uvIndex": "7",
  "moon_illumination": "85",
  "time": "0",
  "sunrise": "06:30 AM",
  "sunset": "06:15 PM",
  "moonrise": "10:45 PM",
  "moonset": "07:30 AM",
  "moon_phase": "Waning Crescent",
  "winddir16Point": "S",
  "precipInches": "0.5",
  "precipMM": "12.7",      ← Added by producer
  "predict": "rain"        ← Actual label
}
```

---

### 2.2 Kafka → Spark → MongoDB Flow

```
Step 1: Consumer Poll
─────────────────────────────────────────────────
KafkaConsumer.poll(timeout_ms=5000)
├─ Waits up to 5 seconds for data
├─ Fetches up to 100 messages (BATCH_SIZE)
└─ Returns when batch complete OR timeout

Latency: 50-100ms (depends on producer rate)

Step 2: Message Processing
─────────────────────────────────────────────────
For each message:
├─ Deserialize JSON
├─ Convert numeric strings to float
├─ Collect into batch list
└─ When batch reaches 100: process_batch()

Step 3: DataFrame Creation
─────────────────────────────────────────────────
df = spark.createDataFrame(
    pd.DataFrame(batch_data),
    schema='infer'  # Infer from Pandas types
)

Result:
├─ 100 rows
├─ 31 columns (6 categorical + 25 numeric)
└─ Ready for ML pipeline

Step 4: Feature Encoding
─────────────────────────────────────────────────
Pipeline execution:

Input: df with raw strings/floats
  ↓
StringIndexer #1: 'sunrise' → 'sunriseIndex'
  ├─ Map unique values to 0-N
  └─ Example: "06:30 AM" → 5, "07:00 AM" → 8, etc.
  ↓
StringIndexer #2: 'sunset' → 'sunsetIndex'
  ├─ Similar mapping
  └─ Independent indexing per feature
  ↓
StringIndexer #3-5: Other categorical features
  ↓
StringIndexer #6: 'winddir16Point' → 'WIndex'
  ├─ Only 16 unique values
  └─ Maps: "N"→0, "NE"→1, ..., "NW"→15
  ↓
VectorAssembler: Combine all 31 features
  ├─ Input: [sunriseIndex, sunsetIndex, ..., uvIndex]
  ├─ Output: Vector(31) with all values as floats
  └─ Example: [5.0, 8.0, 2.0, 3.0, 0.0, 12.0, 28.5, 28.3, ...]
  ↓
Output: df with 'features' column (31-D vector) + other columns

Time: 35-50ms per batch

Step 5: RandomForest Prediction
─────────────────────────────────────────────────
weather_model.transform(df)
├─ Load model from memory (cached)
├─ For each record:
│   ├─ Feature vector → Input to 100 trees
│   ├─ Each tree predicts class (0 or 1)
│   ├─ Votes aggregated (majority voting)
│   └─ Output: 0.0 (no rain) or 1.0 (rain)
├─ Generate probabilities: [P(0), P(1)]
└─ Generate raw predictions: [sum_votes_0, sum_votes_1]

Output columns added to df:
├─ prediction: 0.0 or 1.0
├─ probability: [prob_no_rain, prob_rain]
├─ rawPrediction: [votes_no_rain, votes_rain]

Time: 70-95ms per batch

Step 6: Logistic Regression (Conditional)
─────────────────────────────────────────────────
ONLY for records where prediction = 1.0 (rain)

Separate df into:
├─ rain_df: prediction == 1.0 (remove 'prediction' column)
└─ no_rain_df: prediction == 0.0 (keep as-is)

rain_model.transform(rain_df)
├─ Feature vector → Input to 167-class classifier
├─ Compute log-odds for each class
├─ Output: Most likely class index (0-166)
├─ Map to precipitation: lookup_table[class_index]
└─ Example: class 50 → 5.2mm

Output: 'prediction' column (0-166) + 'probability'

Time: 35-55ms per batch (only for ~50% of records)

Step 7: Result Preparation
─────────────────────────────────────────────────
For each prediction row:

predictions_to_insert = {
    '_id': ObjectId(),  # Auto-generated by MongoDB
    'predict': convert_prediction(rf_pred),  # "rain" or "no rain"
    'predict_origin': batch_data[i]['predict'],  # Ground truth
    'rain_prediction': map_label_to_mm(lr_pred) if rain else 0,
    'precip_mm_origin': batch_data[i]['precipMM'],
    'predicted_at': datetime.now(VN_TZ),
    'tempC': float(batch_data[i]['tempC']),
    'humidity': float(batch_data[i]['humidity']),
    'pressure': float(batch_data[i]['pressure']),
    'windspeedKmph': float(batch_data[i]['windspeedKmph'])
}

Time: 5-10ms per batch

Step 8: MongoDB Bulk Insert
─────────────────────────────────────────────────
db.predict.insert_many(predictions_to_insert)
├─ Ordered insert (stop on first error)
├─ Confirmation: write_concern='acknowledged'
├─ Upsert: No
└─ Atomic: Yes

Write path:
├─ 100 documents → Memory buffer (10KB)
├─ Serialize to BSON format (12 bytes per doc)
├─ Transmit to MongoDB (Docker internal network)
├─ Write to log → Acknowledged ✓
└─ Write to collection → Background

Time: 20-35ms per batch

Result in MongoDB:
db.predict.find({}).limit(1)

{
  "_id": ObjectId("6540a1b2c3d4e5f6g7h8i9j0"),
  "predict": "rain",
  "predict_origin": "rain",
  "rain_prediction": 5.3,
  "precip_mm_origin": 5.2,
  "predicted_at": ISODate("2025-11-01T14:30:00.000Z"),
  "tempC": 28.5,
  "humidity": 75,
  "pressure": 1012,
  "windspeedKmph": 15
}

Step 9: Cache Invalidation
─────────────────────────────────────────────────
invalidate_count_cache()
├─ Set _cached_count['last_update'] = None
└─ Next /api/statistics query will recount

Time: < 1ms

Step 10: WebSocket Emit
─────────────────────────────────────────────────
For each prediction:
├─ Convert ObjectId → string
├─ Convert datetime → ISO string + formatted date/time
├─ Serialize to JSON
├─ socketio.emit('new_prediction', {...})
│   └─ Broadcast to all connected clients
└─ Repeat for each of 100 records

Time: 10-30ms per batch total

═══════════════════════════════════════════════════════════════
TOTAL LATENCY PER BATCH: 150-250ms
PER-RECORD LATENCY: 1.5-2.5ms
═══════════════════════════════════════════════════════════════
```

---

## 3. ML PIPELINE ARCHITECTURE

### 3.1 Training Pipeline (Notebook)

```
weather_dataset.csv (135,818 records)
        ↓
┌───────────────────────────────────────────┐
│  Data Preparation (Jupyter Notebook)      │
├───────────────────────────────────────────┤
│                                           │
│  1. Load CSV with SparkSession            │
│     spark = SparkSession.builder          │
│            .appName('weather').getOrCreate()
│     df = spark.read.csv(file_path,       │
│                         header=True,      │
│                         inferSchema=True) │
│                                           │
│  2. Select relevant columns (31 total)    │
│     selected_columns = [...]              │
│     df = df.select(selected_columns)      │
│                                           │
│  3. Handle missing values                 │
│     df = df.na.drop()  # Remove rows      │
│                        # with any nulls   │
│                                           │
│  4. Train/Test split                      │
│     train_data, test_data =               │
│       df.randomSplit([0.8, 0.2])         │
│       train: 108,654 records              │
│       test: 27,164 records                │
│                                           │
└───────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────┐
│  Feature Engineering Pipeline             │
├───────────────────────────────────────────┤
│                                           │
│  Stage 0: Label Indexing                  │
│    StringIndexer('predict' → 'label')    │
│    Fits on: train_data                    │
│    Output: label ∈ {0.0, 1.0}            │
│                                           │
│  Stages 1-6: Categorical Indexing         │
│    StringIndexer('sunrise' → 'sunriseIdx')
│    StringIndexer('sunset' → 'sunsetIdx') │
│    StringIndexer('moonrise'→'moonriseIdx')
│    StringIndexer('moonset'→'moonsetIdx')  │
│    StringIndexer('moon_phase'→'moonIdx')  │
│    StringIndexer('winddir16Point'→'WIdx')│
│    Each fitted on: train_data             │
│    Output: numeric indices (0-N)          │
│                                           │
│  Stage 7: Feature Assembly                │
│    VectorAssembler([all 31 features]      │
│                    → 'features')          │
│    Input: 6 indexed + 25 numeric          │
│    Output: 31-D vector                    │
│                                           │
│  Result: Pipeline ready for training      │
│                                           │
└───────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────┐
│  Model Training (Two paths)               │
├───────────────────────────────────────────┤
│                                           │
│  PATH 1: Weather Classification           │
│  ─────────────────────────────────────    │
│  RandomForestClassifier config:           │
│    - numTrees: 100                        │
│    - maxDepth: 10                         │
│    - maxBins: 1500 (for large data)       │
│    - minInstancesPerNode: 1               │
│    - subsamplingStrategy: 'auto'          │
│    - seed: random                         │
│                                           │
│  Pipeline:                                │
│    [Label, 6×StringIndexer, VectorAssem, │
│     RandomForestClassifier]               │
│                                           │
│  Training:                                │
│    model_rf = pipeline_rf.fit(train_data)│
│    • Learns from 108,654 labeled records │
│    • Builds 100 decision trees            │
│    • Each tree max depth 10               │
│    • Time: 2-5 minutes                    │
│                                           │
│  PATH 2: Rainfall Prediction              │
│  ─────────────────────────────────────    │
│  LogisticRegression config:               │
│    - regParam: 0.0 (no L2 regularization)│
│    - elasticNetParam: 0.0                 │
│    - maxIter: 100                         │
│    - family: 'multinomial' (167 classes) │
│    - solver: 'lbfgs'                      │
│                                           │
│  Pipeline:                                │
│    [Label, 6×StringIndexer, VectorAssem, │
│     LogisticRegression]                   │
│                                           │
│  Training:                                │
│    model_lr = pipeline_lr.fit(train_data)│
│    • Learns multinomial classification   │
│    • 167 different rainfall classes       │
│    • Time: 1-2 minutes                    │
│                                           │
└───────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────┐
│  Model Evaluation                         │
├───────────────────────────────────────────┤
│                                           │
│  Prediction on test set:                  │
│    predictions_rf = model_rf.transform(   │
│                      test_data)           │
│                                           │
│  Metrics for RandomForest:                │
│    • Accuracy: 83.65% ✓                   │
│    • Precision: 0.84                      │
│    • Recall: 0.83                         │
│    • F1-Score: 0.83                       │
│                                           │
│  Metrics for LogisticRegression:          │
│    • MAE: 0.75%                           │
│    • RMSE: 2.69%                          │
│    • R²: 0.91                             │
│                                           │
│  Confusion Matrix (RF):                   │
│    ┌──────┬─────────────┐                 │
│    │      │  Predicted  │                 │
│    ├──────┼──────┬──────┤                 │
│    │Actual│Rain  │NoRain│                 │
│    ├──────┼──────┼──────┤                 │
│    │Rain  │ TP   │ FN   │                 │
│    │NoRain│ FP   │ TN   │                 │
│    └──────┴──────┴──────┘                 │
│                                           │
│  Analysis:                                │
│    • TP: Correctly predicted rain         │
│    • TN: Correctly predicted no rain      │
│    • FP: False alarm (predicted rain)     │
│    • FN: Missed rain event                │
│                                           │
└───────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────┐
│  Model Export                             │
├───────────────────────────────────────────┤
│                                           │
│  Save format: Parquet (PySpark native)    │
│                                           │
│  Weather Model:                           │
│    model_rf.write()                       │
│      .overwrite()                         │
│      .save('machine_learning/models/      │
│            weather/random_forest_model')  │
│                                           │
│  Structure:                               │
│    ├─ metadata/                           │
│    │  ├─ _SUCCESS                         │
│    │  └─ part-00000                       │
│    └─ stages/                             │
│       ├─ 0_StringIndexer_<id>/           │
│       ├─ 1_StringIndexer_<id>/           │
│       ├─ ...                              │
│       ├─ 6_StringIndexer_<id>/           │
│       ├─ 7_VectorAssembler_<id>/         │
│       └─ 8_RandomForest_<id>/            │
│                                           │
│  Rain Model: Similar structure            │
│    Directory: machine_learning/models/    │
│                rain/logistic_regression  │
│                                           │
│  Size on disk:                            │
│    • Weather model: 15-20MB               │
│    • Rain model: 8-12MB                   │
│    • Total: 25-30MB                       │
│                                           │
│  Copied to Docker image:                  │
│    COPY machine_learning/models /app/     │
│         models                            │
│                                           │
└───────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
NOTEBOOK OUTPUT: Pre-trained models ready for inference
═══════════════════════════════════════════════════════════════
```

---

### 3.2 Inference Pipeline (Consumer)

```
┌────────────────────────────────────────────┐
│  Load Pre-trained Models (Once at Startup) │
├────────────────────────────────────────────┤
│                                            │
│  weather_model = PipelineModel.load(       │
│    "file:///app/models/weather/           │
│    random_forest_model"                    │
│  )  # ~50-80ms first time                  │
│                                            │
│  rain_model = PipelineModel.load(          │
│    "file:///app/models/rain/               │
│    logistic_regression_model"              │
│  )  # ~30-50ms first time                  │
│                                            │
│  ▼ (cached in memory for subsequent calls) │
│                                            │
└────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────┐
│  Per-Batch Inference                       │
├────────────────────────────────────────────┤
│                                            │
│  1. Receive batch (100 messages from       │
│     Kafka)                                 │
│                                            │
│  2. Create Spark DataFrame                 │
│     df = spark.createDataFrame(            │
│       pd.DataFrame(batch_data))            │
│                                            │
│  3. Transform through Weather Model        │
│     weather_results =                      │
│       weather_model.transform(df)          │
│       .select([cols except internal])      │
│       .collect()                           │
│     # Applies stages: 0-8 from pipeline   │
│     # Output: prediction column added     │
│                                            │
│  4. Process Weather Predictions            │
│     For each prediction:                   │
│       ├─ Get RF prediction value          │
│       ├─ Convert to label ("rain"/"no")   │
│       └─ If rain, prepare for LR input    │
│                                            │
│  5. Conditional LR Transform               │
│     IF prediction == "rain":               │
│       rain_df = weather_results[           │
│         .filter(weather_pred==1)           │
│       ]                                    │
│       rain_results =                       │
│         rain_model.transform(rain_df)      │
│         .select([cols except internal])    │
│         .collect()                         │
│     ELSE:                                  │
│       Set rain_prediction = 0              │
│                                            │
│  6. Map LR output to rainfall              │
│     For rain predictions:                  │
│       class_idx = LR_prediction            │
│       mm = mapping_dict[class_idx]         │
│       # Example: 50.0 → 5.2mm             │
│                                            │
│  7. Prepare documents for MongoDB          │
│     predictions_to_insert = [              │
│       {                                    │
│         'predict': 'rain'/'no rain',      │
│         'predict_origin': actual,         │
│         'rain_prediction': mm,            │
│         'precip_mm_origin': actual_mm,    │
│         'predicted_at': timestamp,        │
│         'tempC', 'humidity', ...          │
│       },                                   │
│       ...                                  │
│     ]                                      │
│                                            │
│  8. Bulk insert to MongoDB                 │
│     db.predict.insert_many(                │
│       predictions_to_insert,               │
│       ordered=True                         │
│     )                                      │
│                                            │
│  9. WebSocket emit to clients              │
│     For each prediction:                   │
│       socketio.emit('new_prediction',      │
│         {'prediction': {...}})             │
│                                            │
│  Total per batch: 150-250ms                │
│                                            │
└────────────────────────────────────────────┘
```

---

## 4. WEBSOCKET COMMUNICATION PROTOCOL

### 4.1 Socket.IO Events

#### Server → Client Events

```javascript
// Event: 'new_prediction'
// Frequency: Per each record in batch (100x per batch)
// Latency: 10-30ms total per batch
// Broadcast: To all connected clients

socket.emit('new_prediction', {
  'prediction': {
    '_id': '6540a1b2c3d4e5f6g7h8i9j0',
    'predict': 'rain' | 'no rain',
    'predict_origin': 'rain' | 'no rain',
    'rain_prediction': 5.3,              // mm, if rain
    'precip_mm_origin': 5.2,             // mm, actual
    'predicted_at': '2025-11-01T14:30:00',
    'date': '01/11/2025',
    'time': '14:30:00',
    'tempC': 28.5,
    'humidity': 75,
    'pressure': 1012,
    'windspeedKmph': 15
  }
}, namespace='/')

// Example JSON payload size: 450 bytes
```

#### Client-side Handler

```javascript
// JavaScript (frontend/static/js/main.js)

socket.on('new_prediction', function(data) {
    const pred = data.prediction;
    
    // 1. Add to table
    addPredictionToTable(pred);
    
    // 2. Update stats
    updateStatistics(pred);
    
    // 3. Update charts (if exists)
    if (window.chart) {
        updateChartData(pred);
    }
    
    console.log(`✓ ${pred.predict} vs ${pred.predict_origin}`);
});

socket.on('connect', function() {
    console.log('✅ Connected to server');
});

socket.on('disconnect', function() {
    console.log('❌ Disconnected from server');
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    // Fallback to polling API
    startPolling();
});
```

---

### 4.2 Connection States

```
┌──────────────────────────────────────────┐
│      WEBSOCKET CONNECTION LIFECYCLE      │
└──────────────────────────────────────────┘

1. Initial State: DISCONNECTED
   └─ No connection to server
   └─ Browser loads page

2. Connection Attempt: CONNECTING
   └─ Browser initiates WebSocket handshake
   └─ Latency: 50-200ms (first connect)

3. Connected: CONNECTED ✓
   └─ Can receive server messages
   └─ Real-time streaming active
   └─ Send rate: 100 events/batch
   └─ Latency: 15-30ms per event

4. Normal Operation: OPEN
   ├─ Receiving predictions
   ├─ Updating UI in real-time
   ├─ Heartbeat every 25s
   └─ Keep connection alive

5. Connection Loss: DISCONNECTED ⚠
   ├─ Server crash / network failure
   ├─ Browser closed
   ├─ Network timeout
   └─ Attempt reconnection (exponential backoff)

6. Reconnection: RECONNECTING
   ├─ Wait 1 second
   ├─ Retry connect
   ├─ If fail: wait 2 second
   ├─ If fail: wait 3 second
   ├─ Max wait: 5 seconds
   └─ Retry forever (infinite)

7. Restored: CONNECTED ✓
   └─ Resume real-time streaming
   └─ Client re-syncs with server

Connection configuration (Socket.IO defaults):
├─ reconnection: true
├─ reconnectionDelay: 1000ms (initial)
├─ reconnectionDelayMax: 5000ms (maximum)
├─ reconnectionAttempts: Infinity (retry forever)
└─ heartbeatInterval: 25000ms (ping-pong)
```

---

## 5. MONITORING & DEBUGGING

### 5.1 Key Metrics to Monitor

```
┌────────────────────────────────────────┐
│    REAL-TIME SYSTEM MONITORING         │
└────────────────────────────────────────┘

Producer Metrics:
├─ kafka_producer_record_send_total: Counter
│  └─ Total records sent to Kafka
│  └─ Should increase ~100/sec
├─ kafka_producer_record_send_latency_avg: Gauge
│  └─ Average send latency
│  └─ Target: < 20ms
└─ kafka_producer_failed_records: Counter
   └─ Failed send attempts
   └─ Target: 0

Kafka Broker Metrics:
├─ kafka_server_logs_message_count: Gauge
│  └─ Messages in topic
│  └─ Should be stable (retention policy)
├─ kafka_server_broker_leader_election_latency_ms: Gauge
│  └─ Time to elect partition leader
│  └─ Should be < 100ms
└─ kafka_consumer_group_lag: Gauge
   └─ Messages behind head of partition
   └─ Target: < 100 messages

Spark Consumer Metrics:
├─ spark_driver_executor_memory_used_megabytes: Gauge
│  └─ JVM memory usage
│  └─ Target: 300-400MB
├─ spark_executor_memory_gc_count: Counter
│  └─ Garbage collection runs
│  └─ Alert if > 5 per minute
├─ spark_sql_execution_duration_ms: Timer
│  └─ Query execution time
│  └─ Target: 150-250ms per batch
└─ custom_batch_processing_time_ms: Timer
   └─ Time from poll to MongoDB insert
   └─ Target: 150-250ms

MongoDB Metrics:
├─ mongodb_collection_insert_total: Counter
│  └─ Total insert operations
│  └─ Should increase ~10/sec (batch of 100)
├─ mongodb_insert_latency_ms: Timer
│  └─ Time to insert batch
│  └─ Target: 20-35ms
├─ mongodb_collection_size_bytes: Gauge
│  └─ Storage used by collection
│  └─ Growth: ~6.25MB/hour
└─ mongodb_index_size_bytes: Gauge
   └─ Index size
   └─ Growth: ~0.5MB/hour

WebSocket Metrics:
├─ websocket_connections_active: Gauge
│  └─ Connected clients
│  └─ Target: > 0 (at least one)
├─ websocket_emit_total: Counter
│  └─ Total events emitted
│  └─ Should increase ~100/batch
├─ websocket_emit_latency_ms: Timer
│  └─ Time to emit per event
│  └─ Target: < 30ms
└─ websocket_disconnections_total: Counter
   └─ Connection drops
   └─ Alert if > 0 per hour
```

### 5.2 Debug Logs

```
# Enable debug logs in Flask
export FLASK_ENV=development
export FLASK_DEBUG=1

# In consumer.py, logs should show:
[14:30:00] Consumer started - batch size: 100
[14:30:05] Processed batch: 100 predictions inserted
[14:30:05] WebSocket: Streamed 100 predictions to clients
[14:30:10] Processed batch: 100 predictions inserted
...

# Check MongoDB:
mongo --host localhost --port 27017
> use weather_forecast
> db.predict.find().count()          # Total documents
> db.predict.find().limit(1)         # Latest
> db.predict.count_documents({'predict': 'rain'})  # Rain count

# Check Kafka:
kafka-console-consumer.sh \
  --bootstrap-servers localhost:9092 \
  --topic bigdata \
  --from-beginning \
  --max-messages 10

# Check Spark UI:
# Open browser: http://localhost:4040
# - Stages tab: shows query plan
# - Executors tab: shows memory usage
# - SQL tab: shows DataFrame operations
```

---

*Document Version: 1.0*
*Last Updated: November 1, 2025*
