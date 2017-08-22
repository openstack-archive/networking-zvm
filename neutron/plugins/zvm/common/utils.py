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


from oslo_config import cfg
from oslo_log import log as logging

from zvmsdk import utils as xcatutils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class zvmUtils(object):
    _MAX_REGRANT_USER_NUMBER = 1000

    def __init__(self):
        self._xcat_url = xcatutils.get_xcat_url()
        self._xcat_node_name = self._get_xcat_node_name()

    def get_node_from_port(self, port_id):
        return self.get_nic_settings(port_id, get_node=True)

    def get_nic_ids(self):
        addp = ''
        url = self._xcat_url.tabdump("/switch", addp)
        with xcatutils.expect_invalid_xcat_resp_data():
            nic_settings = xcatutils.xcat_request("GET", url)['data'][0]
        # remove table header
        nic_settings.pop(0)
        # it's possible to return empty array
        return nic_settings

    def get_nic_settings(self, port_id, field=None, get_node=False):
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
                LOG.warning("Unknown vlan '%(vlan)s' for user %(user)s.",
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
                    LOG.warning("Grant user failed")

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
                LOG.info("Garbage port found. port id: %s" % port_id)

        return ports

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
