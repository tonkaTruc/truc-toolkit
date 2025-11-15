import json

import pytest

from tests import log
from dtk.network.interfaces import create_interfaces_dict


@pytest.fixture()
def net_interfaces() -> dict:
    return create_interfaces_dict()


def test_create_interfaces_dict(net_interfaces):
    log.info(json.dumps(net_interfaces, indent=4))
    assert isinstance(net_interfaces, dict)
    assert len(net_interfaces) > 0


def test_interface_vitals(net_interfaces):
    for iface in net_interfaces:
        addrs = [
            addr["address"]
            for addr in net_interfaces[iface]["addresses"]
        ]
        log.info(f"Int: {iface} {addrs}")
        assert isinstance(iface, str)
        assert len(iface) > 0


def test_interface_addr_family(net_interfaces):
    """Verify that the address family strings are valid"""

    for iface in net_interfaces:
        for addr in net_interfaces[iface]["addresses"]:
            log.info(
                f"{iface} - Family: {addr['family']} Addr: {addr['address']}"
            )
