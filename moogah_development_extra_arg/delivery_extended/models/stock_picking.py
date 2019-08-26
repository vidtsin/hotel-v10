# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transport_company_id = fields.Many2one('res.partner', "Transport Company")
    freight_id = fields.Many2one('freight.freight', "Freight",
                                 states={'done': [('readonly', True)],
                                         'cancel': [('readonly', True)]})
    transport_note = fields.Text('Transport note')
    volume_done = fields.Float(string='Volume', digits=(16, 4),
                               compute='_compute_vol_wght',
                               help="Sum qty done * product volume in all operations")
    weight_done = fields.Float(string='Weight', digits=(16, 4),
                               compute='_compute_vol_wght',
                               help="Sum of qty done * product weight in all operations")
    del_sequence = fields.Integer(string="Delivery Sequence",index=True)

    @api.depends('pack_operation_product_ids',
                 'pack_operation_product_ids.qty_done')
    def _compute_vol_wght(self):
        for picking in self:
            picking.volume_done = sum(
                x.product_id.uom_id._compute_quantity(x.qty_done,
                                                      x.product_uom_id) * x.product_id.volume
                for x in picking.pack_operation_product_ids)
            picking.weight_done = sum(
                x.product_id.uom_id._compute_quantity(x.qty_done,
                                                      x.product_uom_id) * x.product_id.weight
                for x in picking.pack_operation_product_ids)

    @api.onchange('transport_company_id')
    def onchange_transport_company_id(self):
        self.transport_note = self.transport_company_id.comment

class StockPickingLinesWizard(models.TransientModel):
    _name = 'stock.picking.lines.wizard'

    spw_id = fields.Many2one('stock.picking.wizard')
    name = fields.Char(string="Nro")
    partner_id = fields.Many2one('res.partner',string="Entrega a")
    transport_company_id = fields.Many2one('res.partner',string="Transporte")
    delivery_sequence = fields.Integer(string="Orden")

class StockPickingWizard(models.TransientModel):
    _name = 'stock.picking.wizard'

    z_ids = fields.Char(string="list of ids")
    freight_id = fields.Many2one('freight.freight',string="Flete")
    date = fields.Date(string="Fecha",default=datetime.now())
    sp_ids = fields.One2many('stock.picking.lines.wizard', 'spw_id')

    @api.onchange('z_ids')
    def onchange_z_ids(self):
        idlist = self.z_ids.replace('[','')
        idlist = idlist.replace(']','')
        pick_list = map(int, idlist.split(','))
        sp = self.env['stock.picking'].browse(pick_list)
        list_lines = list()
        for pick in sp:
            list_lines.append((0, False, {
                'name':pick.name,
                'partner_id':pick.partner_id.id,
                'transport_company_id':pick.transport_company_id.id
            }))
        self.sp_ids = list_lines


    def fill_window(self):
        for line in self.sp_ids:
            sp = self.env['stock.picking'].search([('name', '=', line.name)])
            date = datetime.strptime(self.date, "%Y-%m-%d") + timedelta(hours=3)
            sp.write({'min_date': date, 'freight_id': self.freight_id.id, 'del_sequence': line.delivery_sequence})

        return {'type': 'ir.actions.act_window_close'}