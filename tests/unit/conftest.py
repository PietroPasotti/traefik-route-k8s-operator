# Copyright 2022 pietro
# See LICENSE file for licensing details.
import json
from functools import cached_property
from inspect import getmembers

import pytest as pytest
import yaml
from ops.testing import Harness

from charm import TraefikRouteK8SCharm

MODEL_NAME = "model"
REMOTE_APP_NAME = "remote"  # the app requesting ingress
REMOTE_UNIT_NAME = f"{REMOTE_APP_NAME}/0"  # the unit requesting ingress
TRAEFIK_APP_NAME = "traefik"  # the app providing ingress
TRAEFIK_UNIT_NAME = f"{TRAEFIK_APP_NAME}/0"  # the unit providing ingress
SAMPLE_RULE = "Host(`foo.bar/{{juju_model}}-{{juju_unit}}`)"
SAMPLE_URL = "http://foo.bar/{{juju_model}}-{{juju_unit}}"
SAMPLE_CONFIG = {"rule": SAMPLE_RULE, "root_url": SAMPLE_URL}

# mock of the data that the unit requesting ingress might share
# when requesting ingress; as implemented by ipuRequirer
SAMPLE_INGRESS_DATA = {
    "data": {"model": MODEL_NAME, "name": REMOTE_UNIT_NAME, "host": "foo", "port": 42}
}
SAMPLE_INGRESS_DATA_ENCODED = {"data": json.dumps(SAMPLE_INGRESS_DATA["data"])}
# mock of the data traefik might share when providing ingress to our remote unit
SAMPLE_TRAEFIK_DATA = {"data": {REMOTE_UNIT_NAME: {"url": "https://foo.bar/baz"}}}
SAMPLE_TRAEFIK_DATA_ENCODED = {"data": json.dumps(SAMPLE_TRAEFIK_DATA["data"])}


@pytest.fixture
def harness() -> Harness[TraefikRouteK8SCharm]:
    harness = Harness(TraefikRouteK8SCharm)
    harness.set_leader(True)
    # this charm can't be scaled, so we won't ever need leadership checks
    harness.begin_with_initial_hooks()
    yield harness
    harness.cleanup()


def mock_ipu_relation(harness: Harness):
    # mock ipu relation
    ipu_relation_id = harness.add_relation(
        TraefikRouteK8SCharm._ingress_endpoint, REMOTE_APP_NAME
    )
    harness.add_relation_unit(ipu_relation_id, REMOTE_UNIT_NAME)
    return ipu_relation_id


def mock_route_relation(harness):
    # mock traefik_route relation
    route_relation_id = harness.add_relation(
        TraefikRouteK8SCharm._traefik_route_endpoint, TRAEFIK_APP_NAME
    )
    harness.add_relation_unit(route_relation_id, TRAEFIK_UNIT_NAME)
    return route_relation_id


def mock_config(harness):
    # init the config in a good way
    harness.update_config(SAMPLE_CONFIG)


def mock_happy_path(harness: Harness):
    # set the harness up in its 'happy path' scenario: all relations green,
    # config good.
    ipu_relation_id = mock_ipu_relation(harness)
    route_relation_id = mock_route_relation(harness)
    mock_config(harness)

    # reinstantiate the charm, to work around
    # https://github.com/canonical/operator/issues/736
    reinstantiate_charm(harness)
    return ipu_relation_id, route_relation_id


def reinstantiate_charm(harness: Harness):
    charm = harness.charm
    harness.framework._forget(charm)
    harness.framework._forget(charm.on)
    harness.framework._forget(charm.ingress_per_unit)
    harness.framework._forget(charm.ingress_per_unit.on)
    harness.framework._forget(charm.traefik_route)
    harness.framework._forget(charm.traefik_route.on)
    harness._charm = None
    harness.begin()
