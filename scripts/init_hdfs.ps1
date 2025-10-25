# Initialize HDFS with dataset and models
# PowerShell version

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "🚀 Initializing HDFS Cluster" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Wait for HDFS to be fully ready
Write-Host "`n⏳ Waiting for HDFS to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`n📂 Creating HDFS directories..." -ForegroundColor Green
docker exec namenode hdfs dfs -mkdir -p /dataset
docker exec namenode hdfs dfs -mkdir -p /models/weather
docker exec namenode hdfs dfs -mkdir -p /models/amount_of_rain
docker exec namenode hdfs dfs -mkdir -p /predictions

Write-Host "`n📤 Uploading dataset to HDFS..." -ForegroundColor Green
docker exec namenode hdfs dfs -put -f /dataset/weather_dataset.csv /dataset/
Write-Host "✅ Dataset uploaded: weather_dataset.csv" -ForegroundColor Green

Write-Host "`n📤 Uploading ML models to HDFS..." -ForegroundColor Green
# Upload weather models
docker exec namenode bash -c "cd /models/rain && hdfs dfs -put -f random_forest_model /models/weather/"
Write-Host "✅ Weather Random Forest model uploaded" -ForegroundColor Green

# Upload rain prediction models  
docker exec namenode bash -c "cd /models/rain && hdfs dfs -put -f logistic_regression_model /models/amount_of_rain/"
Write-Host "✅ Rain Logistic Regression model uploaded" -ForegroundColor Green

Write-Host "`n🔍 Verifying HDFS contents..." -ForegroundColor Yellow
Write-Host "`n📁 Dataset directory:" -ForegroundColor Cyan
docker exec namenode hdfs dfs -ls /dataset

Write-Host "`n📁 Models directory:" -ForegroundColor Cyan
docker exec namenode hdfs dfs -ls /models
docker exec namenode hdfs dfs -ls /models/weather
docker exec namenode hdfs dfs -ls /models/amount_of_rain

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "✅ HDFS Initialization Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "`n🌐 HDFS Web UI: http://localhost:9870" -ForegroundColor Yellow
Write-Host "📊 Check NameNode status and browse files" -ForegroundColor Yellow
Write-Host ""
