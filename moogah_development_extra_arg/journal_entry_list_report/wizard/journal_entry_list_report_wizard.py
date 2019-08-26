# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields


class JournalEntryListReportWizard(models.TransientModel):
    _name = 'journal.entry_list.report.wizard'
    _description = 'Wizard that show the journal entry report'

    start_date = fields.Date('Start Date', default=lambda s: datetime.today().replace(month=1, day=1), required=True)
    end_date = fields.Date('End Date', default=lambda s: datetime.today().replace(month=12, day=31), required=True)
    sort_by = fields.Selection([('name', 'Number'), ('date', 'Transaction Date')],
                               'Sort by', default='name')
