from odoo import http, models, fields, api, _
from cStringIO import StringIO
import base64
import xlwt
from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

class CustomerOutstandingStatementWizard2(models.TransientModel):
    _name = "customer.outstanding.statement.wizard2"
    _inherit = "customer.outstanding.statement.wizard"

    type = fields.Selection([('customer','customer'),('supplier','supplier')])
    print_by = fields.Selection([('html','HTML'),('pdf','PDF'),('excel','Export xlsx')],
                                string="Printing Options",default="html",required=True)
    number_partner_ids = fields.Integer(default=0)
    c_partner_ids = fields.Many2many('res.partner', string="Customers", translate=True, domain="[('customer', '=', True)]")
    p_partner_ids = fields.Many2many('res.partner', string="Suppliers", translate=True, domain="[('supplier', '=', True)]")


    def doit(self):
        if self.type == 'customer':
            ids = self.c_partner_ids._ids
            if not ids:
                ids = self.env['res.partner'].search([('customer', '=', True)])._ids
        if self.type == 'supplier':
            ids = self.p_partner_ids._ids
            if not ids:
                ids = self.env['res.partner'].search([('supplier', '=', True)])._ids

        datas = {
            'date_end': self.date_end,
            'company_id': self.company_id.id,
            'partner_ids': ids,
            'show_aging_buckets': self.show_aging_buckets,
            'filter_non_due_partners': self.filter_partners_non_due,
            'docs': ids,
            'type': self.type,
        }
        if self.print_by in ('html','pdf'):
            if self.print_by == 'pdf':
                return self.env['report'].with_context(landscape=True).get_action(self,'customer_outstanding_statement.statement', data=datas)
            if self.print_by == 'html':
                return self.env['report'].with_context(landscape=True).get_action(self,'vitt_customer_outstanding_statement.statement', data=datas)

        if self.print_by == 'excel':
            data = datas
            company_id = data['company_id']
            partner_ids = data['partner_ids']
            date_end = data['date_end']
            today = fields.Date.today()

            buckets_to_display = {}
            lines_to_display, amount_due = {}, {}
            currency_to_display = {}
            today_display, date_end_display = {}, {}

            rep_obj = self.env['report.customer_outstanding_statement.statement']
            lines = rep_obj._get_account_display_lines(
                company_id, partner_ids, date_end, supplier=(self.type == 'supplier'))

            for partner_id in partner_ids:
                lines_to_display[partner_id], amount_due[partner_id] = {}, {}
                currency_to_display[partner_id] = {}
                today_display[partner_id] = rep_obj._format_date_to_partner_lang(
                    today, partner_id)
                date_end_display[partner_id] = rep_obj._format_date_to_partner_lang(
                    date_end, partner_id)
                for line in lines[partner_id]:
                    currency = self.env['res.currency'].browse(line['currency_id'])
                    if currency not in lines_to_display[partner_id]:
                        lines_to_display[partner_id][currency] = []
                        currency_to_display[partner_id][currency] = currency
                        amount_due[partner_id][currency] = 0.0
                    if not line['blocked']:
                        amount_due[partner_id][currency] += line['open_amount']
                    line['balance'] = amount_due[partner_id][currency]
                    line['date'] = rep_obj._format_date_to_partner_lang(line['date'], partner_id)
                    line['date_maturity'] = rep_obj._format_date_to_partner_lang(line['date_maturity'], partner_id)

                    # NEW
                    move = self.env['account.move'].search([('name', '=', line['move_id'])])
                    if move.origin_document:
                        line['move_id'] = move.origin_document

                    lines_to_display[partner_id][currency].append(line)

            if data['show_aging_buckets']:
                buckets = rep_obj._get_account_show_buckets(
                    company_id, partner_ids, date_end, supplier=(self.type == 'supplier'))
                for partner_id in partner_ids:
                    buckets_to_display[partner_id] = {}
                    for line in buckets[partner_id]:
                        currency = self.env['res.currency'].browse(
                            line['currency_id'])
                        if currency not in buckets_to_display[partner_id]:
                            buckets_to_display[partner_id][currency] = []
                        buckets_to_display[partner_id][currency] = line

            docargs = {
                'doc_ids': partner_ids,
                'doc_model': 'res.partner',
                'docs': self.env['res.partner'].browse(partner_ids),
                'Amount_Due': amount_due,
                'Lines': lines_to_display,
                'Buckets': buckets_to_display,
                'Currencies': currency_to_display,
                'Show_Buckets': data['show_aging_buckets'],
                'Filter_non_due_partners': data['filter_non_due_partners'],
                'Date_end': date_end_display,
                'Date': today_display,
            }

            context = self._context
            filename = 'Outstanding_report.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            worksheet = workbook.add_sheet('Detalle')
            line = row = 0
            for partner in docargs['docs']:
                if len(docargs['Lines'][partner.id]) > 0:
                    worksheet.write(line, row, _('Partner'))
                    row += 1
                    worksheet.write(line, row, partner.name)


                    for currency in docargs['Lines'][partner.id]:
                        line += 1
                        row = 0
                        worksheet.write(line, row, _('Reference number'))
                        row += 1
                        worksheet.write(line, row, _('Date'))
                        row += 1
                        worksheet.write(line, row, _('Due Date'))
                        row += 1
                        worksheet.write(line, row, _('Description'))
                        row += 1
                        worksheet.write(line, row, _('Original Amount'))
                        row += 1
                        worksheet.write(line, row, _('Open Amount'))
                        row += 1
                        worksheet.write(line, row, _('Balance'))
                        line += 1
                        row = 0
                        for line_doc in docargs['Lines'][partner.id][currency]:
                            worksheet.write(line, row, line_doc['move_id'])
                            row += 1
                            worksheet.write(line, row, line_doc['date'])
                            row += 1
                            worksheet.write(line, row, line_doc['date_maturity'])
                            row += 1
                            tmp = ""
                            if line_doc['name'] != '/':
                                if not line_doc['ref']:
                                    tmp = line_doc['name']
                                if line_doc['name'] and line_doc['ref']:
                                    if line_doc['name'] not in line_doc['ref']:
                                        tmp = line_doc['name']
                                    if line_doc['ref'] not in line_doc['name']:
                                        tmp = line_doc['ref']
                            else:
                                tmp = line_doc['ref']
                            worksheet.write(line, row, tmp)
                            row += 1
                            worksheet.write(line, row, line_doc['amount'])
                            row += 1
                            worksheet.write(line, row, line_doc['open_amount'])
                            row += 1
                            worksheet.write(line, row, line_doc['balance'])
                            row = 0
                            line += 1
                        line += 2
                        row = 0
                        worksheet.write(line, row, _('aging report at ') + docargs['Date_end'][partner.id] + ' in '
                                        + docargs['Currencies'][partner.id][currency].name)
                        line += 1
                        row  = 0
                        worksheet.write(line, row, _('Current Due'))
                        row  += 1
                        worksheet.write(line, row, _('1-30 Days Due'))
                        row  += 1
                        worksheet.write(line, row, _('30-60 Days Due'))
                        row  += 1
                        worksheet.write(line, row, _('60-90 Days Due'))
                        row  += 1
                        worksheet.write(line, row, _('90-120 Days Due'))
                        row  += 1
                        worksheet.write(line, row, _('+120 Days Due'))
                        row  += 1
                        worksheet.write(line, row, _('Balance'))

                        line += 1
                        row = 0
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['current'])
                        row  += 1
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['b_1_30'])
                        row  += 1
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['b_30_60'])
                        row  += 1
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['b_60_90'])
                        row  += 1
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['b_90_120'])
                        row  += 1
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['b_over_120'])
                        row  += 1
                        worksheet.write(line, row, docargs['Buckets'][partner.id][currency]['balance'])
                        line += 2
                        row = 0



            fp = StringIO()
            workbook.save(fp)
            export_id = self.env['excel.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename }).id
            fp.close()
            return{
                'view_mode': 'form',
                'res_id': export_id,
                'res_model': 'excel.extended',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }





class CustomerOutstandingStatement(models.AbstractModel):
    _name = 'report.vitt_customer_outstanding_statement.statement'
    _inherit = 'report.customer_outstanding_statement.statement'

class CustomerOutstandingStatement2(models.AbstractModel):
    """Model of Customer Outstanding Statement"""

    _inherit = 'report.customer_outstanding_statement.statement'

    @api.multi
    def render_html(self, docids, data):
        company_id = data['company_id']
        partner_ids = data['partner_ids']
        date_end = data['date_end']
        today = fields.Date.today()

        buckets_to_display = {}
        lines_to_display, amount_due = {}, {}
        currency_to_display = {}
        today_display, date_end_display = {}, {}

        lines = self._get_account_display_lines(
            company_id, partner_ids, date_end, supplier=(data['type'] == 'supplier'))

        for partner_id in partner_ids:
            lines_to_display[partner_id], amount_due[partner_id] = {}, {}
            currency_to_display[partner_id] = {}
            today_display[partner_id] = self._format_date_to_partner_lang(
                today, partner_id)
            date_end_display[partner_id] = self._format_date_to_partner_lang(
                date_end, partner_id)
            for line in lines[partner_id]:
                currency = self.env['res.currency'].browse(line['currency_id'])
                if currency not in lines_to_display[partner_id]:
                    lines_to_display[partner_id][currency] = []
                    currency_to_display[partner_id][currency] = currency
                    amount_due[partner_id][currency] = 0.0
                if not line['blocked']:
                    amount_due[partner_id][currency] += line['open_amount']
                line['balance'] = amount_due[partner_id][currency]
                line['date'] = self._format_date_to_partner_lang(line['date'], partner_id)
                line['date_maturity'] = self._format_date_to_partner_lang(line['date_maturity'], partner_id)

                #NEW
                move = self.env['account.move'].search([('name', '=', line['move_id'])])
                if move.origin_document:
                        line['move_id'] = move.origin_document


                lines_to_display[partner_id][currency].append(line)

        if data['show_aging_buckets']:
            buckets = self._get_account_show_buckets(
                company_id, partner_ids, date_end, supplier=(data['type'] == 'supplier'))
            for partner_id in partner_ids:
                buckets_to_display[partner_id] = {}
                for line in buckets[partner_id]:
                    currency = self.env['res.currency'].browse(
                        line['currency_id'])
                    if currency not in buckets_to_display[partner_id]:
                        buckets_to_display[partner_id][currency] = []
                    buckets_to_display[partner_id][currency] = line

        docargs = {
            'doc_ids': partner_ids,
            'doc_model': 'res.partner',
            'docs': self.env['res.partner'].browse(partner_ids),
            'Amount_Due': amount_due,
            'Lines': lines_to_display,
            'Buckets': buckets_to_display,
            'Currencies': currency_to_display,
            'Show_Buckets': data['show_aging_buckets'],
            'Filter_non_due_partners': data['filter_non_due_partners'],
            'Date_end': date_end_display,
            'Date': today_display,
        }
        return self.env['report'].render(
            'customer_outstanding_statement.statement', values=docargs)

    def _display_lines_sql_q1(self, partners, date_end, supplier):
        if not supplier:
            return """
                SELECT m.name as move_id, l.partner_id, l.date, l.name,
                                l.ref, l.blocked, l.currency_id, l.company_id,
                CASE WHEN (l.currency_id is not null AND l.amount_currency > 0.0)
                    THEN avg(l.amount_currency)
                    ELSE avg(l.debit)
                END as debit,
                CASE WHEN (l.currency_id is not null AND l.amount_currency < 0.0)
                    THEN avg(l.amount_currency * (-1))
                    ELSE avg(l.credit)
                END as credit,
                CASE WHEN l.balance > 0.0
                    THEN l.balance - sum(coalesce(pd.amount, 0.0))
                    ELSE l.balance + sum(coalesce(pc.amount, 0.0))
                END AS open_amount,
                CASE WHEN l.balance > 0.0
                    THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
                    ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
                END AS open_amount_currency,
                CASE WHEN l.date_maturity is null
                    THEN l.date
                    ELSE l.date_maturity
                END as date_maturity
                FROM account_move_line l
                JOIN account_account_type at ON (at.id = l.user_type_id)
                JOIN account_move m ON (l.move_id = m.id)
                LEFT JOIN Q0 ON Q0.id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.credit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pd ON pd.debit_move_id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.debit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pc ON pc.credit_move_id = l.id
                WHERE l.partner_id IN (%s) AND at.type = 'receivable'
                                    AND (Q0.reconciled_date is null or
                                        Q0.reconciled_date > '%s')
                                    AND l.date <= '%s'
                GROUP BY l.partner_id, m.name, l.date, l.date_maturity, l.name,
                                    l.ref, l.blocked, l.currency_id,
                                    l.balance, l.amount_currency, l.company_id
            """ % (date_end, date_end, partners, date_end, date_end)
        else:
            return """
                SELECT m.name as move_id, l.partner_id, l.date, l.name,
                                l.ref, l.blocked, l.currency_id, l.company_id,
                CASE WHEN (l.currency_id is not null AND l.amount_currency > 0.0)
                    THEN avg(l.amount_currency)
                    ELSE avg(l.debit)
                END as debit,
                CASE WHEN (l.currency_id is not null AND l.amount_currency < 0.0)
                    THEN avg(l.amount_currency * (-1))
                    ELSE avg(l.credit)
                END as credit,
                CASE WHEN l.balance > 0.0
                    THEN l.balance - sum(coalesce(pd.amount, 0.0))
                    ELSE l.balance + sum(coalesce(pc.amount, 0.0))
                END AS open_amount,
                CASE WHEN l.balance > 0.0
                    THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
                    ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
                END AS open_amount_currency,
                CASE WHEN l.date_maturity is null
                    THEN l.date
                    ELSE l.date_maturity
                END as date_maturity
                FROM account_move_line l
                JOIN account_account_type at ON (at.id = l.user_type_id)
                JOIN account_move m ON (l.move_id = m.id)
                LEFT JOIN Q0 ON Q0.id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.credit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pd ON pd.debit_move_id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.debit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pc ON pc.credit_move_id = l.id
                WHERE l.partner_id IN (%s) AND at.type = 'payable'
                                    AND (Q0.reconciled_date is null or
                                        Q0.reconciled_date > '%s')
                                    AND l.date <= '%s'
                GROUP BY l.partner_id, m.name, l.date, l.date_maturity, l.name,
                                    l.ref, l.blocked, l.currency_id,
                                    l.balance, l.amount_currency, l.company_id
            """ % (date_end, date_end, partners, date_end, date_end)


    def _show_buckets_sql_q1(self, partners, date_end, supplier=False):
        if not supplier:
            return """
                SELECT l.partner_id, l.currency_id, l.company_id, l.move_id,
                CASE WHEN l.balance > 0.0
                    THEN l.balance - sum(coalesce(pd.amount, 0.0))
                    ELSE l.balance + sum(coalesce(pc.amount, 0.0))
                END AS open_due,
                CASE WHEN l.balance > 0.0
                    THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
                    ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
                END AS open_due_currency,
                CASE WHEN l.date_maturity is null
                    THEN l.date
                    ELSE l.date_maturity
                END as date_maturity
                FROM account_move_line l
                JOIN account_account_type at ON (at.id = l.user_type_id)
                JOIN account_move m ON (l.move_id = m.id)
                LEFT JOIN Q0 ON Q0.id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.credit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pd ON pd.debit_move_id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.debit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pc ON pc.credit_move_id = l.id
                WHERE l.partner_id IN (%s) AND at.type = 'receivable'
                                    AND (Q0.reconciled_date is null or
                                        Q0.reconciled_date > '%s')
                                    AND l.date <= '%s' AND not l.blocked
                GROUP BY l.partner_id, l.currency_id, l.date, l.date_maturity,
                                    l.amount_currency, l.balance, l.move_id,
                                    l.company_id
            """ % (date_end, date_end, partners, date_end, date_end)
        else:
            return """
                SELECT l.partner_id, l.currency_id, l.company_id, l.move_id,
                CASE WHEN l.balance > 0.0
                    THEN l.balance - sum(coalesce(pd.amount, 0.0))
                    ELSE l.balance + sum(coalesce(pc.amount, 0.0))
                END AS open_due,
                CASE WHEN l.balance > 0.0
                    THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
                    ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
                END AS open_due_currency,
                CASE WHEN l.date_maturity is null
                    THEN l.date
                    ELSE l.date_maturity
                END as date_maturity
                FROM account_move_line l
                JOIN account_account_type at ON (at.id = l.user_type_id)
                JOIN account_move m ON (l.move_id = m.id)
                LEFT JOIN Q0 ON Q0.id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.credit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pd ON pd.debit_move_id = l.id
                LEFT JOIN (SELECT pr.*
                    FROM account_partial_reconcile pr
                    INNER JOIN account_move_line l2
                    ON pr.debit_move_id = l2.id
                    WHERE l2.date <= '%s'
                ) as pc ON pc.credit_move_id = l.id
                WHERE l.partner_id IN (%s) AND at.type = 'payable'
                                    AND (Q0.reconciled_date is null or
                                        Q0.reconciled_date > '%s')
                                    AND l.date <= '%s' AND not l.blocked
                GROUP BY l.partner_id, l.currency_id, l.date, l.date_maturity,
                                    l.amount_currency, l.balance, l.move_id,
                                    l.company_id
            """ % (date_end, date_end, partners, date_end, date_end)

    def _get_account_show_buckets(self, company_id, partner_ids, date_end, supplier=False):
        res = dict(map(lambda x: (x, []), partner_ids))
        partners = ', '.join([str(i) for i in partner_ids])
        date_end = datetime.strptime(
            date_end, DEFAULT_SERVER_DATE_FORMAT).date()
        full_dates = self._get_bucket_dates(date_end)
        # pylint: disable=E8103
        self.env.cr.execute("""
        WITH Q0 AS (%s), Q1 AS (%s), Q2 AS (%s), Q3 AS (%s), Q4 AS (%s)
        SELECT partner_id, currency_id, current, b_1_30, b_30_60, b_60_90,
                            b_90_120, b_over_120,
                            current+b_1_30+b_30_60+b_60_90+b_90_120+b_over_120
                            AS balance
        FROM Q4
        GROUP BY partner_id, currency_id, current, b_1_30, b_30_60, b_60_90,
        b_90_120, b_over_120""" % (
            self._show_buckets_sql_q0(date_end),
            self._show_buckets_sql_q1(partners, date_end, supplier),
            self._show_buckets_sql_q2(
                full_dates['date_end'],
                full_dates['minus_30'],
                full_dates['minus_60'],
                full_dates['minus_90'],
                full_dates['minus_120']),
            self._show_buckets_sql_q3(company_id),
            self._show_buckets_sql_q4()))
        for row in self.env.cr.dictfetchall():
            res[row.pop('partner_id')].append(row)
        return res

    def _get_account_display_lines(self, company_id, partner_ids, date_end, supplier=False):
        res = dict(map(lambda x: (x, []), partner_ids))
        partners = ', '.join([str(i) for i in partner_ids])
        date_end = datetime.strptime(
            date_end, DEFAULT_SERVER_DATE_FORMAT).date()
        # pylint: disable=E8103
        self.env.cr.execute("""
        WITH Q0 as (%s), Q1 AS (%s), Q2 AS (%s), Q3 AS (%s)
        SELECT partner_id, currency_id, move_id, date, date_maturity, debit,
                            credit, amount, open_amount, name, ref, blocked
        FROM Q3
        ORDER BY date, date_maturity, move_id""" % (
            self._display_lines_sql_q0(date_end),
            self._display_lines_sql_q1(partners, date_end, supplier),
            self._display_lines_sql_q2(),
            self._display_lines_sql_q3(company_id)))
        for row in self.env.cr.dictfetchall():
            res[row.pop('partner_id')].append(row)
        return res
