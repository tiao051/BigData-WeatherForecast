Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Initializing HDFS Cluster" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

Write-Host "`nWaiting for HDFS to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`nCreating HDFS directories..." -ForegroundColor Green
docker exec namenode hdfs dfs -mkdir -p /dataset
docker exec namenode hdfs dfs -mkdir -p /models/weather
docker exec namenode hdfs dfs -mkdir -p /models/amount_of_rain
docker exec namenode hdfs dfs -mkdir -p /predictions

Write-Host "`nUploading dataset to HDFS..." -ForegroundColor Green
docker exec namenode hdfs dfs -put -f /dataset/weather_dataset.csv /dataset/
Write-Host "Dataset uploaded: weather_dataset.csv" -ForegroundColor Green

Write-Host "`nVerifying dataset in HDFS..." -ForegroundColor Yellow
docker exec namenode hdfs dfs -ls /dataset

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "HDFS Initialization Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan

Write-Host "`nHDFS Web UI: http://localhost:9870" -ForegroundColor Yellow
Write-Host "Check NameNode status and browse files" -ForegroundColor Yellow
