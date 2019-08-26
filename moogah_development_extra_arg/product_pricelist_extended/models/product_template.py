# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    product_currency_id = fields.Many2one('res.currency', 'Product currency',
                                          required=True,
                                          default=_default_currency)
    last_po_cost = fields.Float("Last PO cost", digits=(16, 4),
                                currency_field='product_currency_id',
                                readonly=True)
    lp_base = fields.Float("LP base", digits=(16, 4),
                           currency_field='product_currency_id')
    cost = fields.Float("Cost", digits=(16, 4),
                        currency_field='product_currency_id')
    update_last_po_cost = fields.Boolean("Update last PO cost", default=True)
