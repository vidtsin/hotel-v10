# -*- coding: utf-8 -*-

import time
from datetime import datetime

from odoo import models, api
from odoo.tools import append_content_to_html, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import formatLang, ustr
from odoo.tools.translate import _


class ReportAccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    @api.model
    def get_lines(self, context_id, line_id=None, public=False):
        # Get date format for the lang
        lang_code = context_id.partner_id.lang or self.env.user.lang or 'en_US'
        lang_ids = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang_ids.date_format or DEFAULT_SERVER_DATE_FORMAT

        def formatLangDate(date):
            date_dt = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
            return date_dt.strftime(date_format.encode('utf-8')).decode('utf-8')

        lines = []
        res = {}
        today = datetime.today().strftime('%Y-%m-%d')
        line_num = 0
        for l in context_id.partner_id.unreconciled_aml_ids:
            if public and l.blocked:
                continue
            currency = l.currency_id or l.company_id.currency_id
            if currency not in res:
                res[currency] = []
            res[currency].append(l)
        for currency, aml_recs in res.items():
            total = 0
            total_issued = 0
            aml_recs = sorted(aml_recs, key=lambda aml: aml.blocked)
            for aml in aml_recs:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                date_due = formatLangDate(aml.date_maturity or aml.date)
                total += not aml.blocked and amount or 0
                is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                is_payment = aml.payment_id
                if is_overdue or is_payment:
                    total_issued += not aml.blocked and amount or 0
                if is_overdue:
                    date_due = (date_due, 'color: red;')
                if is_payment:
                    date_due = ''
                amount = formatLang(self.env, amount, currency_obj=currency).replace(' ', '&nbsp;')
                line_num += 1
                name = aml.move_id.name
                if aml.invoice_id:
                    name = aml.invoice_id.display_name
                if aml.payment_id and aml.payment_id.payment_group_id:
                    name = aml.payment_id.payment_group_id.display_name
                lines.append({
                    'id': aml.id,
                    'name': name,
                    'action': aml.get_model_id_and_name(),
                    'move_id': aml.move_id.id,
                    'type': is_payment and 'payment' or 'unreconciled_aml',
                    'footnotes': {},
                    'unfoldable': False,
                    'columns': [formatLangDate(aml.date), date_due, aml.invoice_id.name or aml.name] + (not public and [aml.expected_pay_date and (aml.expected_pay_date, aml.internal_note) or ('', ''), aml.blocked] or []) + [amount],
                    'blocked': aml.blocked,
                })
            total = formatLang(self.env, total, currency_obj=currency).replace(' ', '&nbsp;')
            line_num += 1
            lines.append({
                'id': line_num,
                'name': '',
                'type': 'total',
                'footnotes': {},
                'unfoldable': False,
                'level': 0,
                'columns': (not public and ['', ''] or []) + ['', '', total >= 0 and _('Total Due') or ''] + [total],
            })
            if total_issued > 0:
                total_issued = formatLang(self.env, total_issued, currency_obj=currency).replace(' ', '&nbsp;')
                line_num += 1
                lines.append({
                    'id': line_num,
                    'name': '',
                    'type': 'total',
                    'footnotes': {},
                    'unfoldable': False,
                    'level': 0,
                    'columns': (not public and ['', ''] or []) + ['', '', _('Total Overdue')] + [total_issued],
                })
        return lines

    # @api.model
    # def get_template(self):
    #     return 'customer_statement_report.report_followup_customer_statement'



class AccountReportContextFollowup(models.TransientModel):
    _inherit = "account.report.context.followup"

    @api.multi
    def send_email(self):
        partner = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        email = partner.email_collections and partner.email_collections or partner.email
        if email and email.strip():
            email = self.env['mail.mail'].create({
                'subject': _('%s Payment Reminder') % (self.env.user.company_id.name) + ' - ' + self.partner_id.name,
                'body_html': append_content_to_html(self.with_context(public=True, mode='print').get_html(), self.env.user.signature, plaintext=False),
                'email_from': self.env.user.email or '',
                'email_to': email,
            })
            msg = self._get_email_sent_log()
            msg += '<br>' + ustr(self.with_context(public=True, mode='print').get_html())
            self.partner_id.message_post(body=msg, subtype='account_reports.followup_logged_action')
            return True
        return False
