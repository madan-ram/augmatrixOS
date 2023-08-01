import os
import sys
from pathlib import Path
import urllib.parse
import requests
import json
import yaml
from .data_formater.text_classification import TextClassifier


class AugmatrixLoader:

    def __init__(self, annotation_name):

        self.token = os.environ.get('AUGMATRIX_TOKEN')
        self.base_url = os.environ.get('AUGMATRIX_API_URL')
        self.annotation_name = annotation_name

        if self.token is None:
            raise ValueError("AGUMATRIX_TOKEN environment variable not set.")

        if annotation_name is None:
            raise ValueError("File name is not entered")

    def load_datasets(self):
        annotations_data = []
        dataset_data = []
        pipeline_type = ""
        target_label = ""
        url = urllib.parse.urljoin(
            self.base_url,
            f"api/auth_load_dataset/?token={self.token}&annotation_name={self.annotation_name}",
        )
        response = requests.get(url)
        presigend_urls = json.loads(response.content)

        annotations_urls = presigend_urls["annotation_data"]
        dataset_urls = presigend_urls["dataset_data"]
        config_json = presigend_urls["config_json"]
        response_config_json = requests.get(config_json)
        download_text_data = json.loads(response_config_json.content)

        for key, value in download_text_data.items():
            pipeline_type = value["pipeline_tag"]
            target_label = value["target_label"]

        for key, value in annotations_urls.items():
            annotations_data.append(value)

        for key, value in dataset_urls.items():
            dataset_data.append(value)

        if pipeline_type == "text-classification":
            classifier = TextClassifier(annotations_data, dataset_data, target_label)
            config_json = classifier.text_classifications()
            return config_json
        elif pipeline_type == "object-detection":
            raise ValueError("Comming Soon")
        elif pipeline_type == "zero-shot-classification":
            raise ValueError("Comming Soon")
        else:
            raise ValueError("Comming Soon")
