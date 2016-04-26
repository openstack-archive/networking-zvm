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

import contextlib
import functools

from oslo_log import log as logging
from oslo_serialization import jsonutils
from six.moves import http_client as httplib

from neutron._i18n import _LE
from neutron.plugins.zvm.common import config
from neutron.plugins.zvm.common import constants
from neutron.plugins.zvm.common import exception

LOG = logging.getLogger(__name__)
CONF = config.CONF


class xCatURL(object):
    """To return xCat url for invoking xCat REST API."""

    def __init__(self):
        """Set constant that used to form xCat url."""
        self.PREFIX = '/xcatws'
        self.SUFFIX = ('?userName=' + CONF.AGENT.zvm_xcat_username +
                       '&password=' + CONF.AGENT.zvm_xcat_password +
                       '&format=json')

        self.NODES = '/nodes'
        self.TABLES = '/tables'
        self.XDSH = '/dsh'

    def tabdump(self, arg='', addp=None):
        rurl = self.PREFIX + self.TABLES + arg + self.SUFFIX
        return self._append_addp(rurl, addp)

    def _append_addp(self, rurl, addp=None):
        if addp is not None:
            return rurl + addp
        else:
            return rurl

    def gettab(self, arg='', addp=None):
        """Get table arg, with attribute addp."""
        rurl = self.PREFIX + self.TABLES + arg + self.SUFFIX
        return self._append_addp(rurl, addp)

    def tabch(self, arg='', addp=None):
        """Add/update/delete row(s) in table arg, with attribute addp."""
        rurl = self.PREFIX + self.TABLES + arg + self.SUFFIX
        return self._append_addp(rurl, addp)

    def xdsh(self, arg=''):
        """Run shell command."""
        return self.PREFIX + self.NODES + arg + self.XDSH + self.SUFFIX


class xCatConnection():
    """Https requests to xCat web service."""
    def __init__(self):
        """Initialize https connection to xCat service."""
        self.host = CONF.AGENT.zvm_xcat_server
        self.xcat_timeout = CONF.AGENT.zvm_xcat_timeout
        try:
            self.conn = httplib.HTTPSConnection(self.host, None, None, None,
                                                True, self.xcat_timeout)
        except Exception:
            LOG.error(_LE("Connect to xCat server %s failed") % self.host)
            raise exception.zVMxCatConnectionFailed(xcatserver=self.host)

    def request(self, method, url, body=None, headers=None):
        """Do http request to xCat server

        Will return (response_status, response_reason, response_body)
        """
        headers = headers or {}
        if body is not None:
            body = jsonutils.dumps(body)
            headers = {'content-type': 'text/plain',
                       'content-length': len(body)}

        try:
            self.conn.request(method, url, body, headers)
        except Exception as err:
            LOG.error(_LE("Request to xCat server %(host)s failed: %(err)s") %
                      {'host': self.host, 'err': err})
            raise exception.zVMxCatRequestFailed(xcatserver=self.host,
                                                 err=err)

        res = self.conn.getresponse()
        msg = res.read()
        resp = {
            'status': res.status,
            'reason': res.reason,
            'message': msg}

        # NOTE(rui): Currently, only xCat returns 200 or 201 can be
        #            considered acceptable.
        err = None
        if method == "POST":
            if res.status != 201:
                err = str(resp)
        else:
            if res.status != 200:
                err = str(resp)

        if err is not None:
            LOG.error(_LE("Request to xCat server %(host)s failed: %(err)s") %
                      {'host': self.host, 'err': err})
            raise exception.zVMxCatRequestFailed(xcatserver=self.host,
                                                 err=err)

        return resp


def xcat_request(method, url, body=None, headers=None):
    headers = headers or {}
    conn = xCatConnection()
    resp = conn.request(method, url, body, headers)
    return load_xcat_resp(method, url, body, resp['message'])


def jsonloads(jsonstr):
    try:
        return jsonutils.loads(jsonstr)
    except ValueError:
        LOG.error(_LE("Respone is not in JSON format"))
        raise exception.zVMJsonLoadsError()


def wrap_invalid_xcat_resp_data_error(function):
    """zVM driver get zVM hypervisor and virtual machine information
    from xCat. xCat REST API response has its own fixed format(a JSON
    stream). zVM driver abstract useful info base on the special format,
    and raise exception if the data in incorrect format.
    """
    @functools.wraps(function)
    def decorated_function(*arg, **kwargs):
        try:
            return function(*arg, **kwargs)
        except (ValueError, TypeError, IndexError) as err:
            LOG.error(_LE('Invalid data returned from xCat: %s') % err)
            raise exception.zVMInvalidxCatResponseDataError(msg=err)
        except Exception as err:
            raise

    return decorated_function


@wrap_invalid_xcat_resp_data_error
def load_xcat_resp(method, url, body, message):
    """Abstract information from xCat REST response body.

    As default, xCat response will in format of JSON and can be
    converted to Python dictionary, would looks like:
    {"data": [{"info": [info,]}, {"data": [data,]}, ..., {"error": [error,]}]}

    Returns a Python dictionary, looks like:
    {'info': [info,],
     'data': [data,],
     'error': [error,]}
    """
    resp_list = jsonloads(message)['data']
    keys = constants.XCAT_RESPONSE_KEYS
    msg = ("url is %(url)s, body is %(body)s, result is %(result)s" %
           {'url': url, 'body': body, 'result': message})
    resp = {}
    try:
        for k in keys:
            resp[k] = []

        for d in resp_list:
            for k in keys:
                if d.get(k) is not None:
                    resp[k].append(d.get(k))
    except Exception:
        LOG.error(_LE("Invalid data returned from xCat: %s") % msg)
        raise exception.zVMInvalidxCatResponseDataError(msg=msg)

    LOG.debug("Data return from xCAT restapi: %s" % message)
    if not verify_xcat_resp(method, resp):
        raise exception.zVMInvalidxCatResponseDataError(msg=msg)
    else:
        return resp


@wrap_invalid_xcat_resp_data_error
def verify_xcat_resp(method, resp_dict):
    """Check whether xCAT REST API response contains an error."""
    if resp_dict.get('error'):
        if resp_dict['error'][0][0].find('Warning'):
            return True
        return False
    elif method == "GET" and (
        resp_dict.get('errorcode') and resp_dict['errorcode'][0][0] != '0'):
        return False
    elif method == "GET" and not (resp_dict.get('data')
              and resp_dict['data'] and resp_dict['data'][0]):
        return False
    else:
        return True


@contextlib.contextmanager
def expect_invalid_xcat_resp_data():
    """Catch exceptions when using xCAT response data."""
    try:
        yield
    except (ValueError, TypeError, IndexError, AttributeError,
            KeyError) as err:
        raise exception.zVMInvalidxCatResponseDataError(msg=err)
