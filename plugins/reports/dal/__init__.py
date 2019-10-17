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

from mcfw.rpc import returns, arguments
from plugins.reports.models import IntegrationSettingsData, IntegrationSettings, Consumer, RogerthatUser, Incident
from plugins.rogerthat_api.to import UserDetailsTO


@returns()
@arguments(sik=unicode, integration=unicode, data=IntegrationSettingsData)
def save_integration_settings(sik, integration, data):
    # type: (str, str, IntegrationSettingsData) -> IntegrationSettings
    k = IntegrationSettings.create_key(sik)
    settings = k.get() or IntegrationSettings(key=k)
    settings.integration = integration
    settings.data = data
    settings.put()
    return settings


@returns(IntegrationSettings)
@arguments(sik=unicode)
def get_integration_settings(sik):
    # type: (str) -> IntegrationSettings
    return IntegrationSettings.create_key(sik).get()


@returns(Consumer)
@arguments(consumer_key=unicode)
def get_consumer(consumer_key):
    # type: (str) -> Consumer
    return Consumer.create_key(consumer_key).get()


def save_rogerthat_user(user_details):
    # type: (UserDetailsTO) -> RogerthatUser
    rt_user_id = RogerthatUser.create_user_id(user_details.email, user_details.app_id)
    rt_user_key = RogerthatUser.create_key(rt_user_id)
    rt_user = rt_user_key.get()
    if not rt_user:
        rt_user = RogerthatUser(key=rt_user_key)
        rt_user.email = user_details.email
        rt_user.name = user_details.name
        rt_user.avatar_url = user_details.avatar_url
        rt_user.language = user_details.language
        rt_user.app_id = user_details.app_id
        rt_user.put()

    return rt_user


def get_rogerthat_user(user_id):
    # type: (str) -> RogerthatUser
    return RogerthatUser.create_key(user_id).get()


def get_incident(incident_id):
    # type: (str) -> Incident
    return Incident.create_key(incident_id).get()
