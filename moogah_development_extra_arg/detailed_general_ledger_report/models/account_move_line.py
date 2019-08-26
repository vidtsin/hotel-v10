# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, exceptions, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from parser import parser
# from lxml import etree



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    @api.model
    def _query_get(self, domain=None):
        context = dict(self._context or {})
        domain = domain and safe_eval(str(domain)) or []

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        # if context.get('without_initial_balance'):
        #     domain += [(date_field, '>=', context['date_from'])]
        if context.get('date_from'):
            if context.get(''):
                domain += [(date_field, '>=', context['date_from'])]
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']),
                           ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        if 'company_ids' in context:
            domain += [('company_id', 'in', context['company_ids'])]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|',
                       ('matched_debit_ids.create_date', '>', context['reconcile_date']),
                       ('matched_credit_ids.create_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += ['|', ('analytic_account_id.tag_ids', 'in', context['analytic_tag_ids'].ids),
                       ('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('account_type_ids'):
            domain += [('account_id.user_type_id', 'in', context['account_type_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        if context.get('account_range'):
            # a_filter = "from 5 to 6 not 7, 8 and 92,784".replace(',', ' ').replace(';', ' ')
            a_filter = context['account_range'].replace(',', ' ').replace(';', ' ')
            a_list = [token for token in a_filter.split(' ') if token.isalnum()]
            account_range = []
            domain_account = []
            try:
                parser(a_list, account_range)
            except Exception, e:
                raise exceptions.UserError(_('sintaxsis incorrecta.'))
            if account_range:
                if account_range[0].get('ini') and account_range[0].get('end'):
                    domain_account += [('code', '>=', account_range[0].get('ini')),
                                       ('code', '<=', account_range[0].get('end'))]
                if account_range[0].get('exclude'):
                    domain_account += [('code', 'not in', account_range[0].get('exclude'))]
                account_ids_1 = self.env['account.account'].search(domain_account).ids
                if account_range[0].get('include'):
                    domain_account = [('code', 'in', account_range[0].get('include'))]
                account_ids_2 = self.env['account.account'].search(domain_account).ids

                domain += [('account_id.id', 'in', list(set(account_ids_1+ account_ids_2)))]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            query = self._where_calc(domain)
            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params

