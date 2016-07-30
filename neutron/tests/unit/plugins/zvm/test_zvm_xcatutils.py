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
#from twisted.internet.test.fakeendpoint import fake

"""
Unit tests for the z/VM xCAT utils.
"""

import mock
from oslo_config import cfg

from neutron.plugins.zvm.common import exception
from neutron.plugins.zvm.common import xcatutils
from neutron.tests import base


class TestZVMXcatUtils(base.BaseTestCase):
    _FAKE_XCAT_SERVER = "127.0.0.1"
    _FAKE_XCAT_TIMEOUT = 300

    def setUp(self):
        super(TestZVMXcatUtils, self).setUp()
        cfg.CONF.set_override('zvm_xcat_server',
                              self._FAKE_XCAT_SERVER, 'AGENT')
        cfg.CONF.set_override('zvm_xcat_username',
                              'dummy', group='AGENT')
        cfg.CONF.set_override('zvm_xcat_password',
                              'dummy', group='AGENT')
        cfg.CONF.set_override('zvm_xcat_timeout',
                              self._FAKE_XCAT_TIMEOUT, 'AGENT')
        self._xcaturl = xcatutils.xCatURL()
        with mock.patch.multiple(xcatutils.httplib,
            HTTPSConnection=mock.MagicMock()):
            self._zvm_xcat_connection = xcatutils.xCatConnection()

    def test_restapi_command_return_error(self):
        fake_method = "GET"
        fake_url = "fake"
        fake_body = "fake"
        fake_messages = ('{"data":[{"data":'
                   '["zhcp: ERROR: Unsupported API function name",null]},'
                   '{"errorcode":["1"]}]}')
        try:
            with mock.patch.object(xcatutils, "LOG") as log:
                xcatutils.load_xcat_resp(fake_method, fake_url,
                                        fake_body, fake_messages)
                log.error.assert_called_with("Error returned from xCAT: %s",
                                          fake_messages)
        except Exception:
            self.assertRaises(exception.zVMInvalidxCatResponseDataError,
                              xcatutils.load_xcat_resp, fake_method, fake_url,
                              fake_body, fake_messages)

    @mock.patch('neutron.plugins.zvm.common.xcatutils.xcat_request')
    def test_get_xcat_version(self, mock_get):
        ret = ["Version 2.8.3.5 (built Mon Apr 27 10:50:11 EDT 2015)"]
        mock_get.return_value = {'data': [ret]}
        version = xcatutils.get_xcat_version()
        self.assertEqual(version, '2.8.3.5')
