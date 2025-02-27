# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Executor factory modules."""
from abc import abstractmethod
import warnings

from ..._ffi.base import string_types
from ..._ffi.registry import get_global_func
from ...runtime import ndarray


class ExecutorFactoryModule:
    """Common interface for executor factory modules
    This class describes the common API of different
    factory modules
    """

    @abstractmethod
    def get_executor_config(self):
        """ Return the internal configuration the executor uses to execute the network """
        raise NotImplementedError

    @abstractmethod
    def get_params(self):
        """Return the compiled parameters."""
        raise NotImplementedError

    @abstractmethod
    def get_lib(self):
        """ Return the generated library"""
        raise NotImplementedError

    def __getitem__(self, item):
        return self.module.__getitem__(item)

    def __iter__(self):
        warnings.warn(
            "legacy graph executor behavior of producing json / lib / params will be "
            "removed in the next release."
            " Please see documents of tvm.contrib.graph_executor.GraphModule for the "
            " new recommended usage.",
            DeprecationWarning,
            2,
        )
        return self

    def __next__(self):
        if self.iter_cnt > 2:
            raise StopIteration

        objs = [self.get_executor_config(), self.lib, self.params]
        obj = objs[self.iter_cnt]
        self.iter_cnt += 1
        return obj


class AOTExecutorFactoryModule(ExecutorFactoryModule):
    """AOT executor factory module.

    Attributes
    ----------
    target : tvm.Target
        The Target used to build this module.
    libmod : tvm.Module
        The module of the corresponding function
    libmod_name: str
        The name of module
    params : dict of str to NDArray
        The parameters of module
    """

    def __init__(self, ir_mod, target, libmod, libmod_name, params):
        self.ir_mod = ir_mod
        self.target = target
        self.lib = libmod
        self.libmod_name = libmod_name
        self.params = params
        self.iter_cnt = 0

    def get_params(self):
        return self.params

    def get_executor_config(self):
        return None

    def get_lib(self):
        return self.lib


class GraphExecutorFactoryModule(ExecutorFactoryModule):
    """Graph executor factory module.
    This is a module of graph executor factory

    Attributes
    ----------
    graph_json_str : the json graph to be deployed in json format output by graph compiler.
        The graph can contain operator(tvm_op) that points to the name of
        PackedFunc in the libmod.
    target : tvm.Target
        The Target used to build this module.
    libmod : tvm.Module
        The module of the corresponding function
    libmod_name: str
        The name of module
    params : dict of str to NDArray
        The parameters of module
    """

    def __init__(self, ir_mod, target, graph_json_str, libmod, libmod_name, params):
        assert isinstance(graph_json_str, string_types)
        fcreate = get_global_func("tvm.graph_executor_factory.create")
        args = []
        for k, v in params.items():
            args.append(k)
            args.append(ndarray.array(v))

        self.ir_mod = ir_mod
        self.target = target
        self.module = fcreate(graph_json_str, libmod, libmod_name, *args)
        self.graph_json = graph_json_str
        self.lib = libmod
        self.libmod_name = libmod_name
        self.params = params
        self.iter_cnt = 0

    def export_library(self, file_name, fcompile=None, addons=None, **kwargs):
        return self.module.export_library(file_name, fcompile, addons, **kwargs)

    def get_params(self):
        return self.params

    def get_graph_json(self):
        return self.graph_json

    def get_executor_config(self):
        return self.graph_json

    def get_lib(self):
        return self.lib
