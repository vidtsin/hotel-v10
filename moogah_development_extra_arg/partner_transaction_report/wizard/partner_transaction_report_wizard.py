# -*- coding: utf-8 -*-

import calendar
from datetime import datetime
from lxml import etree
from odoo import api, models, fields, _


class PartnerTransactionReportWizard(models.TransientModel):
    _name = 'partner.transaction.report.wizard'
    _description = 'Wizard that show the partners transactions report'

    initial_date = fields.Date(
        'Date From', default=lambda s: datetime.today().replace(day=1), required=True)
    end_date = fields.Date(
        'Date To', default=lambda s: datetime.today().replace(day=1).replace(
        day=calendar.monthrange(datetime.today().year, datetime.today().month)[1]), required=True)
    partner_ids = fields.Many2many(
        'res.partner', string='Partners', required=True)
    type = fields.Selection(
        [('customer', 'Customer'), ('supplier', 'Supplier')], default='customer', string='Type')
    level = fields.Selection(
        [('overview', 'Overview'), ('detailed', 'Detailed')], default='overview', string='Level')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(PartnerTransactionReportWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context.get('default_type', False) and view_type == 'form':
            type = self._context.get('default_type', False)
            for node in doc.xpath("//field[@name='partner_ids']"):
                if type == 'customer':
                    node.set('domain', "[('customer', '=', True)]")
                else:
                    node.set('domain', "[('supplier', '=', True)]")
            res['arch'] = etree.tostring(doc)
        return res

    def _build_contexts(self, data):
        result = {
            'initial_date': data['form']['initial_date'] or False,
            'end_date': data['form']['end_date'] or False,
            'type': data['form']['type'] or False,
            'level': data['form']['level'] or False
        }
        return result

    def _print_report(self, data):
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env['report'].with_context(landscape=True).get_action(
            records, 'partner_transaction_report.report_partner_transaction',
            data=data)

    @api.multi
    def export_pdf(self):
        self.ensure_one()
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(
                ['initial_date', 'end_date', 'partner_ids', 'type',
                 'level'])[0]
        }
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(
            used_context, lang=self.env.context.get('lang'))
        return self._print_report(data)

    @api.multi
    def export_xls(self):
        context = self._context
        datas = {
            'ids': context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(
                ['initial_date', 'end_date', 'partner_ids', 'type',
                 'level'])[0]}
        used_context = self._build_contexts(datas)
        datas['form']['used_context'] = dict(
            used_context, lang=self.env.context.get('lang', 'en_US'))
        return self.env['report.partner_transaction_report.report_xlsx'].generate_xlsx_report(datas)

    @api.model
    def get_filename(self):
        return _('Partner Transaction') + '.xls'

    @api.model
    def get_file(self):
        return self.export_xls()


    @api.model
    def get_content_type(self):
        return 'application/vnd.ms-excel'
