import os

os.environ["MXNET_ENGINE_TYPE"] = "NaiveEngine"
import mxnet

# os.environ["JAX_PLATFORM_NAME"] = "cpu"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["JAX_ENABLE_X64"] = "true"
import jax

__version__ = '0.0.5'
