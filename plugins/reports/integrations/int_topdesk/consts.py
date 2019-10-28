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

from plugins.rogerthat_api.plugin_utils import Enum


class TopdeskFieldMappingType(Enum):
    TEXT = 1
    GPS_SINGLE_FIELD = 2
    GPS_URL = 3
    FIXED_VALUE = 4
    REVERSE_MAPPING = 5
    PUBLIC_CONSENT = 6  # consent that incident can be made public


class TopdeskPropertyName(Enum):
    BRIEF_DESCRIPTION = 'briefDescription'
    REQUEST = 'request'
    CALL_TYPE = 'callType'
    CATEGORY = 'category'
    SUB_CATEGORY = 'subcategory'
    BRANCH = 'branch'
    ENTRY_TYPE = 'entryType'
    LOCATION = 'location'
    OPERATOR = 'operator'
    OPERATOR_GROUP = 'operatorGroup'
    OPTIONAL_FIELDS_1 = 'optionalFields1'
    OPTIONAL_FIELDS_2 = 'optionalFields2'


ENDPOINTS = {
    TopdeskPropertyName.ENTRY_TYPE: '/incidents/entry_types',
    TopdeskPropertyName.CALL_TYPE: '/incidents/call_types',
    TopdeskPropertyName.CATEGORY: '/incidents/categories',
    TopdeskPropertyName.SUB_CATEGORY: '/incidents/subcategories',
    TopdeskPropertyName.BRANCH: '/branches',
    TopdeskPropertyName.LOCATION: '/locations',
    TopdeskPropertyName.OPERATOR: '/operators',
    TopdeskPropertyName.OPERATOR_GROUP: '/operatorgroups',
}

TEXT_OPTIONS = ['text1', 'text2', 'text3', 'text4', 'text5']
