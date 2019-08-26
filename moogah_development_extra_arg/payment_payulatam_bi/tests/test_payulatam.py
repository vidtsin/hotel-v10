# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
from lxml import objectify
import urlparse

import odoo
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_payulatam_bi.controllers.main import PayuLatamController
from odoo.tools import mute_logger


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(False)
class PayuLatamCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(PayuLatamCommon, self).setUp()
        self.base_url = self.env[
            'ir.config_parameter'].get_param('web.base.url')
        # get the payulatam account
        self.payulatam = self.env.ref('payment_payulatam_bi.payment_acquirer_payu')


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(False)
class PayuLatamForm(PayuLatamCommon):

    def test_10_payulatam_form_render(self):
        self.assertEqual(
            self.payulatam.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        form_values = {
            'key': self.payulatam.payulatam_merchant_key,
            'txnid': 'SO004',
            'amount': '2240.0',
            'productinfo': 'SO004',
            'firstname': 'Norbert',
            'email': 'norbert.buyer@example.com',
            'phone': '0032 12 34 56 78',
            'service_provider': 'payu_paisa',
            'udf1': None,
            'surl': '%s' % urlparse.urljoin(self.base_url, PayuLatamController._response_url),
            'furl': '%s' % urlparse.urljoin(self.base_url, PayuLatamController._confirm_url),
        }

        form_values['signature'] = self.env['payment.acquirer']._payu_generate_sign(
            self.payulatam, 'in', form_values)

        # render the button
        res = self.payulatam.render(
            'SO004', 2240.0, self.currency_euro_id, partner_id=None, partner_values=self.buyer_values)

        # check form result
        tree = objectify.fromstring(res[0])
        self.assertEqual(
            tree.get('action'), 'https://test.payu.in/_payment', 'PayuLatam: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'PayuLatam: wrong value for input %s: received %s instead of %s' % (
                    form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('odoo.addons.payment_payulatam_bi.models.payulatam', 'ValidationError')
    def test_20_payulatam_form_management(self):
        self.assertEqual(
            self.payulatam.environment, 'test', 'test without test environment')

        # typical data posted by payulatam after client has successfully paid
        payulatam_post_data = {
            'key': u'YATU7J',
            'firstname': u'michael',
            'productinfo': u'SO004',
            'txnid': u'SO004',
            'amount': u'2240.0',
            'email': u'michael.partner@example.com',
            'signature': u'3cbc9aa39a7cb7472144957be6d4a2ed43f72c267677d671101bde8cf909c39add98f5d7b82a19a3f6c3880af1c9f2b98f6ba163d95697645fc479e033ff86d2',
            'mihpayid': u'403993715511008414',
            'udf1': u'',
            'status': u'success',
            'payuLatamId': u'110024086',
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(
                payulatam_post_data, 'payulatam')

        tx = self.env['payment.transaction'].create(
            {
                'amount': 2240.0,
                'acquirer_id': self.payulatam.id,
                'currency_id': self.currency_euro_id,
                'reference': 'SO004',
                'partner_name': 'Michael Partner',
                'partner_country_id': self.country_france_id,
            })
        # validate it
        self.env['payment.transaction'].form_feedback(
            payulatam_post_data, 'payulatam')
        # check state
        self.assertEqual(
            tx.state, 'done', 'PayuLatam: validation did not put tx into done state')
        self.assertEqual(tx.payulatam_txnid, payulatam_post_data.get(
            'mihpayid'), 'PayuLatam: validation did not update tx payid')
        self.assertEqual(tx.payulatam_id, payulatam_post_data.get(
            'payuLatamId'), 'PayuLatam: validation did not update unique payment id')
        # reset tx
        tx.write(
            {'state': 'draft', 'date_validate': False, 'payulatam_txnid': False})

        # now payulatam post is ok: try to modify the signature
        payulatam_post_data['signature'] = '51fbd1f0b8cff2f0342bd88e8aa199fbd144f94ed0c55653b50f76b8051def415261f381625838303e1df11cf75866dd35079c7aa2001e7d459bf4ffd'
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(
                payulatam_post_data, 'payulatam')

        # simulate an error
        payulatam_post_data['status'] = u'pending'
        payulatam_post_data['signature'] = u'877728be77b25e0f7d82141d4fff1b22135f5fd251b084ee277f6e6275650bf54df7802679aa30fa5fc9b6ca55394dccfbc3459144b8a840d27fc6ed8f7cd605'
        self.env['payment.transaction'].form_feedback(payulatam_post_data, 'payulatam')
        # check state
        self.assertEqual(tx.state, 'pending', 'PayuLatam: erroneous validation did not put tx into pending state')
