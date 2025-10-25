#!/bin/bash
# Initialize HDFS with dataset and models

echo "================================================"
echo "🚀 Initializing HDFS Cluster"
echo "================================================"

# Wait for HDFS to be fully ready
echo "⏳ Waiting for HDFS to be ready (30 seconds)..."
sleep 30

echo ""
echo "📂 Creating HDFS directories..."
docker exec namenode hdfs dfs -mkdir -p /dataset
docker exec namenode hdfs dfs -mkdir -p /models/weather
docker exec namenode hdfs dfs -mkdir -p /models/amount_of_rain
docker exec namenode hdfs dfs -mkdir -p /predictions

echo ""
echo "📤 Uploading dataset to HDFS..."
docker exec namenode hdfs dfs -put -f /dataset/weather_dataset.csv /dataset/
echo "✅ Dataset uploaded: weather_dataset.csv"

echo ""
echo "📤 Uploading ML models to HDFS..."
# Upload weather models
docker exec namenode bash -c "cd /models/rain && hdfs dfs -put -f random_forest_model /models/weather/"
echo "✅ Weather Random Forest model uploaded"

# Upload rain prediction models  
docker exec namenode bash -c "cd /models/rain && hdfs dfs -put -f logistic_regression_model /models/amount_of_rain/"
echo "✅ Rain Logistic Regression model uploaded"

echo ""
echo "🔍 Verifying HDFS contents..."
echo ""
echo "📁 Dataset directory:"
docker exec namenode hdfs dfs -ls /dataset

echo ""
echo "📁 Models directory:"
docker exec namenode hdfs dfs -ls /models
docker exec namenode hdfs dfs -ls /models/weather
docker exec namenode hdfs dfs -ls /models/amount_of_rain

echo ""
echo "================================================"
echo "✅ HDFS Initialization Complete!"
echo "================================================"
echo ""
echo "🌐 HDFS Web UI: http://localhost:9870"
echo "📊 Check NameNode status and browse files"
echo ""
