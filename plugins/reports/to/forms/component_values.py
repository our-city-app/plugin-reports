# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley Belgium NV
# NOTICE: THIS FILE HAS BEEN MODIFIED BY GREEN VALLEY BELGIUM NV IN ACCORDANCE WITH THE APACHE LICENSE VERSION 2.0
# Copyright 2018 GIG Technology NV
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
# @@license_version:1.6@@

from datetime import datetime

from mcfw.properties import unicode_property, float_property, long_property, unicode_list_property, typed_property

from framework.to import TO
from .enums import FormComponentType


class BaseComponentValue(object):
    def get_string_value(self):
        raise NotImplementedError()


class FieldComponentValueTO(TO):
    type = unicode_property('type')
    id = unicode_property('id')


class TextInputComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    value = unicode_property('value')

    def get_string_value(self):
        return self.value


class SingleSelectComponentValueTO(TextInputComponentValueTO, BaseComponentValue):
    pass


class MultiSelectComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    values = unicode_list_property('values')

    def get_string_value(self):
        return ', '.join(self.values)


class DatetimeValueTO(TO):
    day = long_property('day')
    month = long_property('month')
    year = long_property('year')
    hour = long_property('hour')
    minute = long_property('minute')


class DatetimeComponentValueTO(FieldComponentValueTO, DatetimeValueTO, BaseComponentValue):

    def get_date(self):
        return datetime(self.year, self.month, self.day, self.hour, self.minute)

    def get_string_value(self, fmt='%d/%m/%Y %H:%M'):
        return self.get_date().strftime(fmt)


class FileComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    value = unicode_property('value')
    name = unicode_property('name')
    file_type = unicode_property('file_type')

    def to_statistics(self):
        return [self.value, self.name, self.file_type]

    def get_string_value(self):
        return self.value

    @classmethod
    def from_statistics(cls, stats):
        return cls(value=stats[0], name=stats[1], file_type=stats[2])


# https://schema.org/PostalAddress + address_lines
class PostalAddressTO(TO):
    country = unicode_property('country', default=None)
    locality = unicode_property('locality', default=None)
    region = unicode_property('region', default=None)
    post_office_box_number = unicode_property('post_office_box_number', default=None)
    postal_code = unicode_property('postal_code', default=None)
    street_address = unicode_property('street_address', default=None)
    address_lines = unicode_list_property('address_lines', default=[])


class LocationComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    latitude = float_property('latitude')
    longitude = float_property('longitude')
    address = typed_property('address', PostalAddressTO, default=None)  # type: PostalAddressTO

    def get_string_value(self):
        return ', '.join(self.address.address_lines) if self.address else '%s,%s' % (self.latitude, self.longitude)

    def to_statistics(self):
        return [self.latitude, self.longitude]

    @classmethod
    def from_statistics(cls, stats):
        return cls(latitude=stats[0], longitude=stats[1])


FORM_COMPONENT_VALUES = {
    FormComponentType.TEXT_INPUT: TextInputComponentValueTO,
    FormComponentType.SINGLE_SELECT: SingleSelectComponentValueTO,
    FormComponentType.MULTI_SELECT: MultiSelectComponentValueTO,
    FormComponentType.DATETIME: DatetimeComponentValueTO,
    FormComponentType.LOCATION: LocationComponentValueTO,
    FormComponentType.FILE: FileComponentValueTO,
}
