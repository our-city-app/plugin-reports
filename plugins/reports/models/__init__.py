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

from framework.models.common import NdbModel, TOProperty
from framework.to import TO
from mcfw.properties import unicode_property, object_factory, unicode_list_property, long_property, bool_property, \
    typed_property
from plugins.reports.consts import NAMESPACE
from plugins.rogerthat_api.plugin_utils import Enum


class ElasticsearchSettings(NdbModel):
    NAMESPACE = NAMESPACE

    base_url = ndb.StringProperty(indexed=False)

    auth_username = ndb.StringProperty(indexed=False)
    auth_password = ndb.StringProperty(indexed=False)

    @classmethod
    def create_key(cls):
        return ndb.Key(cls, u'ElasticsearchSettings', namespace=cls.NAMESPACE)


class BaseIntegrationSettings(TO):
    provider = unicode_property('provider')


class TopdeskfieldMapping(TO):
    # id of form step
    step_id = unicode_property('step_id')
    # property name on topdesk, See TopdeskPropertyName
    property = unicode_property('property')
    # in case of optional fields, there need to be one or more value fields. SEE TEXT_OPTIONS
    value_properties = unicode_list_property('value_properties')
    # See TopdeskFieldMappingType
    type = long_property('type')
    # In case type == TopdeskFieldMappingType.FIXED_VALUE, 'step_id' is ignored and this is always used
    default_value = unicode_property('default_value')


class TopdeskSettings(BaseIntegrationSettings):
    api_url = unicode_property('api_url')
    username = unicode_property('username')
    password = unicode_property('password')
    call_type_id = unicode_property('call_type_id')
    category_id = unicode_property('category_id')
    sub_category_id = unicode_property('sub_category_id')
    entry_type_id = unicode_property('entry_type_id')
    operator_id = unicode_property('operator_id')
    operator_group_id = unicode_property('operator_group_id')
    caller_branch_id = unicode_property('caller_branch_id')
    branch_id = unicode_property('branch_id')
    unregistered_users = bool_property('unregistered_users')
    field_mapping = typed_property('field_mapping', TopdeskfieldMapping, True)


class ThreePSettings(BaseIntegrationSettings):
    gcs_bucket_name = unicode_property('gcs_bucket_name')


class IntegrationProvider(Enum):
    TOPDESK = u'topdesk'
    THREE_P = u'3p'


INTEGRATION_SETTINGS_MAPPING = {
    IntegrationProvider.TOPDESK: TopdeskSettings,
    IntegrationProvider.THREE_P: ThreePSettings,
}


class IntegrationSettingsData(object_factory):
    provider = unicode_property('provider')

    def __init__(self):
        super(IntegrationSettingsData, self).__init__('provider', INTEGRATION_SETTINGS_MAPPING)


class IntegrationSettings(NdbModel):
    NAMESPACE = NAMESPACE

    integration = ndb.StringProperty(indexed=False)
    data = TOProperty(IntegrationSettingsData())

    @property
    def sik(self):
        return self.key.id().decode('utf8')

    @classmethod
    def create_key(cls, sik):
        return ndb.Key(cls, sik, namespace=NAMESPACE)


class Consumer(NdbModel):
    NAMESPACE = NAMESPACE

    ref = ndb.StringProperty(indexed=False)
    sik = ndb.StringProperty(indexed=False)

    @property
    def consumer_key(self):
        return self.key.id().decode('utf8')

    @classmethod
    def create_key(cls, consumer_key):
        return ndb.Key(cls, consumer_key, namespace=cls.NAMESPACE)


class RogerthatUser(NdbModel):
    NAMESPACE = NAMESPACE

    email = ndb.StringProperty(indexed=False)
    name = ndb.StringProperty(indexed=False)
    avatar_url = ndb.StringProperty(indexed=False)
    language = ndb.StringProperty(indexed=False)
    app_id = ndb.StringProperty(indexed=False)
    external_id = ndb.StringProperty()

    @property
    def user_id(self):
        return self.key.id().decode('utf8')

    @classmethod
    def create_user_id(cls, email, app_id):
        return '%s:%s' % (email, app_id)

    @classmethod
    def create_key(cls, user_id):
        return ndb.Key(cls, user_id, namespace=cls.NAMESPACE)


class IncidentStatus(Enum):
    # TODO real statuses
    TODO = 'todo'


class IncidentDetails(NdbModel):
    status = ndb.StringProperty(indexed=False, choices=[IncidentStatus.all()])
    title = ndb.StringProperty(indexed=False)
    description = ndb.TextProperty(indexed=False)
    geo_location = ndb.GeoPtProperty(indexed=False)


class Incident(NdbModel):
    NAMESPACE = NAMESPACE

    sik = ndb.StringProperty(indexed=True)
    user_id = ndb.StringProperty(indexed=True)
    report_time = ndb.DateTimeProperty(indexed=True)
    resolve_time = ndb.DateTimeProperty(indexed=True)

    visible = ndb.BooleanProperty(indexed=True, default=False)
    cleanup_time = ndb.DateTimeProperty(indexed=True)

    integration = ndb.StringProperty(indexed=False)
    params = ndb.JsonProperty()

    details = ndb.LocalStructuredProperty(IncidentDetails)

# topdesk
# incident_number = ndb.StringProperty(indexed=True)
# parent_message_key = ndb.StringProperty(indexed=True)
# status = ndb.StringProperty(indexed=True)

    @property
    def incident_id(self):
        return self.key.id()

    @classmethod
    def create_key(cls, incident_id):
        return ndb.Key(cls, incident_id, namespace=cls.NAMESPACE)


class IncidentVote(NdbModel):
    NAMESPACE = NAMESPACE

    NEGATIVE = u'negative'
    POSITIVE = u'positive'

    negative_count = ndb.IntegerProperty(indexed=False)
    positive_count = ndb.IntegerProperty(indexed=False)

    @property
    def incident_id(self):
        return self.key.id().decode('utf8')

    @classmethod
    def create_key(cls, incident_id):
        return ndb.Key(cls, incident_id, namespace=cls.NAMESPACE)


class UserIncidentVote(NdbModel):
    NAMESPACE = NAMESPACE

    incident_id = ndb.StringProperty(indexed=True)
    option_id = ndb.StringProperty(indexed=True)

    @classmethod
    def create_parent_key(cls, user_id):
        return ndb.Key(cls, user_id, namespace=cls.NAMESPACE)

    @classmethod
    def create_key(cls, user_id, incident_id):
        return ndb.Key(cls, incident_id, parent=cls.create_parent_key(user_id))
