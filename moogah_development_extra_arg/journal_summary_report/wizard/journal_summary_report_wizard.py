# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from datetime import datetime


class JournalSummaryReportWizard(models.TransientModel):
    _name = 'journal.summary.report.wizard'
    _description = 'Wizard that show the journal summary report'

    start_date = fields.Date('Start Date', default=lambda s: datetime.today().replace(month=1, day=1), required=True)
    end_date = fields.Date('End Date', default=lambda s: datetime.today().replace(month=12, day=31), required=True)
    legal_no = fields.Integer('Legal Ser.No.')
    customer_invoices = fields.Boolean('Customer Invoices', default=True)
    vendor_invoices = fields.Boolean('Vendor Bills', default=True)
    supplier_payments = fields.Boolean('Supplier Payments', default=True)
    customer_receipts = fields.Boolean('Customer Receipts', default=True)
    sort_by = fields.Selection([('monthly','Monthly summary'), ('number','Number'), ('date','Journal Entry Date')],
                               'Sort by', default='monthly')
    show_reg_number = fields.Boolean(string="Show Reg. Number",default=True)

