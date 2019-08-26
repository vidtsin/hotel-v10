# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
from odoo import models, fields, api, _


class AccountPaymentConfig(models.TransientModel):
    _inherit = 'account.config.settings'

    module_payulatam_payment = fields.Boolean(
            'Manage Payments Using PayuLatam',
            help='-It installs the module "payment_payulatam".')
