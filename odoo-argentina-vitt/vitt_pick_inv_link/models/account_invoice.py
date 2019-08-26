# -*- coding: utf-8 -*-
from odoo import fields, models

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    move_line_ids = fields.One2many(
        'stock.move',
        'invoice_line_id',
        readonly=True,
        copy=False,
    )

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    picking_ids = fields.Many2many(
        'stock.picking',
        string='Pickings',
        readonly=True,
        copy=False
    )

    def get_dels(self,inv):
        lst = inv.picking_ids.mapped('OfficialSerNr')
        res = ""
        for x in lst:
            if x:
                res += str(x) + ","
        return res
