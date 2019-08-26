# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    analytic_tags_to_rows = fields.Boolean(string='Analytic Tags from Header To Rows')


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    analytic_tags_to_rows = fields.Boolean(string='Analytic Tags from Header To Rows', related='company_id.analytic_tags_to_rows',)
