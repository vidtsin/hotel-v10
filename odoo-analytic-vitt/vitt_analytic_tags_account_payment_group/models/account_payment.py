# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = "account.payment"


    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        self._add_analytic_tags(self.analytic_tag_ids)

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)
        self.analytic_tag_ids = analytic_tags


    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        move_line = super(AccountPayment, self)._get_shared_move_line_vals(debit, credit, amount_currency, move_id, invoice_id)
        move_line.update({'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)]})

        return move_line