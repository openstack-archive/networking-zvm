# Copyright 2014 IBM Corp.
#
# All Rights Reserved.
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

import eventlet
import operator
import sys
import time

from neutron_lib import constants as q_const
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import versionutils

from neutron.agent import rpc as agent_rpc
from neutron.common import config as common_config
from neutron.common import topics
from neutron._i18n import _, _LE, _LI, _LW
from neutron import context
from neutron.plugins.common import constants as p_const
from neutron.plugins.ml2.drivers.zvm import mech_zvm
from neutron.plugins.zvm.agent import zvm_network
from neutron.plugins.zvm.common import constants
from neutron.plugins.zvm.common import exception
from neutron.plugins.zvm.common import utils
from neutron.plugins.zvm.common import xcatutils


LOG = logging.getLogger(__name__)


def restart_wrapper(func):
    def wrapper(*args, **kw):
        gen = func(*args, **kw)
        gen.next()
        return gen
    return wrapper


class zvmNeutronAgent(object):
    RPC_API_VERSION = '1.1'

    def __init__(self):
        super(zvmNeutronAgent, self).__init__()
        self._utils = utils.zvmUtils()
        self._polling_interval = cfg.CONF.AGENT.polling_interval
        self._zhcp_node = cfg.CONF.AGENT.xcat_zhcp_nodename
        self._host = cfg.CONF.AGENT.zvm_host or cfg.CONF.host
        self._port_map = {}
        self._xcat_url = xcatutils.xCatURL()

        zvm_net = zvm_network.zvmNetwork()
        self.agent_state = {
            'binary': 'neutron-zvm-agent',
            'host': self._host,
            'topic': q_const.L2_AGENT_TOPIC,
            'configurations': {'vswitch_mappings': zvm_net.get_network_maps()},
            'agent_type': mech_zvm.AGENT_TYPE_ZVM,
            'start_flag': True}
        self._setup_server_rpc()
        self._zhcp_userid = self._utils.get_zhcp_userid(self._zhcp_node)
        self._restart_handler = self._handle_restart()

    def _version_check(self, req_ver=None, op=operator.lt):
        try:
            if req_ver is not None:
                cur = versionutils.convert_version_to_int(self._xcat_version)
                req = versionutils.convert_version_to_int(req_ver)
                if op(cur, req):
                    return False
            return True
        except Exception:
            return False

    def has_min_version(self, req_ver=None):
        return self._version_check(req_ver=req_ver, op=operator.lt)

    def has_version(self, req_ver=None):
        return self._version_check(req_ver=req_ver, op=operator.ne)

    def _check_xcat_version(self):
        # incremental sleep interval list
        _inc_slp = [5, 10, 20, 30, 60]
        _slp = 5

        # TODO(jichenjc): update _xcat_version when xcat reboot
        self._xcat_version = xcatutils.get_xcat_version()
        version_ok = self.has_min_version(constants.XCAT_MINIMUM_VERSION)
        while (not version_ok):
            LOG.warning(_LW("WARNING: the xcat version communicating with is "
                            "%(xcat_version)s, but the minimum requested "
                            "version by neutron agent is %(minimum)s "
                            "will sleep some time and check again"),
                        {'xcat_version': self._xcat_version,
                         'minimum': constants.XCAT_MINIMUM_VERSION})
            self._xcat_version = self._get_xcat_version()
            version_ok = self.has_min_version(constants.XCAT_MINIMUM_VERSION)

            _slp = len(_inc_slp) != 0 and _inc_slp.pop(0) or _slp
            time.sleep(_slp)

    def _setup_server_rpc(self):
        self.agent_id = 'zvm_agent_%s' % self._zhcp_node
        self.topic = topics.AGENT
        self.plugin_rpc = agent_rpc.PluginApi(topics.PLUGIN)
        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.PLUGIN)

        self.context = context.get_admin_context_without_session()

        self.endpoints = [self]
        consumers = [[topics.PORT, topics.UPDATE],
                     [topics.NETWORK, topics.DELETE]]
        self.connection = agent_rpc.create_consumers(self.endpoints,
                                                     self.topic,
                                                     consumers)

        report_interval = cfg.CONF.AGENT.report_interval
        if report_interval:
            heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            heartbeat.start(interval=report_interval)

    def _report_state(self):
        try:
            self.state_rpc.report_state(self.context, self.agent_state)
            self.agent_state.pop('start_flag', None)
        except Exception:
            LOG.exception(_LE("Failed reporting state!"))

    def network_delete(self, context, network_id=None):
        LOG.info(_LI("Network delete received. UUID: %s"), network_id)

    def port_update(self, context, **kwargs):
        port = kwargs.get('port')
        LOG.debug("Port update received. UUID: %s", port)

        if not self._port_map or not port['id'] in self._port_map.keys():
            # update a port which is not coupled to any NIC, nothing
            # to do for a user based vswitch
            return

        vswitch = self._port_map[port['id']]['vswitch']
        userid = self._port_map[port['id']]['userid']
        if port['admin_state_up']:
            self._utils.couple_nic_to_vswitch(vswitch, port['id'],
                                             self._zhcp_node, userid)
            self.plugin_rpc.update_device_up(self.context, port['id'],
                                             self.agent_id)
        else:
            self._utils.uncouple_nic_from_vswitch(vswitch, port['id'],
                                                self._zhcp_node, userid)
            self.plugin_rpc.update_device_down(self.context, port['id'],
                                               self.agent_id)
        self._utils.put_user_direct_online(self._zhcp_node,
                                           self._zhcp_userid)

    def port_bound(self, port_id, net_uuid,
                   network_type, physical_network, segmentation_id, userid):
        LOG.info(_LI("Start to bind port port_id:%(port_id)s, "
                     "net_uuid:%(net_uuid)s, network_type: %(network_type)s, "
                     "physical_network: %(physical_network)s, "
                     "userid: %(userid)s, segmentation_id:%(seg_id)s"),
                 {'port_id': port_id, 'net_uuid': net_uuid,
                  'network_type': network_type,
                  'physical_network': physical_network,
                  'seg_id': segmentation_id,
                  'userid': userid})

        self._utils.grant_user(self._zhcp_node, physical_network, userid)
        if network_type == p_const.TYPE_VLAN:
            LOG.info(_LI('Binding VLAN, VLAN ID: %(segmentation_id)s, '
                         'port_id: %(port_id)s'),
                     {'segmentation_id': segmentation_id,
                      'port_id': port_id})
            self._utils.set_vswitch_port_vlan_id(segmentation_id, port_id,
                                                 self._zhcp_node,
                                                 physical_network)
        else:
            LOG.info(_LI('Bind %s port done'), port_id)

    def port_unbound(self, port_id):
        LOG.info(_LI("Unbinding port %s"), port_id)
        # uncouple is not necessary, because revoke user will uncouple it
        # automatically.
        self._utils.revoke_user(self._zhcp_node,
                                self._port_map[port_id]['vswitch'],
                                self._port_map[port_id]['userid'])

    def _update_ports(self, registered_ports):
        ports_info = self._utils.get_nic_ids()
        ports = set()
        for p in ports_info:
            target_host = p.split(',')[5].strip('"')
            new_port_id = p.split(',')[2].strip('"')
            if target_host == self._zhcp_node:
                ports.add(new_port_id)

        if ports == registered_ports:
            return

        added = ports - registered_ports
        removed = registered_ports - ports
        return {'current': ports, 'added': added, 'removed': removed}

    def _treat_vif_port(self, port_id, network_id, network_type,
                        physical_network, segmentation_id,
                        admin_state_up):
        node = self._utils.get_node_from_port(port_id)
        userid = self._utils.get_userid_from_node(node)
        LOG.info(_LI("Update port for node:%s") % node)
        if admin_state_up:
            self.port_bound(port_id, network_id, network_type,
                            physical_network, segmentation_id,
                            userid)
        else:
            self._utils.grant_user(self._zhcp_node, physical_network, userid)
        return (node, userid)

    def _treat_devices_added(self, devices):
        nics_info = {}
        for device in devices:
            LOG.info(_LI("Adding port %s") % device)
            try:
                details = self.plugin_rpc.get_device_details(self.context,
                                                             device,
                                                             self.agent_id)
            except Exception:
                LOG.info(_LI("Unable to get port details for %s:"), device)
                continue

            try:
                if 'port_id' in details:
                    LOG.info(_LI("Port %(device)s updated. "
                               "Details: %(details)s"),
                             {'device': device, 'details': details})
                    (node, userid) = self._treat_vif_port(
                                     details['port_id'],
                                     details['network_id'],
                                     details['network_type'],
                                     details['physical_network'],
                                     details['segmentation_id'],
                                     details['admin_state_up'])
                    # add device done, keep port map info
                    self._port_map[device] = {}
                    self._port_map[device]['userid'] = userid
                    self._port_map[device]['nodename'] = node
                    self._port_map[device]['vswitch'] = details[
                                                        'physical_network']
                    self._port_map[device]['vlan_id'] = details[
                                                        'segmentation_id']

                    # no rollback if this fails
                    self._utils.update_xcat_switch(details['port_id'],
                                     details['physical_network'],
                                     details['segmentation_id'])
                    if details.get('admin_state_up'):
                        LOG.info(_LI("Setting status for %s to UP"), device)
                        self.plugin_rpc.update_device_up(
                            self.context, device, self.agent_id, self._host)
                        mac = ''.join(details['mac_address'].split(':'))[6:]
                        if not nics_info.get(node):
                            nics_info[node] = []
                        nics_info[node].append(
                                    {'port_id': details['port_id'],
                                    'vswitch': details['physical_network'],
                                    'mac': mac})
                        LOG.debug("New added NIC info: %s", nics_info[node])
                    else:
                        LOG.info(_LI("Setting status for %s to DOWN"), device)
                        self.plugin_rpc.update_device_down(
                            self.context, device, self.agent_id, self._host)

                else:
                    LOG.warning(_LW("Device %(device)s not defined on "
                                    "Neutron server, The output detail is "
                                    "%(details)s"),
                                {'device': device, 'details': details})
                    continue
            except Exception as e:
                LOG.exception(_LE("Can not add device %(device)s: %(msg)s"),
                              {'device': device, 'msg': e})
                continue

        for node, nic_list in nics_info.items():
            LOG.debug("Adding NICs for %(node)s, info: %(nic)s",
                      {'node': node, 'nic': nic_list})
            self._utils.add_nics_to_direct(self._zhcp_node, node, nic_list)

    def _treat_devices_removed(self, devices):
        for device in devices:
            LOG.info(_LI("Removing port %s"), device)
            try:
                if not self._port_map or device not in self._port_map:
                    LOG.warning(_LW("Can't find port %s in zvm agent"), device)
                    continue

                if self._port_map[device]['vswitch']:
                    self.port_unbound(device)
                self.plugin_rpc.update_device_down(self.context,
                                                   device,
                                                   self.agent_id)
                del self._port_map[device]
            except Exception as e:
                LOG.exception(_LE("Removing port failed %(device)s: %(msg)s"),
                              {'device': device, 'msg': e})
                continue

    def _process_network_ports(self, port_info):
        if len(port_info['added']):
            self._treat_devices_added(port_info['added'])
        if len(port_info['removed']):
            self._treat_devices_removed(port_info['removed'])

    def xcatdb_daemon_loop(self):
        ports = set()
        # Get all exsited ports as configured
        all_ports_info = self._update_ports(ports)
        if all_ports_info is not None:
            ports = all_ports_info['current']

        connect = True
        while True:
            try:
                start_time = time.time()
                port_info = self._update_ports(ports)

                # if no exception is raised in _update_ports,
                # then the connection has recovered
                if connect is False:
                    self._restart_handler.send(None)
                    connect = True

                if port_info:
                    LOG.info(_LI("Devices change, info: %s"), port_info)
                    self._process_network_ports(port_info)
                    ports = port_info['current']
            except exception.zVMxCatRequestFailed as e:
                LOG.error(_LE("Lost connection to xCAT. %s"), e)
                connect = False
            except Exception as e:
                LOG.exception(_LE("error in xCAT DB query loop: %s"), e)

            # sleep till end of polling interval
            elapsed = (time.time() - start_time)
            if (elapsed < self._polling_interval):
                sleep_time = self._polling_interval - elapsed
                LOG.debug("Sleep %s", sleep_time)
                time.sleep(sleep_time)
            else:
                LOG.debug("Looping iteration exceeded interval")

    def _init_xcat_mgt(self):
        '''xCAT Management Node(MN) use the first flat network to manage all
        the instances. So a flat network is required.
        To talk to xCAT MN, xCAT MN requires every instance has a NIC which is
        in the same subnet as xCAT. The xCAT MN's IP address is xcat_mgt_ip,
        mask is xcat_mgt_mask in the config file,
        by default neutron_zvm_plugin.ini.
        '''

        if (cfg.CONF.AGENT.xcat_mgt_ip is None or
                cfg.CONF.AGENT.xcat_mgt_mask is None):
            LOG.info(_LI("User does not configure management IP. Don't need to"
                       " initialize xCAT management network."))
            return
        if not len(cfg.CONF.ml2_type_flat.flat_networks):
            raise exception.zVMConfigException(
                        msg=_('Can not find xCAT management network,'
                              'a flat network is required by xCAT.'))
        self._utils.create_xcat_mgt_network(self._zhcp_node,
                            cfg.CONF.AGENT.xcat_mgt_ip,
                            cfg.CONF.AGENT.xcat_mgt_mask,
                            cfg.CONF.ml2_type_flat.flat_networks[0])

    @restart_wrapper
    def _handle_restart(self):
        xcat_uptime, zvm_uptime = (None, None)
        while True:
            LOG.info(_LI("Try to reinitialize network ... "))
            try:
                tmp_new_time = self._utils.query_xcat_uptime()
                if xcat_uptime != tmp_new_time:
                    self._init_xcat_mgt()
                    xcat_uptime = tmp_new_time

                tmp_new_time = self._utils.query_zvm_uptime(self._zhcp_node)
                if zvm_uptime != tmp_new_time:
                    self._port_map = self._utils.re_grant_user(self._zhcp_node)
                    zvm_uptime = tmp_new_time
                yield
            except exception.zVMConfigException:
                raise
            except Exception:
                LOG.error(_LE("Failed to handle restart,"
                            "try again in 5 seconds"))
                time.sleep(5)


def main():
    eventlet.monkey_patch()
    cfg.CONF(project='neutron')
    common_config.init(sys.argv[1:])
    common_config.setup_logging()

    agent = zvmNeutronAgent()

    # Start to query xCAT DB
    LOG.info(_LI("z/VM agent initialized, now running... "))
    agent.xcatdb_daemon_loop()
    sys.exit(0)
