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
Unit tests for neutron z/VM driver
"""

import mock
from oslo_config import cfg

from neutron.plugins.zvm.agent import zvm_neutron_agent
from neutron.plugins.zvm.common import exception
from neutron.tests import base

FLAT_NETWORKS = ['flat_net1']
VLAN_NETWORKS = ['vlan_net1:100:500']
NET_UUID = 'zvm-net-uuid'
PORT_UUID = 'zvm-port-uuid'


class FakeLoopingCall(object):
    def __init__(self, fake_time):
        self.fake_time = fake_time

    def start(self, interval=0):
        self.fake_time()


class TestZVMNeutronAgent(base.BaseTestCase):

    _FAKE_XCAT_USER = "fake_xcat_user"
    _FAKE_XCAT_PW = "fake_xcat_password"
    _FAKE_HOST = {'zvm_host': 'zvm_host',
                  'ipl_time': 'zvm uptime 1'}

    def setUp(self):
        super(TestZVMNeutronAgent, self).setUp()
        self.addCleanup(cfg.CONF.reset)
        cfg.CONF.set_override('rpc_backend',
                              'neutron.openstack.common.rpc.impl_fake')
        cfg.CONF.set_override('flat_networks', FLAT_NETWORKS,
                              group='ml2_type_flat')
        cfg.CONF.set_override('network_vlan_ranges', VLAN_NETWORKS,
                              group='ml2_type_vlan')

        mock.patch('neutron.openstack.common.loopingcall.'
                   'FixedIntervalLoopingCall',
                  new=FakeLoopingCall)

        with mock.patch(
                'neutron.plugins.zvm.common.utils.zvmUtils') as mock_Utils:
            with mock.patch(
                    'zvmsdk.api.SDKAPI') as mock_SDKAPI:
                APIinstance = mock_SDKAPI.return_value
                host_get_info = mock.MagicMock(return_value=self._FAKE_HOST)
                APIinstance.host_get_info = host_get_info

                instance = mock_Utils.return_value
                net_attrs = {'fake_uuid1': {
                        'vswitch': 'fake_vsw', 'userid': 'fake_user1'}}
                instance.re_grant_user = mock.MagicMock(
                                                return_value=net_attrs)
                instance.query_xcat_uptime = mock.MagicMock(
                                                return_value="xcat uptime 1")

                with mock.patch(
                    'zvmsdk.utils.create_xcat_mgt_network',
                    mock.MagicMock()):
                    self.agent = zvm_neutron_agent.zvmNeutronAgent()
                    self.agent.plugin_rpc = mock.Mock()
                    self.agent.context = mock.Mock()
                    self.agent.agent_id = mock.Mock()

    def test_port_bound_vlan(self):
        vid = 100
        with mock.patch.object(zvm_neutron_agent, "LOG") as log:
            self._test_port_bound('vlan', vid)
            log.info.assert_called_with('Binding VLAN, VLAN ID: '
                                        '%(segmentation_id)s, port_id: '
                                        '%(port_id)s',
                                        {'segmentation_id': 100,
                                         'port_id': 1000})

    def test_port_bound_flat(self):
        with mock.patch.object(zvm_neutron_agent, "LOG") as log:
            self._test_port_bound('flat')
            log.info.assert_called_with('Bind %s port done', 1000)

    def _test_port_bound(self, network_type, vid=None):
        port = 1000
        net_uuid = NET_UUID
        mock_enable_vlan = mock.MagicMock()
        enable_vlan = False

        if network_type == 'vlan':
            enable_vlan = True

        with mock.patch.multiple(
                self.agent._sdk_api,
                vswitch_grant_user=mock.MagicMock(),
                vswitch_set_vlan_id_for_user=mock_enable_vlan):

            self.agent.port_bound(port, net_uuid, network_type, None,
                                  vid, 'fake_user')

            self.assertEqual(enable_vlan, mock_enable_vlan.called)

    def test_port_unbound(self):
        # port_unbound just call utils.revoke_user, revoke_user is covered
        # in test_zvm_utils
        pass

    def test_treat_devices_added_returns_true_for_missing_device(self):
        attrs = {'get_device_details.side_effect': Exception()}
        self.agent.plugin_rpc.configure_mock(**attrs)
        # no exception should be raised
        self.agent._treat_devices_added([])

    def test_treat_devices_added_down_port(self):
        details = dict(port_id='added_port_down', physical_network='vsw',
                       segmentation_id='10', network_id='fake_net',
                       mac_address='00:11:22:33:44:55',
                       network_type='flat', admin_state_up=False)
        attrs = {'get_device_details.return_value': details}
        self.agent.plugin_rpc.configure_mock(**attrs)
        with mock.patch.object(self.agent, "_treat_vif_port",
                    mock.Mock(return_value=('fake_node', 'fake_user'))):
            self.agent._treat_devices_added(['added_port_down'])
            self.assertTrue(self.agent.plugin_rpc.update_device_down.called)

    def test_treat_devices_added_up_port(self):
        details = dict(port_id='added_port', physical_network='vsw',
                       segmentation_id='10', network_id='fake_net',
                       mac_address='00:11:22:33:44:55',
                       network_type='flat', admin_state_up=True)
        attrs = {'get_device_details.return_value': details}
        self.agent.plugin_rpc.configure_mock(**attrs)
        with mock.patch.object(self.agent, "_treat_vif_port",
                    mock.Mock(return_value=('fake_node', 'fake_user'))):
            self.agent._treat_devices_added(['added_port'])
            self.assertTrue(self.agent.plugin_rpc.get_device_details.called)

    def test_treat_devices_added_missing_port_id(self):
        details = mock.MagicMock()
        details.__contains__.side_effect = lambda x: False
        attrs = {'get_device_details.return_value': details}
        self.agent.plugin_rpc.configure_mock(**attrs)
        with mock.patch.object(zvm_neutron_agent, "LOG") as log:
            self.agent._treat_devices_added(['unknown_port'])
            self.assertTrue(log.warning.called)

    def test_treat_devices_removed_returns_true_for_missing_device(self):
        attrs = {'update_device_down.side_effect': Exception()}
        self.agent.plugin_rpc.configure_mock(**attrs)
        devices = ['fake_uuid1']
        with mock.patch.object(zvm_neutron_agent, "LOG") as log:
            self.agent._treat_devices_removed(devices)
            self.assertTrue(log.exception.called)

    def test_treat_devices_removed(self):
        devices = ['unknown_port', 'fake_uuid1']
        with mock.patch.object(zvm_neutron_agent, "LOG") as log:
            self.agent._treat_devices_removed(devices)
            log.warning.assert_called_with('Can\'t find port %s in zvm agent',
                                        'unknown_port')
            self.assertTrue(self.agent.plugin_rpc.update_device_down.called)

    @mock.patch('neutron.plugins.zvm.common.utils.zvmUtils.'
                'get_nic_settings')
    def test_port_update_up(self, get_nic):
        get_nic.retrun_value = 'vdev'

        with mock.patch.object(self.agent.plugin_rpc,
                        "update_device_up") as rpc:
            with mock.patch.object(self.agent._sdk_api,
                        "guest_nic_couple_to_vswitch") as couple:
                self.agent.port_update(None, port={'id': 'fake_uuid1',
                                                'admin_state_up': True})
                self.assertTrue(rpc.called)
                self.assertTrue(couple.called)

    @mock.patch('neutron.plugins.zvm.common.utils.zvmUtils.'
                'get_nic_settings')
    def test_port_update_down(self, get_nic):
        get_nic.retrun_value = 'vdev'
        with mock.patch.object(self.agent.plugin_rpc,
                        "update_device_down") as rpc:
            with mock.patch.object(self.agent._sdk_api,
                        "guest_nic_uncouple_from_vswitch") as couple:
                self.agent.port_update(None, port={'id': 'fake_uuid1',
                                                'admin_state_up': False})
                self.assertTrue(rpc.called)
                self.assertTrue(couple.called)

    # Test agent state report
    def test_report_state(self):
        with mock.patch.object(self.agent.state_rpc,
                               "report_state") as report_st:
            self.agent._report_state()
            report_st.assert_called_with(self.agent.context,
                                         self.agent.agent_state)
            self.assertNotIn("start_flag", self.agent.agent_state)

    def test_treat_vif_port(self):
        with mock.patch.object(self.agent, "port_bound") as bound:
            self.agent._treat_vif_port('port_id', 'network_id', 'flat',
                                    'vsw1', '10', True)
            self.assertTrue(bound.called)

        self.agent._treat_vif_port('port_id', 'network_id', 'flat',
                                   'vsw1', '10', False)
        self.assertTrue(self.agent._sdk_api.vswitch_grant_user.called)

    def test_handle_restart_zvm(self):
        q_xcat = mock.MagicMock(return_value="xcat uptime 2")
        re_grant = mock.MagicMock()
        host_info = {'zvm_host': 'zvm_host',
                     'ipl_time': 'zvm uptime 2'}
        g_info = mock.MagicMock(return_value=host_info)

        with mock.patch.multiple(
                self.agent._utils,
                query_xcat_uptime=q_xcat,
                re_grant_user=re_grant):
            with mock.patch.multiple(
                    self.agent._sdk_api,
                    host_get_info=g_info):
                with mock.patch(
                        'zvmsdk.utils.create_xcat_mgt_network',
                        mock.MagicMock()):
                    self.agent._restart_handler.send(None)
                    self.assertTrue(q_xcat.called)
                    self.assertTrue(g_info.called)
                    self.assertTrue(re_grant.called)

    def test_handle_restart_zvm_exception(self):
        i_xcat = mock.MagicMock(side_effect=exception.zVMConfigException(
                                                msg="xcat Config exception"))
        with mock.patch.object(self.agent, "_init_xcat_mgt",
                               i_xcat):
            self.agent._restart_handler.send(None)
            self.assertRaises(exception.zVMConfigException,
                              self.agent._handle_restart)

    def test_has_min_version(self):
        self.agent._xcat_version = '1.2.3.4'
        self.assertFalse(self.agent.has_min_version((1, 3, 3, 4)))
        self.assertTrue(self.agent.has_min_version((1, 1, 3, 5)))
        self.assertTrue(self.agent.has_min_version(None))

    def test_has_version(self):
        xcat_ver = (1, 2, 3, 4)
        self.agent._xcat_version = '1.2.3.4'
        self.assertTrue(self.agent.has_version(xcat_ver))

        for xcat_ver_ in [(1, 1, 3, 4), (1, 3, 3, 2)]:
            self.assertFalse(self.agent.has_version(xcat_ver_))

        self.assertTrue(self.agent.has_version(None))
