import os
import json
from pathlib import Path
import urllib.parse
import requests
from tqdm import tqdm
from constants.model_constants import SINGLE_LINE_FILES


class AugmatrixUploader:
    def __init__(self, file_path):
        self.token = os.environ.get("AUGMATRIX_TOKEN")
        self.base_url = os.environ.get("AUGMATRIX_API_URL")
        self.experiment_name = os.environ.get("EXPERIMENT_NAME")
        self.model_name = os.environ.get("SELECTED_MODEL_NAME")
        self.pipeline_tag = os.environ.get("PIPELINE_NAME")

        if self.token is None:
            raise ValueError("AGUMATRIX_TOKEN environment variable not set.")

        if self.experiment_name is None:
            raise ValueError("experiment_name is not set")

        if self.model_name is None:
            raise ValueError("model is not set")

        self.upload_url = urllib.parse.urljoin(
            self.base_url, "api/auth_upload_model_info/"
        )
        self.model_metrics_url = urllib.parse.urljoin(
            self.base_url, "api/auth_upload_model_metrics/"
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
                "experiment_name": self.experiment_name,
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

            if response.status_code != 200:
                print("Error sending chunk. Status code:", response.status_code)

            print("Merics uploaded successfully")

        except UnicodeDecodeError as e:
            print("Directory not found:", e)

    def artifacts_binary_data_generator(self, file_path):
        with open(file_path, "rb") as file:
            chunk_size = 2000 * 1024 * 1024
            while True:
                data_chunk = file.read(chunk_size)
                if len(data_chunk) == 0:
                    break
                yield ("file", (file_path, data_chunk))

    def push_to_hub(self):
        try:
            if os.path.isdir(self.file_path):
                total_uploaded_size = 0
                total_file_size = 0
                total_chunks = 0
                chunk_number = 1

                for root, _, files in os.walk(self.file_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        total_file_size += os.path.getsize(file_path)
                        total_chunks += 1

                headers = {
                    "Authorization": f"Token {self.token}",
                }
                data = {
                    "experiment_name": self.experiment_name,
                    "selected_model_name": self.model_name,
                    "pipeline_tag": self.pipeline_tag,
                    "chunk_number": chunk_number,
                }
                chunk_size = 5 * 1024 * 1024
                num_iterations = (total_file_size + chunk_size - 1) // chunk_size
                with tqdm(
                    total=total_file_size, desc="Uploading directory", unit="B"
                ) as pbar:
                    for root, _, files in os.walk(self.file_path):
                        for filename in files:
                            file_path = os.path.join(root, filename)

                            with open(file_path, "rb") as f:
                                while True:
                                    chunk = f.read(chunk_size)
                                    if not chunk:
                                        break
                                    response = requests.post(
                                        self.upload_url,
                                        files=self.artifacts_binary_data_generator(
                                            file_path
                                        ),
                                        headers=headers,
                                        data=data,
                                        stream=True,
                                    )
                                    total_uploaded_size += len(chunk)
                                    pbar.update(len(chunk))
                                    chunk_number = chunk_number + 1

                                    if response.status_code != 200:
                                        print(
                                            "Error sending chunk. Status code:",
                                            response.status_code,
                                        )

                print(
                    f"Total uploaded size: {total_uploaded_size}/{total_file_size} bytes"
                )

        except FileNotFoundError:
            print("Directory not found:", self.file_path)
