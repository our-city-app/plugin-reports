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
from mcfw.properties import typed_property, unicode_property, long_property

from framework.to import TO
from plugins.reports.models import INTEGRATION_SETTINGS_DATA, IntegrationSettings
from plugins.rogerthat_api.models.settings import RogerthatSettings


class IntegrationTO(TO):
    id = long_property('id')
    name = unicode_property('name')
    sik = unicode_property('sik')
    consumer_id = unicode_property('consumer_id')
    rogerthat_api_key = unicode_property('rogerthat_api_key')
    data = typed_property('data', INTEGRATION_SETTINGS_DATA)

    @classmethod
    def from_model(cls, model, rogerthat_settings):
        # type: (IntegrationSettings, RogerthatSettings) -> IntegrationTO
        return cls(
            id=model.id,
            name=model.name,
            sik=model.sik,
            rogerthat_api_key=rogerthat_settings and rogerthat_settings.api_key,
            consumer_id=model.consumer_id,
            data=model.data,
        )
