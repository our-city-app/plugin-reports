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
import logging
from pprint import pformat

from google.appengine.api import urlfetch
from google.appengine.ext import ndb, deferred

from framework.bizz.job import run_job
from framework.models.common import NdbModel
from plugins.reports.bizz.elasticsearch import index_docs
from plugins.reports.consts import NAMESPACE
from plugins.reports.integrations.int_topdesk.consts import PropertyName, \
    FieldMappingType
from plugins.reports.integrations.int_topdesk.topdesk import topdesk_api_call
from plugins.reports.models import IntegrationSettings

TEXT_OPTIONS = ['text1', 'text2', 'text3', 'text4', 'text5']


class FieldMapping(NdbModel):
    # id of form step
    step_id = ndb.StringProperty()
    # property name on topdesk
    property = ndb.StringProperty(choices=PropertyName.all(), required=True)
    # in case of optional fields, there need to be one or more value fields.
    value_properties = ndb.StringProperty(choices=TEXT_OPTIONS, repeated=True)
    type = ndb.IntegerProperty(choices=FieldMappingType.all(), required=True)
    # In case type == FieldMappingType.FIXED_VALUE, 'step_id' is ignored and this is always used
    default_value = ndb.StringProperty()


class FakeTopdeskIncident(NdbModel):
    NAMESPACE = NAMESPACE

    description = ndb.TextProperty(indexed=False)
    status = ndb.StringProperty(indexed=False)
    geo_location = ndb.GeoPtProperty(indexed=False)
    
    @property
    def uid(self):
        return self.incident_id

    @property
    def incident_id(self):
        return self.key.id().decode('utf8')
    
    @classmethod
    def create_key(cls, incident_id):
        return ndb.Key(cls, incident_id, namespace=cls.NAMESPACE)


def re_index_all():
    run_job(re_index_query, [], re_index_worker, [])


def re_index_worker(fti_key):
    incident = fti_key.get()
    docs = []

    doc = {
        "location": {
            "lat": incident.geo_location.lat,
            "lon":incident.geo_location.lon
        }
    }

    docs.append({'uid': incident.incident_id, 'data': doc})

    index_docs(docs)


def re_index_query():
    return FakeTopdeskIncident.query()


def test(start=0, page_size=1000):

    sik = u'fake_sik'
    settings = IntegrationSettings(key=IntegrationSettings.create_key(sik))
    settings.integration = IntegrationSettings.INT_TOPDESK
    settings.params = {}

    response = topdesk_api_call(settings, '/api/incidents?start=%s&page_size=%s' % (start, page_size), urlfetch.GET)
    to_put = []
    for item in response:
        d = get_values(item)
        if not d:
            continue
        if  not d['steps']['message_location_gps']:
            continue
        
        i = FakeTopdeskIncident(key=FakeTopdeskIncident.create_key(d['id']))
        i.description = d['briefDescription']
        i.status = d['processingStatus']['name']
        gps_coords = d['steps']['message_location_gps'].split(",")
        i.geo_location = ndb.GeoPt(float(gps_coords[0]), float(gps_coords[1]))

#         logging.debug(pformat(d))

        to_put.append(i)

    logging.info(u'len(to_put): %s' % len(to_put))
    if to_put:
        ndb.put_multi(to_put)

    deferred.defer(test, start + page_size)


def get_field_mapping():
    field_mapping = [FieldMapping(
        step_id='message_category',
        property=PropertyName.CATEGORY,
        type=FieldMappingType.TEXT
    ), FieldMapping(
        step_id='message_location_gps',
        property=PropertyName.OPTIONAL_FIELDS_1,
        value_properties=['text1'],
        type=FieldMappingType.GPS_SINGLE_FIELD
#     ), FieldMapping(
#         step_id='message_location_gps',
#         property=PropertyName.OPTIONAL_FIELDS_1,
#         value_properties=['text2'],
#         type=FieldMappingType.GPS_URL
    ), FieldMapping(
        step_id='message_location_street',
        property=PropertyName.OPTIONAL_FIELDS_1,
        value_properties=['text3'],
        type=FieldMappingType.TEXT
    ), FieldMapping(
        step_id='message_location_number',
        property=PropertyName.OPTIONAL_FIELDS_1,
        value_properties=['text4'],
        type=FieldMappingType.TEXT
#     ), FieldMapping(
#         property=PropertyName.OPTIONAL_FIELDS_1,
#         value_properties=['text5'],
#         type=FieldMappingType.FIXED_VALUE,
#         default_value='2845 Niel'
    ), FieldMapping(
        step_id='message_omschrijving',
        property=PropertyName.BRIEF_DESCRIPTION,
        type=FieldMappingType.TEXT
#     ), FieldMapping(
#         step_id='message_omschrijving',
#         property=PropertyName.REQUEST,
#         type=FieldMappingType.TEXT
#     ), FieldMapping(
#         step_id='message_name',
#         property=PropertyName.REQUEST,
#         type=FieldMappingType.TEXT
#     ), FieldMapping(
#         step_id='message_phone',
#         property=PropertyName.REQUEST,
#         type=FieldMappingType.TEXT
    )]
    
    return field_mapping


def get_values(item):
#     if item['entryType']['name'] != u'Niel App':
#         logging.debug(item['entryType'])
#         return
#     logging.info(pformat(item))
    
    field_mapping = get_field_mapping()
    d = {'steps': {},
         'id': item['id'],
        'entryType': item['entryType'],
         'processingStatus': item['processingStatus'],
         'category': item['category'],
         'subcategory': item['subcategory'],
#         'attachments': item['attachments'],
        'briefDescription': item['briefDescription'],
    }
    for mapping in field_mapping:
        if not mapping.step_id:
            continue
        if mapping.property == PropertyName.REQUEST:
            continue
        v = d['steps'].get(mapping.step_id)
        if v:
            continue
        if mapping.value_properties:
            d['steps'][mapping.step_id] = item[mapping.property][mapping.value_properties[0]]
        else:
            d['steps'][mapping.step_id] = item[mapping.property]
    return d

