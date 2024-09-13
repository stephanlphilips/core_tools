from functools import partial
import io
import os
import shutil
import requests
import xarray as xr
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm
from sqdl_client.client import QDLClient
from core_tools.data.ds.data_set import data_set
from core_tools.data.ds.xarray2ds import xarray2ds

_DATASET_READER = None


@dataclass
class DatasetInfo:
    uuid: str
    name: str
    start_time: datetime
    setup: str
    sample: str
    starred: bool
    variables: list[str]
    axes: list[str]


class DatasetReader:
    def __init__(self, scope_name: str | None = None):
        client = QDLClient()
        self.client = client
        client.login()
        self.s3_session = requests.Session()
        if scope_name:
            self.set_scope(scope_name)
        else:
            self.scope = None

    def logout(self):
        self.client.logout()

    def set_scope(self, scope_name: str):
        sqdl_api = self.client.api
        self.scope = sqdl_api.scope.retrieve_from_name(scope_name)

    def list_scopes(self):
        sqdl_api = self.client.api
        return [scope.name for scope in sqdl_api.scope.list()]

    def load_ds_by_uuid(self, uuid) -> data_set:
        uid_str = str(int(uuid))
        return xarray2ds(self.load_hdf5_by_uid(uid_str))

    def load_hdf5_by_uid(self, uid: str) -> xr.Dataset:
        if self.scope is None:
            raise Exception("sQDL connection must be configured with init_sqdl(scope_name)")
        sqdl_ds = self.scope.retrieve_dataset_from_uid(uid)
        sqdl_files = sqdl_ds.files
        for file in sqdl_files:
            if file.name.endswith('.hdf5'):
                break
        else:
            raise Exception(f"HDF5 file for uid '{uid}' not found")
        if not file.has_data:
            raise Exception(f"HDF5 file for uid '{file.name}' is not uploaded")
        url = file.presigned_url
        return self.load_hdf5_from_url(url)

    def load_hdf5_from_url(self, url) -> xr.Dataset:
        resp = self.s3_session.request("GET", url)
        with io.BytesIO(resp.content) as fp:
            return xr.load_dataset(fp)

    def download_hdf5_by_uid(self, uid: str, download_dir: str):
        sqdl_ds = self.scope.retrieve_dataset_from_uid(uid)
        sqdl_files = sqdl_ds.files
        for file in sqdl_files:
            if file.name.endswith('.hdf5'):
                break
        else:
            raise Exception(f"HDF5 file for uid '{uid}' not found")
        if not file.has_data:
            raise Exception(f"HDF5 file for uid '{file.name}' is not uploaded")
        url = file.presigned_url
        return self.download_hdf5_from_url(url, download_dir, file.name)

    def download_hdf5_from_url(self, url: str, download_dir: str, file_name: str):
        resp = self.s3_session.request("GET", url)
        with io.BytesIO(resp.content) as fsrc:
            with open(os.path.join(download_dir, file_name), "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)

    def query_datasets(
            self,
            name_contains: str = None,
            start_time: datetime = None,
            end_time: datetime = None,
            setup: str = None,
            sample: str = None,
            starred: bool = False,
            variables: list[str] | str | None = None,
            axes: list[str] | str | None = None,
            ) -> list[DatasetInfo]:
        data_identifiers = {}
        if sample is not None:
            data_identifiers['sample'] = sample
        if setup is not None:
            data_identifiers['setup'] = setup
        if variables is not None:
            data_identifiers['variables_measured'] = variables
        if axes is not None:
            data_identifiers['dimensions'] = axes

        sqdl_res = self.scope.search_datasets(
            dataset_name_contains = name_contains,
            collected_since = start_time,
            collected_until = end_time,
            rating = 1 if starred else None,
            data_identifiers = data_identifiers,
            limit=1000,
            )

        res = []
        for r in sqdl_res:
            res.append(
                DatasetInfo(
                    r.uid,
                    r.name,
                    r.date_collected,
                    r.metadata['setup'],
                    r.metadata['sample'],
                    r.rating > 0,
                    r.metadata['variables_measured'],
                    r.metadata['dimensions'],
                    )
                )

        return res


def _get_dataset_reader():
    global _DATASET_READER
    if _DATASET_READER is None:
        _DATASET_READER = DatasetReader()
    return _DATASET_READER


def init_sqdl(scope_name: str):
    _get_dataset_reader().set_scope(scope_name)


def sqdl_logout():
    """Logout sQDL.
    The login window will popup when a new request to sQDL is made.
    """
    global _DATASET_READER
    if _DATASET_READER is not None:
        _DATASET_READER.logout()
    else:
        client = QDLClient()
        client.logout()


def sqdl_query(
            name_contains: str = None,
            start_time: datetime = None,
            end_time: datetime = None,
            setup: str = None,
            sample: str = None,
            starred: bool = False,
            variables: list[str] | str | None = None,
            axes: list[str] | str | None = None,
            ) -> list[DatasetInfo]:

    return _get_dataset_reader().query_datasets(
            name_contains=name_contains,
            start_time=start_time,
            end_time=end_time,
            setup=setup,
            sample=sample,
            starred=starred,
            variables=variables,
            axes=axes,
        )


def list_scopes():
    global _DATASET_READER
    if _DATASET_READER is None:
        _DATASET_READER = DatasetReader()
    return _DATASET_READER.list_scopes()


def load_by_uuid(uuid: str | int):
    reader = _get_dataset_reader()
    if reader.scope is None:
        raise Exception("sQDL connection must be configured with init_sqdl(scope_name)")
    return reader.load_ds_by_uuid(uuid)


def load_uuids_parallel(uuids: list[int | str], print_progress=True):
    iterator = tqdm(uuids) if print_progress else uuids
    with ThreadPoolExecutor() as executor:
        return list(executor.map(load_by_uuid, iterator))


def download_hdf5(uuid: str | int, download_dir: str):
    reader = _get_dataset_reader()
    if reader.scope is None:
        raise Exception("sQDL connection must be configured with init_sqdl(scope_name)")
    reader.download_hdf5_by_uid(uuid, download_dir)


def download_hdf5_parallel(
        uuids: list[str | int],
        download_dir: str,
        print_progress=True):
    reader = _get_dataset_reader()
    if reader.scope is None:
        raise Exception("sQDL connection must be configured with init_sqdl(scope_name)")
    iterator = tqdm(uuids) if print_progress else uuids
    with ThreadPoolExecutor() as executor:
        return list(
            executor.map(
                partial(reader.download_hdf5_by_uid, download_dir=download_dir),
                iterator)
            )
