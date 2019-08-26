# -*- coding: utf-8 -*-
# 2018 Moogah

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError

class StockBook(models.Model):
    _name = "stock.book"

    name = fields.Char(string="Nombre",copy=False,required=True,)
    partner_type = fields.Selection(
        [('customer', 'Customer'), ('supplier', 'Vendor')],
        required=True,
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Entry Sequence',
        help="This field contains the information related to the numbering "
        "of the stock entries of this stockbook.",
        copy=False,
    )
    pos_id = fields.Many2one('stock.book.qweb',string="Template")
    lines_nr = fields.Integer(string="Number of Lines")

class StockBookQweb(models.Model):
    _name = "stock.book.qweb"

    name = fields.Char(string="Code",size=64)
    pos = fields.Selection([('1', 'QWEB 1'),('2', 'QWEB 2'),('3', 'QWEB 3'),('4', 'QWEB 4'),('5', 'QWEB 5')],string="Choose POS")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stockbook_id = fields.Many2one('stock.book',string="StockBook")
    OfficialSerNr = fields.Char(size=64,string="Stock Official No.")

    @api.onchange('stockbook_id')
    def _onchange_stockbook_id(self):
        if self.stockbook_id:
            self.OfficialSerNr = self.env['ir.sequence'].next_by_code(self.stockbook_id.sequence_id.code)

    def write(self, vals):
        if 'OfficialSerNr' in vals.keys():
            if vals['OfficialSerNr'] != False:
                res = self.env['stock.picking'].search([('OfficialSerNr','=',vals['OfficialSerNr'])])
                if len(list(res._ids)) > 1:
                    raise ValidationError(_('error, nro oficial repetido'))
        return super(StockPicking,self).write(vals)

    #ovrewritten
    @api.multi
    def do_new_transfer(self):
        for pick in self:

            if pick.stockbook_id:
                if pick.stockbook_id.lines_nr <= 0:
                    raise UserError(_('Please fill number of lines in stockbook'))

                if pick.state == 'done':
                    raise UserError(_('The pick is already validated'))
                pack_operations_delete = self.env['stock.pack.operation']
                if not pick.move_lines and not pick.pack_operation_ids:
                    raise UserError(
                        _('Please create some Initial Demand or Mark as Todo and create some Operations. '))
                # In draft or with no pack operations edited yet, ask if we can just do everything
                if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                    # If no lots when needed, raise error
                    picking_type = pick.picking_type_id
                    if (picking_type.use_create_lots or picking_type.use_existing_lots):
                        for pack in pick.pack_operation_ids:
                            if pack.product_id and pack.product_id.tracking != 'none':
                                raise UserError(_(
                                    'Some products require lots/serial numbers, so you need to specify those first!'))
                    view = self.env.ref('stock.view_immediate_transfer')
                    wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                    # TDE FIXME: a return in a loop, what a good idea. Really.
                    return {
                        'name': _('Immediate Transfer?'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.immediate.transfer',
                        'views': [(view.id, 'form')],
                        'view_id': view.id,
                        'target': 'new',
                        'res_id': wiz.id,
                        'context': self.env.context,
                    }

                # Check backorder should check for other barcodes
                if pick.check_backorder():
                    view = self.env.ref('stock.view_backorder_confirmation')
                    wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                    # TDE FIXME: same reamrk as above actually
                    return {
                        'name': _('Create Backorder?'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.backorder.confirmation',
                        'views': [(view.id, 'form')],
                        'view_id': view.id,
                        'target': 'new',
                        'res_id': wiz.id,
                        'context': self.env.context,
                    }

                # NEW PART
                x = lot_qty = 0
                for operation in pick.pack_operation_ids:
                    if operation.qty_done < 0:
                        raise UserError(_('No negative quantities allowed'))
                    if operation.qty_done > 0:

                        lot_qty = 0
                        lot_qty =  sum(operation.pack_lot_ids.mapped('qty'))

                        if lot_qty <= 0:
                            if x <= pick.stockbook_id.lines_nr:
                                operation.write({'product_qty': operation.qty_done})
                            x += 1
                        else:
                            if (lot_qty+x) <= pick.stockbook_id.lines_nr:
                                operation.write({'product_qty': operation.qty_done})
                                x += operation.qty_done
                            else:
                                operation.qty_done = (pick.stockbook_id.lines_nr - x)
                                operation.write({'product_qty': operation.qty_done})
                                x += operation.qty_done

                    else:
                        pack_operations_delete |= operation
                    if x > pick.stockbook_id.lines_nr:
                        pack_operations_delete |= operation
                # NEW PART

                if pack_operations_delete:
                    pack_operations_delete.unlink()
                pick.do_transfer()

            else:
                return super(StockPicking, self).do_new_transfer()
