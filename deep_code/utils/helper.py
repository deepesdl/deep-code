import logging
import os
from typing import Optional

import xarray as xr
from xcube.core.store import new_data_store


def serialize(obj):
    """Convert non-serializable objects to JSON-compatible formats.
    Args:
        obj: The object to serialize.
    Returns:
        A JSON-compatible representation of the object.
    Raises:
        TypeError: If the object cannot be serialized.
    """
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def open_dataset(
    dataset_id: str,
    root: str = "deep-esdl-public",
    storage_configs: Optional[list[dict]] = None,
    logger: Optional[logging.Logger] = None,
) -> xr.Dataset:
    """Open an xarray dataset from a specified store.

    Args:
        dataset_id: ID of the dataset (e.g., path to Zarr or NetCDF file).
        storage_type: Type of storage (e.g., 's3', 'file'). Defaults to 's3'.
        root: Root path or bucket for the store. Defaults to 'deep-esdl-public'.
        storage_configs: List of storage configurations. If None, uses default S3 configs.
        logger: Optional logger for logging messages. If None, uses default logger.

    Returns:
        xarray.Dataset: The opened dataset.

    Raises:
        ValueError: If the dataset cannot be opened with any configuration.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Default S3 configurations
    default_configs = [
        {
            "description": "Public store",
            "params": {
                "storage_type": "s3",
                "root": root,
                "storage_options": {"anon": True},
            },
        },
        {
            "description": "Authenticated store",
            "params": {
                "storage_type": "s3",
                "root": os.environ.get("S3_USER_STORAGE_BUCKET", root),
                "storage_options": {
                    "anon": False,
                    "key": os.environ.get("S3_USER_STORAGE_KEY"),
                    "secret": os.environ.get("S3_USER_STORAGE_SECRET"),
                },
            },
        },
    ]

    # Use provided configs or default
    configs = storage_configs or default_configs

    # Iterate through configurations and attempt to open the dataset
    last_exception = None
    tried_configurations = []
    for config in configs:
        tried_configurations.append(config["description"])
        try:
            logger.info(
                f"Attempting to open dataset '{dataset_id}' with configuration: "
                f"{config['description']}"
            )
            store = new_data_store(
                config["params"]["storage_type"],
                root=config["params"]["root"],
                storage_options=config["params"]["storage_options"],
            )
            dataset = store.open_data(dataset_id)
            logger.info(
                f"Successfully opened dataset '{dataset_id}' with configuration: "
                f"{config['description']}"
            )
            return dataset
        except Exception as e:
            logger.error(
                f"Failed to open dataset '{dataset_id}' with configuration: "
                f"{config['description']}. Error: {e}"
            )
            last_exception = e

    raise ValueError(
        f"Failed to open dataset with ID '{dataset_id}'. "
        f"Tried configurations: {', '.join(tried_configurations)}. "
        f"Last error: {last_exception}"
    )
