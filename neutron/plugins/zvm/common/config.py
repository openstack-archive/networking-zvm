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

from neutron._i18n import _
from neutron.agent.common import config


agent_group = cfg.OptGroup("AGENT",
                           title="zvm agent Options",
                           help="""
zvm agent options.
""")

agent_opts = [
    cfg.StrOpt(
        'xcat_zhcp_nodename',
        default='zhcp',
        help=_('xCat zHCP nodename in xCAT ')),
    cfg.StrOpt(
        'zvm_host',
        help=_("DEPRECATED, use 'host' in neutron.conf instead."
               "If it is not specified, 'host' in neutron.conf"
               "will take effect")),
    cfg.StrOpt(
        'zvm_xcat_username',
        default=None,
        help=_('xCat REST API username')),
    cfg.StrOpt(
        'zvm_xcat_password',
        default=None,
        secret=True,
        help=_('Password of the xCat REST API user')),
    cfg.StrOpt(
        'zvm_xcat_server',
        help=_("xCat MN server address")),
    cfg.IntOpt(
        'polling_interval',
        default=2,
        help=_("The number of seconds the agent will wait between "
        "polling for local device changes.")),
    cfg.IntOpt(
        'zvm_xcat_timeout',
        default=300,
        help=_("The number of seconds the agent will wait for "
        "xCAT MN response")),
    cfg.StrOpt(
        'xcat_mgt_ip',
        default=None,
        help=_("The IP address is used for xCAT MN to management instances.")),
    cfg.StrOpt(
        'xcat_mgt_mask',
        default=None,
        help=_("The IP mask is used for xCAT MN to management instances.")),
]

CONF = cfg.CONF
CONF.register_group(agent_group)
CONF.register_opts(agent_opts, group=agent_group)
config.register_agent_state_opts_helper(cfg.CONF)
config.register_root_helper(cfg.CONF)
