# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SalesOrder(models.Model):
    _inherit = 'sale.order'

    transport_company_id = fields.Many2one('res.partner', "Transport Company")
    freight_id = fields.Many2one('freight.freight', "Freight",
                                 states={'cancel': [('readonly', True)],
                                         'done': [('readonly', True)]})
    transport_note = fields.Text('Transport note')

    @api.onchange('transport_company_id')
    def onchange_transport_company_id(self):
        self.transport_note = self.transport_company_id.comment

    @api.multi
    def action_confirm(self):
        res = super(SalesOrder, self).action_confirm()
        for order in self:
            order.picking_ids.write({
                'transport_company_id': order.transport_company_id.id,
                'freight_id': order.freight_id.id,
                'transport_note': order.transport_note,
            })
        return res

    @api.onchange('partner_shipping_id')
    def onchange_partner_shipping_id(self):
        res = False
        if self.partner_shipping_id and self.partner_shipping_id.transport_id:
            res = self.partner_shipping_id.transport_id
        self.transport_company_id = res
