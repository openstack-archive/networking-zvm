# =================================================================
# Licensed Materials - Property of IBM
#
# (c) Copyright IBM Corp. 2014, 2015 All Rights Reserved
#
# US Government Users Restricted Rights - Use, duplication or
# disclosure restricted by GSA ADP Schedule Contract with IBM Corp.
# =================================================================
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


from neutron.plugins.ml2.drivers.zvm import mech_zvm
from neutron.tests.unit.plugins.ml2 import _test_mech_agent as base


class ZvmMechanismBaseTestCase(base.AgentMechanismBaseTestCase):
    VIF_TYPE = mech_zvm.VIF_TYPE_ZVM
    CAP_PORT_FILTER = False
    AGENT_TYPE = mech_zvm.AGENT_TYPE_ZVM

    GOOD_MAPPINGS = {'fake_physical_network': 'fake_vswitch'}
    GOOD_CONFIGS = {'vswitch_mappings': GOOD_MAPPINGS}

    BAD_MAPPINGS = {'wrong_physical_network': 'wrong_vswitch'}
    BAD_CONFIGS = {'vswitch_mappings': BAD_MAPPINGS}

    AGENTS = [{'alive': True,
               'configurations': GOOD_CONFIGS,
               'host': 'host'}]
    AGENTS_DEAD = [{'alive': False,
                    'configurations': GOOD_CONFIGS,
                    'host': 'dead_host'}]
    AGENTS_BAD = [{'alive': False,
                   'configurations': GOOD_CONFIGS,
                   'host': 'bad_host_1'},
                  {'alive': True,
                   'configurations': BAD_CONFIGS,
                   'host': 'bad_host_2'}]

    def setUp(self):
        super(ZvmMechanismBaseTestCase, self).setUp()
        self.driver = mech_zvm.ZvmMechanismDriver()
        self.driver.initialize()


class ZvmMechanismGenericTestCase(ZvmMechanismBaseTestCase,
                                  base.AgentMechanismGenericTestCase):
    pass


class ZvmMechanismLocalTestCase(ZvmMechanismBaseTestCase,
                                base.AgentMechanismLocalTestCase):
    pass


class ZvmvMechanismFlatTestCase(ZvmMechanismBaseTestCase,
                                base.AgentMechanismFlatTestCase):
    pass


class ZvmvMechanismVlanTestCase(ZvmMechanismBaseTestCase,
                                base.AgentMechanismVlanTestCase):
    pass
