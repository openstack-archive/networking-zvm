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

XCAT_RESPONSE_KEYS = ('info', 'data', 'node', 'errorcode', 'error')


# It means we introduced 'version' concept at 2.8.3.7
# later on, any new features especially backward incompatible
# change need a new version such as
# Support_xxxx = 'x.x.x.x', then we will compare whether
# The XCAT we are using has higher or lower version than x.x.x.x
# and do different things according to the version
# we might INFO in log if version is lower than XCAT_INIT_VERSION
XCAT_INIT_VERSION = '2.8.3.7'

# From 2.8.3.7 version, openstack will only send 'nozip' format
# to xcat, so before that, a tgz format will be send and processed
# while >= this version, a nozip flag along with tar format is sent.
# xcat was bumped to this version at 2015.08.06, so version lower than
# it should use zip format instead.
XCAT_BUNDLE_USE_NOZIP = '2.8.3.7'

XCAT_SUPPORT_CHVM_SMCLI_VERSION = '2.8.3.8'


# This is minimum version of xcat needed, if xcat version is lower than
# that, some functions will be missing and neutron agent can't start up
# TODO(jichenjc) clean version check below the minimum version.
XCAT_MINIMUM_VERSION = '2.8.3.16'
