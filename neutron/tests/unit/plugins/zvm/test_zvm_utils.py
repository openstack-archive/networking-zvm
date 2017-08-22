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

from neutron.plugins.zvm.common import utils
from neutron.tests import base
from zvmsdk import utils as zvmutils


class TestZVMUtils(base.BaseTestCase):

    _FAKE_VSWITCH_NAME = "fakevsw1"
    _FAKE_PORT_NAME = "fake_port_name"
    _FAKE_VLAN_ID = "fake_vlan_id"
    _FAKE_ZHCP_NODENAME = "fakezhcp"
    _FAKE_XCAT_NODENAME = "fakexcat"

    def setUp(self):
        super(TestZVMUtils, self).setUp()
        self._xcat_url = zvmutils.get_xcat_url()
        self.addCleanup(cfg.CONF.reset)

        with mock.patch(
            'neutron.plugins.zvm.common.utils.zvmUtils._get_xcat_node_name',
                mock.Mock(return_value=self._FAKE_XCAT_NODENAME)):
            self._utils = utils.zvmUtils()

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_nic_ids(self, xrequest):
        xrequest.return_value = {"data": [["test1", "test2"]]}
        data = 'fnode,fswitch,fport,fvlan,finf,-,false'
        xrequest.return_value = {'data': [[(
            '#node,switch,port,vlan,interface,comments,disable'), data]]}
        addp = ''
        url = self._xcat_url.tabdump("/switch", addp)
        info = self._utils.get_nic_ids()
        xrequest.assert_called_with('GET', url)
        self.assertEqual(info, [data])

    @mock.patch.object(utils.zvmUtils, 'get_nic_settings')
    def test_get_node_from_port(self, get_nic):
        self._utils.get_node_from_port(self._FAKE_PORT_NAME)
        get_nic.assert_called_once_with(self._FAKE_PORT_NAME, get_node=True)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_userid_from_node(self, xrequest):
        xrequest.return_value = {'data': [["fake_user"]]}
        addp = '&col=node&value=%s&attribute=userid' % self._FAKE_ZHCP_NODENAME
        url = self._xcat_url.gettab("/zvm", addp)
        ret = self._utils.get_userid_from_node(self._FAKE_ZHCP_NODENAME)
        xrequest.assert_called_with('GET', url)
        self.assertEqual(ret, "fake_user")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_re_grant_user(self, xrequest):
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

        xrequest.side_effect = [{'data': [fake_user_id]},
                    {'data': [['OK']]},  # run_command step 1, regrant two node
                    {'data': [['OK']]},  # run_command remove
                    {'data': [['OK']]},  # run_command step 2
                    {'data': [['OK']]}]  # run_command remove

        with mock.patch.object(utils.zvmUtils, '_MAX_REGRANT_USER_NUMBER', 2):
            self._utils.re_grant_user(self._FAKE_ZHCP_NODENAME)
            url_command = self._xcat_url.xdsh("/%s"
                                              % self._FAKE_ZHCP_NODENAME)
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
                        [cmd_vsw_couple]) in xrequest.call_args_list:
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
                in xrequest.call_args_list) or
                (mock.call('PUT', url_command, [body_cmd_node_2])
                in xrequest.call_args_list))

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_query_xcat_uptime(self, xrequest):
        xrequest.return_value = {'data': [['2014-06-11 02:41:15']]}
        url = self._xcat_url.xdsh("/%s" % self._FAKE_XCAT_NODENAME)
        cmd = 'date -d "$(awk -F. \'{print $1}\' /proc/uptime) second ago"'
        cmd += ' +"%Y-%m-%d %H:%M:%S"'
        xdsh_commands = 'command=%s' % cmd
        body = [xdsh_commands]
        ret = self._utils.query_xcat_uptime()
        xrequest.assert_called_with('PUT', url, body)
        self.assertEqual(ret, '2014-06-11 02:41:15')
