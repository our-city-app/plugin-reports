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

from framework.models.common import NdbModel
from plugins.reports.consts import NAMESPACE


class ElasticsearchSettings(NdbModel):
    NAMESPACE = NAMESPACE

    base_url = ndb.StringProperty(indexed=False)

    auth_username = ndb.StringProperty(indexed=False)
    auth_password = ndb.StringProperty(indexed=False)

    @classmethod
    def create_key(cls):
        return ndb.Key(cls, u'ElasticsearchSettings', namespace=cls.NAMESPACE)


class IntegrationSettings(NdbModel):
    NAMESPACE = NAMESPACE

    INT_NONE = u'none'
    INT_TOPDESK = u'topdesk'
    INT_3P = u'3p'

    integration = ndb.StringProperty(indexed=False)
    params = ndb.JsonProperty(indexed=False)

# mutual
#     rogerthat_branding_key = ndb.StringProperty(indexed=False)

# topdesk
#     topdesk_api_url = ndb.StringProperty(indexed=False)
#     topdesk_username = ndb.StringProperty(indexed=False)
#     topdesk_password = ndb.StringProperty(indexed=False)
#     topdesk_api_user = ndb.StringProperty(indexed=False)
#     topdesk_call_type = ndb.StringProperty(indexed=False)
#     topdesk_category = ndb.StringProperty(indexed=False)
#     topdesk_sub_category = ndb.StringProperty(indexed=False)

# 3p
#     gcs_bucket_name = ndb.StringProperty(indexed=False)

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

    @property
    def user_id(self):
        return self.key.id().decode('utf8')

    @classmethod
    def create_user_id(cls, email, app_id):
        return '%s:%s' % (email, app_id)

    @classmethod
    def create_key(cls, user_id):
        return ndb.Key(cls, user_id, namespace=cls.NAMESPACE)


class IncidentDetails(NdbModel):
    status = ndb.StringProperty(indexed=False)
    title = ndb.StringProperty(indexed=False)
    description = ndb.TextProperty(indexed=False)
    geo_location = ndb.GeoPtProperty(indexed=False)


class Incident(NdbModel):
    NAMESPACE = NAMESPACE

    STATUS_TODO = u'todo'

    sik = ndb.StringProperty(indexed=True)
    user_id = ndb.StringProperty(indexed=True)
    report_time = ndb.DateTimeProperty(indexed=True)
    resolve_time = ndb.DateTimeProperty(indexed=True)

    visible = ndb.BooleanProperty(indexed=True)
    cleanup_time = ndb.DateTimeProperty(indexed=True)
    search_keys = ndb.StringProperty(indexed=False, repeated=True)

    integration = ndb.StringProperty(indexed=False)
    params = ndb.JsonProperty(indexed=False)

    details = ndb.LocalStructuredProperty(IncidentDetails)

# topdesk
# incident_number = ndb.StringProperty(indexed=True)
# parent_message_key = ndb.StringProperty(indexed=True)
# status = ndb.StringProperty(indexed=True)

    @property
    def incident_id(self):
        return self.key.id().decode('utf8')

    @classmethod
    def create_key(cls, incident_id=None):
        if incident_id is None:
            incident_id = cls.allocate_ids(1)[0]
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
