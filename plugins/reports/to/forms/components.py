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

from __future__ import unicode_literals

from framework.to import TO
from mcfw.properties import typed_property, unicode_property, unicode_list_property, object_factory, bool_property
from typing import List
from .enums import FormComponentType, DateFormat, KeyboardType
from .validators import FormValidatorTO, FormValidatorType


class ParagraphComponentTO(TO):
    type = unicode_property('type')
    title = unicode_property('title', default=None)
    description = unicode_property('description', default=None)


class FieldComponentTO(ParagraphComponentTO):
    id = unicode_property('id')
    sensitive = bool_property('sensitive', default=False)


class ValidatedComponentTO(TO):
    validators = typed_property('validators', FormValidatorTO(), True, default=[])  # type: List[FormValidatorTO]


class TextInputComponentTO(FieldComponentTO, ValidatedComponentTO):
    placeholder = unicode_property('placeholder', default=None)
    multiline = bool_property('multiline', default=False)
    keyboard_type = unicode_property('keyboard_type', default=KeyboardType.DEFAULT)


class NextActionType(object):
    NEXT = 'next'
    SECTION = 'section'
    SUBMIT = 'submit'
    URL = 'url'


# Default next action: go to next section
class NextActionDefaultTO(TO):
    type = unicode_property('type', default=NextActionType.NEXT)


# Go to specific section
class NextActionSectionTO(TO):
    type = unicode_property('type', default=NextActionType.SECTION)
    section = unicode_property('section')


# Submit form
class NextActionSubmitTO(TO):
    type = unicode_property('type', default=NextActionType.SUBMIT)


# Submit form & open URL
class NextActionURLTO(TO):
    type = unicode_property('type', default=NextActionType.URL)
    url = unicode_property('url')


NEXT_ACTION_MAPPING = {
    NextActionType.NEXT: NextActionDefaultTO,
    NextActionType.SECTION: NextActionSectionTO,
    NextActionType.SUBMIT: NextActionSubmitTO,
    NextActionType.URL: NextActionURLTO,
}


class NextActionTO(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(NextActionTO, self).__init__('type', NEXT_ACTION_MAPPING)


class ValueTO(TO):
    value = unicode_property('value')
    label = unicode_property('label', default=None)
    image_url = unicode_property('image_url', default=None)
    next_action = typed_property('next_action', NextActionTO(), default=None)


class SelectComponentTO(FieldComponentTO, ValidatedComponentTO):
    choices = typed_property('choices', ValueTO, True)  # type: List[ValueTO]


class SingleSelectComponentTO(SelectComponentTO):
    pass


class MultiSelectComponentTO(SelectComponentTO):
    pass


class DatetimeComponentTO(FieldComponentTO, ValidatedComponentTO):
    format = unicode_property('format', default=DateFormat.DATETIME)


class LocationComponentTO(FieldComponentTO, ValidatedComponentTO):
    pass


class FileComponentTO(FieldComponentTO, ValidatedComponentTO):
    file_types = unicode_list_property('file_types', default=[])


FORM_COMPONENTS = {
    FormComponentType.PARAGRAPH: ParagraphComponentTO,
    FormComponentType.TEXT_INPUT: TextInputComponentTO,
    FormComponentType.SINGLE_SELECT: SingleSelectComponentTO,
    FormComponentType.MULTI_SELECT: MultiSelectComponentTO,
    FormComponentType.DATETIME: DatetimeComponentTO,
    FormComponentType.LOCATION: LocationComponentTO,
    FormComponentType.FILE: FileComponentTO,
}

VALIDATOR_MAPPING = {
    FormComponentType.TEXT_INPUT: [FormValidatorType.REQUIRED, FormValidatorType.MIN, FormValidatorType.MAX,
                                   FormValidatorType.MINLENGTH, FormValidatorType.MAXLENGTH, FormValidatorType.REGEX],
    FormComponentType.SINGLE_SELECT: [FormValidatorType.REQUIRED],
    FormComponentType.MULTI_SELECT: [FormValidatorType.REQUIRED, FormValidatorType.MIN, FormValidatorType.MAX],
    FormComponentType.DATETIME: [FormValidatorType.REQUIRED, FormValidatorType.MINDATE, FormValidatorType.MAXDATE],
    FormComponentType.LOCATION: [FormValidatorType.REQUIRED],
    FormComponentType.FILE: [FormValidatorType.REQUIRED, FormValidatorType.MIN, FormValidatorType.MAX,
                             FormValidatorType.MINLENGTH, FormValidatorType.MAXLENGTH],
}


class FormComponentTO(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(FormComponentTO, self).__init__('type', FORM_COMPONENTS)
