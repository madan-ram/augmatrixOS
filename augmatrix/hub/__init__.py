from .model_uploader import AugmatrixUploader
import os

def push_to_hub(output_file_path):
    AugmatrixUploader(output_file_path).push_to_metrics()
    AugmatrixUploader('mlruns/models').push_to_hub()