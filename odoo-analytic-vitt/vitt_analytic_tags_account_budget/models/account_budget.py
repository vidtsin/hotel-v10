# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CrossoveredBudget(models.Model):
    _inherit = 'crossovered.budget.lines'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        self._add_analytic_tags(self.analytic_tag_ids)

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)
        self.analytic_tag_ids = analytic_tags
