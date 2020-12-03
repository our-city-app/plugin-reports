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
from __future__ import unicode_literals

from framework.to import TO
from mcfw.properties import unicode_property, typed_property, object_factory, long_property
from plugins.reports.integrations.int_topdesk.consts import TopdeskPropertyName
from plugins.reports.to import FormComponentType
from plugins.rogerthat_api.plugin_utils import Enum
from typing import List


class BaseComponent(TO):
    id = unicode_property('id')


class TOPDeskCategoryMapping(BaseComponent):
    type = unicode_property('type', default=TopdeskPropertyName.CATEGORY)
    categories = typed_property('categories', dict)  # mapping from component id -> topdesk category


class TOPDeskSubCategoryMapping(BaseComponent):
    type = unicode_property('type', default=TopdeskPropertyName.SUB_CATEGORY)
    subcategories = typed_property('subcategories', dict)  # mapping from component id -> topdesk subcategory


class TOPDeskBriefDescriptionMapping(BaseComponent):
    type = unicode_property('type', default=TopdeskPropertyName.SUB_CATEGORY)
    # No special options for now


class OptionalFieldLocationFormat(Enum):
    LATITUDE = 0  # only latitude
    LONGITUDE = 1  # only longitude
    LATITUDE_LONGITUDE = 2  # comma separated


class OptionalFieldLocationOptions(TO):
    type = unicode_property('type', default=FormComponentType.LOCATION)
    format = long_property('format')  # see OptionalFieldLocationFormat


# class OptionalFieldTextOptions(TO):
#     type = unicode_property('type', default=FormComponentType.TEXT_INPUT)
#
#
# class OptionalFieldSingleSelectOptions(TO):
#     type = unicode_property('type', default=FormComponentType.SINGLE_SELECT)
#
#
# class OptionalFieldDateTimeOptions(TO):
#     type = unicode_property('type', default=FormComponentType.DATETIME)


OPTIONAL_FIELDS_OPTIONS = {
    FormComponentType.LOCATION: OptionalFieldLocationOptions,
    # implemented/uncomment when needed
    # FormComponentType.TEXT_INPUT: OptionalFieldTextOptions,
    # FormComponentType.SINGLE_SELECT: OptionalFieldSingleSelectOptions,
    # FormComponentType.DATETIME: OptionalFieldDateTimeOptions,
}


class OptionalFieldsOptions(object_factory):

    def __init__(self):
        super(OptionalFieldsOptions, self).__init__('type', OPTIONAL_FIELDS_OPTIONS)


class OptionalFieldsMapping(BaseComponent):
    field = unicode_property('field')  # text1, number2, date5 etc
    # Options depend on the component type of the field.
    options = typed_property('options', OptionalFieldsOptions())


class TOPDeskOptionalFields1Mapping(OptionalFieldsMapping):
    type = unicode_property('type', default=TopdeskPropertyName.OPTIONAL_FIELDS_1)


class TOPDeskOptionalFields2Mapping(OptionalFieldsMapping):
    type = unicode_property('type', default=TopdeskPropertyName.OPTIONAL_FIELDS_1)


COMP_MAPPING = {
    TopdeskPropertyName.CATEGORY: TOPDeskCategoryMapping,
    TopdeskPropertyName.SUB_CATEGORY: TOPDeskSubCategoryMapping,
    TopdeskPropertyName.BRIEF_DESCRIPTION: TOPDeskBriefDescriptionMapping,
    TopdeskPropertyName.OPTIONAL_FIELDS_1: TOPDeskOptionalFields1Mapping,
    TopdeskPropertyName.OPTIONAL_FIELDS_2: TOPDeskOptionalFields2Mapping,
}


class TOPDeskComponentMapping(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(TOPDeskComponentMapping, self).__init__('type', COMP_MAPPING)


class TOPDeskSectionMapping(TO):
    id = unicode_property('id')
    components = typed_property('component', TOPDeskComponentMapping(), True)  # type: List[TOPDeskComponentMapping]


class TOPDeskFormConfiguration(TO):
    provider = unicode_property('provider', default='topdesk')
    mapping = typed_property('mapping', TOPDeskSectionMapping, True)  # type: List[TOPDeskSectionMapping]
