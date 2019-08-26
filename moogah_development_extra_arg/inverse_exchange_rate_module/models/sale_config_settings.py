# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_use_manual_exchange_rate = fields.Boolean("Allow the use of Manual Exchange Rates", default=False,
                                                    help="Allow the use of Manual Exchange Rates",
                                                    implied_group='inverse_exchange_rate_module.group_use_manual_exchange_rate')
    keep_exchange_rate = fields.Boolean("Keep the Exchange Rate from Quotations and Sales Order into Invoices",
                                        default=False)

    @api.multi
    def set_auto_keep_exchange_rate_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'keep_exchange_rate', self.keep_exchange_rate)
