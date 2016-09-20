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

import re

from oslo_config import cfg
from oslo_log import log as logging

from neutron._i18n import _LI, _LW, _LE
from neutron.plugins.zvm.common import exception
from neutron.plugins.zvm.common import xcatutils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class zvmUtils(object):
    _MAX_REGRANT_USER_NUMBER = 1000

    def __init__(self):
        self._xcat_url = xcatutils.xCatURL()
        self._zhcp_userid = None
        self._userid_map = {}
        self._xcat_node_name = self._get_xcat_node_name()

    def get_node_from_port(self, port_id):
        return self._get_nic_settings(port_id, get_node=True)

    def get_nic_ids(self):
        addp = ''
        url = self._xcat_url.tabdump("/switch", addp)
        with xcatutils.expect_invalid_xcat_resp_data():
            nic_settings = xcatutils.xcat_request("GET", url)['data'][0]
        # remove table header
        nic_settings.pop(0)
        # it's possible to return empty array
        return nic_settings

    def _get_nic_settings(self, port_id, field=None, get_node=False):
        """Get NIC information from xCat switch table."""
        LOG.debug("Get nic information for port: %s", port_id)
        addp = '&col=port&value=%s' % port_id + '&attribute=%s' % (
                                                field and field or 'node')
        url = self._xcat_url.gettab("/switch", addp)
        with xcatutils.expect_invalid_xcat_resp_data():
            ret_value = xcatutils.xcat_request("GET", url)['data'][0][0]
        if field is None and not get_node:
            ret_value = self.get_userid_from_node(ret_value)
        return ret_value

    def get_userid_from_node(self, node):
        addp = '&col=node&value=%s&attribute=userid' % node
        url = self._xcat_url.gettab("/zvm", addp)
        with xcatutils.expect_invalid_xcat_resp_data():
            return xcatutils.xcat_request("GET", url)['data'][0][0]

    def couple_nic_to_vswitch(self, vswitch_name, switch_port_name,
                              zhcp, userid, dm=True, immdt=True):
        """Couple nic to vswitch."""
        LOG.debug("Connect nic to switch: %s", vswitch_name)
        vdev = self._get_nic_settings(switch_port_name, "interface")
        if vdev:
            self._couple_nic(zhcp, vswitch_name, userid, vdev, dm, immdt)
        else:
            raise exception.zVMInvalidDataError(msg=('Cannot get vdev for '
                            'user %s, couple to port %s') %
                            (userid, switch_port_name))
        return vdev

    def uncouple_nic_from_vswitch(self, vswitch_name, switch_port_name,
                                  zhcp, userid, dm=True, immdt=True):
        """Uncouple nic from vswitch."""
        LOG.debug("Disconnect nic from switch: %s", vswitch_name)
        vdev = self._get_nic_settings(switch_port_name, "interface")
        self._uncouple_nic(zhcp, userid, vdev, dm, immdt)

    def set_vswitch_port_vlan_id(self, vlan_id, switch_port_name, zhcp,
                                 vswitch_name):
        userid = self._get_nic_settings(switch_port_name)
        if not userid:
            raise exception.zVMInvalidDataError(msg=('Cannot get userid by '
                            'port %s') % (switch_port_name))
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += " -T %s" % userid
        commands += ' -k grant_userid=%s' % userid
        commands += " -k switch_name=%s" % vswitch_name
        commands += " -k user_vlan_id=%s" % vlan_id
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        xcatutils.xcat_request("PUT", url, body)

    def grant_user(self, zhcp, vswitch_name, userid):
        """Set vswitch to grant user."""
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += " -T %s" % userid
        commands += " -k switch_name=%s" % vswitch_name
        commands += " -k grant_userid=%s" % userid
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        xcatutils.xcat_request("PUT", url, body)

    def revoke_user(self, zhcp, vswitch_name, userid):
        """Set vswitch to grant user."""
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += " -T %s" % userid
        commands += " -k switch_name=%s" % vswitch_name
        commands += " -k revoke_userid=%s" % userid
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        xcatutils.xcat_request("PUT", url, body)

    def _couple_nic(self, zhcp, vswitch_name, userid, vdev, dm, immdt):
        """Couple NIC to vswitch by adding vswitch into user direct."""
        url = self._xcat_url.xdsh("/%s" % zhcp)
        if dm:
            commands = '/opt/zhcp/bin/smcli'
            commands += ' Virtual_Network_Adapter_Connect_Vswitch_DM'
            commands += " -T %s " % userid + "-v %s" % vdev
            commands += " -n %s" % vswitch_name
            xdsh_commands = 'command=%s' % commands
            body = [xdsh_commands]
            xcatutils.xcat_request("PUT", url, body)
        if immdt:
            # the inst must be active, or this call will failed
            commands = '/opt/zhcp/bin/smcli'
            commands += ' Virtual_Network_Adapter_Connect_Vswitch'
            commands += " -T %s " % userid + "-v %s" % vdev
            commands += " -n %s" % vswitch_name
            xdsh_commands = 'command=%s' % commands
            body = [xdsh_commands]
            xcatutils.xcat_request("PUT", url, body)

    def _uncouple_nic(self, zhcp, userid, vdev, dm, immdt):
        """Couple NIC to vswitch by adding vswitch into user direct."""
        url = self._xcat_url.xdsh("/%s" % zhcp)
        if dm:
            commands = '/opt/zhcp/bin/smcli'
            commands += ' Virtual_Network_Adapter_Disconnect_DM'
            commands += " -T %s " % userid + "-v %s" % vdev
            xdsh_commands = 'command=%s' % commands
            body = [xdsh_commands]
            xcatutils.xcat_request("PUT", url, body)
        if immdt:
            # the inst must be active, or this call will failed
            commands = '/opt/zhcp/bin/smcli'
            commands += ' Virtual_Network_Adapter_Disconnect'
            commands += " -T %s " % userid + "-v %s" % vdev
            xdsh_commands = 'command=%s' % commands
            body = [xdsh_commands]
            xcatutils.xcat_request("PUT", url, body)

    def put_user_direct_online(self, zhcp, userid):
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Static_Image_Changes_Immediate_DM'
        commands += " -T %s" % userid
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        xcatutils.xcat_request("PUT", url, body)

    def get_zhcp_userid(self, zhcp):
        if not self._zhcp_userid:
            self._zhcp_userid = self.get_userid_from_node(zhcp)
        return self._zhcp_userid

    @xcatutils.wrap_invalid_xcat_resp_data_error
    def get_admin_created_vsw(self, zhcp):
        '''Check whether the vswitch is preinstalled in env,
        these vswitchs should not be handled by neutron-zvm-agent.
        '''
        url = self._xcat_url.xdsh('/%s' % self._xcat_node_name)
        commands = 'command=vmcp q v nic'
        body = [commands]
        result = xcatutils.xcat_request("PUT", url, body)
        if (result['errorcode'][0][0] != '0'):
            raise exception.zvmException(
                msg=("Query xcat nic info failed, %s") % result['data'][0][0])

        output = result['data'][0][0].split('\n')
        vswitch = []
        index = 0
        for i in output:
            if ('Adapter 0600' in i) or ('Adapter 0700' in i):
                vsw_start = output[index + 1].rfind(' ') + 1
                vswitch.append(output[index + 1][vsw_start:])
            index += 1
        LOG.debug("admin config vswitch is %s" % vswitch)

        return vswitch

    @xcatutils.wrap_invalid_xcat_resp_data_error
    def add_vswitch(self, zhcp, name, rdev,
                    controller='*',
                    connection=1, queue_mem=8, router=0, network_type=2, vid=0,
                    port_type=1, update=1, gvrp=2, native_vid=1):
        '''
           connection:0-unspecified 1-Actice 2-non-Active
           router:0-unspecified 1-nonrouter 2-prirouter
           type:0-unspecified 1-IP 2-ethernet
           vid:1-4094 for access port defaut vlan
           port_type:0-unspecified 1-access 2-trunk
           update:0-unspecified 1-create 2-create and add to system
                  configuration file
           gvrp:0-unspecified 1-gvrp 2-nogvrp
        '''
        vswitch_info = self._check_vswitch_status(zhcp, name)
        if vswitch_info is not None:
            LOG.info(_LI('Vswitch %s already exists,check rdev info.'), name)
            if rdev is None:
                LOG.debug('vswitch %s is not changed', name)
                return
            else:
                # as currently zvm-agent can only set one rdev for vswitch
                # so as long one of rdev in vswitch env are same as rdevs
                # list in config file, we think the vswitch does not change.
                rdev_list = rdev.split(',')
                for i in vswitch_info:
                    for j in rdev_list:
                        if i.strip() == j.strip():
                            LOG.debug('vswitch %s is not changed', name)
                            return

                LOG.info(_LI('start changing vswitch %s '), name)
                self._set_vswitch_rdev(zhcp, name, rdev)
                return

        # if vid = 0, port_type, gvrp and native_vlanid are not
        # allowed to specified
        if not len(vid):
            vid = 0
            port_type = 0
            gvrp = 0
            native_vid = -1
        else:
            vid = str(vid[0][0]) + '-' + str(vid[0][1])

        userid = self.get_zhcp_userid(zhcp)
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Create'
        commands += " -T %s" % userid
        commands += ' -n %s' % name
        if rdev:
            commands += " -r %s" % rdev.replace(',', ' ')
        # commands += " -a %s" % osa_name
        if controller != '*':
            commands += " -i %s" % controller
        commands += " -c %s" % connection
        commands += " -q %s" % queue_mem
        commands += " -e %s" % router
        commands += " -t %s" % network_type
        commands += " -v %s" % vid
        commands += " -p %s" % port_type
        commands += " -u %s" % update
        commands += " -G %s" % gvrp
        commands += " -V %s" % native_vid
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        result = xcatutils.xcat_request("PUT", url, body)
        if ((result['errorcode'][0][0] != '0') or
            (self._check_vswitch_status(zhcp, name) is None)):
            raise exception.zvmException(
                msg=("switch: %s add failed, %s") %
                    (name, result['data']))
        LOG.info(_LI('Created vswitch %s done.'), name)

    @xcatutils.wrap_invalid_xcat_resp_data_error
    def _check_vswitch_status(self, zhcp, vsw):
        '''
        check the vswitch exists or not,return rdev info
        return value:
        None: vswitch does not exist
        []: vswitch exists but does not connect to a rdev
        ['xxxx','xxxx']:vswitch exists and 'xxxx' is rdev value
        '''
        userid = self.get_zhcp_userid(zhcp)
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Query'
        commands += " -T %s" % userid
        commands += " -s %s" % vsw
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        result = xcatutils.xcat_request("PUT", url, body)
        if (result['errorcode'][0][0] != '0' or not
                result['data'] or not result['data'][0]):
            return None
        else:
            output = re.findall('Real device: (.*)\n', result['data'][0][0])
            return output

    @xcatutils.wrap_invalid_xcat_resp_data_error
    def _set_vswitch_rdev(self, zhcp, vsw, rdev):
        """Set vswitch's rdev."""
        userid = self.get_zhcp_userid(zhcp)
        url = self._xcat_url.xdsh("/%s" % zhcp)
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += ' -T %s' % userid
        commands += ' -k switch_name=%s' % vsw
        if rdev:
            commands += ' -k real_device_address=%s' % rdev.replace(',', ' ')
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        result = xcatutils.xcat_request("PUT", url, body)
        if (result['errorcode'][0][0] != '0'):
            raise exception.zvmException(
                msg=("switch: %s changes failed, %s") %
                    (vsw, result['data']))
        LOG.info(_LI('change vswitch %s done.'), vsw)

    def re_grant_user(self, zhcp):
        """Grant user again after z/VM is re-IPLed."""
        ports_info = self._get_userid_vswitch_vlan_id_mapping(zhcp)
        records_num = 0
        cmd = ''

        def run_command(command):
            xdsh_commands = 'command=%s' % command
            body = [xdsh_commands]
            url = self._xcat_url.xdsh("/%s" % zhcp)
            xcatutils.xcat_request("PUT", url, body)

        for (port_id, port) in ports_info.items():
            if port['userid'] is None or port['vswitch'] is None:
                continue
            if len(port['userid']) == 0 or len(port['vswitch']) == 0:
                continue

            cmd += '/opt/zhcp/bin/smcli '
            cmd += 'Virtual_Network_Vswitch_Set_Extended '
            cmd += '-T %s ' % port['userid']
            cmd += '-k switch_name=%s ' % port['vswitch']
            cmd += '-k grant_userid=%s' % port['userid']
            try:
                if int(port['vlan_id']) in range(1, 4094):
                    cmd += ' -k user_vlan_id=%s\n' % port['vlan_id']
                else:
                    cmd += '\n'
            except ValueError:
                # just in case there are bad records of vlan info which
                # could be a string
                LOG.warning(_LW("Unknown vlan '%(vlan)s' for user %(user)s."),
                            {'vlan': port['vlan_id'], 'user': port['userid']})
                cmd += '\n'
                continue
            records_num += 1
            if records_num >= self._MAX_REGRANT_USER_NUMBER:
                try:
                    commands = 'echo -e "#!/bin/sh\n%s" > grant.sh' % cmd[:-1]
                    run_command(commands)
                    commands = 'sh grant.sh;rm -f grant.sh'
                    run_command(commands)
                    records_num = 0
                    cmd = ''
                except Exception:
                    LOG.warning(_LW("Grant user failed"))

        if len(cmd) > 0:
            commands = 'echo -e "#!/bin/sh\n%s" > grant.sh' % cmd[:-1]
            run_command(commands)
            commands = 'sh grant.sh;rm -f grant.sh'
            run_command(commands)
        return ports_info

    @xcatutils.wrap_invalid_xcat_resp_data_error
    def _get_userid_vswitch_vlan_id_mapping(self, zhcp):
        ports_info = self.get_nic_ids()
        ports = {}
        for p in ports_info:
            port_info = p.split(',')
            target_host = port_info[5].strip('"')
            port_vid = port_info[3].strip('"')
            port_id = port_info[2].strip('"')
            vswitch = port_info[1].strip('"')
            nodename = port_info[0].strip('"')
            if target_host == zhcp:
                ports[port_id] = {'nodename': nodename,
                                  'vswitch': vswitch,
                                  'userid': None,
                                  'vlan_id': port_vid}

        def get_all_userid():
            users = {}
            addp = ''
            url = self._xcat_url.tabdump("/zvm", addp)
            all_userids = xcatutils.xcat_request("GET", url)
            all_userids['data'][0].pop(0)
            if len(all_userids) > 0:
                for u in all_userids['data'][0]:
                    user_info = u.split(',')
                    userid = user_info[2].strip('"')
                    nodename = user_info[0].strip('"')
                    users[nodename] = {'userid': userid}

            return users

        users = get_all_userid()

        for (port_id, port) in ports.items():
            try:
                ports[port_id]['userid'] = users[port['nodename']]['userid']
            except Exception:
                LOG.info(_LI("Garbage port found. port id: %s") % port_id)

        return ports

    def update_xcat_switch(self, port, vswitch, vlan):
        """Update information in xCAT switch table."""
        commands = "port=%s" % port
        commands += " switch.switch=%s" % vswitch
        commands += " switch.vlan=%s" % (vlan and vlan or -1)
        url = self._xcat_url.tabch("/switch")
        body = [commands]
        xcatutils.xcat_request("PUT", url, body)

    @xcatutils.wrap_invalid_xcat_resp_data_error
    def create_xcat_mgt_network(self, zhcp, mgt_ip, mgt_mask, mgt_vswitch):
        url = self._xcat_url.xdsh("/%s" % self._xcat_node_name)
        xdsh_commands = ('command=vmcp q v nic 800')
        body = [xdsh_commands]
        result = xcatutils.xcat_request("PUT", url, body)['data'][0][0]
        cmd = ''
        # nic does not exist
        if 'does not exist' in result:
            cmd = ('vmcp define nic 0800 type qdio\n' +
                   'vmcp couple 0800 system %s\n' % (mgt_vswitch))
        # nic is created but not couple
        elif 'LAN: *' in result:
            cmd = ('vmcp couple 0800 system %s\n' % (mgt_vswitch))
        # couple and active
        elif "VSWITCH: SYSTEM" in result:
            # Only support one management network.
            url = self._xcat_url.xdsh("/%s") % self._xcat_node_name
            xdsh_commands = "command=ifconfig enccw0.0.0800|grep 'inet '"
            body = [xdsh_commands]
            result = xcatutils.xcat_request("PUT", url, body)
            if result['errorcode'][0][0] == '0' and result['data']:
                cur_ip = re.findall('inet (.*)  netmask',
                                   result['data'][0][0])
                cur_mask = re.findall('netmask (.*)  broadcast',
                                   result['data'][0][0])
                if not cur_ip:
                    LOG.warning(_LW("Nic 800 has been created, but IP "
                          "address is not correct, will config it again"))
                elif mgt_ip != cur_ip[0]:
                    raise exception.zVMConfigException(
                        msg=("Only support one Management network,"
                             "it has been assigned by other agent!"
                             "Please use current management network"
                             "(%s/%s) to deploy." % (cur_ip[0], cur_mask)))
                else:
                    LOG.debug("IP address has been assigned for NIC 800.")
                    return
            else:
                LOG.warning(_LW("Nic 800 has been created, but IP address "
                              "doesn't exist, will config it again"))
        else:
            message = ("Command 'query v nic' return %s,"
                    " it is unkown information for zvm-agent") % result
            LOG.error(_LE("Error: %s") % message)
            raise exception.zvmException(msg=message)

        url = self._xcat_url.xdsh("/%s") % self._xcat_node_name
        cmd += ('/usr/bin/perl /usr/sbin/sspqeth2.pl ' +
              '-a %s -d 0800 0801 0802 -e enccw0.0.0800 -m %s -g %s'
              % (mgt_ip, mgt_mask, mgt_ip))
        xdsh_commands = 'command=%s' % cmd
        body = [xdsh_commands]
        xcatutils.xcat_request("PUT", url, body)

    def _get_xcat_node_ip(self):
        addp = '&col=key&value=master&attribute=value'
        url = self._xcat_url.gettab("/site", addp)
        with xcatutils.expect_invalid_xcat_resp_data():
            return xcatutils.xcat_request("GET", url)['data'][0][0]

    def _get_xcat_node_name(self):
        xcat_ip = self._get_xcat_node_ip()
        addp = '&col=ip&value=%s&attribute=node' % (xcat_ip)
        url = self._xcat_url.gettab("/hosts", addp)
        with xcatutils.expect_invalid_xcat_resp_data():
            return (xcatutils.xcat_request("GET", url)['data'][0][0])

    def query_xcat_uptime(self):
        url = self._xcat_url.xdsh("/%s" % self._xcat_node_name)
        # get system uptime
        cmd = 'date -d "$(awk -F. \'{print $1}\' /proc/uptime) second ago"'
        cmd += ' +"%Y-%m-%d %H:%M:%S"'
        xdsh_commands = 'command=%s' % cmd
        body = [xdsh_commands]
        with xcatutils.expect_invalid_xcat_resp_data():
            return xcatutils.xcat_request("PUT", url, body)['data'][0][0]

    def query_zvm_uptime(self, zhcp):
        url = self._xcat_url.xdsh("/%s" % zhcp)
        cmd = '/opt/zhcp/bin/smcli System_Info_Query'
        xdsh_commands = 'command=%s' % cmd
        body = [xdsh_commands]
        with xcatutils.expect_invalid_xcat_resp_data():
            ret_str = xcatutils.xcat_request("PUT", url, body)['data'][0][0]
        return ret_str.split('\n')[4].split(': ', 3)[2]

    def add_nic_to_user_direct(self, nodename, nic_info):
        """add one NIC's info to user direct."""
        vdev = self._get_nic_settings(nic_info['port_id'], "interface")

        url = self._xcat_url.chvm('/' + nodename)
        command = 'Image_Definition_Update_DM -T %userid%'
        command += ' -k \'NICDEF=VDEV=%s TYPE=QDIO ' % vdev
        command += 'MACID=%s ' % nic_info['mac']
        command += 'LAN=SYSTEM '
        command += 'SWITCHNAME=%s\'' % nic_info['vswitch']
        body = ['--smcli', command]

        with xcatutils.expect_invalid_xcat_resp_data():
            xcatutils.xcat_request("PUT", url, body)

    def add_nics_to_direct(self, zhcp, nodename, nic_info_list):
        """add all NIC's info to user direct."""
        for nic_info in nic_info_list:
            self.add_nic_to_user_direct(nodename, nic_info)
