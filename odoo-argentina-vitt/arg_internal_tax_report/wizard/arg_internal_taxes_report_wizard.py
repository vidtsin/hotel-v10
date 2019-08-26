# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import cStringIO
import base64
from odoo import api, fields, models
from lxml import etree
import xlwt
from xlwt.Style import default_style
from datetime import *

from odoo import http
from odoo.http import request
from odoo.tools import ustr


class ArgInternalTaxesReportWizard(models.TransientModel):
    _name = 'arg.internal.taxes.report.wizard'
    _description = "Internal taxes report"

    # TODO solucion para restringir el dominio de los impuestos
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ArgInternalTaxesReportWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        group_ids = self.env['account.tax.group'].search([('application', '=', 'internal_taxes')]).ids
        tax_ids = self.env['account.tax'].search([('tax_group_id', 'in', group_ids)]).ids
        for field in res['fields']:
            if field in ['account_tax_id']:
                res['fields'][field]['domain'] = [('id', 'in', tax_ids), ('type_tax_use', '=', 'sale')]
            if field in ['purchase_tax_id']:
                res['fields'][field]['domain'] = [('id', 'in', tax_ids), ('type_tax_use', '=', 'purchase')]
        res['arch'] = etree.tostring(doc)
        return res

    date_from = fields.Date('Start date', required=True)
    date_to = fields.Date('End date', required=True)
    account_tax_id = fields.Many2one('account.tax', string="Sales Tax Code", required=True)
    purchase_tax_id = fields.Many2one('account.tax', string="Purchase Tax Code", required=True)
    format = fields.Selection([('pdf', 'PDF'), ('xls', 'Excel')], string="Format", required=True)

    @api.multi
    def print_report(self):
        data = {'form': {}}
        data['form'].update(self.read(['date_from', 'date_to', 'account_tax_id', 'purchase_tax_id', 'format'])[0])
        if data['form']['format'] == 'pdf':
            return self.env['report'].get_action(self, 'arg_internal_tax_report.internal_taxes', data=data)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'arg_internal_tax_report.report_internal_taxes.xls',
            'datas': data['form']}
