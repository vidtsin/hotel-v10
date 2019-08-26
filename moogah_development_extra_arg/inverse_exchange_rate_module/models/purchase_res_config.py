# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    group_use_manual_exchange_rate = fields.Boolean("Allow the use of Manual Exchange Rates", default=False,
                                                    help="Allow the use of Manual Exchange Rates",
                                                    implied_group='inverse_exchange_rate_module.group_use_manual_exchange_rate_purchase')
    keep_exchange_rate = fields.Boolean("Keep the Exchange Rate from Quotations and Purchase Order into Vendor Bills",
                                        default=False)

    @api.multi
    def set_auto_keep_exchange_rate_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'purchase.config.settings', 'keep_exchange_rate', self.keep_exchange_rate)
