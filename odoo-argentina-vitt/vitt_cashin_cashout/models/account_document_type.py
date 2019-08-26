# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _


class AcountDocumentType(models.Model):
    _inherit = 'account.document.type'

    internal_type = fields.Selection(selection_add = [
        ('cash_in', 'Entrada de Caja'),
        ('cash_out', 'Salida de Caja'),
    ])

