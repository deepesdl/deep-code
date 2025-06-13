import xarray as xr
from xrlint.linter import new_linter
from xrlint.result import Result

from deep_code.utils.custom_xrlint_rules import export_config
from deep_code.utils.helper import open_dataset


class LintDataset:
    """Lints xarray dataset using xrlint library.

    Args:
        dataset_id (str | None): ID of a Zarr dataset in the DeepESDL public or team bucket.
        dataset (xr.Dataset | None): In-memory xarray.Dataset instance.

    Note:
        One of `dataset_id` or `dataset` must be provided.
    """

    def __init__(
        self, dataset_id: str | None = None, dataset: xr.Dataset | None = None
    ):
        if not dataset_id and not dataset:
            raise ValueError("You must provide either `dataset_id` or `dataset`.")
        self.dataset_id = dataset_id
        self.dataset = dataset

    def lint_dataset(self) -> Result:
        if self.dataset is not None:
            ds = self.dataset
        elif self.dataset_id is not None:
            ds = open_dataset(self.dataset_id)
        else:
            raise RuntimeError("No dataset to lint.")

        linter = new_linter(*export_config())
        return linter.validate(ds)
