# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, Warning

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state_id = fields.Many2one(
        'res.country.state',
        string="State",
        translate=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def write(self,vals):
        for rec in self:
            if rec.picking_type_id and rec.origin:
                po = rec.env['purchase.order'].search([('name','=',rec.origin)])
                if po:
                    po.write({'state_id':rec.picking_type_id.warehouse_id.partner_id.state_id.id})
        return super(StockPicking, self).write(vals)
