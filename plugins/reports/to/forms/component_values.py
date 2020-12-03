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
import urllib
from datetime import datetime, time

from framework.to import TO
from mcfw.properties import unicode_property, float_property, long_property, unicode_list_property, typed_property
from .components import FieldComponentTO, TextInputComponentTO, SingleSelectComponentTO, MultiSelectComponentTO, \
    DatetimeComponentTO, \
    FileComponentTO, LocationComponentTO
from .enums import FormComponentType, DateFormat


class BaseComponentValue(object):
    def get_string_value(self, component):
        # type: (FieldComponentTO) -> str
        raise NotImplementedError()


class FieldComponentValueTO(TO):
    type = unicode_property('type')
    id = unicode_property('id')


class TextInputComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    value = unicode_property('value')

    def get_string_value(self, component):
        # type: (TextInputComponentTO) -> str
        return self.value or ''


class SingleSelectComponentValueTO(TextInputComponentValueTO, BaseComponentValue):
    def get_string_value(self, component):
        # type: (SingleSelectComponentTO) -> str
        choices_map = {choice.value: choice.label for choice in component.choices}
        return choices_map.get(self.value, self.value)


class MultiSelectComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    values = unicode_list_property('values')

    def get_string_value(self, component):
        # type: (MultiSelectComponentTO) -> str
        choices_map = {choice.value: choice.label for choice in component.choices}
        return ', '.join([choices_map.get(val, val) for val in self.values])


class DatetimeValueTO(TO):
    day = long_property('day')
    month = long_property('month')
    year = long_property('year')
    hour = long_property('hour')
    minute = long_property('minute')


class DatetimeComponentValueTO(FieldComponentValueTO, DatetimeValueTO, BaseComponentValue):

    def get_string_value(self, component):
        # type: (DatetimeComponentTO) -> str
        if component.format == DateFormat.DATE:
            fmt = '%d/%m/%Y'
            date = datetime(self.year, self.month, self.day)
        elif component.format == DateFormat.TIME:
            fmt = '%H:%M'
            date = time(self.hour, self.minute)
        else:
            fmt = '%d/%m/%Y %H:%M'
            date = datetime(self.year, self.month, self.day, self.hour, self.minute)
        return date.strftime(fmt)


class FileComponentValueTO(FieldComponentValueTO, BaseComponentValue):
    value = unicode_property('value')
    name = unicode_property('name')
    file_type = unicode_property('file_type')

    def to_statistics(self):
        return [self.value, self.name, self.file_type]

    def get_string_value(self, component):
        # type: (FileComponentTO) -> str
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

    def get_string_value(self, component):
        # type: (LocationComponentTO) -> str
        latlon = '%s,%s' % (self.latitude, self.longitude)
        if self.address:
            return ', '.join(self.address.address_lines) + ' | %s' % latlon
        return latlon

    def to_statistics(self):
        return [self.latitude, self.longitude]

    def get_maps_url(self):
        query = '%s,%s' % (self.latitude, self.longitude)
        params = {
            'api': 1,
            'query': query,
        }
        return 'https://www.google.com/maps/search/?' + urllib.urlencode(params, doseq=True)

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
