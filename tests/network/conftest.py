import pytest


@pytest.fixture
def mcast_client():
    """Create a multicast client fixture"""
    from dtk.network.multicast import MulticastMgr

    mgr = MulticastMgr(switch_ip="192.168.0.1")
    return mgr
