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
from neutron.conf.agent import common as config


agent_opts = [
    cfg.IntOpt(
        'polling_interval',
        default=2,
        help=_("The number of seconds the agent will wait between "
        "polling for local device changes.")),
    cfg.URIOpt('cloud_connector_url',
               schemes=['http', 'https'],
               sample_default='http://zvm.example.org:8080/',
               help="""
URL to be used to communicate with z/VM Cloud Connector.
"""),
    cfg.StrOpt('zvm_cloud_connector_ca_file',
               default=None,
               help="""
CA certificate file to be verified in httpd server.
A string, it must be a path to a CA bundle to use.
"""),
    cfg.StrOpt('zvm_cloud_connector_token_file',
               default=None,
               help="""
Token file that contains admin-token to access sdk http server.
"""),
]

CONF = cfg.CONF
CONF.register_opts(agent_opts, "AGENT")
config.register_agent_state_opts_helper(cfg.CONF)
config.register_root_helper(cfg.CONF)
