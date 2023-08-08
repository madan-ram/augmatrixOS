import os
import json
import urllib.parse
import requests
import hashlib
import base64

from pathlib import Path
from azure.storage.blob import BlobClient
from tqdm import tqdm
from .constants.model_constants import SINGLE_LINE_FILES


class AugmatrixUploader:
    def __init__(self, file_path):
        self.token = os.environ.get("AUGMATRIX_TOKEN")
        self.base_url = os.environ.get("AUGMATRIX_API_URL")
        self.mlflow_experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME")
        self.model_name = os.environ.get("SELECTED_MODEL_NAME")
        self.pipeline_tag = os.environ.get("PIPELINE_NAME")

        if self.token is None:
            raise ValueError("AGUMATRIX_TOKEN environment variable not set.")

        if self.mlflow_experiment_name is None:
            raise ValueError("mlflow_experiment_name is not set")

        if self.model_name is None:
            raise ValueError("model is not set")

        self.upload_url = urllib.parse.urljoin(
            self.base_url, "api/auth_upload_model_info/"
        )
        self.model_metrics_url = urllib.parse.urljoin(
            self.base_url, "api/auth_upload_model_metrics/"
        )
        self.output_MD5keys_url = urllib.parse.urljoin(
            self.base_url, "api/auth_upload_model_MD5Hash/"
        )
        self.file_path = file_path

    def converting_the_metrics_to_json(self, file_path):
        labels = []
        datasets = []
        epoch_set = set()
        sending_data_json = {}
        try:
            for root, _, files in os.walk(file_path):
                for filename in files:
                    if str(filename) not in SINGLE_LINE_FILES:
                        label_data = []
                        file_path = os.path.join(root, filename)

                        with open(file_path, "r") as file:
                            chunk_size = 8192
                            while True:
                                data_chunk = file.read(chunk_size)
                                if len(data_chunk) == 0:
                                    break
                                lines = data_chunk.strip().split("\n")
                                for line in lines:
                                    parts = line.split()
                                    if len(parts) >= 3:
                                        # time = parts[0]
                                        value = parts[1]
                                        epoch = parts[-1]

                                        try:
                                            epoch = int(epoch)
                                            value = int(value)
                                        except ValueError:
                                            epoch = float(epoch)
                                            value = float(value)

                                        if filename != "epoch":
                                            label_data.append(value)

                                        elif (
                                            filename == "epoch"
                                            and value not in epoch_set
                                        ):
                                            labels.append(value)
                                            epoch_set.add(value)
                                if filename != "epoch":
                                    dataset = {
                                        "label": filename,
                                        "data": label_data,
                                    }
                                    datasets.append(dataset)
                                sending_data_json = {
                                    "label": list(labels),
                                    "dataset": datasets,
                                }
            return sending_data_json
        except FileNotFoundError:
            print("Directory not found:", self.file_path)

    def push_to_metrics(self):
        try:
            sending_data_json = self.converting_the_metrics_to_json(self.file_path)
            sending_binary_data = json.dumps(
                sending_data_json, ensure_ascii=False
            ).encode("utf-8")
            headers = {"Authorization": f"Token {self.token}"}

            data = {
                "mlflow_experiment_name": self.mlflow_experiment_name,
                "selected_model_name": self.model_name,
                "model_metrics": sending_binary_data,
                "pipeline_tag": self.pipeline_tag,
            }

            response = requests.post(
                self.model_metrics_url,
                headers=headers,
                data=data,
                stream=True,
            )
            recive_data = response.content
            status = recive_data.decode("utf-8")
            if response.status_code != 200:
                print("Error sending chunk. Status code:", response.status_code)
            elif "permission denied" in status:
                print("permission denied")
            else:
                print("Merics uploaded successfully")

        except UnicodeDecodeError as e:
            print("Directory not found:", e)

    def send_the_file(self, file_name):
        headers = {
            "Authorization": f"Token {self.token}",
        }
        data = {
            "mlflow_experiment_name": self.mlflow_experiment_name,
            "selected_model_name": self.model_name,
            "pipeline_tag": self.pipeline_tag,
            "file_name": str(file_name),
        }
        response = requests.post(
            self.upload_url,
            headers=headers,
            data=data,
            stream=True,
        )
        recive_data = response.content
        return recive_data.decode("utf-8")

    def send_the_md5Hash(self, hash_keys):
        headers = {
            "Authorization": f"Token {self.token}",
        }
        data = {
            "mlflow_experiment_name": self.mlflow_experiment_name,
            "selected_model_name": self.model_name,
            "pipeline_tag": self.pipeline_tag,
            "hash_keys": json.dumps(hash_keys),
        }
        response = requests.post(
            self.output_MD5keys_url,
            headers=headers,
            data=data,
            stream=True,
        )

    def push_to_hub(self):
        model_ouput_file_hash_keys = {}
        try:
            print("uploading files")
            if os.path.isdir(self.file_path):
                for root, _, files in os.walk(self.file_path):
                    for filename in files:
                        received_data = self.send_the_file(filename)
                        received_upload_data = json.loads(received_data)
                        if received_upload_data["message"] == "Success":
                            received_url = received_upload_data[
                                "sending_model_upload_url"
                            ]
                            received_file_name = received_upload_data["file_name"]
                            model_output_file_path = os.path.join(
                                root, received_file_name
                            )
                            print(f"{received_file_name} file uploading")
                            blob_client = BlobClient.from_blob_url(received_url["url"])
                            with open(model_output_file_path, "rb") as d_file:
                                blob_client.upload_blob(d_file, overwrite=True)
                                d_file.seek(0)
                                hash_data = d_file.read()
                                md5_hash_id = base64.b64encode(
                                    hashlib.md5(hash_data).digest()
                                ).decode("utf-8")
                                model_ouput_file_hash_keys[
                                    received_file_name
                                ] = md5_hash_id
                        else:
                            print("permission denied")
                            break
                self.send_the_md5Hash(model_ouput_file_hash_keys)
        except Exception as e:
            print("An error occurred:", str(e))
