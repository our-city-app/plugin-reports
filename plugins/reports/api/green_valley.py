# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley NV
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

from framework.plugin_loader import get_config
from framework.utils import try_or_defer
from mcfw.restapi import rest
from mcfw.rpc import returns, arguments
from plugins.reports.consts import NAMESPACE
from plugins.reports.integrations.int_green_valley.green_valley import handle_message_received
from plugins.reports.integrations.int_green_valley.notifications import GVExternalNotification
from plugins.reports.models import IntegrationSettings, IntegrationProvider


def validate_request(f, handler):
    auth = handler.request.headers.get('Authorization', None)
    return auth == get_config(NAMESPACE).gv_activemq_proxy_secret


@rest('/green-valley/topics', 'get', silent_result=True)
@returns([dict])
@arguments()
def api_get_topics():
    integrations = IntegrationSettings.list_by_integration(IntegrationProvider.GREEN_VALLEY)
    return [{'integration_id': integration.id, 'name': integration.data.topic}
            for integration in integrations if integration.data.topic]


@rest('/green-valley/message/<integration_id:[^/]+>', 'post', silent_result=True, custom_auth_method=validate_request)
@returns()
@arguments(integration_id=(int, long), data=GVExternalNotification)
def api_on_message(integration_id, data):
    try_or_defer(handle_message_received, integration_id, data)
