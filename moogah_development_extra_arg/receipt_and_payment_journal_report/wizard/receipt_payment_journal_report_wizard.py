# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _
import calendar
from lxml import etree


class ReceiptAndPaymentJournalReportWizard(models.TransientModel):
    _name = 'receipt.and.payment.journal.report.wizard'
    _description = 'Wizard that show the receipt or payment journal report'

    start_date = fields.Date('Start Date', default=lambda s: datetime.today().replace(day=1), required=True)
    end_date = fields.Date('End Date', default=lambda s: datetime.today().replace(
        day=calendar.monthrange(datetime.today().year, datetime.today().month)[1]),
                           required=True)
    payment_no = fields.Char('Payment No')
    receipt_no = fields.Char('Receipt No')
    journal_ids = fields.Many2many('account.journal', string='Journals')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag (From Supplier)')
    reference = fields.Char('Reference')
    draft = fields.Boolean('Draft', default=True)
    confirmed = fields.Boolean('Confirmed', default=True)
    posted = fields.Boolean('Posted', default=True)
    detail_level_p = fields.Selection([('per_supplier', 'Per Supplier'), ('overview', 'Overview')],
                                      'Detail Level', default='overview')
    detail_level_r = fields.Selection([('per_customer', 'Per Customer'), ('overview', 'Overview')],
                                      'Detail Level', default='overview')
    type = fields.Selection([('receipt', 'Receipt'), ('payment', 'Payment')],
                            'Type of Report')

    company_id = fields.Many2one('res.company', 'Company')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ReceiptAndPaymentJournalReportWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('default_type'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='partner_id']"):
                if self._context['default_type'] == 'payment':
                    node.set('domain', "[('supplier', '=', True)]")
                else:
                    node.set('domain', "[('customer', '=', True)]")
                    res['fields']['partner_id']['string'] = _('Customer')

            for node in doc.xpath("//field[@name='journal_ids']"):
                if self._context['default_type'] == 'payment':
                    node.set('domain', "[('type', 'in', ['bank', 'cash']),"
                                       "('outbound_payment_method_ids.code', 'in',"
                                       "['manual', 'delivered_third_check', 'issue_check', 'withholding']),"
                                       "('outbound_payment_method_ids.payment_type', '=', 'outbound')]")
                else:
                    node.set('domain', "[('type', 'in', ['bank', 'cash']),"
                                       "('inbound_payment_method_ids.code', 'in',"
                                       "['manual', 'electronic', 'received_third_check', 'withholding']),"
                                       "('inbound_payment_method_ids.payment_type', '=', 'inbound')]")
            res['arch'] = etree.tostring(doc)
        return res
