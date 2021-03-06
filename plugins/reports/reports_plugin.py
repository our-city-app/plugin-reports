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

import webapp2

from framework.bizz.authentication import get_current_session
from framework.handlers import render_logged_in_page
from framework.plugin_loader import Plugin, get_plugin, get_auth_plugin
from framework.utils.plugins import Handler, Module
from mcfw.consts import NOT_AUTHENTICATED
from mcfw.restapi import rest_functions
from mcfw.rpc import parse_complex_value
from plugins.basic_auth.basic_auth_plugin import get_basic_auth_plugin
from plugins.basic_auth.permissions import APP_ADMIN_GROUP_ID, BARole
from plugins.reports import rogerthat_callbacks
from plugins.reports.api import map_api, reports, green_valley
from plugins.reports.bizz.rtemail import EmailHandler
from plugins.reports.handlers.cron import ReportsCleanupTimedOutHandler, \
    ReportsCountIncidentsHandler, BuildIncidentStatisticsHandler
from plugins.reports.integrations import integrations_api
from plugins.reports.integrations.int_green_valley.notifications import NotificationAttachmentHandler
from plugins.reports.integrations.int_topdesk.handlers import TopdeskCallbackHandler
from plugins.reports.permissions import ROLE_GROUPS, ReportsPermission
from plugins.reports.to import ReportsPluginConfiguration
from plugins.rogerthat_api.rogerthat_api_plugin import RogerthatApiPlugin


class IndexHandler(webapp2.RequestHandler):
    def get(self, *args, **kwargs):
        if get_current_session():
            render_logged_in_page(self)
        else:
            self.redirect(get_auth_plugin().get_login_url())


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
            yield Handler(url='/', handler=IndexHandler)
            yield Handler(url='/plugins/reports/topdesk/callback_api', handler=TopdeskCallbackHandler)
            for mod in [map_api, reports, integrations_api, green_valley]:
                for url, handler in rest_functions(mod, authentication=NOT_AUTHENTICATED):
                    yield Handler(url=url, handler=handler)
            yield Handler(
                '/plugins/reports/green_valley/<integration_id:[^/]+>/notifications/<notification_id:[^/]+>/attachments/<attachment_id:[^/]+>',
                NotificationAttachmentHandler)
        if auth == Handler.AUTH_ADMIN:
            yield Handler(url='/_ah/mail/<email:.*>', handler=EmailHandler)
            yield Handler(url='/admin/cron/reports/cleanup/timed_out', handler=ReportsCleanupTimedOutHandler)
            yield Handler(url='/admin/cron/reports/incidents/count', handler=ReportsCountIncidentsHandler)
            yield Handler(url='/admin/cron/reports/incidents-stats', handler=BuildIncidentStatisticsHandler)

    def get_modules(self):
        yield Module('integrations', [], 1)

    def get_client_routes(self):
        return ['/integrations<route:.*>']
