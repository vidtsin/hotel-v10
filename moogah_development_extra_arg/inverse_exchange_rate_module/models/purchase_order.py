# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Manual Rate', digits=(12, 6))


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        super(PurchaseOrderLine, self)._onchange_quantity()
        if self.price_unit and self.order_id.manual_currency_rate_active and self.order_id.currency_id != self.order_id.company_id.currency_id:
            seller = self.product_id._select_seller(
                partner_id=self.partner_id,
                quantity=self.product_qty,
                date=self.order_id.date_order and self.order_id.date_order[:10],
                uom_id=self.product_uom)
            price_unit = self.env['account.tax']._fix_tax_included_price(seller.price,
                                                                         self.product_id.supplier_taxes_id,
                                                                         self.taxes_id) if seller else 0.0
            if price_unit:
                price_unit = price_unit / self.invoice_id.manual_currency_rate
            if seller and self.product_uom and seller.product_uom != self.product_uom:
                price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)
            self.price_unit = price_unit
