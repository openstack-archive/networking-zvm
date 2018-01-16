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


from oslo_log import log as logging
import six.moves.urllib.parse as urlparse

from neutron.plugins.zvm.common import config as cfg
from neutron.plugins.zvm.common import exception
from zvmconnector import connector

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class zVMConnectorRequestHandler(object):

    def __init__(self):
        _url = urlparse.urlparse(CONF.AGENT.cloud_connector_url)
        _ca_file = CONF.AGENT.zvm_cloud_connector_ca_file
        _token_file = CONF.AGENT.zvm_cloud_connector_token_file
        kwargs = {}
        if _url.scheme == 'https':
            kwargs['ssl_enabled'] = True
        else:
            kwargs['ssl_enabled'] = False

        if _token_file is not None:
            kwargs['token_path'] = _token_file

        if ((kwargs['ssl_enabled']) and
            (_ca_file is not None)):
            kwargs['verify'] = _ca_file
        else:
            kwargs['verify'] = False

        self._conn = connector.ZVMConnector(_url.hostname, _url.port, **kwargs)

    def call(self, func_name, *args, **kwargs):
        results = self._conn.send_request(func_name, *args, **kwargs)
        if results['overallRC'] == 0:
            return results['output']
        else:
            msg = ("SDK request %(api)s failed with parameters: %(args)s "
                   "%(kwargs)s . Results: %(results)s" %
                   {'api': func_name, 'args': str(args), 'kwargs': str(kwargs),
                    'results': str(results)})
            LOG.debug(msg)
            raise exception.ZVMSDKRequestFailed(msg=msg, results=results)


class zvmUtils(object):

    def __init__(self):
        self._requesthandler = zVMConnectorRequestHandler()

    def get_port_map(self):
        ports_info = self._requesthandler.call('guests_get_nic_info')
        ports = {}
        for p in ports_info:
            if p['port'] is not None:
                userid = p['userid']
                vswitch = p['switch']
                port_id = p['port']
                ports[port_id] = {'userid': userid,
                                  'vswitch': vswitch}
        return ports
