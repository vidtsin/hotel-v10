# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockMove(models.Model):
    _inherit = "stock.move"

    invoice_line_id = fields.Many2one(
        'account.invoice.line',
        string='Invoice Line',
        copy=False,
        readonly=True
    )