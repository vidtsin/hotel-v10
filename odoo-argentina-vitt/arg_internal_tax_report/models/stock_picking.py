# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_dispatch_number = fields.Char(string='Custom Dispatch Number', size=16,
                                         states={'done': [('readonly', True)]})
    show_dispatch_number = fields.Boolean('Show custom dispatch number field?', compute="_compute_show_dispatch_number",
                                          multi='dispatch_number')

    custom_dispatch_number_fnc = fields.Char(string='Custom Dispatch Number', size=16,
                                             compute="_compute_dispatch_number_fnc")
    show_dispatch_number_fnc = fields.Boolean('Show custom dispatch number field?',
                                              compute="_compute_show_dispatch_number", default=False,
                                              multi='dispatch_number')

    @api.multi
    def _compute_show_dispatch_number(self):
        for rec in self:
            rec.show_dispatch_number = rec.picking_type_id.code == 'incoming'
            rec.show_dispatch_number_fnc = rec.picking_type_id.code == 'outgoing'

    @api.multi
    def _compute_dispatch_number_fnc(self):
        for rec in self:
            if len(rec.pack_operation_product_ids):
                pack_lots = rec.pack_operation_product_ids.mapped('pack_lot_ids')
                if len(pack_lots):
                    rec.custom_dispatch_number_fnc = pack_lots[0].custom_dispatch_number

    def _create_lots_for_picking(self):
        super(StockPicking, self)._create_lots_for_picking()
        for pack_op_lot in self.mapped('pack_operation_ids').mapped('pack_lot_ids'):
            lot = pack_op_lot.lot_id.write({'custom_dispatch_number': pack_op_lot.custom_dispatch_number})


class PackOperationLot(models.Model):
    _inherit = "stock.pack.operation.lot"

    custom_dispatch_number = fields.Char(string='Custom Dispatch Number', size=16,
                                         compute='_compute_custom_dispatch_number_lot')

    @api.multi
    def _compute_custom_dispatch_number_lot(self):
        for rec in self:
            if rec.operation_id.picking_id.picking_type_id.code == 'incoming':
                rec.custom_dispatch_number = rec.operation_id.picking_id.custom_dispatch_number
            else:
                pack_lots = self.search([('lot_id', '=', rec.lot_id.id),
                                         ('operation_id.product_id', '=', rec.operation_id.product_id.id),
                                         ('operation_id.picking_id.picking_type_id.code', '=', 'incoming')])
                if len(pack_lots):
                    rec.custom_dispatch_number = pack_lots[0].operation_id.picking_id.custom_dispatch_number


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    custom_dispatch_number = fields.Char(string='Custom Dispatch Number', size=16)
