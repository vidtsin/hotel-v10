# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##################################################################################

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from datetime import datetime, timedelta
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from operator import itemgetter


class AccountReportContextCommon(models.TransientModel):
    _inherit = "account.report.context.common"

    filter_unfold_all = fields.Boolean('Unfold All', default=False)
    new_filter_unfold_all = fields.Boolean('New filter to fold and unfold lines', default=False)

    def _report_name_to_report_model(self):
        res = super(AccountReportContextCommon, self)._report_name_to_report_model()
        res.update({'vendor_transaction_report': 'vendor.transaction.report',
                    'partner_transaction_report': 'partner.transaction.report',
                    'currencies_customer_ledger_report':'currencies.customer.ledger.report',
                    'currencies_vendor_ledger_report':'currencies.vendor.ledger.report'})
        return res


    def _report_model_to_report_context(self):
        res = super(AccountReportContextCommon, self)._report_model_to_report_context()
        res.update({'partner.transaction.report': 'partner.transection.context.report',
                    'vendor.transaction.report': 'vendor.transection.context.report',
                    'currencies.customer.ledger.report': 'currencies.customer.ledger.context.report',
                    'currencies.vendor.ledger.report': 'currencies.vendor.ledger.context.report'})
        return res

    @api.multi
    def get_html_and_data(self, given_context=None):
        if self.get_report_obj().get_name() in ['partner_transaction_report', 'vendor_transaction_report',
                                                'currencies_vendor_ledger_report', 'currencies_customer_ledger_report']:
            if given_context is None:
                given_context = {}
            result = {}
            if given_context:
                if 'force_account' in given_context and (not self.date_from or self.date_from == self.date_to):
                    self.date_from = \
                        self.env.user.company_id.compute_fiscalyear_dates(datetime.strptime(self.date_to, "%Y-%m-%d"))[
                            'date_from']
                    self.date_filter = 'custom'
                if given_context.get('active_id'):
                    if self.get_report_obj().get_name() in ['partner_transaction_report','vendor_transaction_report']:
                        self.write({'partner_id': given_context.get('active_id')})
                    if self.get_report_obj().get_name() in ['currencies_vendor_ledger_report','currencies_customer_ledger_report']:
                        wizard = self.env['partner.transaction.report.wizard'].browse(given_context.get('active_id'))
                        if wizard and self.wizard_id != wizard.id:
                            self.write({
                                'date_from': wizard.initial_date,
                                'date_to': wizard.end_date,
                                'date_filter': 'custom',
                                'wizard_id': wizard.id,
                                'partners_ids': [(6, 0, wizard.partner_ids.ids)]})
            lines = self.get_report_obj().get_lines(self)
            rcontext = {
                'res_company': self.env['res.users'].browse(self.env.uid).company_id,
                'context': self.with_context(**given_context),
                'report': self.get_report_obj(),
                'lines': lines,
                'footnotes': self.get_footnotes_from_lines(lines),
                'mode': 'display',
            }
            result['html'] = self.env['ir.model.data'].xmlid_to_object(self.get_report_obj().get_template()).render(
                rcontext)
            result['report_type'] = self.get_report_obj().get_report_type().read(
                ['date_range', 'comparison', 'cash_basis', 'analytic', 'extra_options'])[0]
            select = ['id', 'date_filter', 'date_filter_cmp', 'date_from', 'date_to', 'periods_number', 'date_from_cmp',
                      'date_to_cmp', 'cash_basis', 'all_entries', 'company_ids', 'multi_company', 'hierarchy_3',
                      'analytic',
                      'filter_unfold_all']
            if self.get_report_obj().get_name() == 'general_ledger':
                select += ['journal_ids']
                result['available_journals'] = self.get_available_journal_ids_names_and_codes()
            if self.get_report_obj().get_name() == 'partner_ledger':
                select += ['account_type']
            result['report_context'] = self.read(select)[0]
            result['report_context'].update(self._context_add())
            if result['report_type']['analytic']:
                result['report_context']['analytic_account_ids'] = [(t.id, t.name) for t in self.analytic_account_ids]
                result['report_context']['analytic_tag_ids'] = [(t.id, t.name) for t in self.analytic_tag_ids]
                result['report_context'][
                    'available_analytic_account_ids'] = self.analytic_manager_id.get_available_analytic_account_ids_and_names()
                result['report_context'][
                    'available_analytic_tag_ids'] = self.analytic_manager_id.get_available_analytic_tag_ids_and_names()
            result['xml_export'] = self.env['account.financial.html.report.xml.export'].is_xml_export_available(
                self.get_report_obj())
            result['fy'] = {
                'fiscalyear_last_day': self.env.user.company_id.fiscalyear_last_day,
                'fiscalyear_last_month': self.env.user.company_id.fiscalyear_last_month,
            }
            result['available_companies'] = self.multicompany_manager_id.get_available_company_ids_and_names()
            result['report_context']['new_filter_unfold_all'] = True
            return result
        else:
            res = super(AccountReportContextCommon, self).get_html_and_data(given_context)
            return res

    @api.model
    def return_context(self, report_model, given_context, report_id=None):
        if report_model in ['partner.transaction.report', 'vendor.transaction.report',
                            'currencies.vendor.ledger.report', 'currencies.customer.ledger.report']:
            context_model = self._report_model_to_report_context()[report_model]

            domain = [('create_uid', '=', self.env.user.id)]
            if report_id:
                domain.append(('report_id', '=', int(report_id)))
            context = False
            for c in self.env[context_model].search(domain):
                if c.available_company_ids and c.available_company_ids <= self.env[
                    'account.report.multicompany.manager']._default_company_ids():
                    context = c
                    break
            if context and (report_model == 'account.bank.reconciliation.report' and given_context.get('active_id')):
                context.unlink()
                context = self.env[context_model].browse(
                    [])
            if not context:
                create_vals = {}
                if report_id:
                    create_vals['report_id'] = report_id
                if report_model == 'account.bank.reconciliation.report' and given_context.get('active_id'):
                    create_vals['journal_id'] = given_context['active_id']
                context = self.env[context_model].create(create_vals)
            if 'force_account' in given_context:
                context.unfolded_accounts = [(6, 0, [given_context['active_id']])]

            update = {}
            for field in given_context:
                if field.startswith('add_'):
                    if field.startswith('add_tag_'):
                        ilike = self.env['account.report.tag.ilike'].create({'text': given_context[field]})
                        update[field[8:]] = [(4, ilike.id)]
                    else:
                        update[field[4:]] = [(4, int(given_context[field]))]
                if field.startswith('remove_'):
                    update[field[7:]] = [(3, int(given_context[field]))]
                if context._fields.get(field) and given_context[field] != 'undefined':
                    if given_context[field] == 'false':
                        given_context[field] = False
                    if given_context[field] == 'none':
                        given_context[field] = None
                    if field in ['analytic_account_ids', 'analytic_tag_ids',
                                 'company_ids']:
                        update[field] = [(6, 0, [int(id) for id in given_context[field]])]
                    else:
                        update[field] = given_context[field]

            if given_context.get('from_report_id') and given_context.get(
                    'from_report_model') and report_model == 'account.financial.html.report' and report_id:
                from_report = self.env[given_context['from_report_model']].browse(given_context['from_report_id'])
                to_report = self.env[report_model].browse(report_id)
                if not from_report.get_report_type().date_range and to_report.get_report_type().date_range:
                    dates = self.env.user.company_id.compute_fiscalyear_dates(datetime.today())
                    update['date_from'] = fields.Datetime.to_string(dates['date_from'])

            if given_context.get('filter_unfold_all'):
                update['filter_unfold_all'] = given_context.get('filter_unfold_all')

            if given_context.get('unfold_lines'):
                update['unfolded_payments'] = [(4, line) for line in given_context.get('unfold_lines')]

            if not update.get('filter_unfold_all', True):
                update['unfolded_payments'] = [(5,)]

            if update:
                context.write(update)
            return [context_model, context.id]
        else:
            res = super(AccountReportContextCommon, self).return_context(report_model,
                                                                                 given_context,
                                                                                 report_id)
            return res



