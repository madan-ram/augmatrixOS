import json
import requests

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from datasets import Dataset, DatasetDict, ClassLabel, Features
from typing import List, Any
import datasets


class TextClassifier:

    def __init__(self, annotations_data, dataset_data, config_json):
        self.annotations_data = annotations_data
        self.dataset_data = dataset_data
        self.config_json = config_json

    def text_classifications(self):
        text_data = []
        label_data = []
        label_url_lst = self.annotations_data
        text_url_lst = self.dataset_data
        target_label = self.config_json

        for label_url, text_url in zip(label_url_lst, text_url_lst):
            # Download label
            response_label_data = requests.get(label_url)
            annotations_labels = response_label_data.content
            annotations_labels_json = json.loads(annotations_labels)
            annotations = annotations_labels_json["annotations"]
            for annotation in annotations:
                for choice in annotation:
                    if choice["from_name"] == target_label:
                        label_data.append(choice["value"]["choices"][0])
            # Download text
            response_text_data = requests.get(text_url)
            download_text_data = response_text_data.content
            text_data.append(download_text_data.decode('utf-8'))

        label_list = ['food menu', 'delivery', 'coupons', 'payment']

        encoder = LabelEncoder()
        encoder.fit(label_list)
        label_encoded = encoder.transform(label_data)
        label_encoded_list = label_encoded.tolist()

        class_label = ClassLabel(names=encoder.classes_.tolist())

        X_train, X_test, y_train, y_test = train_test_split(
            text_data, label_encoded_list, test_size=0.25, random_state=0
        )

        # Creating the Features object to define the dataset schema
        custom_features = Features({
            'labels': class_label,
            'text': datasets.Value("string"),
        })

        dataset = DatasetDict({
            "train": Dataset.from_dict({"labels": y_train, "text": X_train}, features=custom_features),
            "test": Dataset.from_dict({"labels": y_test, "text": X_test}, features=custom_features),
        })

        return dataset
