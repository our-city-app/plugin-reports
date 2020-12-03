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
from mcfw.properties import long_property, unicode_property, typed_property, object_factory, bool_property

from framework.to import TO
from typing import List
from .component_values import FORM_COMPONENT_VALUES
from .components import FormComponentTO, NextActionTO


class FormSectionBrandingTO(TO):
    logo_url = unicode_property('logo_url')
    avatar_url = unicode_property('avatar_url')


class FormSectionTO(TO):
    id = unicode_property('id', default=None)
    title = unicode_property('title')
    description = unicode_property('description', default=None)
    components = typed_property('components', FormComponentTO(), True)  # type: list[FormComponentTO]
    next_action = typed_property('next_action', NextActionTO(), default=None)
    branding = typed_property('branding', FormSectionBrandingTO, False, default=None)  # type: FormSectionBrandingTO
    next_button_caption = unicode_property('next_button_caption', default=None)


class DynamicFormTO(TO):
    id = long_property('id')
    title = unicode_property('title')
    sections = typed_property('sections', FormSectionTO, True)  # type: list[FormSectionTO]
    submission_section = typed_property('submission_section', FormSectionTO, default=None)  # type: FormSectionTO
    max_submissions = long_property('max_submissions', default=-1)
    version = long_property('version')


class FormComponentValueTO(object_factory):
    type = unicode_property('type')
    id = unicode_property('id')

    def __init__(self):
        super(FormComponentValueTO, self).__init__('type', FORM_COMPONENT_VALUES)

    def get_string_value(self):
        raise NotImplementedError()


class FormSectionValueTO(TO):
    id = unicode_property('id')
    components = typed_property('components', FormComponentValueTO(), True)  # type: List[FormComponentValueTO]


class DynamicFormValueTO(TO):
    id = long_property('id')
    version = long_property('version')
    sections = typed_property('sections', FormSectionValueTO, True)  # type: List[FormSectionValueTO]


class FormSubmittedCallbackResultTO(TO):
    valid = bool_property('valid', default=True)
    error = unicode_property('error', default=None)
