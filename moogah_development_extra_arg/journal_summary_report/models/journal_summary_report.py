# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import calendar
import StringIO
import xlsxwriter
from odoo.tools import config

month_list = [
    (1, _('January')),
    (2, _('February')),
    (3, _('March')),
    (4, _('April')),
    (5, _('May')),
    (6, _('June')),
    (7, _('July')),
    (8, _('August')),
    (9, _('September')),
    (10, _('October')),
    (11, _('November')),
    (12, _('December')),
]


class JournalSummaryReport(models.AbstractModel):
    _name = "journal.summary.report"
    _description = "Journal Summary Report"

    def _formatted(self, value, digit):
        formatted = ('%.' + str(digit) + 'f') % value
        return formatted


    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['journal.summary.context.report'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'state': context_id.all_entries and 'all' or 'posted',
            'cash_basis': context_id.cash_basis,
            'context_id': context_id,
            'company_ids': context_id.company_ids.ids,
            'legal_no': context_id.legal_no,
            'customer_invoices': context_id.customer_invoices,
            'vendor_invoices': context_id.vendor_invoices,
            'supplier_payments': context_id.supplier_payments,
            'customer_receipts': context_id.customer_receipts,
            'sort_by': context_id.sort_by,
            'show_reg_number': context_id.show_reg_number,
        })
        if new_context.get('xlsx_format'):
            res = self.with_context(new_context)._xlsx_lines(line_id)
        else:
            res = self.with_context(new_context)._lines(line_id)
        return res

    @api.model
    def _lines(self, line_id=None):
        ctx = self._context
        lines = []
        summary_section = []
        lang = self.env['res.lang']._lang_get(ctx.get('lang') or 'en_US')
        domain = [('date', '>=', ctx.get('date_from')), ('date', '<=', ctx.get('date_to'))]

        start_date = datetime.strptime(ctx.get('date_from'), '%Y-%m-%d')
        end_date = datetime.strptime(ctx.get('date_to'), '%Y-%m-%d')

        if start_date.month != end_date.month:
            month = start_date.month
            while month <= end_date.month:
                initial_date = start_date.replace(month=month)
                if initial_date.month == start_date.month:
                    final_date = initial_date.replace(month=month, day=1).replace(
                        day=calendar.monthrange(initial_date.year, initial_date.month)[1])
                elif initial_date.month != end_date.month:
                    initial_date = initial_date.replace(day=1)
                    final_date = initial_date.replace(
                        day=calendar.monthrange(initial_date.year, initial_date.month)[1])
                else:
                    initial_date = initial_date.replace(day=1)
                    final_date = end_date

                self.get_summary_section(ctx, summary_section,
                                         initial_date.strftime('%Y-%m-%d'), final_date.strftime('%Y-%m-%d'), month, lang,
                                         final_date.month)
                month += 1
        else:
            self.get_summary_section(ctx, summary_section, ctx.get('date_from'),
                                     ctx.get('date_to'), start_date.month, lang)

        account_moves = self.env['account.move'].search(domain)
        if summary_section:
            account_moves = account_moves.filtered(
                lambda m: filter(lambda n: m.id not in n['move_lines'].ids, summary_section))
        if ctx.get('sort_by') in ['date', 'monthly']:
            sorted_account_moves = account_moves.sorted(key=lambda r: r.date)
        else:
            sorted_account_moves = account_moves.sorted(key=lambda r: r.name)

        number = ctx.get('legal_no', False) and ctx.get('legal_no') or 1

        for move in sorted_account_moves:
            if ctx.get('sort_by') == 'monthly' and summary_section:
                lines, number = self.get_summary_section_move_line('html',summary_section, lines, ctx.get('sort_by'), number, move)

            move_month = datetime.strptime(move.date, '%Y-%m-%d').month
            name = move.display_name if ctx.get('show_reg_number') else ''
            lines.append({
                'id': move.id,
                'type': 'line',
                'name': " " + str(number),
                'footnotes': self.env.context['context_id']._get_footnotes('line', move.id),
                'columns': [str(number), datetime.strptime(move.date, '%Y-%m-%d').strftime(lang.date_format),
                            name, '', ''],
                'level': 2,
                'unfoldable': False,
                'month': move_month,
            })
            lines = self.get_account_move_line('html', move, lines, move_month, lang)
            number += 1
            if move == sorted_account_moves[-1] and ctx.get('sort_by') == 'monthly':
                lines, number = self.get_summary_section_move_line('html', summary_section, lines, ctx.get('sort_by'),
                                                                   number, move,
                                                                   sorted_account_moves[-1])
        if ctx.get('sort_by') in ['date', 'number'] and summary_section:
            lines, number = self.get_summary_section_move_line('html',summary_section, lines, ctx.get('sort_by'), number)

        return lines

    @api.model
    def _xlsx_lines(self, line_id=None):
        ctx = self._context
        lines = []
        summary_section = []
        lang = self.env['res.lang']._lang_get(ctx.get('lang') or 'en_US')
        domain = [('date', '>=', ctx.get('date_from')), ('date', '<=', ctx.get('date_to'))]
        start_date = datetime.strptime(ctx.get('date_from'), '%Y-%m-%d')
        end_date = datetime.strptime(ctx.get('date_to'), '%Y-%m-%d')

        if start_date.month != end_date.month:
            month = start_date.month
            while month <= end_date.month:
                initial_date = start_date.replace(month=month)
                if initial_date.month == start_date.month:
                    final_date = initial_date.replace(month=month, day=1).replace(
                        day=calendar.monthrange(initial_date.year, initial_date.month)[1])
                elif initial_date.month != end_date.month:
                    initial_date = initial_date.replace(day=1)
                    final_date = initial_date.replace(
                        day=calendar.monthrange(initial_date.year, initial_date.month)[1])
                else:
                    initial_date = initial_date.replace(day=1)
                    final_date = end_date

                self.get_summary_section(ctx, summary_section,
                                         initial_date.strftime('%Y-%m-%d'), final_date.strftime('%Y-%m-%d'), month, lang,
                                         final_date.month)
                month += 1
        else:
            self.get_summary_section(ctx, summary_section, ctx.get('date_from'), ctx.get('date_to'), start_date.month, lang)

        account_moves = self.env['account.move'].search(domain)
        if summary_section:
            account_moves = account_moves.filtered(
                lambda m: filter(lambda n: m.id not in n['move_lines'].ids, summary_section))
        if ctx.get('sort_by') in ['date', 'monthly']:
            sorted_account_moves = account_moves.sorted(key=lambda r: r.date)
        else:
            sorted_account_moves = account_moves.sorted(key=lambda r: r.name)

        number = ctx.get('legal_no', False) and ctx.get('legal_no') or 1
        for move in sorted_account_moves:
            if ctx.get('sort_by') == 'monthly' and summary_section:
                lines, number = self.get_summary_section_move_line('xlsx',summary_section, lines, ctx.get('sort_by'), number, move)

            ref = move.display_name
            if ref != '/':
                if len(move.display_name.split('/')) > 1:
                    ref = move.display_name.split('/')[0]
                else:
                    if move.document_type_id and move.document_type_id.doc_code_prefix \
                            and move.document_number:
                        ref = move.document_type_id.doc_code_prefix

            move_month = datetime.strptime(move.date, '%Y-%m-%d').month

            lines = self.get_account_move_line('xlsx', move, lines, move_month, lang, number, ref)
            number += 1
            if move == sorted_account_moves[-1] and ctx.get('sort_by') == 'monthly':
                lines, number = self.get_summary_section_move_line('xlsx', summary_section, lines, ctx.get('sort_by'),
                                                                   number, move,
                                                                   sorted_account_moves[-1])

        if ctx.get('sort_by') in ['date', 'number'] and summary_section:
            lines, number = self.get_summary_section_move_line('xlsx',summary_section, lines, ctx.get('sort_by'), number)


        return lines

    def get_summary_section(self, ctx, summary_section, start_date, end_date, month, lang, end_month=None):
        date = datetime.strptime(end_date, '%Y-%m-%d').strftime(lang.date_format)
        if end_month != None and month == end_month:
            date_convert = datetime.strptime(start_date, '%Y-%m-%d')
            date = date_convert.replace(day=calendar.monthrange(date_convert.year, date_convert.month)[1]).strftime(lang.date_format)
        if ctx.get('customer_invoices'):
            customer_invoices_move_ids = self.get_account_invoices_move_ids(start_date, end_date, 'sale')
            if customer_invoices_move_ids:
                summary_section.append({
                    'type': 'customer_invoices',
                    'month': month,
                    'date': date,
                    'move_lines': customer_invoices_move_ids
                })

        if ctx.get('vendor_invoices'):
            vendor_invoices_move_ids = self.get_account_invoices_move_ids(start_date, end_date, 'purchase')
            if vendor_invoices_move_ids:
                summary_section.append({
                    'type': 'vendor_invoices',
                    'month': month,
                    'date': date,
                    'move_lines': vendor_invoices_move_ids
                })

        if ctx.get('customer_receipts'):
            customer_receipts_move_ids = self.get_account_payment_group_move_ids(start_date, end_date,
                                                                                 ['inbound_payment_voucher',
                                                                                  'customer_payment'])
            if customer_receipts_move_ids:
                summary_section.append({
                    'type': 'customer_receipts',
                    'month': month,
                    'date': date,
                    'move_lines': customer_receipts_move_ids.mapped('move_id')
                })

        if ctx.get('supplier_payments'):
            supplier_payments_move_ids = self.get_account_payment_group_move_ids(start_date, end_date,
                                                                             ['outbound_payment_voucher',
                                                                              'supplier_payment'])
            if supplier_payments_move_ids:
                summary_section.append({
                    'type': 'supplier_payments',
                    'month': month,
                    'date': date,
                    'move_lines': supplier_payments_move_ids.mapped('move_id')
                })

    def get_account_move_line(self, type, line, lines, month, lang, number=None, ref=None):
        move_line = self.env['account.move.line'].search([
            ('move_id', '=', line.id)])
        accounts = move_line.mapped('account_id')
        for account in accounts:
            filter_move_line = move_line.filtered(lambda l: l.account_id.id == account.id)
            if type == 'html':
                columns = [account.code, '', account.name, str(self._formatted(sum(filter_move_line.mapped('debit')), 2)),
                            str(self._formatted(sum(filter_move_line.mapped('credit')), 2))]
            else:
                columns = [str(number) if number != None else '',
                           datetime.strptime(line.date, '%Y-%m-%d').strftime(lang.date_format), line.display_name,
                           ref if ref != None else '', account.code, account.name,
                           str(self._formatted(sum(filter_move_line.mapped('debit')), 2)),
                           str(self._formatted(sum(filter_move_line.mapped('credit')), 2))]
            lines.append({
                'id': account.id,
                'type': 'line',
                'unfoldable': False,
                'name': account.code,
                'footnotes': self.env.context['context_id']._get_footnotes('line', account.id),
                'columns': columns,
                'level': 1,
                'month': month,
            })

        return lines

    def get_account_invoices_move_ids(self, start_date, end_date, type):
        # TODO: Probar con consulta a la BD..
        account_move_line = self.env['account.move.line'].search(
            [('invoice_id', '!=', False),
                ('invoice_id.journal_id.type', '=', type),
                ('move_id.date', '>=', start_date),
                ('move_id.date', '<=', end_date),
             ('move_id.document_type_id.internal_type', 'in',
              ['invoice', 'debit_note', 'credit_note', 'ticket'])])
        if account_move_line:
            return account_move_line.mapped('move_id')
        return []


    def get_account_payment_group_move_ids(self, start_date, end_date, internal_types):
        #TODO: Probar con una consulta a la BD..
        customer_receipts_move_line_ids = self.env['account.move.line'].search(
            [('payment_id.journal_id.type', 'in', ['bank', 'cash']),
             ('move_id.date', '>=', start_date),
             ('move_id.date', '<=', end_date),
             ('move_id.document_type_id.internal_type', 'in',internal_types)])
        if customer_receipts_move_line_ids:
            return customer_receipts_move_line_ids
        return []


    def get_summary_section_move_line(self, type, summary_section, lines, sort_by, number, move=None, last_move=None):
        summary_section_filter = []
        if sort_by == 'monthly' and move != None:
            move_date = datetime.strptime(move.date, '%Y-%m-%d')
            if lines and lines[-1].get('month', False) and move_date.month != lines[-1]['month']:
                summary_section_filter = filter(
                    lambda x: x['month'] == lines[-1]['month'], summary_section)
            if not lines and filter(lambda x: x['month'] < move_date.month, summary_section):
                summary_section_filter = filter(
                    lambda x: x['month'] < move_date.month, summary_section)
            if last_move != None and move != None and move == last_move:
                summary_section_filter = filter(
                    lambda x: x['month'] >= lines[-1]['month']
                              and x['month'] not in
                              [l['month'] for l in filter(lambda l: l.get('line_type', False) and l['month'] == x['month'], lines)],
                    summary_section)

        if sort_by != 'monthly':
            summary_section_filter = summary_section

        for summary in summary_section_filter:
            if summary['type'] == 'customer_invoices':
                ref = _('Sales / ') + month_list[summary['month']-1][1]
            elif summary['type'] == 'vendor_invoices':
                ref = _('Purchases / ') + month_list[summary['month']-1][1]
            elif summary['type'] == 'supplier_payments':
                ref = _('Payments / ') + month_list[summary['month']-1][1]
            else:
                ref = _('Receipts / ') + month_list[summary['month']-1][1]
            if type == 'html':
                lines.append({
                    'id': 1,
                    'type': 'line',
                    'name': " " + str(number),
                    'footnotes': {},
                    'columns': [str(number), summary['date'], _('Summary Journal Transaction'), '', ref],
                    'level': 2,
                    'unfoldable': False,
                    'month': summary['month'],
                    'line_type': 'summary',
                })
            move_line = summary['move_lines'].mapped('line_ids')
            accounts = move_line.mapped('account_id')
            for account in accounts:
                filter_move_line = move_line.filtered(lambda l: l.account_id.id == account.id)
                if type == 'html':
                    columns = [account.code, '', account.name, str(self._formatted(sum(filter_move_line.mapped('debit')), 2)),
                                str(self._formatted(sum(filter_move_line.mapped('credit')), 2))]
                else:
                    columns = [str(number), summary['date'], _('Summary Journal Transaction'), ref,
                               account.code, account.name, str(self._formatted(sum(filter_move_line.mapped('debit')), 2)),
                               str(self._formatted(sum(filter_move_line.mapped('credit')), 2))]
                lines.append({
                    'id': account.id,
                    'type': 'line',
                    'unfoldable': False,
                    'name': account.code,
                    'footnotes': self.env.context['context_id']._get_footnotes('line', account.id),
                    'columns': columns,
                    'level': 1,
                    'month': summary['month'],
                    'line_type': 'summary',
                })
            number += 1
        return lines, number

    @api.model
    def get_title(self):
        return _("Journal Summary")

    @api.model
    def get_name(self):
        return 'journal_summary'

    @api.model
    def get_report_type(self):
        return self.env.ref('journal_summary_report.journal_summary_report_type')

    def get_template(self):
        return 'journal_summary_report.report_financial_journal_summary'


class JournalSummaryContextReport(models.TransientModel):
    _name = "journal.summary.context.report"
    _description = "A particular context for the journal summary"
    _inherit = "account.report.context.common"

    fold_field = 'unfolded_accounts'
    unfolded_accounts = fields.Many2many('account.account', 'journal_summary_to_accounts', string='Unfolded lines')
    wizard_id = fields.Integer(string='Journal Summary Wizard')
    legal_no = fields.Integer('Legal Ser.No.')
    customer_invoices = fields.Boolean('Customer Invoices')
    vendor_invoices = fields.Boolean('Customer Invoices')
    supplier_payments = fields.Boolean('Supplier Payments')
    customer_receipts = fields.Boolean('Customer Receipts')
    sort_by = fields.Selection([('monthly', 'Monthly summary'), ('number', 'Number'), ('date', 'Journal Entry Date')],
                               'Sort by', default='monthly')
    show_reg_number = fields.Boolean(string="Show Reg. Number",default=True)

    @api.multi
    def get_html_and_data(self, given_context=None):
        for record in self:
            if given_context.get('active_id', False):
                wizard = self.env['journal.summary.report.wizard'].browse(given_context.get('active_id'))
                if wizard and record.wizard_id != wizard.id:
                    record.write({
                        'date_from': wizard.start_date,
                        'date_to': wizard.end_date,
                        'date_filter': 'custom',
                        'legal_no': wizard.legal_no,
                        'customer_invoices': wizard.customer_invoices,
                        'vendor_invoices': wizard.vendor_invoices,
                        'supplier_payments': wizard.supplier_payments,
                        'customer_receipts': wizard.customer_receipts,
                        'sort_by': wizard.sort_by,
                        'wizard_id': wizard.id,
                        'show_reg_number': wizard.show_reg_number})
        res = super(JournalSummaryContextReport, self).get_html_and_data(given_context=given_context)
        return res

    def get_report_obj(self):
        return self.env['journal.summary.report']

    def get_column_row_1(self):
        if self.show_reg_number:
            return [_("Journal Entry No"), _("Date"), _("Reg. Number"), _(" "), _(" ")]
        else:
            return [_("Journal Entry No"), _("Date"), _(" "), _(" "), _(" ")]

    def get_column_row_2(self):
        return [_("Account No."), _(" "), _("Description"), _("Debit"), _("Credit")]

    def get_xlsx_columns_names(self):
        return [_("Journal Entry No"), _("Date"), _("Comment"), _(" "), _("Account No."), _("Description"), _("Debit"), _("Credit")]

    @api.multi
    def get_columns_types(self):
        return ["text", "date", "text", "text", "text"]

    def get_xlsx(self, response):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        report_id = self.get_report_obj()
        sheet = workbook.add_worksheet(report_id.get_title())

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        sheet.set_column(0, 0, 15) #  Set the first column width to 15

        sheet.write(0, 4, _(report_id.get_title()), title_style)

        y_offset = 2
        if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
            sheet.write(y_offset, 0, '', title_style)
            sheet.write(y_offset, 1, '', title_style)
            x = 2
            for column in self.with_context(is_xls=True).get_special_date_line_names():
                sheet.write(y_offset, x, column, title_style)
                sheet.write(y_offset, x+1, '', title_style)
                x += 2
            sheet.write(y_offset, x, '', title_style)
            y_offset += 1

        x = 1
        for column in self.with_context(is_xls=True).get_xlsx_columns_names():
            sheet.write(y_offset, x, column.replace('<br/>', ' ').replace('&nbsp;',' '), title_style)
            x += 1
        y_offset += 1

        lines = report_id.with_context(no_format=True, print_mode=True, xlsx_format=True).get_lines(self)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_right = def_style
                style = def_style
            elif lines[y].get('level') == 2:
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line':
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_right = def_style
            for x in xrange(1, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, lines[y]['columns'][x - 1], style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, max_width+1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def get_pdf(self):

        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        report_obj = self.get_report_obj()
        lines = report_obj.with_context(print_mode=True).get_lines(self)
        footnotes = self.get_footnotes_from_lines(lines)
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        wizard = self.env['journal.summary.report.wizard'].browse(self._context['uid'])
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
            'date_from': datetime.strptime(wizard.start_date, "%Y-%m-%d").strftime("%d-%m-%Y"),
            'date_to': datetime.strptime(wizard.end_date, "%Y-%m-%d").strftime("%d-%m-%Y"),
        }

        body = self.env['ir.ui.view'].render_template(
            "journal_summary_report.report_financial_letter_journal_summary",
            values=dict(rcontext, lines=lines, footnotes=footnotes, report=report_obj, context=self),
        )

        header = self.env['report'].render(
            "journal_summary_report.internal_layout",
            values=rcontext,
        )
        header = self.env['report'].render(
            "report.minimal_layout",
            values=dict(rcontext, subst=True, body=header),
        )
        landscape = False

        #OJG hardcoded
        pf_id = self.env['report.paperformat'].search([('name','=','Journal Summary')])
        return self.env['report']._run_wkhtmltopdf([header], [''], [(0, body)], landscape, pf_id, spec_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10})

    def get_full_date_names(self, dt_to, dt_from=None):
        convert_date = self.env['ir.qweb.field.date'].value_to_html
        date_to = convert_date(dt_to, None)
        dt_to = datetime.strptime(dt_to, "%Y-%m-%d")
        if dt_from:
            date_from = convert_date(dt_from, None)
        if 'month' in self.date_filter:
            return '%s %s' % (self._get_month(dt_to.month - 1), dt_to.year)
        if 'quarter' in self.date_filter:
            month_start = self.env.user.company_id.fiscalyear_last_month + 1
            month = dt_to.month if dt_to.month >= month_start else dt_to.month + 12
            quarter = int((month - month_start) / 3) + 1
            return dt_to.strftime(_('Quarter #') + str(quarter) + ' %Y')
        if 'year' in self.date_filter:
            if self.env.user.company_id.fiscalyear_last_day == 31 and self.env.user.company_id.fiscalyear_last_month == 12:
                return dt_to.strftime('%Y')
            else:
                return str(dt_to.year - 1) + ' - ' + str(dt_to.year)
        if not dt_from:
            return _('As of %s') % (date_to,)
        return _(_("From ") + '%s <br/>'+ _("to ")+'%s') % (date_from, date_to)
