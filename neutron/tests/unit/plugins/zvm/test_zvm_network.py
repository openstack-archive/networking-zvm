# Copyright 2014 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Unit tests for the z/VM network.
"""

import mock
from oslo_config import cfg

from neutron.plugins.zvm.agent import zvm_network
from neutron.plugins.zvm.common import utils as zvmutils
from neutron.tests import base


SDK_URL = 'https://10.10.10.1:8080'
FLAT_NETWORKS = ['flat_net1', '9dotvsw']
VLAN_NETWORKS = ['vlan_net1:100:500', '10dotvsw:10:100']
NETWORK_MAPS = {'vlan_net1': [(100, 500)], 'flat_net1': [],
                '9dotvsw': [], '10dotvsw': [(10, 100)]}


class TestZVMNetwork(base.BaseTestCase):

    _FAKE_NETWORK_VLAN_RANGES = "fakevsw1:1:4094,fakevsw2,fakevsw3:2:2999"

    @mock.patch.object(zvmutils.zVMConnectorRequestHandler, 'call')
    def setUp(self, call):
        super(TestZVMNetwork, self).setUp()
        cfg.CONF.set_override('flat_networks', FLAT_NETWORKS,
                              group='ml2_type_flat')
        cfg.CONF.set_override('network_vlan_ranges', VLAN_NETWORKS,
                              group='ml2_type_vlan')
        cfg.CONF.set_override('cloud_connector_url', SDK_URL,
                              group='AGENT')
        call.return_value = []
        self._zvm_network = zvm_network.zvmNetwork()

    def test_init_driver(self):
        self.assertIsInstance(self._zvm_network._requesthandler,
                              zvmutils.zVMConnectorRequestHandler)

    def test_get_network_maps(self):
        maps = self._zvm_network.get_network_maps()
        self.assertEqual(maps, NETWORK_MAPS)
