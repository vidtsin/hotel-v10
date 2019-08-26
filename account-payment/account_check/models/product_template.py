# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tc_state = fields.Selection([
        ('tc_canceled','Cheques 3ros Cancelados'),
        ('tc_rejected','Cheques 3ros Rechazados'),
        #('tc_rec_endorsed','Cheques 3ros Rechazados desde '),
        ],
        translate=True,
        string="Third Check State")
    oc_state = fields.Selection([
        ('oc_canceled','Cheques Propios Cancelados'),
        ('oc_rejected','Cheques Propios Rechazados')],
        translate=True,
        string="Own Check State")

