from .dataset_loader import AugmatrixLoader


def load_dataset(dataset_names):
    return AugmatrixLoader(dataset_names).load_datasets()