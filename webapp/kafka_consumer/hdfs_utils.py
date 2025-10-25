"""
HDFS Utility Functions for saving predictions
"""
from datetime import datetime
import pytz

def save_to_hdfs(predictions_data, spark, hdfs_namenode):
    """Save predictions to HDFS in Parquet format for long-term analytics"""
    if not predictions_data:
        return
    
    try:
        import pandas as pd
        
        # Convert to Spark DataFrame
        df = spark.createDataFrame(pd.DataFrame(predictions_data))
        
        # Partition by date for efficient querying
        VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
        current_date = datetime.now(VN_TZ).strftime('%Y/%m/%d')
        
        hdfs_path = f"hdfs://{hdfs_namenode}/predictions/{current_date}"
        
        # Save as Parquet (columnar format, compressed, efficient for analytics)
        df.write.mode("append").parquet(hdfs_path)
        
        print(f"HDFS: Saved {len(predictions_data)} predictions to {hdfs_path}")
    except Exception as e:
        print(f"HDFS save error: {e}")
        raise  # Re-raise to let caller handle
