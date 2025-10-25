#!/usr/bin/env python3
"""
Kafka Producer for Weather Data Streaming
Reads weather data from CSV and sends to Kafka topic for real-time processing
"""

import os
import sys
import time
import json
import argparse
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_NAME = os.environ.get("KAFKA_TOPIC_NAME", "bigdata")
DATASET_PATH = os.environ.get("DATASET_PATH", "/app/dataset/weather_dataset.csv")


def create_producer(bootstrap_servers):
    """Create and return a Kafka producer instance"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                max_block_ms=5000
            )
            return producer
        
        except NoBrokersAvailable:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                sys.exit(1)
        except Exception as e:
            sys.exit(1)

def load_dataset(file_path, limit=None):
    """Load weather dataset from CSV file with 50/50 rain/no-rain balance"""
    try:
        df = pd.read_csv(file_path)
        
        # Separate rain and no-rain records
        rain_df = df[df['predict'] == 'rain'].copy()
        no_rain_df = df[df['predict'] == 'no rain'].copy()
        
        print(f"Original dataset: {len(rain_df)} rain, {len(no_rain_df)} no-rain records")
        
        # Get equal amounts from each class
        min_size = min(len(rain_df), len(no_rain_df))
        
        if limit and limit > 0:
            # If limit specified, take half from each class
            samples_per_class = min(limit // 2, min_size)
            rain_sample = rain_df.head(samples_per_class)
            no_rain_sample = no_rain_df.head(samples_per_class)
        else:
            # Otherwise take all available (balanced)
            rain_sample = rain_df.head(min_size)
            no_rain_sample = no_rain_df.head(min_size)
        
        # Combine and shuffle
        balanced_df = pd.concat([rain_sample, no_rain_sample], ignore_index=True)
        balanced_df = balanced_df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        print(f"Balanced dataset: {len(balanced_df)} total records (50% rain, 50% no-rain)")
        
        return balanced_df
    except FileNotFoundError:
        sys.exit(1)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)


def send_data(producer, topic_name, data_df, delay=0.1, continuous=False):
    """Send weather data to Kafka topic"""
    if continuous:
        print("Continuous mode: Will loop forever")

    sent_count = 0
    
    try:
        while True:
            for index, row in data_df.iterrows():
                # Convert row to dictionary
                data = row.to_dict()
                
                # Convert all non-string values to strings for JSON serialization
                for key, value in data.items():
                    if not isinstance(value, str):
                        data[key] = str(value)
                
                # Send to Kafka
                producer.send(topic_name, value=data)
                sent_count += 1
                
                # Print progress every 10 records
                if sent_count % 10 == 0 or index == 0:
                    print(f"[{sent_count}] Sent: Date={data.get('date_time', 'N/A')}, "
                          f"Weather={data.get('predict', 'N/A')}, Temp={data.get('tempC', 'N/A')}°C")
                
                # Delay between messages
                if delay > 0:
                    time.sleep(delay)
            
            # If not continuous mode, break after one iteration
            if not continuous:
                break
            
            # Small delay between loops in continuous mode
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\nError sending data: {e}")
    finally:
        producer.close()
        print(f"Producer closed. Total records sent: {sent_count}")

def main():
    parser = argparse.ArgumentParser(description='Kafka Weather Data Producer')
    
    parser.add_argument('--records', type=str, default='100',
                        help='Number of records to send (use "all" for entire dataset, default: 100)')
    parser.add_argument('--delay', type=float, default=0.1,
                        help='Delay in seconds between messages (default: 0.1)')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuously (loop forever)')
    parser.add_argument('--kafka', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help=f'Kafka bootstrap servers (default: {KAFKA_BOOTSTRAP_SERVERS})')
    parser.add_argument('--topic', type=str, default=KAFKA_TOPIC_NAME,
                        help=f'Kafka topic name (default: {KAFKA_TOPIC_NAME})')
    parser.add_argument('--dataset', type=str, default=DATASET_PATH,
                        help=f'Path to weather dataset CSV (default: {DATASET_PATH})')
    
    args = parser.parse_args()
    
    # Parse record limit
    record_limit = None if args.records.lower() == 'all' else int(args.records)
    
    # Create producer
    producer = create_producer(args.kafka)
    
    # Load dataset
    dataset = load_dataset(args.dataset, limit=record_limit)
    
    # Send data
    send_data(producer, args.topic, dataset, delay=args.delay, continuous=args.continuous)


if __name__ == "__main__":
    main()
