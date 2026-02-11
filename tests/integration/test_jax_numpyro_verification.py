import pytest
import jax
import jax.numpy as jnp
import numpyro
import numpyro.distributions as dist
from jax import random

def test_jax_backend():
    """Verify JAX backend and basic matrix multiplication."""
    # Check available devices
    devices = jax.devices()
    print(f"JAX Devices: {devices}")
    
    # Assert we have at least one device
    assert len(devices) > 0
    
    # Perform a simple matrix multiplication
    key = random.PRNGKey(0)
    x = random.normal(key, (1000, 1000))
    y = jnp.dot(x, x)
    
    # Ensure computation actually happened (block until ready)
    y.block_until_ready()
    assert y.shape == (1000, 1000)

def test_numpyro_sampling():
    """Verify NumPyro basic sampling capability."""
    def model():
        numpyro.sample("x", dist.Normal(0, 1))

    # Run the model once to verify it works
    seed = random.PRNGKey(0)
    trace = numpyro.handlers.trace(numpyro.handlers.seed(model, seed)).get_trace()
    
    assert "x" in trace
    assert trace["x"]["value"].shape == ()
    
    # Try a small MCMC run
    nuts_kernel = numpyro.infer.NUTS(model)
    mcmc = numpyro.infer.MCMC(nuts_kernel, num_warmup=10, num_samples=10, progress_bar=False)
    mcmc.run(seed)
    mcmc.get_samples()
    
    assert mcmc.num_samples == 10
