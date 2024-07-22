import io
import requests
import xarray as xr
from typing import Optional, Union

from sqdl_client.client import QDLClient
from core_tools.data.ds.data_set import data_set
from core_tools.data.ds.xarray2ds import xarray2ds

_DATASET_READER = None

class DatasetReader:
    def __init__(self, scope_name: Optional[str] = None):
        client = QDLClient()
        self.client = client
        client.login()
        self.s3_session = requests.Session()
        if scope_name:
            sqdl_api = client.api
            self.scope = sqdl_api.scope.retrieve_from_name(scope_name)
        else:
            self.scope = None

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


def init_sqdl(scope_name: str):
    global _DATASET_READER
    if _DATASET_READER is None:
        _DATASET_READER = DatasetReader(scope_name)
    else:
        _DATASET_READER.set_scope(scope_name)

def list_scopes():
    global _DATASET_READER
    if _DATASET_READER is None:
        _DATASET_READER = DatasetReader()
    return _DATASET_READER.list_scopes()


def load_by_uuid(uuid: Union[str, int]):
    if _DATASET_READER is None or _DATASET_READER.scope is None:
        raise Exception("sQDL connection must be configured with init_sqdl(scope_name)")
    reader = _DATASET_READER
    return reader.load_ds_by_uuid(uuid)
