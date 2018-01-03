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


class zVMInvalidDataError(exception.NeutronException):
    message = _('Invalid data error: %(msg)s')


class ZVMSDKRequestFailed(exception.NeutronException):
    message = _('z/VM SDK request failed: %(msg)s')

    def __init__(self, **kwargs):
        self.results = {'rs': 0, 'overallRC': 1, 'modID': 0, 'rc': 0,
                        'output': '', 'errmsg': ''}
        if 'results' in kwargs:
            self.results = kwargs.pop('results')
        super(ZVMSDKRequestFailed, self).__init__(**kwargs)
