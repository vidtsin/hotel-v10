# -*- coding: utf-8 -*-
###############################################################################
#
#   account_origin_document for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2017-today Troova Software Development Group (troovacomercial@gmail.com).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import api, exceptions, fields, models, _
from collections import defaultdict

class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        # group quants by cost
        quant_cost_qty = defaultdict(lambda: 0.0)
        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty

        AccountMove = self.env['account.move']
        for cost, qty in quant_cost_qty.iteritems():
            move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            if move_lines:
                date = self._context.get('force_period_date', fields.Date.context_today(self))
                new_account_move = AccountMove.create({
                    'journal_id': journal_id,
                    'line_ids': move_lines,
                    'date': date,
                    'ref': move.picking_id.name,
                    'origin_document': move.picking_id.display_name,
                    'type_document': 'stock_move',
                    'document_id': move.picking_id.id})
                new_account_move.post()
