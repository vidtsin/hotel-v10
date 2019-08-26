# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'product_analytic_tags_rel', 'prod_id', 'analytic_tag_id', string='Analytic Tags')
    supplier_analytic_tag_ids = fields.Many2many('account.analytic.tag', 'supplier_product_analytic_tags_rel', 'prod_id', 'analytic_tag_id', string='Vendor Analytic Tags')


class ProductCategory(models.Model):
    _inherit = "product.category"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'product_analytic_tags_rel', 'prod_id', 'analytic_tag_id', string='Analytic Tags')
    supplier_analytic_tag_ids = fields.Many2many('account.analytic.tag', 'supplier_product_analytic_tags_rel', 'prod_id', 'analytic_tag_id', string='Vendor Analytic Tags')
