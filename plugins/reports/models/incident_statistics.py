# -*- coding: utf-8 -*-
# Copyright 2020 Green Valley NV
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


class IncidentStatistics(NdbModel):
    NAMESPACE = NAMESPACE
    data = ndb.JsonProperty()
    integration_id = ndb.IntegerProperty()

    @property
    def year(self):
        return int(self.key.id().split('-')[1])

    @property
    def month(self):
        return int(self.key.id().split('-')[2])

    @classmethod
    def create_key(cls, integration_id, year, month=None):
        if month:
            key_name = '%s-%s-%s' % (integration_id, year, month)
        else:
            key_name = '%s-%s' % (integration_id, year)
        return ndb.Key(cls, key_name, namespace=NAMESPACE)

    @classmethod
    def list_by_integration(cls, integration_id):
        return cls.query().filter(cls.integration_id == integration_id)


class NameValue(NdbModel):
    id = ndb.TextProperty()
    name = ndb.TextProperty()


class IncidentTagMapping(NdbModel):
    NAMESPACE = NAMESPACE
    categories = ndb.StructuredProperty(NameValue, indexed=False, repeated=True)
    subcategories = ndb.StructuredProperty(NameValue, indexed=False, repeated=True)

    @classmethod
    def create_key(cls, integration_id):
        return ndb.Key(cls, integration_id, namespace=NAMESPACE)
