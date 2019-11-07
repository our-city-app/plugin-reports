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
from mcfw.properties import object_factory, long_property, unicode_property

from framework.to import TO
from .component_values import DatetimeValueTO


class FormValidatorType(object):
    REQUIRED = 'required'
    MIN = 'min'
    MAX = 'max'
    MINDATE = 'mindate'
    MAXDATE = 'maxdate'
    MINLENGTH = 'minlength'
    MAXLENGTH = 'maxlength'
    REGEX = 'regex'


class _Validator(TO):
    type = unicode_property('type')
    error_message = unicode_property('error_message', default=None)


class RequiredValidatorTO(_Validator):
    pass


class MinValidatorTO(_Validator):
    value = long_property('value')


class MaxValidatorTO(_Validator):
    value = long_property('value')


class DateValidatorTO(_Validator, DatetimeValueTO):
    pass


class MinDateValidatorTO(DateValidatorTO):
    pass


class MaxDateValidatorTO(DateValidatorTO):
    pass


class MinLengthValidatorTO(_Validator):
    value = long_property('value')


class MaxLengthValidatorTO(_Validator):
    value = long_property('value')


class RegexValidatorTO(_Validator):
    value = unicode_property('value')


FORM_VALIDATORS = {
    FormValidatorType.REQUIRED: RequiredValidatorTO,
    FormValidatorType.MIN: MinValidatorTO,
    FormValidatorType.MAX: MaxValidatorTO,
    FormValidatorType.MINDATE: MinDateValidatorTO,
    FormValidatorType.MAXDATE: MaxDateValidatorTO,
    FormValidatorType.MINLENGTH: MinLengthValidatorTO,
    FormValidatorType.MAXLENGTH: MaxLengthValidatorTO,
    FormValidatorType.REGEX: RegexValidatorTO,
}


class FormValidatorTO(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(FormValidatorTO, self).__init__('type', FORM_VALIDATORS)
