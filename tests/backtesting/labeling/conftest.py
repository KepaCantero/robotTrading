"""
Minimal conftest for triple barrier tests.
"""

import pytest


@pytest.fixture
def matplotlib_figure():
    """Fixture to manage matplotlib figures."""
    import matplotlib

    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt

    fig = plt.figure()
    yield fig
    plt.close(fig)
