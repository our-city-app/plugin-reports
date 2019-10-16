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
from plugins.reports.models import RogerthatUser, Incident, IntegrationSettings, \
    Consumer


@returns()
@arguments(sik=unicode, integration=unicode, params=dict)
def save_integration_settings(sik, integration, params):
    k = IntegrationSettings.create_key(sik)
    settings = k.get()
    if not settings:
        settings = IntegrationSettings(key=k)

    settings.integration = integration
    settings.params = params
    settings.put()


@returns(IntegrationSettings)
@arguments(sik=unicode)
def get_integration_settings(sik):
    return IntegrationSettings.create_key(sik).get()


@returns(Consumer)
@arguments(consumer_key=unicode)
def get_consumer(consumer_key):
    return Consumer.create_key(consumer_key).get()


def save_rogerthat_user(user_details):
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
    return RogerthatUser.create_key(user_id).get()


def get_incident(incident_id):
    return Incident.create_key(incident_id).get()
