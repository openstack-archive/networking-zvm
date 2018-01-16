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

"""
Unit tests for the z/VM utils.
"""
import mock
import os

from oslo_config import cfg

from neutron.plugins.zvm.common import exception
from neutron.plugins.zvm.common import utils
from neutron.tests import base
from zvmconnector import connector

HTTPS_SDK_URL = 'https://10.10.10.1:8080'
HTTP_SDK_URL = 'http://10.10.10.1:8080'
CA_FILE = '/tmp/ca.pem'
TOKEN_FILE = '/tmp/token.dat'


class TestZVMUtils_HTTPS_without_verify(base.BaseTestCase):
    def setUp(self):
        super(TestZVMUtils_HTTPS_without_verify, self).setUp()
        self.addCleanup(cfg.CONF.reset)
        cfg.CONF.set_override('cloud_connector_url', HTTPS_SDK_URL,
                              group='AGENT')
        self._utils = utils.zVMConnectorRequestHandler()

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call(self, request):
        request.return_value = {"overallRC": 0, 'output': "OK"}
        info = self._utils.call('API', "parm1", "parm2")
        request.assert_called_with('API', "parm1", "parm2")
        self.assertEqual("OK", info)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call_exception(self, request):
        request.return_value = {"overallRC": 1, 'output': ""}
        self.assertRaises(exception.ZVMSDKRequestFailed,
                          self._utils.call,
                          "API")


class TestZVMUtils_HTTPS_with_verify(base.BaseTestCase):
    def setUp(self):
        super(TestZVMUtils_HTTPS_with_verify, self).setUp()
        if not os.path.exists(CA_FILE):
            os.mknod(CA_FILE)
        cfg.CONF.set_override('cloud_connector_url', HTTPS_SDK_URL,
                              group='AGENT')
        cfg.CONF.set_override('zvm_cloud_connector_ca_file', CA_FILE,
                              group='AGENT')
        self._utils = utils.zVMConnectorRequestHandler()
        self.addCleanup(cfg.CONF.reset)
        self.addCleanup(os.remove, CA_FILE)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call(self, request):
        request.return_value = {"overallRC": 0, 'output': "OK"}
        info = self._utils.call('API', "parm1", "parm2")
        request.assert_called_with('API', "parm1", "parm2")
        self.assertEqual("OK", info)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call_exception(self, request):
        request.return_value = {"overallRC": 1, 'output': ""}
        self.assertRaises(exception.ZVMSDKRequestFailed,
                          self._utils.call,
                          "API")


class TestZVMUtils_HTTP_without_verify(base.BaseTestCase):
    def setUp(self):
        super(TestZVMUtils_HTTP_without_verify, self).setUp()
        self.addCleanup(cfg.CONF.reset)
        cfg.CONF.set_override('cloud_connector_url', HTTP_SDK_URL,
                              group='AGENT')
        self._utils = utils.zVMConnectorRequestHandler()

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call(self, request):
        request.return_value = {"overallRC": 0, 'output': "OK"}
        info = self._utils.call('API', "parm1", "parm2")
        request.assert_called_with('API', "parm1", "parm2")
        self.assertEqual("OK", info)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call_exception(self, request):
        request.return_value = {"overallRC": 1, 'output': ""}
        self.assertRaises(exception.ZVMSDKRequestFailed,
                          self._utils.call,
                          "API")


class TestZVMUtils_HTTP_with_verify(base.BaseTestCase):
    def setUp(self):
        super(TestZVMUtils_HTTP_with_verify, self).setUp()
        if not os.path.exists(CA_FILE):
            os.mknod(CA_FILE)
        cfg.CONF.set_override('cloud_connector_url', HTTP_SDK_URL,
                              group='AGENT')
        cfg.CONF.set_override('zvm_cloud_connector_ca_file', CA_FILE,
                              group='AGENT')
        self._utils = utils.zVMConnectorRequestHandler()
        self.addCleanup(cfg.CONF.reset)
        self.addCleanup(os.remove, CA_FILE)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call(self, request):
        request.return_value = {"overallRC": 0, 'output': "OK"}
        info = self._utils.call('API', "parm1", "parm2")
        request.assert_called_with('API', "parm1", "parm2")
        self.assertEqual("OK", info)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call_exception(self, request):
        request.return_value = {"overallRC": 1, 'output': ""}
        self.assertRaises(exception.ZVMSDKRequestFailed,
                          self._utils.call,
                          "API")


class TestZVMUtils_HTTP_token_with_verify(base.BaseTestCase):
    def setUp(self):
        super(TestZVMUtils_HTTP_token_with_verify, self).setUp()
        if not os.path.exists(CA_FILE):
            os.mknod(CA_FILE)
        if not os.path.exists(TOKEN_FILE):
            os.mknod(TOKEN_FILE)
        cfg.CONF.set_override('cloud_connector_url', HTTP_SDK_URL,
                              group='AGENT')
        cfg.CONF.set_override('zvm_cloud_connector_ca_file', CA_FILE,
                              group='AGENT')
        cfg.CONF.set_override('zvm_cloud_connector_token_file', TOKEN_FILE,
                              group='AGENT')
        self._utils = utils.zVMConnectorRequestHandler()
        self.addCleanup(cfg.CONF.reset)
        self.addCleanup(os.remove, CA_FILE)
        self.addCleanup(os.remove, TOKEN_FILE)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call(self, request):
        request.return_value = {"overallRC": 0, 'output': "OK"}
        info = self._utils.call('API', "parm1", "parm2")
        request.assert_called_with('API', "parm1", "parm2")
        self.assertEqual("OK", info)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call_exception(self, request):
        request.return_value = {"overallRC": 1, 'output': ""}
        self.assertRaises(exception.ZVMSDKRequestFailed,
                          self._utils.call,
                          "API")


class TestZVMUtils_HTTPS_token_without_verify(base.BaseTestCase):
    def setUp(self):
        super(TestZVMUtils_HTTPS_token_without_verify, self).setUp()
        if not os.path.exists(TOKEN_FILE):
            os.mknod(TOKEN_FILE)
        cfg.CONF.set_override('cloud_connector_url', HTTPS_SDK_URL,
                              group='AGENT')
        cfg.CONF.set_override('zvm_cloud_connector_token_file', TOKEN_FILE,
                              group='AGENT')
        self._utils = utils.zVMConnectorRequestHandler()
        self.addCleanup(cfg.CONF.reset)
        self.addCleanup(os.remove, TOKEN_FILE)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call(self, request):
        request.return_value = {"overallRC": 0, 'output': "OK"}
        info = self._utils.call('API', "parm1", "parm2")
        request.assert_called_with('API', "parm1", "parm2")
        self.assertEqual("OK", info)

    @mock.patch.object(connector.ZVMConnector, 'send_request')
    def test_call_exception(self, request):
        request.return_value = {"overallRC": 1, 'output': ""}
        self.assertRaises(exception.ZVMSDKRequestFailed,
                          self._utils.call,
                          "API")
