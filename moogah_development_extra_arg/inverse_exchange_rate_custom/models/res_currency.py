# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
import datetime


class res_currency(models.Model):
    _inherit = 'res.currency'

    inverse_rate = fields.Float(string='Inverse Rate', digits=(12, 6))

    #    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits=(12, 6),
    #                    help='The rate of the currency to the currency of rate 1.', store=True)

    @api.multi
    def write(self, vals):
        print "===============vals", vals
        res = super(res_currency, self).write(vals)
        if vals.get('inverse_rate'):
            self.env['res.currency.rate'].create({
                'name': datetime.datetime.now(),
                'rate': 1.0 / vals.get('inverse_rate'),
                'inverse_rate': vals.get('inverse_rate'),
                'currency_id': self.id
            })
        return res


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    inverse_rate = fields.Float(string='Inverse Rate', digits=(12, 6))
