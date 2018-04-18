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

from neutron_lib.plugins import utils as plugin_utils
from oslo_config import cfg
from oslo_log import log as logging

from neutron.plugins.zvm.common import utils

LOG = logging.getLogger(__name__)

vswitch_opts = [
    cfg.StrOpt('rdev_list',
               help='RDev list for vswitch uplink port')]

CONF = cfg.CONF
CONF.import_opt('flat_networks', "neutron.plugins.ml2.drivers.type_flat",
                'ml2_type_flat')
CONF.import_opt('network_vlan_ranges', "neutron.plugins.ml2.drivers.type_vlan",
                'ml2_type_vlan')


class zvmVswitch(object):
    def __init__(self, name, vlan):
        self._requesthandler = utils.zVMConnectorRequestHandler()
        # check vlan set
        if not len(vlan):
            vlan = 'UNAWARE'
        else:
            vlan = str(vlan[0][0])
        self._requesthandler.call('vswitch_create', name,
                          rdev=getattr(CONF.get(name), "rdev_list"),
                          vid=vlan, network_type='ETHERNET')


class zvmNetwork(object):
    def __init__(self):
        self._requesthandler = utils.zVMConnectorRequestHandler()
        self._vsws = []
        self._maps = {}
        self._creat_networks()

    def _creat_networks(self):
        admin_vsw = self._requesthandler.call('vswitch_get_list')
        self._maps = plugin_utils.parse_network_vlan_ranges(
                            CONF.ml2_type_vlan.network_vlan_ranges +
                            CONF.ml2_type_flat.flat_networks)
        self._vsws = []
        for vsw in self._maps.keys():
            CONF.register_opts(vswitch_opts, vsw)
            if vsw.upper() in admin_vsw:
                LOG.info('Vswitch %s is pre-created by admin or system, '
                    'neutron-zvm-agent will not handle it' % vsw)
            else:
                self._vsws.append(zvmVswitch(vsw, self._maps[vsw]))

    def get_network_maps(self):
        return self._maps
