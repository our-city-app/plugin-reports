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


class FormComponentType(object):
    PARAGRAPH = 'paragraph'
    TEXT_INPUT = 'text_input'
    SINGLE_SELECT = 'single_select'
    MULTI_SELECT = 'multi_select'
    DATETIME = 'datetime'
    FILE = 'file'
    LOCATION = 'location'


class LocationMode(object):
    GPS = 'gps'
    TEXT = 'text'


class DateFormat(object):
    DATE = 'date'
    DATETIME = 'datetime'
    TIME = 'time'


class KeyboardType(object):
    DEFAULT = 'DEFAULT'
    AUTO_CAPITALIZED = 'AUTO_CAPITALIZED'
    EMAIL = 'EMAIL'
    URL = 'URL'
    PHONE = 'PHONE'
    NUMBER = 'NUMBER'
    DECIMAL = 'DECIMAL'
    PASSWORD = 'PASSWORD'
    NUMBER_PASSWORD = 'NUMBER_PASSWORD'
