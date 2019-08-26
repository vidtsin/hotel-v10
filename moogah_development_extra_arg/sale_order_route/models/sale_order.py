# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    route_id = fields.Many2one('stock.location.route',
                               string='Delivery Process')

    @api.one
    def action_update(self):
        self.order_line.write({'route_id': self.route_id.id})
        return True
