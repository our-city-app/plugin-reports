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
from framework.utils.plugins import Handler
from mcfw.consts import DEBUG
from mcfw.rpc import parse_complex_value
from plugins.reports import rogerthat_callbacks
from plugins.reports.bizz.rtemail import EmailHandler
from plugins.reports.handlers import ReportItemsHandler, \
    ReportItemDetailsHandler, ReportItemsVoteHandler
from plugins.reports.handlers.cron import ReportsCleanupTimedOutHandler
from plugins.reports.integrations.int_topdesk.handlers import TopdeskCallbackHandler
from plugins.reports.to import ReportsPluginConfiguration
from plugins.rogerthat_api.rogerthat_api_plugin import RogerthatApiPlugin


class ReportsPlugin(Plugin):
    def __init__(self, configuration):
        super(ReportsPlugin, self).__init__(configuration)
        self.configuration = parse_complex_value(ReportsPluginConfiguration, configuration, False)
        if DEBUG:
            self.configuration.base_url = 'http://localhost:8800'

        rogerthat_api_plugin = get_plugin('rogerthat_api')
        assert (isinstance(rogerthat_api_plugin, RogerthatApiPlugin))
        rogerthat_api_plugin.subscribe('messaging.flow_member_result', rogerthat_callbacks.flow_member_result)

    def get_handlers(self, auth):
        if auth == Handler.AUTH_UNAUTHENTICATED:
            yield Handler(url='/plugins/reports/topdesk/callback_api', handler=TopdeskCallbackHandler)
            yield Handler(url='/plugins/reports/items', handler=ReportItemsHandler)
            yield Handler(url='/plugins/reports/items/detail', handler=ReportItemDetailsHandler)
            yield Handler(url='/plugins/reports/items/vote', handler=ReportItemsVoteHandler)
        if auth == Handler.AUTH_ADMIN:
            yield Handler(url='/_ah/mail/<email:.*>', handler=EmailHandler)
            yield Handler(url='/admin/cron/reports/cleanup/timed_out', handler=ReportsCleanupTimedOutHandler)
