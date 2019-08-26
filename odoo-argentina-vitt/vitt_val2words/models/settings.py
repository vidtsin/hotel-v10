# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    val2words_default = fields.Many2one('vitt_val2words.config_text', string='Default Language Val to Words', help='Set default language to convert Val to Text')
