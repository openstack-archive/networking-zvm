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

from neutron_lib import exceptions as exception


from neutron._i18n import _


class zvmException(exception.NeutronException):
    message = _('zvmException: %(msg)s')


class zVMConfigException(exception.NeutronException):
    message = _('zVMConfig Error: %(msg)s')


class zVMxCatConnectionFailed(exception.NeutronException):
    message = _('Failed to connect xCAT server: %(xcatserver)s')


class zVMxCatRequestFailed(exception.NeutronException):
    message = _('Request to xCAT server %(xcatserver)s failed: %(err)s')


class zVMJsonLoadsError(exception.NeutronException):
    message = _('JSON loads error: not in JSON format')


class zVMInvalidDataError(exception.NeutronException):
    message = _('Invalid data error: %(msg)s')


class zVMInvalidxCatResponseDataError(exception.NeutronException):
    message = _('Invalid data returned from xCAT: %(msg)s')
