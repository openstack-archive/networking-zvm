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

from oslo_config import cfg
from oslo_log import log as logging

from neutron._i18n import _LI
from neutron.plugins.common import utils as plugin_utils
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
    def __init__(self, zhcp, name, vlan):
        self._utils = utils.zvmUtils()
        self._utils.add_vswitch(zhcp, name,
                getattr(CONF.get(name), "rdev_list"), vid=vlan)
        self.zhcp = zhcp


class zvmNetwork(object):
    def __init__(self):
        self._utils = utils.zvmUtils()
        self._zhcp = CONF.AGENT.xcat_zhcp_nodename
        self._vsws = []
        self._maps = {}
        self._creat_networks()

    def _creat_networks(self):
        admin_vsw = self._utils.get_admin_created_vsw(self._zhcp)
        self._maps = plugin_utils.parse_network_vlan_ranges(
                            CONF.ml2_type_vlan.network_vlan_ranges +
                            CONF.ml2_type_flat.flat_networks)
        self._vsws = []
        for vsw in self._maps.keys():
            CONF.register_opts(vswitch_opts, vsw)
            if vsw.upper() in admin_vsw:
                LOG.info(_LI('Vswitch %s is pre-created by admin or system, '
                    'neutron-zvm-agent will not handle it') % vsw)
            else:
                self._vsws.append(zvmVswitch(self._zhcp, vsw, self._maps[vsw]))

    def get_network_maps(self):
        return self._maps
