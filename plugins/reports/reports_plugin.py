# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley Belgium NV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @@license_version:1.5@@

from __future__ import unicode_literals

from framework.plugin_loader import Plugin, get_plugin
from framework.utils.plugins import Handler, Module
from mcfw.consts import NOT_AUTHENTICATED
from mcfw.restapi import rest_functions
from mcfw.rpc import parse_complex_value
from plugins.basic_auth.basic_auth_plugin import get_basic_auth_plugin
from plugins.basic_auth.permissions import APP_ADMIN_GROUP_ID, BARole
from plugins.reports import rogerthat_callbacks
from plugins.reports.api import map_api, reports
from plugins.reports.bizz.rtemail import EmailHandler
from plugins.reports.handlers.cron import ReportsCleanupTimedOutHandler
from plugins.reports.integrations import integrations_api
from plugins.reports.integrations.int_topdesk.handlers import TopdeskCallbackHandler
from plugins.reports.permissions import ROLE_GROUPS, ReportsPermission
from plugins.reports.to import ReportsPluginConfiguration
from plugins.rogerthat_api.rogerthat_api_plugin import RogerthatApiPlugin


class ReportsPlugin(Plugin):
    def __init__(self, configuration):
        super(ReportsPlugin, self).__init__(configuration)
        self.configuration = parse_complex_value(ReportsPluginConfiguration, configuration, False)

        rogerthat_api_plugin = get_plugin('rogerthat_api')
        assert (isinstance(rogerthat_api_plugin, RogerthatApiPlugin))
        rogerthat_api_plugin.subscribe('messaging.flow_member_result', rogerthat_callbacks.flow_member_result)
        plugin = get_basic_auth_plugin()
        plugin.register_groups(ROLE_GROUPS)
        # Add all this plugin its permissions to the 'admin' role of the basic authentication plugin
        plugin.add_permissions_to_role(APP_ADMIN_GROUP_ID, BARole.ADMIN, ReportsPermission.all())

    def get_handlers(self, auth):
        if auth == Handler.AUTH_UNAUTHENTICATED:
            yield Handler(url='/plugins/reports/topdesk/callback_api', handler=TopdeskCallbackHandler)
            for mod in [map_api, reports]:
                for url, handler in rest_functions(mod, authentication=NOT_AUTHENTICATED):
                    yield Handler(url=url, handler=handler)
            for url, handler in rest_functions(integrations_api, authentication=NOT_AUTHENTICATED):
                yield Handler(url=url, handler=handler)
        if auth == Handler.AUTH_ADMIN:
            yield Handler(url='/_ah/mail/<email:.*>', handler=EmailHandler)
            yield Handler(url='/admin/cron/reports/cleanup/timed_out', handler=ReportsCleanupTimedOutHandler)

    def get_modules(self):
        yield Module('integrations', [], 1)

    def get_client_routes(self):
        return ['/integrations<route:.*>']
