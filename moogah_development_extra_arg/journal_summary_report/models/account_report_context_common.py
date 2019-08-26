# -*- coding: utf-8 -*-

from odoo import models


class AccountReportContextCommon(models.TransientModel):
    _inherit = "account.report.context.common"
    
    def _report_name_to_report_model(self):
        res = super(AccountReportContextCommon, self)._report_name_to_report_model()
        res.update({'journal_summary': 'journal.summary.report'})
        return res

    def _report_model_to_report_context(self):
        res = super(AccountReportContextCommon, self)._report_model_to_report_context()
        res.update({'journal.summary.report': 'journal.summary.context.report'})
        return res

