from typing import Any

import h5py
import numpy as np
import torch
from torch_geometric.data import Data, HeteroData


class H5Interface:
    def __init__(self, file: h5py.File):
        self.f = file

    def save_data(self, data: Data) -> None:
        code

    def _add_dataset(self, key: str, val: Any) -> None:
        if np.isscalar(val):
            self._data = self._data + (val,)
            field = (key, type(val))
        else:
            if val.nelement() == 0: # save tensor with zero-sized dimension as a scalar 0
                # HDF5 compound data type does not allow zero-size dimension
                # ValueError: Zero-sized dimension specified (zero-sized dimension specified)
                self._data = self._data + (0,)
                field = (key, val.numpy().dtype)
            else:
                val = val.numpy() # convert a tensor to numpy
                self._data = self._data + (val,)
                field = (key, val.dtype, val.shape)
        self._fields.append(field)

    def save_heterodata(self, data: HeteroData) -> None:

        self._data = ()
        self._fields = []

        nodes, edges = data.metadata()

        # save node stores
        for node in nodes:
            if "_" in node:
                raise Exception(f'"{node}" is not a valid node store name! Underscores are not supported.')
            for key in data[node].keys():
                self._add_dataset(f'{node}/{key}', data[node][key])

        # save edge stores
        for edge in edges:
            for tmp in edge:
                if "_" in tmp:
                    raise Exception(f'"{tmp}" is not a valid edge store name component! Underscores are not supported.')
            name = "_".join(edge)
            for key in data[edge].keys():
                self._add_dataset(f'{name}/{key}', data[edge][key])

    def save(self, name: str, data: Any) -> None:
        if isinstance(data, Data):
            self.save_data(data)
        elif isinstance(data, HeteroData):
            self.save_heterodata(data)
        else:
            raise NotImplementedError(f'No save method implemented for {type(data)}!')

        # create a scalar dataset of compound data type
        ctype = np.dtype(self._fields)
        ds = self.f.create_dataset(f'/{name}', shape=(), dtype=ctype, data=self._data)
        del ctype, self._fields, self._data, ds

    def load_heterodata(self, name: str) -> HeteroData:
        data = HeteroData()
        # Read the whole dataset idx, dataset name is self.groups[idx]
        group = self.f[name][()]
        dataset_names = group.dtype.names

        for dataset in dataset_names:
            store, attr = dataset.split('/')
            if "_" in store: store = tuple(store.split("_"))
            if attr in ['run','subrun','event','num_nodes']: # scalar
                data[store][attr] = torch.as_tensor(group[dataset][()])
            elif group[dataset].ndim == 0:
                # other zero-dimensional size datasets
                data[store][attr] = torch.LongTensor([[],[]])
            else: # multi-dimension array
                data[store][attr] = torch.as_tensor(group[dataset][:])
        return data
