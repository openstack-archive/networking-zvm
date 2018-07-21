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
import sys
import time

from neutron_lib.agent import topics
from neutron_lib import constants as q_const
from neutron_lib import context
from oslo_log import log as logging
from oslo_service import loopingcall

from neutron.agent import rpc as agent_rpc
from neutron.common import config as common_config
from neutron.plugins.ml2.drivers.zvm import mech_zvm
from neutron.plugins.zvm.agent import zvm_network
from neutron.plugins.zvm.common import config as cfg
from neutron.plugins.zvm.common import exception
from neutron.plugins.zvm.common import utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


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
        self._requesthandler = utils.zVMConnectorRequestHandler()
        self._utils = utils.zvmUtils()
        self._polling_interval = CONF.AGENT.polling_interval
        self._host = self._requesthandler.call('host_get_info').get(
                                        'zvm_host') or CONF.host
        self._port_map = {}

        zvm_net = zvm_network.zvmNetwork()
        self.agent_state = {
            'binary': 'neutron-zvm-agent',
            'host': self._host,
            'topic': q_const.L2_AGENT_TOPIC,
            'configurations': {'vswitch_mappings': zvm_net.get_network_maps()},
            'agent_type': mech_zvm.AGENT_TYPE_ZVM,
            'start_flag': True}
        self._setup_server_rpc()
        self._restart_handler = self._handle_restart()

    def _setup_server_rpc(self):
        self.agent_id = 'zvm_agent_%s' % self._host
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

        report_interval = CONF.AGENT.report_interval
        if report_interval:
            heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            heartbeat.start(interval=report_interval)

    def _report_state(self):
        try:
            self.state_rpc.report_state(self.context, self.agent_state)
            self.agent_state.pop('start_flag', None)
        except Exception:
            LOG.exception("Failed reporting state!")

    def network_delete(self, context, network_id=None):
        LOG.info("Network delete received. UUID: %s", network_id)

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
            nic_info = self._requesthandler.call('guests_get_nic_info',
                                                 nic_id=port['id'])
            if ((len(nic_info) != 1) or
                (len(nic_info[0]) != 5) or
                (not nic_info[0]['interface'])):
                raise exception.zVMInvalidDataError(msg=('Cannot get vdev '
                                'for user %s, couple to port %s, '
                                'SDK output is %s') %
                                (userid, port['id'], nic_info))
            else:
                vdev = nic_info[0]['interface']
            self._requesthandler.call('guest_nic_couple_to_vswitch', userid,
                                      vdev, vswitch)
            self.plugin_rpc.update_device_up(self.context, port['id'],
                                             self.agent_id)
        else:
            nic_info = self._requesthandler.call('guests_get_nic_info',
                                                 nic_id=port['id'])
            if ((len(nic_info) != 1) or
                (len(nic_info[0]) != 5) or
                (not nic_info[0]['interface'])):
                raise exception.zVMInvalidDataError(msg=('Cannot get vdev '
                                'for user %s, uncouple port %s, '
                                'SDK output is %s') %
                                (userid, port['id'], nic_info))
            else:
                vdev = nic_info[0]['interface']
            self._requesthandler.call('guest_nic_uncouple_from_vswitch',
                                      userid, vdev)
            self.plugin_rpc.update_device_down(self.context, port['id'],
                                               self.agent_id)

    def port_bound(self, port_id, net_uuid,
                   network_type, physical_network, segmentation_id, userid):
        LOG.info("Start to bind port port_id:%(port_id)s, "
                 "net_uuid:%(net_uuid)s, network_type: %(network_type)s, "
                 "physical_network: %(physical_network)s, "
                 "userid: %(userid)s, segmentation_id:%(seg_id)s",
                 {'port_id': port_id, 'net_uuid': net_uuid,
                  'network_type': network_type,
                  'physical_network': physical_network,
                  'seg_id': segmentation_id,
                  'userid': userid})

        self._requesthandler.call('vswitch_grant_user',
                                  physical_network, userid)
        if network_type == q_const.TYPE_VLAN:
            LOG.info('Binding VLAN, VLAN ID: %(segmentation_id)s, '
                     'port_id: %(port_id)s',
                     {'segmentation_id': segmentation_id,
                      'port_id': port_id})
            self._requesthandler.call('vswitch_set_vlan_id_for_user',
                                      physical_network, userid,
                                      int(segmentation_id))
        else:
            LOG.info('Bind %s port done', port_id)

    def port_unbound(self, port_id):
        LOG.info("Unbinding port %s", port_id)
        # uncouple is not necessary, because revoke user will uncouple it
        # automatically.
        self._requesthandler.call('vswitch_revoke_user',
                                  self._port_map[port_id]['vswitch'],
                                  self._port_map[port_id]['userid'])

    def _update_ports(self, registered_ports):
        nic_info = self._requesthandler.call('guests_get_nic_info')
        ports = set()
        for p in nic_info:
            if p['port'] is not None:
                new_port_id = p['port']
                ports.add(new_port_id)
        if ports == registered_ports:
            return

        added = ports - registered_ports
        removed = registered_ports - ports
        return {'current': ports, 'added': added, 'removed': removed}

    def _treat_vif_port(self, port_id, network_id, network_type,
                        physical_network, segmentation_id,
                        admin_state_up):
        nic_info = self._requesthandler.call('guests_get_nic_info',
                                             nic_id=port_id)
        if ((len(nic_info) != 1) or
            (len(nic_info[0]) != 5) or
            (not nic_info[0]['userid'])):
            raise exception.zVMInvalidDataError(msg=('Cannot get userid '
                                'for port %s, SDK output is %s') %
                                (port_id, nic_info))
        else:
            userid = nic_info[0]['userid']

        LOG.info("Update port for user:%s" % userid)
        if admin_state_up:
            self.port_bound(port_id, network_id, network_type,
                            physical_network, segmentation_id,
                            userid)
        else:
            self._requesthandler.call('vswitch_grant_user',
                                      physical_network, userid)
        return userid

    def _treat_devices_added(self, devices):
        nics_info = {}
        for device in devices:
            LOG.info("Adding port %s" % device)
            try:
                details = self.plugin_rpc.get_device_details(self.context,
                                                             device,
                                                             self.agent_id,
                                                             self._host)
            except Exception:
                LOG.info("Unable to get port details for %s:", device)
                continue

            try:
                if 'port_id' in details:
                    LOG.info("Port %(device)s updated. "
                             "Details: %(details)s",
                             {'device': device, 'details': details})
                    userid = self._treat_vif_port(
                                     details['port_id'],
                                     details['network_id'],
                                     details['network_type'],
                                     details['physical_network'],
                                     details['segmentation_id'],
                                     details['admin_state_up'])
                    # add device done, keep port map info
                    self._port_map[device] = {}
                    self._port_map[device]['userid'] = userid
                    self._port_map[device]['nodename'] = userid
                    self._port_map[device]['vswitch'] = details[
                                                        'physical_network']
                    self._port_map[device]['vlan_id'] = details[
                                                        'segmentation_id']

                    if details.get('admin_state_up'):
                        mac = ''.join(details['mac_address'].split(':'))[6:]
                        if not nics_info.get(userid):
                            nics_info[userid] = []
                        nics_info[userid].append(
                                    {'port_id': details['port_id'],
                                    'vswitch': details['physical_network'],
                                    'mac': mac})

                        LOG.debug("Adding NICs for %(userid)s, info: %(nic)s",
                                  {'userid': userid, 'nic': nics_info[userid]})
                        nic_info = self._requesthandler.call(
                                                    'guests_get_nic_info',
                                                    nic_id=details['port_id'])
                        if ((len(nic_info) != 1) or
                            (len(nic_info[0]) != 5) or
                            (not nic_info[0]['interface'])):
                            raise exception.zVMInvalidDataError(msg=('Cannot '
                                'get vdev for port %s, SDK output is %s') %
                                (details['port_id'], nic_info))
                        else:
                            vdev = nic_info[0]['interface']
                        self._requesthandler.call(
                                            'guest_nic_couple_to_vswitch',
                                            userid, vdev,
                                            details['physical_network'])

                        LOG.debug("New added NIC info: %s", nics_info[userid])

                        LOG.info("Setting status for %s to UP", device)
                        self.plugin_rpc.update_device_up(
                            self.context, device, self.agent_id, self._host)
                    else:
                        LOG.info("Setting status for %s to DOWN", device)
                        self.plugin_rpc.update_device_down(
                            self.context, device, self.agent_id, self._host)

                else:
                    LOG.warning("Device %(device)s not defined on "
                                "Neutron server, The output detail is "
                                "%(details)s",
                                {'device': device, 'details': details})
                    continue
            except Exception as e:
                LOG.exception("Can not add device %(device)s: %(msg)s",
                              {'device': device, 'msg': e})
                continue

    def _treat_devices_removed(self, devices):
        for device in devices:
            LOG.info("Removing port %s", device)
            try:
                if not self._port_map or device not in self._port_map:
                    LOG.warning("Can't find port %s in zvm agent", device)
                    continue

                if self._port_map[device]['vswitch']:
                    self.port_unbound(device)
                self.plugin_rpc.update_device_down(self.context,
                                                   device,
                                                   self.agent_id)
                del self._port_map[device]
            except Exception as e:
                LOG.exception("Removing port failed %(device)s: %(msg)s",
                              {'device': device, 'msg': e})
                continue

    def _process_network_ports(self, port_info):
        if len(port_info['added']):
            self._treat_devices_added(port_info['added'])
        if len(port_info['removed']):
            self._treat_devices_removed(port_info['removed'])

    def daemon_loop(self):
        ports = set()
        # Get all exsited ports as configured
        all_ports_info = self._update_ports(ports)
        if all_ports_info is not None:
            ports = all_ports_info['current']

        while True:
            try:
                start_time = time.time()
                port_info = self._update_ports(ports)

                if port_info:
                    LOG.info("Devices change, info: %s", port_info)
                    self._process_network_ports(port_info)
                    ports = port_info['current']
            except Exception as e:
                LOG.exception("Error in neutron agent loop: %s", e)

            # sleep till end of polling interval
            elapsed = (time.time() - start_time)
            if (elapsed < self._polling_interval):
                sleep_time = self._polling_interval - elapsed
                LOG.debug("Sleep %s", sleep_time)
                time.sleep(sleep_time)
            else:
                LOG.debug("Looping iteration exceeded interval")

    @restart_wrapper
    def _handle_restart(self):
        zvm_uptime = None
        while True:
            LOG.info("Try to reinitialize network ... ")
            try:
                tmp_new_time = self._requesthandler.call('host_get_info').get(
                                        'ipl_time')
                if zvm_uptime != tmp_new_time:
                    self._port_map = self._utils.get_port_map()
                    zvm_uptime = tmp_new_time
                yield
            except Exception:
                LOG.error("Failed to handle restart,"
                          "try again in 5 seconds")
                time.sleep(5)


def main():
    eventlet.monkey_patch()
    CONF(project='neutron')
    common_config.init(sys.argv[1:])
    common_config.setup_logging()

    agent = zvmNeutronAgent()

    # Start to query ZVMSDK DB
    LOG.info("z/VM agent initialized, now running... ")
    agent.daemon_loop()
    sys.exit(0)
