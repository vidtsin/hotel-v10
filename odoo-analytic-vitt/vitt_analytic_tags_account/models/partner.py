# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class Partner(models.Model):
    _inherit = "res.partner"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'partner_analytic_tags_rel', 'partner_id', 'analytic_tag_id', string='Analytic Tags')
    supplier_analytic_tag_ids = fields.Many2many('account.analytic.tag', 'supplier_partner_analytic_tags_rel', 'partner_id', 'analytic_tag_id', string='Vendor Analytic Tags')
