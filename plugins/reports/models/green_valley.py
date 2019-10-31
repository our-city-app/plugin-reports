# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley NV
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
from mcfw.properties import unicode_property, object_factory, typed_property


class GvFieldType(object):
    FLEX = 'flex'
    CONST = 'const'
    PERSON = 'person'
    LOCATION = 'location'
    FIELD = 'field'
    ATTACHMENT = 'attachment'


class GvMappingFlex(TO):
    type = unicode_property('type', default=GvFieldType.FLEX)
    id = unicode_property('id')
    field_def_id = unicode_property('field_def_id')


class GvMappingField(TO):
    # maps to a direct property of a case
    type = unicode_property('type', default=GvFieldType.FIELD)
    id = unicode_property('id')
    # One of the following 2 properties needs to be set
    field = unicode_property('field', default=None)
    value = unicode_property('value', default=None)


class GvMappingPerson(TO):
    type = unicode_property('type', default=GvFieldType.PERSON)
    id = unicode_property('id')
    field = unicode_property('field')
    sub_field = unicode_property('sub_field', default=None)


class GvMappingConst(TO):
    # A flex field of which its value is always the same
    type = unicode_property('type', default=GvFieldType.CONST)
    field = unicode_property('field')
    value = unicode_property('value')
    display_value = unicode_property('display_value', default=None)


class GvMappingLocation(TO):
    # Maps a location field to multiple flex fields
    type = unicode_property('type', default=GvFieldType.LOCATION)
    id = unicode_property('id')
    coordinates = unicode_property('coordinates', default=None)
    address = unicode_property('address', default=None)


class GvMappingAttachment(GvMappingFlex):
    # Maps a file upload component to a flex with an attachment_value
    type = unicode_property('type', default=GvFieldType.ATTACHMENT)
    name = unicode_property('name')


GV_MAPPING = {
    GvFieldType.FLEX: GvMappingFlex,
    GvFieldType.CONST: GvMappingConst,
    GvFieldType.PERSON: GvMappingPerson,
    GvFieldType.LOCATION: GvMappingLocation,
    GvFieldType.FIELD: GvMappingField,
    GvFieldType.ATTACHMENT: GvMappingAttachment,
}


class GvComponentMapping(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(GvComponentMapping, self).__init__('type', GV_MAPPING)


class GreenValleySectionMapping(TO):
    id = unicode_property('id')
    components = typed_property('component', GvComponentMapping(), True)  # type: list[GvComponentMapping]


class GreenValleyFormConfiguration(TO):
    provider = unicode_property('provider', default='green_valley')
    type_id = unicode_property('type_id', default=None)
    mapping = typed_property('mapping', GreenValleySectionMapping, True)  # type: list[GreenValleySectionMapping]
