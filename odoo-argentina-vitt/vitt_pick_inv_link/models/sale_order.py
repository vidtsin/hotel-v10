# -*- coding: utf-8 -*-
from odoo import api, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        vals = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        move_ids = self.mapped('procurement_ids').mapped('move_ids').filtered(lambda x:
            not x.location_dest_id.scrap_location
            and x.location_dest_id.usage == 'customer'
            and not x.invoice_line_id).ids
        vals['move_line_ids'] = [(6, 0, move_ids)]
        return vals

    @api.multi
    def invoice_line_create(self, invoice, qty):
        obj = self.mapped('procurement_ids').mapped('move_ids')
        obj = obj.filtered(lambda x: not x.invoice_line_id and x.location_dest_id.usage == 'customer'
                                     and not x.location_dest_id.scrap_location).mapped('picking_id')
        obj.write({'invoice_ids': [(4, invoice)]})
        return super(SaleOrderLine, self).invoice_line_create(invoice, qty)