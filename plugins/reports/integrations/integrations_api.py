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

from mcfw.restapi import rest
from mcfw.rpc import returns, arguments
from plugins.reports.dal import list_integrations, get_integration_settings, save_integration_settings
from plugins.reports.integrations.int_topdesk.topdesk import get_topdesk_data
from plugins.reports.integrations.to import IntegrationTO
from plugins.reports.permissions import ReportsPermission


@rest('/integrations', 'get', silent_result=True, scopes=ReportsPermission.LIST_INTEGRATIONS)
@returns([dict])
@arguments()
def api_list_settings():
    return [{'sik': integration.sik, 'name': integration.name} for integration in list_integrations()]


@rest('/integrations/<sik:[^/]+>', 'get', silent_result=True, scopes=ReportsPermission.GET_INTEGRATION)
@returns(IntegrationTO)
@arguments(sik=unicode)
def api_get_settings(sik):
    return IntegrationTO.from_model(*get_integration_settings(sik))


@rest('/integrations/<sik:[^/]+>', 'put', silent_result=True, scopes=ReportsPermission.UPDATE_INTEGRATIONS)
@returns(IntegrationTO)
@arguments(sik=unicode, data=IntegrationTO)
def api_save_settings(sik, data):
    # type: (str, IntegrationTO) -> IntegrationTO
    return IntegrationTO.from_model(*save_integration_settings(sik, data.rogerthat_api_key, data.name, data.data))


@rest('/topdesk-data', 'post', silent_result=True)
@returns(dict)
@arguments(data=dict)
def api_get_topdesk_data(data):
    return get_topdesk_data(data['api_url'], data['username'], data['password'])
