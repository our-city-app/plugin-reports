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
from plugins.rogerthat_api.to.messaging.flow import FLOW_STEP_TO


class ElasticsearchSettings(NdbModel):
    NAMESPACE = NAMESPACE

    base_url = ndb.StringProperty(indexed=False)

    auth_username = ndb.StringProperty(indexed=False)
    auth_password = ndb.StringProperty(indexed=False)

    @classmethod
    def create_key(cls):
        return ndb.Key(cls, u'ElasticsearchSettings', namespace=cls.NAMESPACE)


class IntegrationProvider(Enum):
    TOPDESK = u'topdesk'
    THREE_P = u'3p'


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


class TopdeskSettings(TO):
    provider = unicode_property('provider', default=IntegrationProvider.THREE_P)
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


class ThreePSettings(TO):
    provider = unicode_property('provider', default=IntegrationProvider.THREE_P)
    gcs_bucket_name = unicode_property('gcs_bucket_name')


INTEGRATION_SETTINGS_MAPPING = {
    IntegrationProvider.TOPDESK: TopdeskSettings,
    IntegrationProvider.THREE_P: ThreePSettings,
}


class IntegrationSettingsData(object_factory):
    provider = unicode_property('provider')

    def __init__(self):
        super(IntegrationSettingsData, self).__init__('provider', INTEGRATION_SETTINGS_MAPPING)


class IncidentSource(object_factory):
    FLOW = 1


class IncidentParamsFlow(TO):
    t = long_property('t', default=IncidentSource.FLOW)
    parent_message_key = unicode_property('parent_message_key')
    steps = typed_property('steps', FLOW_STEP_TO, True)


INCIDENT_PARAMS_MAPPING = {
    IncidentSource.FLOW: IncidentParamsFlow,
}


class IncidentParams(object_factory):
    t = long_property('t')

    def __init__(self):
        super(IncidentParams, self).__init__('t', INCIDENT_PARAMS_MAPPING)


class IdName(TO):
    id = unicode_property('id')
    name = unicode_property('name')


class IntegrationParamsTopdesk(TO):
    t = unicode_property('t', default=IntegrationProvider.TOPDESK)
    status = typed_property('status', IdName)  # type: IdName
    last_message = unicode_property('last_message')  # last message sent by operator


INTEGRATION_PARAMS_MAPPING = {
    IntegrationProvider.TOPDESK: IntegrationParamsTopdesk,
}


class IntegrationParams(object_factory):
    t = unicode_property('t')

    def __init__(self):
        super(IntegrationParams, self).__init__('t', INTEGRATION_PARAMS_MAPPING)


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


class IncidentSource(Enum):
    APP = 'app'


class IncidentDetails(NdbModel):
    status = ndb.StringProperty(indexed=False, choices=IncidentStatus.all())
    title = ndb.StringProperty(indexed=False)
    description = ndb.TextProperty(indexed=False)
    geo_location = ndb.GeoPtProperty(indexed=False)


class Incident(NdbModel):
    NAMESPACE = NAMESPACE

    sik = ndb.StringProperty()
    user_id = ndb.StringProperty()
    report_date = ndb.DateTimeProperty()
    resolve_time = ndb.DateTimeProperty()

    visible = ndb.BooleanProperty(default=False)
    cleanup_date = ndb.DateTimeProperty()

    integration = ndb.StringProperty(indexed=False)
    source = ndb.StringProperty(choices=IncidentSource.all())
    params = TOProperty(IncidentParams())  # type: IncidentParams
    integration_params = TOProperty(IntegrationParams())  # type: IntegrationParams
    external_id = ndb.StringProperty()
    details = ndb.LocalStructuredProperty(IncidentDetails)  # type: IncidentDetails

    @property
    def incident_id(self):
        return self.key.id()

    @classmethod
    def create_key(cls, incident_id):
        return ndb.Key(cls, incident_id, namespace=cls.NAMESPACE)

    @classmethod
    def get_by_external_id(cls, sik, external_id):
        return cls.query() \
            .filter(cls.sik == sik) \
            .filter(cls.external_id == external_id) \
            .get()

    @classmethod
    def list_by_cleanup_date(cls, date):
        return cls.query() \
            .filter(cls.cleanup_date != None) \
            .filter(cls.cleanup_date < date) \
            .order(cls.cleanup_date, cls.key)


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
