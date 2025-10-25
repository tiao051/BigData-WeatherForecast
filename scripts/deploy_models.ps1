Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Deploying Spark ML models to HDFS" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

Write-Host "`nCopying models from host to namenode..." -ForegroundColor Green

docker cp ../machine_learning/models/weather/random_forest_model namenode:/models/weather/
docker cp ../machine_learning/models/weather/logistic_regression_model namenode:/models/weather/
docker cp ../machine_learning/models/rain/random_forest_model namenode:/models/rain/
docker cp ../machine_learning/models/rain/logistic_regression_model namenode:/models/rain/

Write-Host "Models copied to namenode" -ForegroundColor Green

Write-Host "`nUploading models to HDFS..." -ForegroundColor Yellow

docker exec namenode hdfs dfs -put -f /models/weather/random_forest_model/ /models/weather/
docker exec namenode hdfs dfs -put -f /models/weather/logistic_regression_model/ /models/weather/
docker exec namenode hdfs dfs -put -f /models/rain/random_forest_model/ /models/rain/
docker exec namenode hdfs dfs -put -f /models/rain/logistic_regression_model/ /models/rain/

Write-Host "HDFS model upload successful!" -ForegroundColor Green

docker exec namenode hdfs dfs -ls -R /models

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "Model Deployment Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
