# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley Belgium NV
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

from plugins.rogerthat_api.to import PaginatedResultTO, UserDetailsTO
from typing import List
from .forms import *


class GVProxy(TO):
    id = unicode_property('id')
    url = unicode_property('url')
    secret = unicode_property('secret')


class ReportsPluginConfiguration(TO):
    google_maps_key = unicode_property('google_maps_key')
    oca_server_secret = unicode_property('oca_server_secret')
    gv_proxies = typed_property('gv_proxies', GVProxy, True)  # type: List[GVProxy]


class GeoPointTO(TO):
    lat = float_property('1')
    lon = float_property('2')


class MapGeometryType(object):
    LINE_STRING = 'LineString'
    MULTI_LINE_STRING = 'MultiLineString'
    POLYGON = 'Polygon'
    MULTI_POLYGON = 'MultiPolygon'


class CoordsListTO(TO):
    coords = typed_property('coords', GeoPointTO, True)


class PolygonTO(TO):
    rings = typed_property('rings', CoordsListTO, True)


class LineStringGeometryTO(TO):
    type = unicode_property('type', default=MapGeometryType.LINE_STRING)
    color = unicode_property('color')
    line = typed_property('line', CoordsListTO, False)


class MultiLineStringGeometryTO(TO):
    type = unicode_property('type', default=MapGeometryType.MULTI_LINE_STRING)
    color = unicode_property('color')
    lines = typed_property('lines', CoordsListTO, True)


class PolygonGeometryTO(PolygonTO):
    type = unicode_property('type', default=MapGeometryType.POLYGON)
    color = unicode_property('color')


class MultiPolygonGeometryTO(TO):
    type = unicode_property('type', default=MapGeometryType.MULTI_POLYGON)
    color = unicode_property('color')
    polygons = typed_property('polygons', PolygonTO, True)


MAP_GEOMETRY_MAPPING = {
    MapGeometryType.LINE_STRING: LineStringGeometryTO,
    MapGeometryType.MULTI_LINE_STRING: MultiLineStringGeometryTO,
    MapGeometryType.POLYGON: PolygonGeometryTO,
    MapGeometryType.MULTI_POLYGON: MultiPolygonGeometryTO,
}


class MapGeometryTO(object_factory):
    type = unicode_property('type')
    color = unicode_property('color')

    def __init__(self):
        super(MapGeometryTO, self).__init__('type', MAP_GEOMETRY_MAPPING)


class MapSectionType(object):
    TEXT = 'text'
    GEOMETRY = 'geometry'
    VOTE = 'vote'


class TextSectionTO(TO):
    type = unicode_property('type', default=MapSectionType.TEXT)
    title = unicode_property('title')
    description = unicode_property('description')


class GeometrySectionTO(TO):
    type = unicode_property('type', default=MapSectionType.GEOMETRY)
    title = unicode_property('title')
    description = unicode_property('description')
    geometry = typed_property('geometry', MapGeometryTO(), True)


class MapVoteOptionTO(TO):
    id = unicode_property('id')
    icon = unicode_property('icon')
    title = unicode_property('title')
    count = long_property('count')
    color = unicode_property('color')
    selected = bool_property('selected')


class VoteSectionTO(TO):
    type = unicode_property('type', default=MapSectionType.VOTE)
    id = unicode_property('id')
    options = typed_property('options', MapVoteOptionTO, True)


MAP_SECTION_MAPPING = {
    MapSectionType.TEXT: TextSectionTO,
    MapSectionType.GEOMETRY: GeometrySectionTO,
    MapSectionType.VOTE: VoteSectionTO,
}


class MapSectionTO(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(MapSectionTO, self).__init__('type', MAP_SECTION_MAPPING)


class MapIconTO(TO):
    id = unicode_property('1')
    color = unicode_property('2')



class MapAnnouncementType(object):
    TEXT = 'text'


class TextAnnouncementTO(TO):
    type = unicode_property('type', default=MapAnnouncementType.TEXT)
    title = unicode_property('title')
    description = unicode_property('description')


MAP_ANNOUNCEMENT_MAPPING = {
    MapAnnouncementType.TEXT: TextAnnouncementTO,
}


class MapAnnouncementTO(object_factory):
    type = unicode_property('type')

    def __init__(self):
        super(MapAnnouncementTO, self).__init__('type', MAP_ANNOUNCEMENT_MAPPING)


class MapItemTO(TO):
    id = unicode_property('1')
    coords = typed_property('2', GeoPointTO, False)
    icon = typed_property('3', MapIconTO, False)
    title = unicode_property('4')
    description = unicode_property('5')


class MapItemDetailsTO(TO):
    id = unicode_property('id')
    geometry = typed_property('geometry', MapGeometryTO(), True)
    sections = typed_property('sections', MapSectionTO(), True)


class GetMapItemsResponseTO(TO):
    cursor = unicode_property('1', default=None)
    items = typed_property('2', MapItemTO, True, default=[])
    distance = long_property('3', default=0)
    top_sections = typed_property('top_sections', MapSectionTO(), True, default=[])


class GetMapItemDetailsResponseTO(TO):
    items = typed_property('1', MapItemDetailsTO, True, default=[])


class SaveMapItemVoteResponseTO(TO):
    item_id = unicode_property('item_id')
    vote_id = unicode_property('vote_id')
    options = typed_property('options', MapVoteOptionTO, True)


class ItemVoteTO(TO):
    user_id = unicode_property('user_id', default=None)
    vote_id = unicode_property('vote_id', default=None)
    option_id = unicode_property('option_id', default=None)


class LatLonTO(TO):
    lat = float_property('lat')
    lon = float_property('lon')


class IncidentDetailsTO(TO):
    title = unicode_property('title')
    description = unicode_property('description')
    geo_location = typed_property('geo_location', LatLonTO)


class IncidentTO(TO):
    id = unicode_property('id')
    user_id = unicode_property('user_id')
    report_date = unicode_property('report_date')
    status_dates = typed_property('status_dates', dict, True)
    user_consent = bool_property('user_consent')
    visible = bool_property('visible')
    integration = unicode_property('integration')
    source = unicode_property('source')
    # params = typed_property('params', IncidentParams())
    # integration_params = typed_property('incident_params', IntegrationParams())
    external_id = unicode_property('external_id')
    status = unicode_property('status')
    details = typed_property('details', IncidentDetailsTO)  # type: IncidentDetailsTO


class IncidentListTO(PaginatedResultTO):
    results = typed_property('results', IncidentTO, True)


class FormSubmissionTO(TO):
    id = long_property('id')
    sections = typed_property('sections', FormSectionValueTO, True)  # type: List[FormSectionValueTO]
    submitted_date = unicode_property('submitted_date')
    version = long_property('version')
    external_reference = typed_property('external_reference', dict)


# See solutions.common.bizz.forms.integrations.green_valley
class FormSubmittedCallback(TO):
    form = typed_property('form', DynamicFormTO)  # type: DynamicFormTO
    submission = typed_property('submission', FormSubmissionTO)  # type: FormSubmissionTO
    user_details = typed_property('user_details', UserDetailsTO)  # type: UserDetailsTO
