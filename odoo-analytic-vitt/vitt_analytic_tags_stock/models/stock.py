# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'stock.picking'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        self._add_analytic_tags(self.analytic_tag_ids)

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)
        self.analytic_tag_ids = analytic_tags

        # if self.company_id.analytic_tags_to_rows:  # update rows with the header tags
        #     for line in self.invoice_line_ids:
        #         tags_rows = analytic_tags + line.analytic_tag_ids if tags else line.analytic_tag_ids

        #         line._add_analytic_tags(tags_rows)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        self.ensure_one()
        lines = super(StockMove, self)._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
        if lines:
            for line in lines:
                line[2].update({'analytic_tag_ids': [(6, 0, self.picking_id.analytic_tag_ids.ids)]})

        return lines
