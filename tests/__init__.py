import unittest

from mcfw.properties import object_factory
from mcfw.rpc import parse_complex_value
from plugins.reports.bizz.gcs import upload_to_gcs
from plugins.reports.bizz.int_3p import create_incident_xml
from plugins.reports.models import RogerthatUser
from plugins.rogerthat_api.to.messaging.flow import FLOW_STEP_MAPPING


class Test(unittest.TestCase):

    def setup(self):
        # https://cloud.google.com/appengine/docs/standard/python/tools/localunittesting
        from google.appengine.datastore import datastore_stub_util
        from google.appengine.ext import testbed

        self.testbed = testbed.Testbed()
        self.testbed.activate()

        self.testbed.init_app_identity_stub()
        self.testbed.init_blobstore_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_files_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_urlfetch_stub()

    def setup_rt_user(self):
        email = u'john.doe@example.com'
        app_id = u'rogerthat'
        rt_user = RogerthatUser(key=RogerthatUser.create_key(RogerthatUser.create_user_id(email, app_id)))
        rt_user.email = email
        rt_user.name = u'John Doe'
        rt_user.avatar_url = u'avatar_url'
        rt_user.language = u'language'
        rt_user.app_id = app_id
        rt_user.put()
        return rt_user

    def test_create_incident_xml(self):
        self.setup()
        rt_user = self.setup_rt_user()
        gcs_bucket_name = 'test'

        incident_id = 1
        timestamp = 1524557027
        steps_dict = [{u'received_timestamp': 1,
                       u'message_flow_id': u'id1',
                       u'button': u'Meldpunt Gemeente',
                       u'step_type': u'message_step',
                       u'step_id': u'message_keuze',
                       u'message': u'Maak hier jouw meldingskeuze',
                       u'answer_id': u'button_meldpunt gemeente',
                       u'acknowledged_timestamp': 2},
                       {u'received_timestamp': 3,
                        u'message_flow_id': u'id2',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'Korte bescrijving',
                        u'form_type': u'text_line',
                        u'step_id': u'message_description',
                        u'message': u'Gebruik dit formulier om hinder op publiek domein te melden.\n\nGeef een korte beschrijving van het probleem. In de volgende stap kan u een uitgebreidere toelichting ingeven van het probleem.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'Korte bescrijving'}},
                        u'acknowledged_timestamp': 4},
                       {u'received_timestamp': 5,
                        u'message_flow_id': u'id3',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'Langere beschrijving',
                        u'form_type': u'text_block',
                        u'step_id': u'message_explanation',
                        u'message': u'Toelichting',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'Langere beschrijving'}},
                        u'acknowledged_timestamp': 6},
                       {u'received_timestamp': 7,
                        u'message_flow_id': u'id4',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'https://photo.url',
                        u'form_type': u'photo_upload',
                        u'step_id': u'message_photo',
                        u'message': u'Indien mogelijk, neem een foto van het probleem.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'https://photo.url'}},
                        u'acknowledged_timestamp': 8},
                       {u'received_timestamp': 9,
                        u'message_flow_id': u'id5',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'Straatnaam nr x',
                        u'form_type': u'text_block',
                        u'step_id': u'message_location-text',
                        u'message': u'Waar doet het probleem zich voor?\n\nVerduidelijk de plaats zo volledig mogelijk. Bvb. Stationsstraat ter hoogte van nr. 2.\n\nOf geef je huidige locatie door aan de hand van GPS.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'Straatnaam nr x'}},
                        u'acknowledged_timestamp': 10},
                       {u'received_timestamp': 11,
                        u'message_flow_id': u'id6',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'John',
                        u'form_type': u'text_line',
                        u'step_id': u'message_my-firstname',
                        u'message': u'Geef hier je voornaam in.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'John'}},
                        u'acknowledged_timestamp': 12},
                       {u'received_timestamp': 13,
                        u'message_flow_id': u'id7',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'Doe',
                        u'form_type': u'text_line',
                        u'step_id': u'message_my-lastname',
                        u'message': u'Geef hier je achternaam in.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'Doe'}},
                        u'acknowledged_timestamp': 14},
                       {u'received_timestamp': 15,
                        u'message_flow_id': u'id8',
                        u'button': u'Verder',
                        u'step_type': u'form_step',
                        u'display_value': u'mijn telefoonnummer',
                        u'form_type': u'text_line',
                        u'step_id': u'message_my-phone',
                        u'message': u'Om jouw melding goed te kunnen opvolgen, gelieve hier je telefoonnummer in te geven.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'mijn telefoonnummer'}},
                        u'acknowledged_timestamp': 16},
                       {u'received_timestamp': 17,
                        u'message_flow_id': u'id9',
                        u'button': u'Versturen',
                        u'step_type': u'form_step',
                        u'display_value': u'mijn eigen adres',
                        u'form_type': u'text_block',
                        u'step_id': u'message_my-address',
                        u'message': u'Geef hier je adres in.',
                        u'answer_id': u'positive',
                        u'form_result': {u'type': u'unicode_result', u'result': {u'value': u'mijn eigen adres'}},
                        u'acknowledged_timestamp': 18}]
        steps = parse_complex_value(object_factory("step_type", FLOW_STEP_MAPPING), steps_dict, True)
        xml_content = create_incident_xml(incident_id, rt_user, timestamp, steps)
        print(xml_content)

        upload_to_gcs(xml_content, u'text/xml', u'/%s/reports/%s.xml' % (gcs_bucket_name, incident_id))


if __name__ == '__main__':
    unittest.main()
