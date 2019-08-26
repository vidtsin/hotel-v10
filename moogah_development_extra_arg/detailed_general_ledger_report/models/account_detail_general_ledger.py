# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import odoo.tools as tools


class ReportAccountDetailGeneralLedger(models.AbstractModel):
    _name = "account.detail.general.ledger"
    _description = "Detailed General Ledger Report"

    def _format(self, value, currency=False):
        if self.env.context.get('no_format'):
            return value
        currency_id = currency or self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            # don't print -0.0 in reports
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res

    @api.model
    def get_lines(self, context_id, line_id=None, analytic_tag_id=None):
        if type(context_id) == int:
            context_id = self.env[
                'account.context.detail.general.ledger'].search(
                [['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'state': context_id.all_entries and 'all' or 'posted',
            'cash_basis': context_id.cash_basis,
            'context_id': context_id,
            'company_ids': context_id.company_ids.ids,
            'journal_ids': context_id.journal_ids.ids,
            'analytic_account_ids': context_id.analytic_account_ids,
            'analytic_tag_ids': context_id.analytic_tag_ids,
            'analytic_account_dimension_id': context_id.analytic_account_dimension_id,
            'account_ids': context_id.account_ids,
            'account_type_ids': context_id.account_type_ids,
            'balance': context_id.balance,
            'initial_balance': context_id.initial_balance,
            'account_range': context_id.account_range,
            'account_include': context_id.account_include,
            'tag_include': context_id.tag_include,
        })
        return self.with_context(new_context)._lines(line_id, analytic_tag_id)

    def _get_with_statement(self, user_types, domain=None):
        """ This function allow to define a WITH statement as prologue to the usual queries returned by query_get().
            It is useful if you need to shadow a table entirely and let the query_get work normally although you're
            fetching rows from your temporary table (built in the WITH statement) instead of the regular tables.

            @returns: the WITH statement to prepend to the sql query and the parameters used in that WITH statement
            @rtype: tuple(char, list)
        """
        sql = ''
        params = []

        # Cash basis option
        # -----------------
        # In cash basis, we need to show amount on income/expense accounts, but only when they're paid AND under the payment date in the reporting, so
        # we have to make a complex query to join aml from the invoice (for the account), aml from the payments (for the date) and partial reconciliation
        # (for the reconciled amount).
        if self.env.context.get('cash_basis'):
            if not user_types:
                return sql, params
            # we use query_get() to filter out unrelevant journal items to have a shadowed table as small as possible
            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get(domain=domain)
            sql = """WITH account_move_line AS (
              SELECT \"account_move_line\".id, \"account_move_line\".date, \"account_move_line\".name, \"account_move_line\".debit_cash_basis, \"account_move_line\".credit_cash_basis, \"account_move_line\".move_id, \"account_move_line\".account_id, \"account_move_line\".journal_id, \"account_move_line\".balance_cash_basis, \"account_move_line\".amount_residual, \"account_move_line\".partner_id, \"account_move_line\".reconciled, \"account_move_line\".company_id, \"account_move_line\".company_currency_id, \"account_move_line\".amount_currency, \"account_move_line\".balance, \"account_move_line\".user_type_id, \"account_move_line\".analytic_account_id
               FROM """ + tables + """
               WHERE (\"account_move_line\".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                 OR \"account_move_line\".move_id NOT IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s))
                 AND """ + where_clause + """
              UNION ALL
              (
               WITH payment_table AS (
                 SELECT aml.move_id, \"account_move_line\".date, CASE WHEN aml.balance = 0 THEN 0 ELSE part.amount / ABS(aml.balance) END as matched_percentage
                   FROM account_partial_reconcile part LEFT JOIN account_move_line aml ON aml.id = part.debit_move_id, """ + tables + """
                   WHERE part.credit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
                 UNION ALL
                 SELECT aml.move_id, \"account_move_line\".date, CASE WHEN aml.balance = 0 THEN 0 ELSE part.amount / ABS(aml.balance) END as matched_percentage
                   FROM account_partial_reconcile part LEFT JOIN account_move_line aml ON aml.id = part.credit_move_id, """ + tables + """
                   WHERE part.debit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
               )
               SELECT aml.id, ref.date, aml.name,
                 CASE WHEN aml.debit > 0 THEN ref.matched_percentage * aml.debit ELSE 0 END AS debit_cash_basis,
                 CASE WHEN aml.credit > 0 THEN ref.matched_percentage * aml.credit ELSE 0 END AS credit_cash_basis,
                 aml.move_id, aml.account_id, aml.journal_id,
                 ref.matched_percentage * aml.balance AS balance_cash_basis,
                 aml.amount_residual, aml.partner_id, aml.reconciled, aml.company_id, aml.company_currency_id, aml.amount_currency, aml.balance, aml.user_type_id, aml.analytic_account_id
                FROM account_move_line aml
                RIGHT JOIN payment_table ref ON aml.move_id = ref.move_id
                WHERE journal_id NOT IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                  AND aml.move_id IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s)
              )
            ) """
            params = [tuple(user_types.ids)] + where_params + [
                tuple(user_types.ids)] + where_params + [
                         tuple(user_types.ids)] + where_params + [
                         tuple(user_types.ids)]
        return sql, params

    def do_query_unaffected_earnings(self, line_id):
        ''' Compute the sum of ending balances for all accounts that are of a type that does not bring forward the balance in new fiscal years.
            This is needed to balance the trial balance and the general ledger reports (to have total credit = total debit)
        '''

        select = '''
        SELECT COALESCE(SUM("account_move_line".balance), 0),
               COALESCE(SUM("account_move_line".amount_currency), 0),
               COALESCE(SUM("account_move_line".debit), 0),
               COALESCE(SUM("account_move_line".credit), 0)'''
        if self.env.context.get('cash_basis'):
            select = select.replace('debit', 'debit_cash_basis').replace(
                'credit', 'credit_cash_basis')
        select += " FROM %s WHERE %s"
        user_types = self.env['account.account.type'].search(
            [('type', 'in', ('receivable', 'payable'))])
        with_sql, with_params = self._get_with_statement(user_types, domain=[
            ('user_type_id.include_initial_balance', '=', False)])
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get(
            domain=[('user_type_id.include_initial_balance', '=', False)])
        query = select % (tables, where_clause)
        self.env.cr.execute(with_sql + query, with_params + where_params)
        res = self.env.cr.fetchone()
        return {'balance': res[0], 'amount_currency': res[1], 'debit': res[2],
                'credit': res[3]}

    def _do_query(self, line_id, analytic_tag_id=False, group_by_account=True,
                  limit=False):
        if self._context.get('analytic_account_dimension_id'):
            return self._do_query_tag(line_id, analytic_tag_id,
                                      group_by_account, limit)
        if group_by_account:
            select = "SELECT \"account_move_line\".account_id"
            select += ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0),SUM(\"account_move_line\".amount_currency),SUM(\"account_move_line\".debit),SUM(\"account_move_line\".credit)'
            if self.env.context.get('cash_basis'):
                select = select.replace('debit', 'debit_cash_basis').replace(
                    'credit', 'credit_cash_basis')
        else:
            select = "SELECT \"account_move_line\".id"
        sql = "%s FROM %s WHERE %s%s"
        if group_by_account:
            sql += "GROUP BY \"account_move_line\".account_id"
        else:
            sql += " GROUP BY \"account_move_line\".id"
            sql += " ORDER BY MAX(\"account_move_line\".date),\"account_move_line\".id"
            if limit and isinstance(limit, int):
                sql += " LIMIT " + str(limit)
        user_types = self.env['account.account.type'].search(
            [('type', 'in', ('receivable', 'payable'))])
        with_sql, with_params = self._get_with_statement(user_types)
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        line_clause = line_id and ' AND \"account_move_line\".account_id = ' + str(
            line_id) or ''
        query = sql % (select, tables, where_clause, line_clause)
        self.env.cr.execute(with_sql + query, with_params + where_params)
        results = self.env.cr.fetchall()
        return results

    def _do_query_tag(self, line_id, analytic_tag_id, group_by_account=True,
                      limit=False):
        if group_by_account:
            select = "SELECT \"account_move_line\".account_id, \"account_analytic_tag\".id"
            select += ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0),SUM(\"account_move_line\".amount_currency),SUM(\"account_move_line\".debit),SUM(\"account_move_line\".credit)'
            if self.env.context.get('cash_basis'):
                select = select.replace('debit', 'debit_cash_basis').replace(
                    'credit', 'credit_cash_basis')
        else:
            select = "SELECT \"account_move_line\".id"
        sql = "%s FROM %s WHERE %s%s"
        if group_by_account:
            sql += "GROUP BY \"account_move_line\".account_id, \"account_analytic_tag\".id"
        else:
            sql += " GROUP BY \"account_move_line\".id"
            sql += " ORDER BY MAX(\"account_move_line\".date),\"account_move_line\".id"
            if limit and isinstance(limit, int):
                sql += " LIMIT " + str(limit)
        user_types = self.env['account.account.type'].search(
            [('type', 'in', ('receivable', 'payable'))])
        results = []
        if analytic_tag_id:
            tag_ids = [analytic_tag_id]
        else:
            tag_ids = self._context.get(
                'analytic_account_dimension_id').analytic_tag_ids.ids
        for tag in tag_ids:
            analytic_tag_ids = self.env['account.analytic.account'].search(
                [('tag_ids', 'in', [tag])])
            tag_clause = self._get_tag_clause(tag, analytic_tag_ids.ids)
            with_sql, with_params = self._get_with_statement(user_types)
            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get()
            line_clause = line_id and ' AND \"account_move_line\".account_id = ' + str(
                line_id) or ''
            line_clause += tag_clause
            query = sql % (
                select, tables + ',"account_analytic_tag"', where_clause,
                line_clause)
            self.env.cr.execute(with_sql + query, with_params + where_params)
            results_tag = self.env.cr.fetchall()
            if results_tag:
                results.extend(filter(lambda x: x not in results, results_tag))
        return results

    def _get_tag_clause(self, tag, analytic_ids):
        tag_clause = ''
        if analytic_ids and len(analytic_ids) == 1:
            tag_clause_1 = ' AND(( \"account_move_line\".analytic_account_id IN ' + '(' + str(
                analytic_ids[0]) + ')' + ') '

        elif analytic_ids and len(analytic_ids) > 1:
            tag_clause_1 = ' AND(( \"account_move_line\".analytic_account_id IN ' + str(
                tuple(analytic_ids, )) + ') '
        else:
            tag_clause_1 = ' AND( FALSE '

        tag_clause_2 = ' OR(\"account_move_line\"."id" in (SELECT \"account_analytic_tag_account_move_line_rel\"."account_move_line_id" ' \
                       'FROM \"account_analytic_tag_account_move_line_rel\"' \
                       ' WHERE \"account_analytic_tag_account_move_line_rel\"."account_analytic_tag_id" IN ( ' + str(
            tag) + ')' + '))) '

        tag_clause_5 = ' AND("account_analytic_tag".id = ' + str(tag) + ') '

        tag_clause += tag_clause_1 + tag_clause_2 + tag_clause_5

        return tag_clause

    def do_query(self, line_id):
        results = self._do_query(line_id, group_by_account=True, limit=False)
        used_currency = self.env.user.company_id.currency_id
        compute_table = {
            a.id: a.company_id.currency_id.compute
            for a in
            self.env['account.account'].browse([k[0] for k in results if k])
            }
        results = dict([(
                            k[0], {
                                'balance': compute_table[k[0]](k[1],
                                                               used_currency) if
                                k[0] in compute_table else k[1],
                                'amount_currency': k[2],
                                'debit': compute_table[k[0]](k[3],
                                                             used_currency) if
                                k[0] in compute_table else k[3],
                                'credit': compute_table[k[0]](k[4],
                                                              used_currency) if
                                k[0] in compute_table else k[4],
                            }
                        ) for k in results])
        return results

    def do_query_tag(self, line_id, analytic_tag_id):
        results = self._do_query(line_id, analytic_tag_id,
                                 group_by_account=True, limit=False, )
        used_currency = self.env.user.company_id.currency_id
        compute_table = {
            a.id: a.company_id.currency_id.compute
            for a in
            self.env['account.account'].browse([k[0] for k in results if k])
            }
        results_tag = {}
        for k in results:
            if not results_tag.get(k[1]):
                results_tag[k[1]] = [{k[0]: {
                    'balance': compute_table[k[0]](k[2], used_currency) if k[
                                                                               0] in compute_table else
                    k[2],
                    'amount_currency': k[3],
                    'debit': compute_table[k[0]](k[4], used_currency) if k[
                                                                             0] in compute_table else
                    k[4],
                    'credit': compute_table[k[0]](k[5], used_currency) if k[
                                                                              0] in compute_table else
                    k[5],}}]
            else:
                results_tag[k[1]].append({k[0]: {
                    'balance': compute_table[k[0]](k[2], used_currency) if k[
                                                                               0] in compute_table else
                    k[2],
                    'amount_currency': k[3],
                    'debit': compute_table[k[0]](k[4], used_currency) if k[
                                                                             0] in compute_table else
                    k[4],
                    'credit': compute_table[k[0]](k[5], used_currency) if k[
                                                                              0] in compute_table else
                    k[5],}})
        return results_tag

    def group_by_account_id(self, line_id):
        accounts = {}
        results = self.do_query(line_id)
        context = self.env.context
        if context.get('initial_balance', False) and context.get(
                'initial_balance') == 'without_initial_balance':
            results = self.with_context(
                date_from=context['date_from_aml'],
                strict_range=True).do_query(line_id)
        initial_bal_date_to = datetime.strptime(
            self.env.context['date_from_aml'], "%Y-%m-%d") + timedelta(days=-1)
        initial_bal_results = self.with_context(
            date_to=initial_bal_date_to.strftime('%Y-%m-%d')).do_query(line_id)
        unaffected_earnings_xml_ref = self.env.ref(
            'account.data_unaffected_earnings')
        unaffected_earnings_line = True  # used to make sure that we add the unaffected earning initial balance only once
        if unaffected_earnings_xml_ref:
            # compute the benefit/loss of last year to add in the initial balance of the current year earnings account
            last_day_previous_fy = \
                self.env.user.company_id.compute_fiscalyear_dates(
                    datetime.strptime(self.env.context['date_from_aml'],
                                      "%Y-%m-%d"))['date_from'] + timedelta(
                    days=-1)
            unaffected_earnings_results = self.with_context(
                date_to=last_day_previous_fy.strftime('%Y-%m-%d'),
                date_from=False).do_query_unaffected_earnings(line_id)
            unaffected_earnings_line = False
        base_domain = [('date', '<=', context['date_to']),
                       ('company_id', 'in', context['company_ids'])]
        if context.get('journal_ids'):
            base_domain.append(('journal_id', 'in', context['journal_ids']))
        if context['date_from_aml']:
            base_domain.append(('date', '>=', context['date_from_aml']))
        if context['state'] == 'posted':
            base_domain.append(('move_id.state', '=', 'posted'))
        if context.get('account_tag_ids'):
            base_domain += [
                ('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]
        if context.get('analytic_tag_ids'):
            base_domain += ['|', ('analytic_account_id.tag_ids', 'in',
                                  context['analytic_tag_ids'].ids), (
                                'analytic_tag_ids', 'in',
                                context['analytic_tag_ids'].ids)]

        # if not context.get('analytic_tag_ids') and context.get('tag_include'):
        #     tag_include = context.get('tag_include')
        #     if tag_include == 'active_tags':
        #         analytic_tag_ids = self.env['account.analytic.tag'].search([])
        #     elif tag_include == 'archived_tags':
        #         analytic_tag_ids = self.env['account.analytic.tag'].search([('active', '=', False)])
        #     else:
        #         analytic_tag_ids = self.env['account.analytic.tag'].search([('active', '!=', None)])
        #
        #     if analytic_tag_ids:
        #         base_domain += ['|', ('analytic_account_id.tag_ids', 'in', analytic_tag_ids.ids),
        #                    ('analytic_tag_ids', 'in', analytic_tag_ids.ids)]

        if context.get('analytic_account_ids'):
            base_domain += [('analytic_account_id', 'in',
                             context['analytic_account_ids'].ids)]

        # if not context.get('analytic_account_ids') and context.get(
        #         'account_include'):
        #     account_include = context.get('account_include')
        #     if account_include == 'active_accounts':
        #         analytic_account_ids = self.env[
        #             'account.analytic.account'].search([])
        #     elif account_include == 'archived_accounts':
        #         analytic_account_ids = self.env[
        #             'account.analytic.account'].search(
        #             [('active', '=', False)])
        #     else:
        #         analytic_account_ids = self.env[
        #             'account.analytic.account'].search(
        #             [('active', '!=', None)])
        #
        #     if analytic_account_ids:
        #         base_domain += [
        #             ('analytic_account_id', 'in', analytic_account_ids.ids)]

        if context.get('analytic_account_dimension_id'):
            base_domain += ['|', ('analytic_account_id.tag_ids', 'in', context[
                'analytic_account_dimension_id'].analytic_tag_ids.ids), (
                                'analytic_tag_ids', 'in', context[
                                    'analytic_account_dimension_id'].analytic_tag_ids.ids)]
        if context.get('account_ids'):
            base_domain += [('account_id', 'in', context['account_ids'].ids)]
        for account_id, result in results.items():
            domain = list(base_domain)  # copying the base domain
            domain.append(('account_id', '=', account_id))
            account = self.env['account.account'].browse(account_id)
            accounts[account] = result
            accounts[account]['initial_bal'] = initial_bal_results.get(
                account.id,
                {'balance': 0, 'amount_currency': 0, 'debit': 0, 'credit': 0})
            if account.user_type_id.id == self.env.ref(
                    'account.data_unaffected_earnings').id and not unaffected_earnings_line:
                # add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                unaffected_earnings_line = True
                for field in ['balance', 'debit', 'credit']:
                    accounts[account]['initial_bal'][field] += \
                        unaffected_earnings_results[field]
                    accounts[account][field] += unaffected_earnings_results[
                        field]
            # use query_get + with statement instead of a search in order to work in cash basis too
            aml_ctx = {}
            if context.get('date_from_aml'):
                aml_ctx = {
                    'strict_range': True,
                    'date_from': context['date_from_aml'],
                }
            aml_ids = self.with_context(**aml_ctx)._do_query(account_id,
                                                             group_by_account=False)
            aml_ids = [x[0] for x in aml_ids]
            accounts[account]['lines'] = self.env['account.move.line'].browse(
                aml_ids)
        # if the unaffected earnings account wasn't in the selection yet: add it manually
        if not unaffected_earnings_line and unaffected_earnings_results[
            'balance']:
            # search an unaffected earnings account
            unaffected_earnings_account = self.env['account.account'].search([(
                'user_type_id',
                '=',
                self.env.ref(
                    'account.data_unaffected_earnings').id)],
                limit=1)
            if unaffected_earnings_account and (
                        not line_id or unaffected_earnings_account.id == line_id):
                accounts[unaffected_earnings_account[
                    0]] = unaffected_earnings_results
                accounts[unaffected_earnings_account[0]][
                    'initial_bal'] = unaffected_earnings_results
                accounts[unaffected_earnings_account[0]]['lines'] = []
        return accounts

    def group_by_tag_id(self, line_id, analytic_tag_id):
        tags = {}
        results = self.do_query_tag(line_id, analytic_tag_id)
        context = self.env.context
        if context.get('initial_balance', False) and context.get(
                'initial_balance') == 'without_initial_balance':
            results = self.with_context(
                date_from=context['date_from_aml'],
                strict_range=True).do_query_tag(line_id, analytic_tag_id)

        initial_bal_date_to = datetime.strptime(
            self.env.context['date_from_aml'], "%Y-%m-%d") + timedelta(days=-1)
        initial_bal_results = self.with_context(
            date_to=initial_bal_date_to.strftime('%Y-%m-%d')).do_query_tag(
            line_id, analytic_tag_id)
        unaffected_earnings_xml_ref = self.env.ref(
            'account.data_unaffected_earnings')
        unaffected_earnings_line = True  # used to make sure that we add the unaffected earning initial balance only once
        if unaffected_earnings_xml_ref:
            # compute the benefit/loss of last year to add in the initial balance of the current year earnings account
            last_day_previous_fy = \
                self.env.user.company_id.compute_fiscalyear_dates(
                    datetime.strptime(self.env.context['date_from_aml'],
                                      "%Y-%m-%d"))['date_from'] + timedelta(
                    days=-1)
            unaffected_earnings_results = self.with_context(
                date_to=last_day_previous_fy.strftime('%Y-%m-%d'),
                date_from=False).do_query_unaffected_earnings(line_id)
            unaffected_earnings_line = False

        base_domain = [('date', '<=', context['date_to']),
                       ('company_id', 'in', context['company_ids'])]
        if context.get('journal_ids'):
            base_domain.append(('journal_id', 'in', context['journal_ids']))
        if context['date_from_aml']:
            base_domain.append(('date', '>=', context['date_from_aml']))
        if context['state'] == 'posted':
            base_domain.append(('move_id.state', '=', 'posted'))
        if context.get('account_tag_ids'):
            base_domain += [
                ('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]
        if context.get('analytic_tag_ids'):
            base_domain += ['|', ('analytic_account_id.tag_ids', 'in',
                                  context['analytic_tag_ids'].ids),
                            ('analytic_tag_ids', 'in',
                             context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            base_domain += [('analytic_account_id', 'in',
                             context['analytic_account_ids'].ids)]

        if context.get('analytic_account_dimension_id'):
            base_domain += ['|', (
                'analytic_account_id.tag_ids', 'in',
                context['analytic_account_dimension_id'].analytic_tag_ids.ids),
                            ('analytic_tag_ids', 'in', context[
                                'analytic_account_dimension_id'].analytic_tag_ids.ids)]
        if context.get('account_ids'):
            base_domain += [('account_id', 'in', context['account_ids'].ids)]
        for tag_id, values in results.items():
            accounts = {}
            tag = self.env['account.analytic.tag'].browse(tag_id)
            # tags[tag] = result
            for data in values:
                for account_id, account_result in data.items():
                    domain = list(base_domain)  # copying the base domain
                    domain.append(('account_id', '=', account_id))
                    account = self.env['account.account'].browse(account_id)
                    accounts[account] = account_result
                    accounts[account]['initial_bal'] = {'balance': 0,
                                                        'amount_currency': 0,
                                                        'debit': 0,
                                                        'credit': 0}
                    if tag_id in initial_bal_results:
                        account_initial_bal = filter(lambda x: account_id in x,
                                                     initial_bal_results[
                                                         tag_id])
                        if account_initial_bal:
                            accounts[account]['initial_bal'] = \
                                account_initial_bal[0].get(account_id,
                                                           {'balance': 0,
                                                            'amount_currency': 0,
                                                            'debit': 0})

                    if account.user_type_id.id == self.env.ref(
                            'account.data_unaffected_earnings').id and not unaffected_earnings_line:
                        # add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                        unaffected_earnings_line = True
                        for field in ['balance', 'debit', 'credit']:
                            accounts[account]['initial_bal'][field] += \
                                unaffected_earnings_results[field]
                            accounts[account][field] += \
                                unaffected_earnings_results[field]
                    # use query_get + with statement instead of a search in order to work in cash basis too
                    aml_ctx = {}
                    if context.get('date_from_aml'):
                        aml_ctx = {
                            'strict_range': True,
                            'date_from': context['date_from_aml'],
                        }
                    aml_ids = self.with_context(**aml_ctx)._do_query(
                        account_id, tag_id, group_by_account=False)
                    aml_ids = [x[0] for x in aml_ids]
                    accounts[account]['lines'] = self.env[
                        'account.move.line'].browse(aml_ids)
                    # if the unaffected earnings account wasn't in the selection yet: add it manually
                    if not unaffected_earnings_line and \
                            unaffected_earnings_results['balance']:
                        # search an unaffected earnings account
                        unaffected_earnings_account = self.env[
                            'account.account'].search(
                            [('user_type_id', '=', self.env.ref(
                                'account.data_unaffected_earnings').id)],
                            limit=1)
                        if unaffected_earnings_account and (
                                    not line_id or unaffected_earnings_account.id == line_id):
                            accounts[unaffected_earnings_account[
                                0]] = unaffected_earnings_results
                            accounts[unaffected_earnings_account[0]][
                                'initial_bal'] = unaffected_earnings_results
                            accounts[unaffected_earnings_account[0]][
                                'lines'] = []
            tags[tag] = accounts
        return tags

    def _get_taxes(self):
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        query = """
            SELECT rel.account_tax_id, SUM("account_move_line".balance) AS base_amount
            FROM account_move_line_account_tax_rel rel, """ + tables + """ 
            WHERE "account_move_line".id = rel.account_move_line_id
                AND """ + where_clause + """
           GROUP BY rel.account_tax_id"""
        self.env.cr.execute(query, where_params)
        ids = []
        base_amounts = {}
        for row in self.env.cr.fetchall():
            ids.append(row[0])
            base_amounts[row[0]] = row[1]

        res = {}
        for tax in self.env['account.tax'].browse(ids):
            self.env.cr.execute(
                'SELECT sum(debit - credit) FROM ' + tables + ' '
                                                              ' WHERE ' + where_clause + ' AND tax_line_id = %s',
                where_params + [tax.id])
            res[tax] = {
                'base_amount': base_amounts[tax.id],
                'tax_amount': self.env.cr.fetchone()[0] or 0.0,
            }
            if self.env.context['context_id'].journal_ids and \
                            self.env.context['context_id'].journal_ids[
                                0].type == 'sale':
                # sales operation are credits
                res[tax]['base_amount'] = res[tax]['base_amount'] * -1
                res[tax]['tax_amount'] = res[tax]['tax_amount'] * -1
        return res

    def _get_journal_total(self):
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        self.env.cr.execute(
            'SELECT COALESCE(SUM(debit), 0) as debit, COALESCE(SUM(credit), 0) as credit, COALESCE(SUM(debit-credit), 0) as balance FROM ' + tables + ' '
                                                                                                                                                      'WHERE ' + where_clause + ' ',
            where_params)
        return self.env.cr.dictfetchone()

    @api.model
    def _lines(self, line_id=None, analytic_tag_id=None):
        context = self.env.context
        if not context['analytic_account_dimension_id']:
            lang_code = self.env.lang or 'en_US'
            lang = self.env['res.lang']
            lang_id = lang._lang_get(lang_code)
            date_format = lang_id.date_format
            lines = []
            company_id = context.get('company_id') or self.env.user.company_id
            grouped_accounts = self.with_context(
                date_from_aml=context['date_from'],
                date_from=context['date_from'] and
                          company_id.compute_fiscalyear_dates(
                              datetime.strptime(
                                  context['date_from'],
                                  "%Y-%m-%d"))[
                              'date_from'] or None).group_by_account_id(
                line_id)  # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
            sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
            unfold_all = context.get('print_mode') and not \
                context['context_id']['unfolded_accounts']
            for account in sorted_accounts:
                debit = grouped_accounts[account]['debit']
                credit = grouped_accounts[account]['credit']
                balance = grouped_accounts[account]['balance']
                include = False
                amount_currency = '' if not account.currency_id else self._format(
                    grouped_accounts[account]['amount_currency'],
                    currency=account.currency_id)
                if context['balance'] == 'with_balance' and balance or \
                                        context[
                                            'balance'] == 'without_balance' and not balance or \
                                context['balance'] == 'all_balance':
                    include = True
                    lines.append({
                        'id': account.id,
                        'type': 'line',
                        'name': account.code + " " + account.name,
                        'footnotes': self.env.context[
                            'context_id']._get_footnotes('line',
                                                         account.id),
                        'columns': ['', amount_currency,
                                    self._format(debit),
                                    self._format(credit),
                                    self._format(balance)],
                        'level': 2,
                        'unfoldable': True,
                        'unfolded': account in context['context_id'][
                            'unfolded_accounts'] or unfold_all,
                        'colspan': 4,
                    })

                if include and (account in context['context_id'][
                    'unfolded_accounts'] or unfold_all):
                    initial_debit = grouped_accounts[account]['initial_bal'][
                        'debit']
                    initial_credit = grouped_accounts[account]['initial_bal'][
                        'credit']
                    initial_balance = grouped_accounts[account]['initial_bal'][
                        'balance']
                    initial_currency = '' if not account.currency_id else self._format(
                        grouped_accounts[account]['initial_bal'][
                            'amount_currency'], currency=account.currency_id)
                    domain_lines = []
                    if context['initial_balance'] and context[
                        'initial_balance'] == 'with_initial_balance':
                        domain_lines = [{
                            'id': account.id,
                            'type': 'initial_balance',
                            'name': _('Initial Balance'),
                            'footnotes': self.env.context[
                                'context_id']._get_footnotes('initial_balance',
                                                             account.id),
                            'columns': ['', '', '', '', initial_currency,
                                        self._format(initial_debit),
                                        self._format(initial_credit),
                                        self._format(initial_balance)],
                            'level': 1,
                        }]
                    progress = initial_balance
                    if context['initial_balance'] and context[
                        'initial_balance'] == 'without_initial_balance':
                        progress = 0.0
                    amls = amls_all = grouped_accounts[account]['lines']
                    too_many = False
                    if len(amls) > 80 and not context.get('print_mode'):
                        amls = amls[:80]
                        too_many = True
                    used_currency = self.env.user.company_id.currency_id
                    for line in amls:
                        if self.env.context['cash_basis']:
                            line_debit = line.debit_cash_basis
                            line_credit = line.credit_cash_basis
                        else:
                            line_debit = line.debit
                            line_credit = line.credit
                        line_debit = line.company_id.currency_id.compute(
                            line_debit, used_currency)
                        line_credit = line.company_id.currency_id.compute(
                            line_credit, used_currency)
                        progress = progress + line_debit - line_credit
                        currency = "" if not line.currency_id else self.with_context(
                            no_format=False)._format(
                            line.amount_currency, currency=line.currency_id)
                        name = []
                        name = line.name and line.name or ''
                        if line.ref:
                            name = name and name + ' - ' + line.ref or line.ref
                        if len(name) > 35 and not self.env.context.get(
                                'no_format'):
                            name = name[:32] + "..."
                        partner_name = line.partner_id and line.partner_id.name or ''
                        if partner_name and len(
                                partner_name) > 35 and not self.env.context.get(
                            'no_format'):
                            partner_name = partner_name[:32] + "..."
                        if line.payment_id or line.invoice_id:
                            display_name = line.payment_id and line.payment_id.display_name or line.invoice_id.display_name
                        else:
                            display_name = line.move_id.display_name
                        domain_lines.append({
                            'id': line.id,
                            'type': 'move_line_id',
                            'move_id': line.move_id.id,
                            'action': line.get_model_id_and_name(),
                            'name': line.move_id.name if line.move_id.name else '/',
                            'footnotes': self.env.context[
                                'context_id']._get_footnotes('move_line_id',
                                                             line.id),
                            'columns': [datetime.strptime(line.date,
                                                          DEFAULT_SERVER_DATE_FORMAT).strftime(
                                date_format),
                                display_name, name, partner_name,
                                currency,
                                line_debit != 0 and self._format(
                                    line_debit) or '',
                                line_credit != 0 and self._format(
                                    line_credit) or '',
                                self._format(progress)],
                            'level': 1,
                        })
                    domain_lines.append({
                        'id': account.id,
                        'type': 'o_account_reports_domain_total',
                        'name': _('Total '),
                        'footnotes': self.env.context[
                            'context_id']._get_footnotes(
                            'o_account_reports_domain_total',
                            account.id),
                        'columns': ['', '', '', '', amount_currency,
                                    self._format(debit), self._format(credit),
                                    self._format(balance)],
                        'level': 1,
                    })
                    if too_many:
                        domain_lines.append({
                            'id': account.id,
                            'domain': "[('id', 'in', %s)]" % amls_all.ids,
                            'type': 'too_many',
                            'name': _(
                                'There are more than 80 items in this list, click here to see all of them'),
                            'footnotes': {},
                            'colspan': 8,
                            'columns': [],
                            'level': 3,
                        })
                    lines += domain_lines

            if len(context['context_id'].journal_ids) == 1 and context[
                'context_id'].journal_ids.type in ['sale',
                                                   'purchase'] and not line_id:
                total = self._get_journal_total()
                if context['initial_balance'] and context[
                    'initial_balance'] == 'without_initial_balance':
                    total = self.with_context(date_from=context['date_from'],
                                              strict_range=True)._get_journal_total()
                lines.append({
                    'id': 0,
                    'type': 'total',
                    'name': _('Total'),
                    'footnotes': {},
                    'columns': ['', '', '', '', '',
                                self._format(total['debit']),
                                self._format(total['credit']),
                                self._format(total['balance'])],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': False,
                })
                lines.append({
                    'id': 0,
                    'type': 'line',
                    'name': _('Tax Declaration'),
                    'footnotes': {},
                    'columns': ['', '', '', '', '', '', '', ''],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': False,
                })
                lines.append({
                    'id': 0,
                    'type': 'line',
                    'name': _('Name'),
                    'footnotes': {},
                    'columns': ['', '', '', '', '', _('Base Amount'),
                                _('Tax Amount'), ''],
                    'level': 2,
                    'unfoldable': False,
                    'unfolded': False,
                })
                for tax, values in self._get_taxes().items():
                    lines.append({
                        'id': tax.id,
                        'name': tax.name + ' (' + str(tax.amount) + ')',
                        'type': 'tax_id',
                        'footnotes': self.env.context[
                            'context_id']._get_footnotes('tax_id', tax.id),
                        'unfoldable': False,
                        'columns': ['', '', '', '', '', values['base_amount'],
                                    values['tax_amount'], ''],
                        'level': 1,
                    })
        else:
            lines = self._tag_lines(line_id, analytic_tag_id)

        return lines

    @api.model
    def _tag_lines(self, line_id=None, analytic_tag_id=None):
        context = self.env.context
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        lines = []
        company_id = context.get('company_id') or self.env.user.company_id
        grouped_tag_accounts = self.with_context(
            date_from_aml=context['date_from'],
            date_from=context['date_from'] and
                      company_id.compute_fiscalyear_dates(
                          datetime.strptime(
                              context[
                                  'date_from'],
                              "%Y-%m-%d"))[
                          'date_from'] or None).group_by_tag_id(
            line_id,
            analytic_tag_id)  # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
        sorted_tag_accounts = sorted(grouped_tag_accounts, key=lambda a: a.id)
        unfold_all = context.get('print_mode') and not context['context_id'][
            'unfolded_accounts']
        for tag in sorted_tag_accounts:
            sorted_accounts = sorted(grouped_tag_accounts[tag],
                                     key=lambda a: a.code)
            has_balance = self.get_balace(tag, grouped_tag_accounts)
            if context['balance'] == 'with_balance' and has_balance or context[
                'balance'] == 'without_balance' and not has_balance or \
                            context['balance'] == 'all_balance':
                lines.append({
                    'id': tag.id,
                    'tag_id': tag.id,
                    'type': 'line',
                    'name': 'Analytic Tag: ' + tag.name,
                    'footnotes': {},
                    'columns': ['', '', '', '', ''],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': False,
                    'colspan': 4,
                })
            for account in sorted_accounts:
                debit = grouped_tag_accounts[tag][account]['debit']
                credit = grouped_tag_accounts[tag][account]['credit']
                balance = grouped_tag_accounts[tag][account]['balance']
                include = False
                amount_currency = '' if not account.currency_id else self._format(
                    grouped_tag_accounts[tag][account]['amount_currency'],
                    currency=account.currency_id)
                if context['balance'] == 'with_balance' and balance or context[
                    'balance'] == 'without_balance' and not balance or \
                                context['balance'] == 'all_balance':
                    include = True
                    lines.append({
                        'id': account.id,
                        'tag_id': tag.id,
                        'type': 'line',
                        'name': account.code + " " + account.name,
                        'footnotes': self.env.context[
                            'context_id']._get_footnotes('line', account.id),
                        'columns': ['', amount_currency, self._format(debit),
                                    self._format(credit),
                                    self._format(balance)],
                        'level': 2,
                        'unfoldable': True,
                        'unfolded': account in context['context_id'][
                            'unfolded_accounts'] or unfold_all,
                        'colspan': 4,
                    })

                if include and account in context['context_id'][
                    'unfolded_accounts'] or unfold_all:
                    initial_debit = \
                        grouped_tag_accounts[tag][account]['initial_bal'][
                            'debit']
                    initial_credit = \
                        grouped_tag_accounts[tag][account]['initial_bal'][
                            'credit']
                    initial_balance = \
                        grouped_tag_accounts[tag][account]['initial_bal'][
                            'balance']
                    initial_currency = '' if not account.currency_id else self._format(
                        grouped_tag_accounts[tag][account]['initial_bal'][
                            'amount_currency'], currency=account.currency_id)
                    domain_lines = []
                    if context['initial_balance'] and context[
                        'initial_balance'] == 'with_initial_balance':
                        domain_lines = [{
                            'id': account.id,
                            'tag_id': tag.id,
                            'type': 'initial_balance',
                            'name': _('Initial Balance'),
                            'footnotes': self.env.context[
                                'context_id']._get_footnotes('initial_balance',
                                                             account.id),
                            'columns': ['', '', '', '', initial_currency,
                                        self._format(initial_debit),
                                        self._format(initial_credit),
                                        self._format(initial_balance)],
                            'level': 1,
                        }]
                    progress = initial_balance
                    if context['initial_balance'] and context[
                        'initial_balance'] == 'without_initial_balance':
                        progress = 0.0
                    amls = amls_all = grouped_tag_accounts[tag][account][
                        'lines']
                    too_many = False
                    if len(amls) > 80 and not context.get('print_mode'):
                        amls = amls[:80]
                        too_many = True
                    used_currency = self.env.user.company_id.currency_id
                    for line in amls:
                        if self.env.context['cash_basis']:
                            line_debit = line.debit_cash_basis
                            line_credit = line.credit_cash_basis
                        else:
                            line_debit = line.debit
                            line_credit = line.credit
                        line_debit = line.company_id.currency_id.compute(
                            line_debit, used_currency)
                        line_credit = line.company_id.currency_id.compute(
                            line_credit, used_currency)
                        progress = progress + line_debit - line_credit
                        currency = "" if not line.currency_id else self.with_context(
                            no_format=False)._format(
                            line.amount_currency, currency=line.currency_id)
                        name = []
                        name = line.name and line.name or ''
                        if line.ref:
                            name = name and name + ' - ' + line.ref or line.ref
                        if len(name) > 35 and not self.env.context.get(
                                'no_format'):
                            name = name[:32] + "..."
                        partner_name = line.partner_id and line.partner_id.name or ''
                        if partner_name and len(
                                partner_name) > 35 and not self.env.context.get(
                            'no_format'):
                            partner_name = partner_name[:32] + "..."
                        if line.payment_id or line.invoice_id:
                            display_name = line.payment_id and line.payment_id.display_name or line.invoice_id.display_name
                        else:
                            display_name = line.move_id.display_name
                        domain_lines.append({
                            'id': line.id,
                            'tag_id': tag.id,
                            'type': 'move_line_id',
                            'move_id': line.move_id.id,
                            'action': line.get_model_id_and_name(),
                            'name': line.move_id.name if line.move_id.name else '/',
                            'footnotes': self.env.context[
                                'context_id']._get_footnotes('move_line_id',
                                                             line.id),
                            'columns': [
                                datetime.strptime(line.date,
                                                  DEFAULT_SERVER_DATE_FORMAT).strftime(
                                    date_format),
                                display_name, name, partner_name, currency,
                                line_debit != 0 and self._format(
                                    line_debit) or '',
                                line_credit != 0 and self._format(
                                    line_credit) or '',
                                self._format(progress)],
                            'level': 1,
                        })
                    domain_lines.append({
                        'id': account.id,
                        'tag_id': tag.id,
                        'type': 'o_account_reports_domain_total',
                        'name': _('Total '),
                        'footnotes': self.env.context[
                            'context_id']._get_footnotes(
                            'o_account_reports_domain_total',
                            account.id),
                        'columns': ['', '', '', '', amount_currency,
                                    self._format(debit), self._format(credit),
                                    self._format(balance)],
                        'level': 1,
                    })
                    if too_many:
                        domain_lines.append({
                            'id': account.id,
                            'tag_id': tag.id,
                            'domain': "[('id', 'in', %s)]" % amls_all.ids,
                            'type': 'too_many',
                            'name': _(
                                'There are more than 80 items in this list, click here to see all of them'),
                            'footnotes': {},
                            'colspan': 8,
                            'columns': [],
                            'level': 3,
                        })
                    lines += domain_lines

        if len(context['context_id'].journal_ids) == 1 and context[
            'context_id'].journal_ids.type in ['sale',
                                               'purchase'] and not line_id:
            total = self._get_journal_total()
            if context['initial_balance'] and context[
                'initial_balance'] == 'without_initial_balance':
                total = self.with_context(date_from=context['date_from'],
                                          strict_range=True)._get_journal_total()
            lines.append({
                'id': 0,
                'type': 'total',
                'name': _('Total'),
                'footnotes': {},
                'columns': ['', '', '', '', '', self._format(total['debit']),
                            self._format(total['credit']),
                            self._format(total['balance'])],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
            lines.append({
                'id': 0,
                'type': 'line',
                'name': _('Tax Declaration'),
                'footnotes': {},
                'columns': ['', '', '', '', '', '', '', ''],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
            lines.append({
                'id': 0,
                'type': 'line',
                'name': _('Name'),
                'footnotes': {},
                'columns': ['', '', '', '', '', _('Base Amount'),
                            _('Tax Amount'), ''],
                'level': 2,
                'unfoldable': False,
                'unfolded': False,
            })
            for tax, values in self._get_taxes().items():
                lines.append({
                    'id': tax.id,
                    'name': tax.name + ' (' + str(tax.amount) + ')',
                    'type': 'tax_id',
                    'footnotes': self.env.context['context_id']._get_footnotes(
                        'tax_id', tax.id),
                    'unfoldable': False,
                    'columns': ['', '', '', '', '', values['base_amount'],
                                values['tax_amount'], ''],
                    'level': 1,
                })
        return lines

    def get_balace(self, tag, grouped_tag_accounts):
        return filter(lambda x: not (not x['balance']),
                      grouped_tag_accounts[tag].values())

    @api.model
    def get_title(self):
        return _("Detailed General Ledger")

    @api.model
    def get_name(self):
        return 'detailed_general_ledger'

    @api.model
    def get_report_type(self):
        return self.env.ref(
            'detailed_general_ledger_report.account_report_type_detail_general_ledger')

    def get_template(self):
        return 'account_reports.report_financial'
        # return 'detailed_general_ledger_report.report_financial_detailed'


class account_context_general_ledger(models.TransientModel):
    _name = "account.context.detail.general.ledger"
    _description = "A particular context for the general ledger"
    _inherit = "account.report.context.common"

    fold_field = 'unfolded_accounts'
    unfolded_accounts = fields.Many2many('account.account',
                                         'context_to_account_dgl',
                                         string='Unfolded lines')
    journal_ids = fields.Many2many('account.journal',
                                   relation='account_report_dgl_journals')
    available_journal_ids = fields.Many2many('account.journal',
                                             relation='account_report_dgl_available_journal',
                                             default=lambda s: [(6, 0, s.env[
                                                 'account.journal'].search(
                                                 []).ids)])

    @api.multi
    def get_available_journal_ids_names_and_codes(self):
        return [[c.id, c.name, c.code] for c in self.available_journal_ids]

    @api.model
    def get_available_journals(self):
        return self.env.user.journal_ids

    def get_report_obj(self):
        return self.env['account.detail.general.ledger']

    def get_columns_names(self):
        return [_("Date"), _("Document"), _("Communication"), _("Partner"),
                _("Currency"), _("Debit"), _("Credit"), _("Balance")]

    @api.multi
    def get_columns_types(self):
        return ["date", "text", "text", "text", "number", "number", "number",
                "number"]
