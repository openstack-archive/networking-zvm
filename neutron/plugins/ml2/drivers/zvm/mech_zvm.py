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


from neutron_lib.api.definitions import portbindings
from neutron_lib import constants

from neutron.plugins.ml2.drivers import mech_agent


AGENT_TYPE_ZVM = 'z/VM agent'
VIF_TYPE_ZVM = 'zvm'


class ZvmMechanismDriver(mech_agent.SimpleAgentMechanismDriverBase):
    """Attach to networks using zvm vswitch agent.

    The ZvmMechanismDriver integrates the ml2 plugin with the
    z/VM L2 agent. Port binding with this driver requires the
    z/VM vswitch agent to be running on the port's host, and that agent
    to have connectivity to at least one segment of the port's network.
    """

    def __init__(self):
        super(ZvmMechanismDriver, self).__init__(
            AGENT_TYPE_ZVM,
            VIF_TYPE_ZVM,
            {portbindings.CAP_PORT_FILTER: False})

    def get_allowed_network_types(self, agent=None):
        return [constants.TYPE_LOCAL, constants.TYPE_FLAT,
                constants.TYPE_VLAN]

    def get_mappings(self, agent):
        return agent['configurations'].get('vswitch_mappings', {})
