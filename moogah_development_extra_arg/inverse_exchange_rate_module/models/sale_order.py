# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Manual Rate', digits=(12, 6))

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        keep_exchange_rate = self.env['ir.values'].get_default('sale.config.settings', 'keep_exchange_rate')
        if keep_exchange_rate:
            invoice_vals.update({'manual_currency_rate_active': self.manual_currency_rate_active,
                                 'manual_currency_rate': self.manual_currency_rate,
                                 'currency_rate': self.manual_currency_rate})
        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _get_display_price(self, product):
        if self.order_id.manual_currency_rate_active and self.order_id.currency_id != self.order_id.company_id.currency_id:
            return product.lst_price / self.order_id.manual_currency_rate
        return super(SaleOrderLine, self)._get_display_price(product)
