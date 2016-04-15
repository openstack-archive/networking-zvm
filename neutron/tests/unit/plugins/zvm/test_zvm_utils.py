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
Unit tests for the z/VM utils.
"""
import mock
from oslo_config import cfg

from neutron.plugins.zvm.common import exception
from neutron.plugins.zvm.common import utils
from neutron.tests import base


class TestZVMUtils(base.BaseTestCase):

    _FAKE_VSWITCH_NAME = "fakevsw1"
    _FAKE_PORT_NAME = "fake_port_name"
    _FAKE_RET_VAL = 0
    _FAKE_VM_PATH = "fake_vm_path"
    _FAKE_VSWITCH = "fakevsw1"
    _FAKE_VLAN_ID = "fake_vlan_id"
    _FAKE_ZHCP_NODENAME = "fakezhcp"
    _FAKE_ZHCP_USER = 'zhcp_user'
    _FAKE_VDEV = "1000"
    _FAKE_XCAT_NODENAME = "fakexcat"
    _FAKE_XCAT_USER = "fake_xcat_user"
    _FAKE_XCAT_PW = "fake_xcat_password"

    def setUp(self):
        super(TestZVMUtils, self).setUp()
        self.addCleanup(cfg.CONF.reset)
        cfg.CONF.set_override('zvm_xcat_username', self._FAKE_XCAT_USER,
                              group='AGENT')
        cfg.CONF.set_override('zvm_xcat_password', self._FAKE_XCAT_PW,
                              group='AGENT')
        with mock.patch(
            'neutron.plugins.zvm.common.utils.zvmUtils._get_xcat_node_name',
                mock.Mock(return_value=self._FAKE_XCAT_NODENAME)):
            self._utils = utils.zvmUtils()

    def test_couple_nic_to_vswitch(self):
        xcat_req = mock.Mock()
        xcat_req.side_effect = [{'data': [[self._FAKE_VDEV]]},
                                {'data': [['OK']]},
                                {'data': [['OK']]}]
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            ret = self._utils.couple_nic_to_vswitch(self._FAKE_VSWITCH,
                                                self._FAKE_PORT_NAME,
                                                self._FAKE_ZHCP_NODENAME,
                                                "fake_user")
            self.assertEqual(ret, self._FAKE_VDEV)

            url_vdev = ('/xcatws/tables/switch?userName=fake_xcat_user&'
                        'password=fake_xcat_password&format=json&'
                        'col=port&value=fake_port_name&attribute=interface')
            url_couple_nic = ('/xcatws/nodes/fakezhcp/dsh?userName='
                'fake_xcat_user&password=fake_xcat_password&format=json')
            body_couple_nic_dm = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Adapter_Connect_Vswitch_DM -T fake_user'
                ' -v 1000 -n fakevsw1')]
            body_couple_nic = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Adapter_Connect_Vswitch -T fake_user'
                ' -v 1000 -n fakevsw1')]

            calls = [mock.call('GET', url_vdev),
                    mock.call('PUT', url_couple_nic, body_couple_nic_dm),
                    mock.call('PUT', url_couple_nic, body_couple_nic)]
            xcat_req.assert_has_calls(calls)

    def test_grant_user(self):
        xcat_req = mock.Mock()
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.grant_user(self._FAKE_ZHCP_NODENAME,
                                   self._FAKE_VSWITCH,
                                   "fake_user")
            url_grant_user = ('/xcatws/nodes/fakezhcp/dsh?userName='
                    'fake_xcat_user&password=fake_xcat_password&format=json')
            body_grant_user = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Vswitch_Set_Extended -T fake_user'
               ' -k switch_name=fakevsw1 -k grant_userid=fake_user')]
            xcat_req.assert_called_with('PUT', url_grant_user, body_grant_user)

    def test_uncouple_nic_from_vswitch(self):
        xcat_req = mock.Mock()
        xcat_req.side_effect = [{'data': [[self._FAKE_VDEV]]},
                                {'data': [['OK']]},
                                {'data': [['OK']]}]
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.uncouple_nic_from_vswitch(self._FAKE_VSWITCH,
                                                  self._FAKE_PORT_NAME,
                                                  self._FAKE_ZHCP_NODENAME,
                                                  "fake_user")

            url_vdev = ('/xcatws/tables/switch?userName=fake_xcat_user&'
                        'password=fake_xcat_password&format=json&'
                        'col=port&value=fake_port_name&attribute=interface')
            url_uncouple_nic = ('/xcatws/nodes/fakezhcp/dsh?userName='
                'fake_xcat_user&password=fake_xcat_password&format=json')
            body_uncouple_nic_dm = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Adapter_Disconnect_DM -T fake_user'
                ' -v 1000')]
            body_uncouple_nic = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Adapter_Disconnect -T fake_user -v 1000')]

            calls = [mock.call('GET', url_vdev),
                    mock.call('PUT', url_uncouple_nic, body_uncouple_nic_dm),
                    mock.call('PUT', url_uncouple_nic, body_uncouple_nic)]
            xcat_req.assert_has_calls(calls)

    def test_revoke_user(self):
        res = {'errorcode': [['0']]}
        xcat_req = mock.MagicMock()
        xcat_req.return_value = res
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.revoke_user(self._FAKE_ZHCP_NODENAME,
                                    self._FAKE_VSWITCH_NAME,
                                    "fake_user")
            url_revoke_user = ('/xcatws/nodes/fakezhcp/dsh?userName='
                    'fake_xcat_user&password=fake_xcat_password&format=json')
            body_revoke_user = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Vswitch_Set_Extended -T fake_user'
               ' -k switch_name=fakevsw1 -k revoke_userid=fake_user')]
            xcat_req.assert_called_with('PUT', url_revoke_user,
                                        body_revoke_user)

    def test_check_vswitch_status(self):
        self._utils.get_zhcp_userid = mock.MagicMock(
                                    return_value=self._FAKE_ZHCP_USER)
        xcat_req = mock.Mock()
        res = {'data': [[u'zhcp: VSWITCH:  Name: L3PUB001\nzhcp:   '
                         'Real device: 6263\n Real device: 0000\n']],
               'errorcode': [[u'0']]}      # vswitch does exist
        xcat_req.return_value = res
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            ret = self._utils._check_vswitch_status(self._FAKE_ZHCP_NODENAME,
                                self._FAKE_VSWITCH_NAME)
            self.assertEqual(ret, ['6263', '0000'])
            url = ('/xcatws/nodes/fakezhcp/dsh?userName=fake_xcat_user'
                   '&password=fake_xcat_password&format=json')
            body = [('command=/opt/zhcp/bin/smcli'
                    ' Virtual_Network_Vswitch_Query -T zhcp_user -s fakevsw1')]
            xcat_req.assert_any_call('PUT', url, body)

    def test_add_vswitch_exist_not_changed(self):
        self._utils.get_zhcp_userid = mock.MagicMock(
                                    return_value=self._FAKE_ZHCP_USER)
        res = {'errorcode': [['0']]}
        xcat_req = mock.MagicMock()
        xcat_req.return_value = res
        self._utils._check_vswitch_status = mock.MagicMock(
                                        return_value=['6263'])

        with mock.patch.object(utils, "LOG") as log:
            self._utils.add_vswitch(self._FAKE_ZHCP_NODENAME,
                                    self._FAKE_VSWITCH_NAME,
                                    '6263,6266')
            log.debug.assert_called_with('vswitch %s is not changed',
                                    self._FAKE_VSWITCH_NAME)

    def test_add_vswitch_exist_changed(self):
        res = {'errorcode': [['0']]}
        self._utils.get_zhcp_userid = mock.MagicMock(
                                    return_value=self._FAKE_ZHCP_USER)
        xcat_req = mock.MagicMock()
        xcat_req.return_value = res
        self._utils._check_vswitch_status = mock.MagicMock(
                                        return_value=['6260'])
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            with mock.patch.object(utils, "LOG") as log:
                self._utils.add_vswitch(self._FAKE_ZHCP_NODENAME,
                                        self._FAKE_VSWITCH_NAME,
                                        self._FAKE_VDEV)
                log.info.assert_called_with('change vswitch %s done.',
                                            self._FAKE_VSWITCH_NAME)

    def test_add_vswitch(self):
        self._utils.get_zhcp_userid = mock.MagicMock()
        self._utils.get_zhcp_userid.side_effect = [self._FAKE_ZHCP_USER,
                                                self._FAKE_ZHCP_USER,
                                                self._FAKE_ZHCP_USER]
        xcat_req = mock.Mock()
        res = {'errorcode': [['0']], 'data': [['']]}      # vswitch does exist
        res_err = {'errorcode': [['1']]}  # vswitch does not exist
        xcat_req.side_effect = [res_err, res, res]
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.add_vswitch(self._FAKE_ZHCP_NODENAME,
                                self._FAKE_VSWITCH_NAME,
                                self._FAKE_VDEV,
                                vid=[self._FAKE_VLAN_ID])
            url = ('/xcatws/nodes/fakezhcp/dsh?userName=fake_xcat_user'
                   '&password=fake_xcat_password&format=json')
            body = [('command=/opt/zhcp/bin/smcli'
                    ' Virtual_Network_Vswitch_Create -T zhcp_user -n fakevsw1'
                    ' -r 1000 -c 1 -q 8 -e 0 -t 2 -v f-a'
                    ' -p 1 -u 1 -G 2 -V 1')]
            xcat_req.assert_any_call('PUT', url, body)

    def test_set_vswitch_rdev(self):
        res = {'errorcode': [['0']]}
        self._utils.get_zhcp_userid = mock.MagicMock(
                                    return_value=self._FAKE_ZHCP_USER)
        xcat_req = mock.MagicMock()
        xcat_req.return_value = res
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils._set_vswitch_rdev(self._FAKE_ZHCP_NODENAME,
                                          self._FAKE_VSWITCH, self._FAKE_VDEV)
            url_set_vswitch = ('/xcatws/nodes/fakezhcp/dsh?userName='
                    'fake_xcat_user&password=fake_xcat_password&format=json')
            body_set_vswitch = [('command=/opt/zhcp/bin/smcli'
                ' Virtual_Network_Vswitch_Set_Extended -T zhcp_user'
               ' -k switch_name=fakevsw1 -k real_device_address=1000')]
            xcat_req.assert_called_with('PUT', url_set_vswitch,
                                        body_set_vswitch)

    def test_set_vswitch_port_vlan_id(self):
        self._utils._get_nic_settings = mock.MagicMock(return_value='inst1')
        xcat_req = mock.Mock()
        xcat_req.return_value = "OK"
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.set_vswitch_port_vlan_id(self._FAKE_VLAN_ID,
                                                self._FAKE_PORT_NAME,
                                                self._FAKE_ZHCP_NODENAME,
                                                self._FAKE_VSWITCH)
            url = ('/xcatws/nodes/fakezhcp/dsh?userName=fake_xcat_user'
                   '&password=fake_xcat_password&format=json')
            body = [('command=/opt/zhcp/bin/smcli'
                    ' Virtual_Network_Vswitch_Set_Extended -T inst1'
                    ' -k grant_userid=inst1 -k switch_name=fakevsw1'
                    ' -k user_vlan_id=fake_vlan_id')]
            xcat_req.assert_called_with('PUT', url, body)

    def test_get_nic_ids(self):
        xcat_req = mock.Mock()
        data = 'fnode,fswitch,fport,fvlan,finf,-,false'
        xcat_req.return_value = {'data': [[(
            '#node,switch,port,vlan,interface,comments,disable'), data]]}
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            ret = self._utils.get_nic_ids()
            self.assertEqual(ret, [data])
            url = ('/xcatws/tables/switch?userName=fake_xcat_user&'
                   'password=fake_xcat_password&format=json')
            xcat_req.assert_called_with('GET', url)

    def test_get_node_from_port(self):
        xcat_req = mock.Mock()
        xcat_req.side_effect = [{'data': [[self._FAKE_ZHCP_NODENAME]]}]
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            ret = self._utils.get_node_from_port(self._FAKE_PORT_NAME)
            self.assertEqual(ret, self._FAKE_ZHCP_NODENAME)
            url = ('/xcatws/tables/switch?userName=fake_xcat_user&'
                   'password=fake_xcat_password&format=json&'
                   'col=port&value=fake_port_name&attribute=node')
            calls = [mock.call('GET', url)]
            xcat_req.assert_has_calls(calls)

    def _test_get_userid_from_node(self, node, user):
        xcat_req = mock.Mock()
        xcat_req.return_value = {'data': [[user]]}
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            ret = self._utils.get_zhcp_userid(self._FAKE_ZHCP_NODENAME)
            url = ('/xcatws/tables/zvm?userName=fake_xcat_user&'
                   'password=fake_xcat_password&format=json&col=node&'
                   'value=%s&attribute=userid' % node)
            xcat_req.assert_called_with('GET', url)
        return ret

    def test_get_userid_from_node(self):
        self.assertEqual(self._test_get_userid_from_node(
                                    self._FAKE_ZHCP_NODENAME,
                                    self._FAKE_ZHCP_USER),
                         self._FAKE_ZHCP_USER)

    def test_get_zhcp_userid(self):
        self.assertEqual(self._test_get_userid_from_node(
                                    self._FAKE_ZHCP_NODENAME,
                                    self._FAKE_ZHCP_USER),
                         self._FAKE_ZHCP_USER)

    def test_put_user_direct_online(self):
        xcat_req = mock.Mock()
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.put_user_direct_online(self._FAKE_ZHCP_NODENAME,
                                               'inst1')
            url = ('/xcatws/nodes/fakezhcp/dsh?userName=fake_xcat_user&'
                'password=fake_xcat_password&format=json')
            body = [('command=/opt/zhcp/bin/smcli'
                ' Static_Image_Changes_Immediate_DM -T inst1')]
            xcat_req.assert_called_with('PUT', url, body)

    def test_update_xcat_switch(self):
        xcat_req = mock.Mock()
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            self._utils.update_xcat_switch(self._FAKE_PORT_NAME,
                                        self._FAKE_VSWITCH,
                                        self._FAKE_VLAN_ID)
            url = ('/xcatws/tables/switch?userName=fake_xcat_user&'
                   'password=fake_xcat_password&format=json')
            body = ['port=fake_port_name switch.switch=fakevsw1'
                    ' switch.vlan=fake_vlan_id']
            xcat_req.assert_called_with('PUT', url, body)

    def _verify_query_nic(self, result, xcat_req):
        url = ('/xcatws/nodes/fakexcat/dsh?userName=fake_xcat_user&'
               'password=fake_xcat_password&format=json')
        body = ['command=vmcp q v nic 800']
        xcat_req.assert_any_with('PUT', url, body)

    @mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request')
    @mock.patch('neutron.plugins.zvm.common.utils.zvmUtils.'
                'get_userid_from_node')
    def test_create_xcat_mgt_network_exist(self, mk_get_uid, mk_xcat_req):
        nic_def = ('Adapter 0800.P00 Type: QDIO      '
                   'Name: UNASSIGNED  Devices: 3\n'
                   'MAC: 02-00-01-00-01-66         '
                   'VSWITCH: SYSTEM XCATVSW2\n')

        mk_get_uid.return_value = 'fakeuser'
        mk_xcat_req.side_effect = [
            {'data': [[nic_def]]},
            {'data': [['inet 10.1.0.1  netmask 255.255.0.0'
                       '  broadcast 10.1.255.255']],
             'errorcode': [['0']]}
        ]
        self.assertRaises(exception.zVMConfigException,
                          self._utils.create_xcat_mgt_network,
                          self._FAKE_ZHCP_NODENAME,
                          "10.1.1.1",
                          "255.255.0.0",
                          self._FAKE_VSWITCH)

    @mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request')
    @mock.patch('neutron.plugins.zvm.common.utils.zvmUtils.'
                'get_userid_from_node')
    def test_create_xcat_mgt_network_not_exist(self, mk_get_uid, mk_xcat_req):
        nic_undef = ['HCPNDQ040E Device 0800 does not exist']
        mk_get_uid.return_value = 'fakeuser'
        mk_xcat_req.side_effect = [{'data': [nic_undef]}, {}]

        self._utils.create_xcat_mgt_network(self._FAKE_ZHCP_NODENAME,
                                            "10.1.1.1",
                                            "255.255.0.0",
                                            self._FAKE_VSWITCH)
        url = ('/xcatws/nodes/fakexcat/dsh?userName=fake_xcat_user&'
               'password=fake_xcat_password&format=json')
        body = ['command=vmcp define nic 0800 type qdio\n'
                'vmcp couple 0800 system fakevsw1\n'
                '/usr/bin/perl /usr/sbin/sspqeth2.pl -a 10.1.1.1'
         ' -d 0800 0801 0802 -e enccw0.0.0800 -m 255.255.0.0 -g 10.1.1.1']
        mk_xcat_req.assert_called_with('PUT', url, body)

    def test_re_grant_user(self):
        '''We assume there is three nodes valid in the xCAT MN db, they are:
        node1, node2, node4. We mock _MAX_REGRANT_USER_NUMBER to 2. So the
        process of regrant has two steps. Fisrt grant two nodes and then
        grant one node.
        '''

        fake_port_info = ['node1,switch,port1,10,inf1,fakezhcp,false',
                          'node2,switch,port2,10,inf2,fakezhcp,false',
                          # node3's zhcp field is invalid
                          'node3,switch,port3,10,inf3,zhcp,false',
                          'node4,switch,port3,10,inf4,fakezhcp,false']
        self._utils.get_nic_ids = mock.MagicMock(return_value=fake_port_info)

        fake_user_id = ['#node,hcp,userid,nodetype,parent,comments,disable',
                        '"opnstk1","zhcp.ibm.com",,,,,',    # invalid record
                        '"node1","fakezhcp","user01",,,,',
                        '"zhcp2","zhcp2.ibm.com","ZHCP",,,,',  # invalid record
                        '"node2","fakezhcp","user02",,,,',
                        '"node3","zhcp","user03",,,,',      # invalid record
                        '"node4","fakezhcp","user04",,,,']

        xcat_req = mock.Mock()
        xcat_req.side_effect = [{'data': [fake_user_id]},
                    {'data': [['OK']]},  # run_command step 1, regrant two node
                    {'data': [['OK']]},  # run_command remove
                    {'data': [['OK']]},  # run_command step 2
                    {'data': [['OK']]}]  # run_command remove

        with mock.patch.object(utils.zvmUtils, '_MAX_REGRANT_USER_NUMBER', 2):
            with mock.patch(
                    'neutron.plugins.zvm.common.xcatutils.xcat_request',
                    xcat_req):
                self._utils.re_grant_user(self._FAKE_ZHCP_NODENAME)
                url_command = ('/xcatws/nodes/fakezhcp/dsh?userName='
                    'fake_xcat_user&password=fake_xcat_password&format=json')

                valid_users = [1, 2, 4]
                last_user = None

                # re_grant_user uses a dict to keep the ports info, so we don't
                # know the order, which nodes are reganted in step 1 and which
                # one is regranted in step 2. We will try to find the node
                # removed in step 2 first, because this is easier. Then we
                # verify the step 1.
                for i in valid_users:
                    cmd_vsw_couple = (
                        'command=echo -e "#!/bin/sh\n/opt/zhcp/bin/smcli'
                        ' Virtual_Network_Vswitch_Set_Extended -T user0%s -k'
                        ' switch_name=switch -k grant_userid=user0%s'
                        ' -k user_vlan_id=10" > grant.sh' % (i, i))
                    if mock.call('PUT', url_command,
                            [cmd_vsw_couple]) in xcat_req.call_args_list:
                        last_user = i
                        break
                self.assertTrue(last_user)
                # remove the node from valid users, so we can verify if the
                # other two nodes has been regranted via the valid_users.
                del(valid_users[valid_users.index(last_user)])

                body_cmd_node_1 = (
                    'command=echo -e "#!/bin/sh\n'
                    '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
                    ' -T user0%s -k switch_name=switch -k grant_userid=user0%s'
                    ' -k user_vlan_id=10\n' %
                    (valid_users[0], valid_users[0])) + (
                    '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
                    ' -T user0%s -k switch_name=switch -k grant_userid=user0%s'
                    ' -k user_vlan_id=10" > grant.sh' %
                    (valid_users[1], valid_users[1]))

                body_cmd_node_2 = (
                    'command=echo -e "#!/bin/sh\n'
                    '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
                    ' -T user0%s -k switch_name=switch -k grant_userid=user0%s'
                    ' -k user_vlan_id=10\n' %
                    (valid_users[1], valid_users[1])) + (
                    '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
                    ' -T user0%s -k switch_name=switch -k grant_userid=user0%s'
                    ' -k user_vlan_id=10" > grant.sh' %
                    (valid_users[0], valid_users[0]))
                self.assertTrue(
                    (mock.call('PUT', url_command, [body_cmd_node_1])
                    in xcat_req.call_args_list) or
                    (mock.call('PUT', url_command, [body_cmd_node_2])
                    in xcat_req.call_args_list))

    def test_query_xcat_uptime(self):
        xcat_uptime = {'data':
                [['2014-06-11 02:41:15']]}
        xcat_req = mock.Mock(return_value=xcat_uptime)
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            with mock.patch.object(utils.zvmUtils, "get_userid_from_node",
                    mock.Mock(return_value='xcat')):
                ret = self._utils.query_xcat_uptime()
                self.assertEqual(ret, '2014-06-11 02:41:15')
                url = ('/xcatws/nodes/fakexcat/dsh?userName=fake_xcat_user&'
                       'password=fake_xcat_password&format=json')
                body = ['command=date -d "$(awk -F. \'{print $1}\' '
                        '/proc/uptime) second ago" +"%Y-%m-%d %H:%M:%S"']
                xcat_req.assert_called_with('PUT', url, body)

    def test_query_zvm_uptime(self):
        fake_ret = ('timezone\ncurrent time\nversion\nGen time\n'
                'zhcp: The z/VM CP IPL time: 2014-06-11 01:38:37 EDT\n'
                'storage\n')
        zvm_uptime = {'data': [[fake_ret]]}
        xcat_req = mock.Mock(return_value=zvm_uptime)
        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
                        xcat_req):
            ret = self._utils.query_zvm_uptime(self._FAKE_ZHCP_NODENAME)
            self.assertEqual(ret, '2014-06-11 01:38:37 EDT')
            url = ('/xcatws/nodes/fakezhcp/dsh?userName=fake_xcat_user&'
                   'password=fake_xcat_password&format=json')
            body = ['command=/opt/zhcp/bin/smcli System_Info_Query']
            xcat_req.assert_called_with('PUT', url, body)

    def test_add_nic_to_user_direct(self):
        nic_info = {}
        nic_info['port_id'] = '0'
        nic_info['mac'] = '00:01:02:03:04:05'
        nic_info['vswitch'] = 'vs1'
        self._utils._get_nic_settings = mock.MagicMock(return_value='1000')
        xcat_req = mock.Mock()

        with mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request',
            xcat_req):
            self._utils.add_nic_to_user_direct('dummy', nic_info)
            url = ('/xcatws/vms/dummy?userName=fake_xcat_user&'
                   'password=fake_xcat_password&format=json')
            command = ("Image_Definition_Update_DM -T %userid% "
                       "-k 'NICDEF=VDEV=1000 TYPE=QDIO "
                       "MACID=00:01:02:03:04:05 "
                       "LAN=SYSTEM "
                       "SWITCHNAME=vs1'")
            body = ['--smcli', command]
            calls = [mock.call('PUT', url, body)]
            xcat_req.assert_has_calls(calls)
