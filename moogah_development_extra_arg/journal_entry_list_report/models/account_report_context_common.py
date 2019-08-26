# -*- coding: utf-8 -*-

from odoo import models


class AccountReportContextCommon(models.TransientModel):
    _inherit = "account.report.context.common"

    def _report_name_to_report_model(self):
        res = super(AccountReportContextCommon, self)._report_name_to_report_model()
        res.update({'journal_entry_list': 'journal.entry_list.report'})
        return res

    def _report_model_to_report_context(self):
        res = super(AccountReportContextCommon, self)._report_model_to_report_context()
        res.update({'journal.entry_list.report': 'journal.entry_list.context.report'})
        return res
