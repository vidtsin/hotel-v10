# -*- coding: utf-8 -*-
from odoo import fields, models
# from odoo.exceptions import UserError


class AfipresponsabilityType(models.Model):
    _name = 'afip.responsability.type'
    _description = 'AFIP Responsability Type'
    _order = 'sequence'

    name = fields.Char(
        'Name',
        translate=True, 
        size=64,
        required=True
    )
    sequence = fields.Integer(
        'Sequence',
        translate=True,
    )
    code = fields.Char(
        'Code',
        translate=True, 
        size=8,
        required=True
    )
    active = fields.Boolean(
        'Active',
        translate=True,
        default=True
    )
    issued_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_doc_let_responsability_issuer_rel',
        'afip_responsability_type_id',
        'letter_id',
        'Issued Document Letters',
        translate=True
    )
    received_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_doc_let_responsability_receptor_rel',
        'afip_responsability_type_id',
        'letter_id',
        'Received Document Letters',
        translate=True
    )
    report_code_name = fields.Char(
        'report code name',
        translate=True,
        size=8,
    )
    arciba_resp_code = fields.Char("ARCIBA Resp. Code",size=1)

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
