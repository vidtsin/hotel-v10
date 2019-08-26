# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, osv
import xlsxwriter
from odoo.exceptions import Warning
from datetime import timedelta, datetime
import babel
import calendar
import json
import StringIO
from odoo.tools import config, posix_to_ldml


class AccountReportAnalyticManager(models.TransientModel):
    _inherit = 'account.report.analytic.manager'

    analytic_account_dimension_id = fields.Many2one(
        'account.analytic.dimension', string='Dimension')

    account_include = fields.Selection(
        [('active_accounts', 'Only Active Analytic Accounts'),
         ('archived_accounts', 'Only Archived Analytic Accounts'),
         ('active_archived_accounts', 'Active &amp; Archived Analytic Accounts')],
        string='Accounts to Include', default='active_accounts')

    tag_include = fields.Selection(
        [('active_tags', 'Only Active Analytic Tags'),
         ('archived_tags', 'Only Archived Analytic Tags'),
         ('active_archived_tags',
          'Active &amp; Archived Analytic Tags')],
        string='Tags to Include', default='active_tags')

    @api.multi
    def get_available_analytic_account_dimension_id_and_names(self):
        group_analytic = self.env.ref('analytic.group_analytic_accounting')
        if self.create_uid.id in group_analytic.users.ids:
            return [[t.id, t.name] for t in
                    self.env['account.analytic.dimension'].search([])]
        return []

    @api.multi
    def get_available_analytic_account_ids_active_and_names(self):
        group_analytic = self.env.ref('analytic.group_analytic_accounting')
        if self.create_uid.id in group_analytic.users.ids:
            return [[a.id, a.name, a.active] for a in
                    self.env['account.analytic.account'].search(
                        [('active', '!=', None)])]
        return []

    @api.multi
    def get_available_analytic_tag_ids_active_and_names(self):
        group_analytic = self.env.ref('analytic.group_analytic_accounting')
        if self.create_uid.id in group_analytic.users.ids:
            return [[t.id, t.name, t.active] for t in
                    self.env['account.analytic.tag'].search(
                        [('active', '!=', None)])]
        return []


class AccountReportAccountManager(models.TransientModel):
    _name = 'account.report.account.manager'
    _description = 'manages account filters for reports'

    account_ids = fields.Many2many('account.account',
                                   relation='account_report_context_account_rel')
    account_type_ids = fields.Many2many('account.account.type',
                                        relation='account_report_context_account_type_rel')
    account_range = fields.Char('Range', default='')

    @api.multi
    def get_available_account_ids_and_names(self):
        return [[t.id, t.name] for t in self.env['account.account'].search([])]

    @api.multi
    def get_available_account_type_ids_and_names(self):
        return [[a.id, a.name] for a in
                self.env['account.account.type'].search([])]

    @api.multi
    def get_available_account_tag_and_names(self):
        return [[a.id, a.name] for a in
                self.env['account.account.tag'].search([])]


class AccountReportContextCommon(models.TransientModel):
    _inherit = 'account.report.context.common'
    _inherits = {
        'account.report.footnotes.manager': 'footnotes_manager_id',
        'account.report.multicompany.manager': 'multicompany_manager_id',
        'account.report.analytic.manager': 'analytic_manager_id',
        'account.report.account.manager': 'account_manager_id',
    }

    account_manager_id = fields.Many2one('account.report.account.manager',
                                         string='Account Filters Manager',
                                         required=True, ondelete='cascade')
    balance = fields.Selection(
        [('all_balance', 'All Balance'), ('with_balance', 'With Balance'),
         ('without_balance', 'Without Balance')], string='Balance',
        default='all_balance')
    initial_balance = fields.Selection(
        [('with_initial_balance', 'With Initial Balance'),
         ('without_initial_balance', 'Without Initial Balance')],
        string='Initial Balance', default='with_initial_balance')

    def _report_name_to_report_model(self):
        res = super(AccountReportContextCommon,
                    self)._report_name_to_report_model()
        res.update(
            {'detailed_general_ledger': 'account.detail.general.ledger'})
        return res

    def _report_model_to_report_context(self):
        res = super(AccountReportContextCommon,
                    self)._report_model_to_report_context()
        res.update({
            'account.detail.general.ledger': 'account.context.detail.general.ledger'})
        return res

    @api.multi
    def get_html_and_data(self, given_context=None):
        if self.get_report_obj().get_name() in ['detailed_general_ledger']:
            if given_context is None:
                given_context = {}
            result = {}
            if given_context:
                if 'force_account' in given_context and (
                            not self.date_from or self.date_from == self.date_to):
                    self.date_from = \
                        self.env.user.company_id.compute_fiscalyear_dates(
                            datetime.strptime(self.date_to, "%Y-%m-%d"))[
                            'date_from']
                    self.date_filter = 'custom'
            lines = self.get_report_obj().get_lines(self)
            rcontext = {
                'res_company': self.env['res.users'].browse(
                    self.env.uid).company_id,
                'context': self.with_context(**given_context),
                'report': self.get_report_obj(),
                'lines': lines,
                'footnotes': self.get_footnotes_from_lines(lines),
                'mode': 'display',
            }
            result['html'] = self.env['ir.model.data'].xmlid_to_object(
                self.get_report_obj().get_template()).render(
                rcontext)
            result['report_type'] = \
                self.get_report_obj().get_report_type().read(
                    ['date_range', 'comparison', 'cash_basis', 'analytic',
                     'extra_options', 'account', 'balance', 'dimension'])[0]
            select = ['id', 'date_filter', 'date_filter_cmp', 'date_from',
                      'date_to', 'periods_number', 'account_range',
                      'date_from_cmp',
                      'date_to_cmp', 'cash_basis', 'all_entries',
                      'company_ids', 'multi_company', 'hierarchy_3',
                      'analytic',
                      'balance', 'analytic_account_dimension_id',
                      'initial_balance','account_include','tag_include']
            if self.get_report_obj().get_name() == 'general_ledger' or \
                            self.get_report_obj().get_name() == 'detailed_general_ledger':
                select += ['journal_ids']
                result[
                    'available_journals'] = self.get_available_journal_ids_names_and_codes()

            if self.get_report_obj().get_name() == 'partner_ledger':
                select += ['account_type']
            result['report_context'] = self.read(select)[0]
            result['report_context'].update(self._context_add())

            # TODO:Incluyendo account
            if result['report_type']['account']:
                result['report_context']['account_ids'] = [(t.id, t.name) for t
                                                           in self.account_ids]
                result['report_context']['account_type_ids'] = [(t.id, t.name)
                                                                for t in
                                                                self.account_type_ids]

                result['report_context'][
                    'available_account_ids'] = self.account_manager_id.get_available_account_ids_and_names()
                result['report_context'][
                    'available_account_type_ids'] = self.account_manager_id.get_available_account_type_ids_and_names()

            if result['report_type']['analytic']:
                result['report_context']['analytic_account_ids'] = [
                    (t.id, t.name) for t in self.analytic_account_ids]
                result['report_context']['analytic_tag_ids'] = [(t.id, t.name)
                                                                for t in
                                                                self.analytic_tag_ids]
                result['report_context'][
                    'available_analytic_account_ids'] = self.analytic_manager_id.get_available_analytic_account_ids_active_and_names()
                result['report_context'][
                    'available_analytic_tag_ids'] = self.analytic_manager_id.get_available_analytic_tag_ids_active_and_names()

                # TODO:Incluyendo dimesion
                # result['report_context']['analytic_account_dimension_id'] = [(t.id, t.name) for t in
                #                                                               self.analytic_account_dimension_id]
                result['report_context'][
                    'available_analytic_account_dimension_id'] = self.analytic_manager_id.get_available_analytic_account_dimension_id_and_names()

            result['xml_export'] = self.env[
                'account.financial.html.report.xml.export'].is_xml_export_available(
                self.get_report_obj())
            result['fy'] = {
                'fiscalyear_last_day': self.env.user.company_id.fiscalyear_last_day,
                'fiscalyear_last_month': self.env.user.company_id.fiscalyear_last_month,
            }
            result[
                'available_companies'] = self.multicompany_manager_id.get_available_company_ids_and_names()
            return result
        else:
            res = super(AccountReportContextCommon, self).get_html_and_data(
                given_context)
            return res

    @api.model
    def return_context(self, report_model, given_context, report_id=None):
        if report_model == 'account.detail.general.ledger':
            context_model = self._report_model_to_report_context()[
                report_model]

            domain = [('create_uid', '=', self.env.user.id)]
            if report_id:
                domain.append(('report_id', '=', int(report_id)))
            context = False
            for c in self.env[context_model].search(domain):
                if c.available_company_ids and \
                                c.available_company_ids <= self.env[
                            'account.report.multicompany.manager']._default_company_ids():
                    context = c
                    break
            if context and (
                            report_model == 'account.bank.reconciliation.report' and given_context.get(
                        'active_id')):
                context.unlink()
                context = self.env[context_model].browse(
                    [])
            if not context:
                create_vals = {}
                if report_id:
                    create_vals['report_id'] = report_id
                if report_model == 'account.bank.reconciliation.report' and given_context.get(
                        'active_id'):
                    create_vals['journal_id'] = given_context['active_id']
                context = self.env[context_model].create(create_vals)
            if 'force_account' in given_context:
                context.unfolded_accounts = [
                    (6, 0, [given_context['active_id']])]

            update = {}
            for field in given_context:
                if field.startswith('add_'):
                    if field.startswith('add_tag_'):
                        ilike = self.env['account.report.tag.ilike'].create(
                            {'text': given_context[field]})
                        update[field[8:]] = [(4, ilike.id)]
                    else:
                        update[field[4:]] = [(4, int(given_context[field]))]
                if field.startswith('remove_'):
                    update[field[7:]] = [(3, int(given_context[field]))]
                if context._fields.get(field) and given_context[
                    field] != 'undefined':
                    if given_context[field] == 'false':
                        given_context[field] = False
                    if given_context[field] == 'none':
                        given_context[field] = None
                    if field in ['analytic_account_ids', 'analytic_tag_ids',
                                 'company_ids', 'account_ids',
                                 'account_type_ids']:  # Needs to be treated differently as they are many2many

                        update[field] = [
                            (6, 0, [int(id) for id in given_context[field]])]
                    else:
                        update[field] = given_context[field]

            if given_context.get('from_report_id') and given_context.get(
                    'from_report_model') and report_model == 'account.financial.html.report' and report_id:
                from_report = self.env[
                    given_context['from_report_model']].browse(
                    given_context['from_report_id'])
                to_report = self.env[report_model].browse(report_id)
                if not from_report.get_report_type().date_range and to_report.get_report_type().date_range:
                    dates = self.env.user.company_id.compute_fiscalyear_dates(
                        datetime.today())
                    update['date_from'] = fields.Datetime.to_string(
                        dates['date_from'])
            if update:
                context.write(update)
            return [context_model, context.id]
        else:
            return super(AccountReportContextCommon, self).return_context(
                report_model, given_context, report_id)
