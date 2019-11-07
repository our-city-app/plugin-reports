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
from google.appengine.ext import ndb

from mcfw.exceptions import HttpNotFoundException
from plugins.reports.bizz.elasticsearch import re_index_incident
from plugins.reports.models import IntegrationSettingsData, IntegrationSettings, Consumer, RogerthatUser, Incident
from plugins.reports.to import IncidentTO
from plugins.rogerthat_api.models.settings import RogerthatSettings
from plugins.rogerthat_api.to import UserDetailsTO
from typing import List, Tuple


def save_integration_settings(integration_id, rogerthat_api_key, name, consumer_id, sik, data):
    # type: (int, str, str, str, str, IntegrationSettingsData) -> Tuple[IntegrationSettings, RogerthatSettings]
    if not integration_id:
        settings = IntegrationSettings(key=IntegrationSettings.create_key(IntegrationSettings.allocate_ids(1)[0]))
    else:
        settings = IntegrationSettings.create_key(integration_id).get()
    settings.integration = data.provider
    settings.name = name

    rogerthat_settings = RogerthatSettings(key=RogerthatSettings.create_key(sik))
    rogerthat_settings.ref = name
    rogerthat_settings.api_key = rogerthat_api_key

    if settings.consumer_id:
        Consumer.create_key(settings.consumer_id).delete()
    settings.consumer_id = consumer_id
    settings.sik = sik

    consumer = Consumer(key=Consumer.create_key(sik))
    consumer.ref = name
    consumer.integration_id = settings.id

    settings.data = data
    ndb.put_multi([settings, rogerthat_settings, consumer])
    return settings, rogerthat_settings


def list_integrations():
    # type: () -> List[IntegrationSettings]
    return IntegrationSettings.list()


def get_integration_settings(integration_id):
    # type: (int) -> IntegrationSettings
    settings = IntegrationSettings.create_key(integration_id).get()
    if not settings:
        raise HttpNotFoundException('settings_not_found', {'integration_id': integration_id})
    return settings


def get_integration_settings_tuple(integration_id):
    # type: (int) -> Tuple[IntegrationSettings, RogerthatSettings]
    settings = IntegrationSettings.create_key(integration_id).get()
    rt_settings = RogerthatSettings.create_key(settings.sik).get() if settings.sik else None
    if not settings:
        raise HttpNotFoundException('settings_not_found', {'integration_id': integration_id})
    return settings, rt_settings


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


def get_incident_by_external_id(integration_id, external_id):
    # type: (int, str) -> Incident
    return Incident.get_by_external_id(integration_id, external_id)


def update_incident(incident, data):
    # type: (Incident, IncidentTO) -> Incident
    incident.set_status(data.status)
    incident.visible = data.visible if incident.can_show_on_map else False
    incident.put()
    re_index_incident(incident)
    return incident
