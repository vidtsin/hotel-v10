# -*- coding: utf-8 -*-

from odoo import models


class AccountReportContextCommon(models.TransientModel):
    _inherit = "account.report.context.common"

    def _report_name_to_report_model(self):
        res = super(AccountReportContextCommon, self)._report_name_to_report_model()
        res.update({'payment_journal': 'payment.journal.report',
                    'receipt_journal': 'receipt.journal.report'})
        return res

    def _report_model_to_report_context(self):
        res = super(AccountReportContextCommon, self)._report_model_to_report_context()
        res.update({'payment.journal.report': 'payment.journal.context.report',
                    'receipt.journal.report': 'receipt.journal.context.report'})
        return res
