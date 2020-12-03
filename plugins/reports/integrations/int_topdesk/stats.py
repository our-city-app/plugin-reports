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
from plugins.reports.integrations.int_topdesk.consts import TopdeskPropertyName
from plugins.reports.integrations.int_topdesk.topdesk import get_topdesk_values
from plugins.reports.models import IntegrationSettings
from plugins.reports.models.incident_statistics import IncidentTagMapping, NameValue


def refresh_topdesk_tags(integration_key):
    integration = integration_key.get()  # type: IntegrationSettings
    settings = integration.data
    categories = get_topdesk_values(settings, TopdeskPropertyName.CATEGORY, {})
    subcategories = get_topdesk_values(settings, TopdeskPropertyName.SUB_CATEGORY, {})
    mapping = IncidentTagMapping(key=IncidentTagMapping.create_key(integration.id))
    mapping.categories = [NameValue(id=c['id'], name=c['name']) for c in categories]
    mapping.subcategories = [NameValue(id=c['id'], name=c['name']) for c in subcategories]
    mapping.put()
