import os
from pathlib import Path
import urllib.parse
import requests
from tqdm import tqdm


class AugmatrixUploader:
    def __init__(self, file_path):
        self.token = os.environ.get('AUGMATRIX_TOKEN')
        self.base_url = os.environ.get('AUGMATRIX_API_URL')
        self.experiment_name = os.environ.get('MLFLOW_EXPERIMENT_NAME')
        self.model_name = os.environ.get('SELECTED_MODEL_NAME')
        self.file_path = file_path

        if self.token is None:
            raise ValueError("AGUMATRIX_TOKEN environment variable not set.")

        if self.experiment_name is None:
            raise ValueError("environmental variable MLFLOW_EXPERIMENT_NAME not set")

        if self.model_name is None:
            raise ValueError("environmental variable SELECTED_MODEL_NAME not set")

        self.upload_url = urllib.parse.urljoin(self.base_url, "api/auth_upload_model_info/")

    def binary_data_generator(self, file_path):
        with open(file_path, "rb") as file:
            chunk_size = 8192
            while True:
                data_chunk = file.read(chunk_size)
                if len(data_chunk) == 0:
                    break
                yield ("file", (file_path, data_chunk))

    def push_to_metrics(self, chunk_size=8192):
        try:
            for root, _, files in os.walk(self.file_path):
                for filename in files:
                    print(filename)
                    file_path = os.path.join(root, filename)
                    headers = {
                        "Authorization": f"Token {self.token}",
                    }

                    data = {"experiment_name": self.experiment_name,"file_type":"matrices", "model_name": self.model_name}

                    response = requests.post(
                        self.upload_url,
                        files=self.binary_data_generator(file_path),
                        headers=headers,
                        data=data, 
                        stream=True,
                    )

                    if response.status_code == 200:
                        print("Chunk sent successfully!")
                    else:
                        print("Error sending chunk. Status code:", response.status_code)
        except FileNotFoundError:
            print("Directory not found:", self.file_path)
 
    def artifacts_binary_data_generator(self, file_path):
        with open(file_path, 'rb') as file:
            chunk_size = 2000 * 1024 * 1024
            while True:
                data_chunk = file.read(chunk_size)
                if len(data_chunk) == 0:
                    break
                yield ("file", (file_path, data_chunk))

    def push_to_hub(self):
        try:
            if os.path.isdir(self.file_path):
                for root, _, files in os.walk(self.file_path):
                    chunk_number = 1
                    for filename in files:
                        file_path = os.path.join(root, filename)

                        headers = {
                            "Authorization": f"Token {self.token}",
                        }
                        data = {
                            "experiment_name": self.experiment_name,
                            "file_type": "output",
                            "model_name": self.model_name,
                            "chunk_number": chunk_number,
                        }
                        total_file_size = os.path.getsize(file_path)
                        chunk_size = 500 * 1024 * 1024
                        num_iterations = (total_file_size + chunk_size - 1) // chunk_size

                        with tqdm(total=num_iterations, desc=f"Uploading {filename}", unit="chunk") as pbar:
                            with open(file_path, "rb") as f:
                                while True:
                                    chunk = f.read(chunk_size)
                                    if not chunk:
                                        break
                                    response = requests.post(
                                        self.upload_url,
                                        files=self.artifacts_binary_data_generator(file_path),
                                        headers=headers,
                                        data=data,
                                        stream=True,
                                    )
                                    chunk_number += 1
                                    pbar.update(1)

                                    if response.status_code == 200:
                                        print("Chunk sent successfully!")
                                    else:
                                        print("Error sending chunk. Status code:", response.status_code)

        except FileNotFoundError:
            print("Directory not found:", self.file_path)
