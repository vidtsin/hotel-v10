# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import xlsxwriter
import StringIO
from odoo.tools import config


class JournalEntryListReport(models.AbstractModel):
    _name = "journal.entry_list.report"
    _description = "Journal Entry List Report"

    def _format(self, value, currency=False):
        if self.env.context.get('no_format'):
            return value
        currency_id = currency or self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            # don't print -0.0 in reports
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res

    def _formatted(self, value, digit):
        formatted = ('%.' + str(digit) + 'f') % value
        return formatted

    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['journal.entry_list.context.report"'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'sort_by': context_id.sort_by,
            'context_id': context_id,
        })
        if new_context.get('print_mode'):
            res = self.with_context(new_context)._lines(line_id)
        else:
            res = self.with_context(new_context)._html_lines(line_id)
        return res

    @api.model
    def _lines(self, line_id=None):
        context = self.env.context
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        lines = []
        am_obj = self.env['account.move']
        sorted_am = am_obj.search(
            [('date', '>=', context['date_from']), ('date', '<=', context['date_to'])], order=context['sort_by'])
        total_debit = 0
        total_credit = 0
        for move in sorted_am:
            debit = 0.0
            credit = 0.0
            used_currency = self.env.user.company_id.currency_id
            first_line = False
            action = False
            if move.type_document != 'no_reference':
                action = [move.action_open_origin_document()['res_model'],
                          move.action_open_origin_document()['res_id']]
            for line in move.line_ids:
                line_debit = line.debit
                line_credit = line.credit
                debit += line_debit
                credit += line_credit
                line_debit = line.company_id.currency_id.compute(line_debit, used_currency)
                line_credit = line.company_id.currency_id.compute(line_credit, used_currency)

                currency = "" if not line.currency_id else self.with_context(no_format=False)._format(
                    line.amount_currency, currency=line.currency_id)
                name = line.name and line.name or ''
                account = line.account_id and line.account_id.name or ''
                ref = not first_line and move.ref or ''
                origin_doc = move.origin_document or move.display_name
                number = not first_line and move.name or ''
                reg_date = not first_line and datetime.strptime(move.create_date,
                                                                DEFAULT_SERVER_DATETIME_FORMAT).strftime(
                    date_format) or None
                trans_date = not first_line and datetime.strptime(move.date, DEFAULT_SERVER_DATE_FORMAT).strftime(
                    date_format) or None
                if not action:
                    action = line.get_model_id_and_name()
                rate = ''
                if line.currency_id and 'manual_currency_rate' in self.env[action[0]].browse(action[1]):
                    rate = ' %s:1' % int(self.env[action[0]].browse(action[1]).manual_currency_rate)
                lines.append({
                    'id': line.id,
                    'type': 'line_id',
                    'move_id': move.id,
                    'action': action,
                    'colspan': 0,
                    'name': not first_line and _('Journal Entry') or '',
                    'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', line.id),
                    'columns': [number, not first_line and origin_doc or '', reg_date, trans_date, ref,
                                not first_line and move.create_uid.name or '', account, name, currency + rate,
                                line_debit != 0 and self._format(line_debit) or '',
                                line_credit != 0 and self._format(line_credit) or ''],
                    'level': 1,
                })
                first_line = True

            lines.append({
                'id': move.id,
                'type': 'total',
                'name': _('Total '),
                'colspan': 0,
                'style': "border-style: none;",
                'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                           move.id),
                'columns': ['', '', None, None, '', '', '', '', ('', "", "border-top:1px solid;"),
                            (self._format(debit), "", "border-top:1px solid;"),
                            (self._format(credit), "", "border-top:1px solid;")], 'level': 1,
            })
            total_debit += debit
            total_credit += credit
        lines.append({
            'id': 0,
            'type': 'total',
            'name': _('Total '),
            'colspan': 0,
            'footnotes': {},
            'columns': ['', '', None, None, '', '', _('Total: Entries List'), '', '', self._formatted(total_debit, 2),
                                                                                self._formatted(total_credit, 2)],
            'level': 0,
        })
        lines.append({
            'id': 0,
            'type': 'total',
            'name': _('Total '),
            'colspan': 0,
            'footnotes': {},
            'columns': ['', '', None, None, '', '', _('Number of Transactions'), '', '', len(sorted_am), ''],
            'level': 0,
        })

        return lines

    @api.model
    def _html_lines(self, line_id=None):
        context = self.env.context
        # if not context['analytic_account_dimension_id']:
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        lines = []
        am_obj = self.env['account.move']
        sorted_am = am_obj.search(
            [('date', '>=', context['date_from']), ('date', '<=', context['date_to'])], order=context['sort_by'])
        total_debit = 0
        total_credit = 0
        for move in sorted_am:
            debit = 0.0
            credit = 0.0
            used_currency = self.env.user.company_id.currency_id
            first_line = False
            action = False
            if move.type_document != 'no_reference':
                action_origin_document = move.action_open_origin_document()
                action = [action_origin_document['res_model'], action_origin_document['res_id'],
                          _(action_origin_document['name']), action_origin_document['views'][0][0]]
            for line in move.line_ids:
                line_debit = line.debit
                line_credit = line.credit
                debit += line_debit
                credit += line_credit
                line_debit = line.company_id.currency_id.compute(line_debit, used_currency)
                line_credit = line.company_id.currency_id.compute(line_credit, used_currency)

                currency = "" if not line.currency_id else self.with_context(no_format=False)._format(
                    line.amount_currency, currency=line.currency_id)
                name = line.name and line.name or ''
                if name and len(name) > 20:
                    name = name[:17] + "..."
                account = line.account_id and line.account_id.name or ''
                if account and len(account) > 20:
                    account = account[:17] + "..."
                ref = not first_line and move.ref or ''
                if ref and len(ref) > 20:
                    ref = ref[:17] + "..."
                origin_doc = move.origin_document or move.display_name
                number = not first_line and move.name or ''
                trans_date = not first_line and datetime.strptime(move.date, DEFAULT_SERVER_DATE_FORMAT).strftime(
                    date_format) or None
                if not action:
                    action = line.get_model_id_and_name()
                rate = ''
                if line.currency_id and 'manual_currency_rate' in self.env[action[0]].browse(action[1]):
                    rate = ' %s:1' % int(self.env[action[0]].browse(action[1]).manual_currency_rate)
                lines.append({
                    'id': line.id,
                    'type': 'line_id',
                    'move_id': move.id,
                    'action': action,
                    'colspan': 0,
                    'name': not first_line and _('Journal Entry') or '',
                    'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', line.id),
                    'columns': [number, not first_line and origin_doc or '', trans_date, ref,
                                account, name, currency + rate,
                                line_debit != 0 and self._format(line_debit) or '',
                                line_credit != 0 and self._format(line_credit) or ''],
                    'level': 1,
                })
                first_line = True

            lines.append({
                'id': move.id,
                'type': 'total',
                'name': _('Total '),
                'colspan': 0,
                'style': "border-style: none;",
                'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                           move.id),
                'columns': ['', '', None, '', '', '', ('', "", "border-top:1px solid;"),
                            (self._format(debit), "", "border-top:1px solid;"),
                            (self._format(credit), "", "border-top:1px solid;")], 'level': 1,
            })
            total_debit += debit
            total_credit += credit
        lines.append({
            'id': 0,
            'type': 'total',
            'name': _('Total '),
            'colspan': 0,
            'footnotes': {},
            'columns': ['', '', None, '', _('Total: Entries List'), '', '', self._formatted(total_debit, 2),
                                                                        self._formatted(total_credit, 2)],
            'level': 0,
        })
        lines.append({
            'id': 0,
            'type': 'total',
            'name': _('Total '),
            'colspan': 0,
            'footnotes': {},
            'columns': ['', '', None, '', _('Number of Transactions'), '', '', len(sorted_am), ''],
            'level': 0,
        })

        return lines

    @api.model
    def get_title(self):
        return _("Journal Entries List")

    @api.model
    def get_name(self):
        return 'journal_entry_list'

    @api.model
    def get_report_type(self):
        return self.env.ref('journal_entry_list_report.journal_entry_list_report_type')

    def get_template(self):
        return 'journal_entry_list_report.report_journal_entry_list'


class JournalEntryListContextReport(models.TransientModel):
    _name = "journal.entry_list.context.report"
    _description = "A particular context for the journal entry list"
    _inherit = "account.report.context.common"

    sort_by = fields.Selection([('name', 'Number'), ('date', 'Transaction Date')],
                               'Sort by', default='name')
    wizard_id = fields.Integer(string='Journal Entry Wizard')

    @api.multi
    def get_html_and_data(self, given_context=None):
        for record in self:
            if given_context.get('active_id', False):
                wizard = self.env['journal.entry_list.report.wizard'].browse(given_context.get('active_id'))
                if wizard and record.wizard_id != wizard.id:
                    record.write({'date_from': wizard.start_date,
                                  'date_to': wizard.end_date,
                                  'sort_by': wizard.sort_by,
                                  'date_filter': 'custom',
                                  'wizard_id': wizard.id,
                                  })
        res = super(JournalEntryListContextReport, self).get_html_and_data(given_context=given_context)
        return res

    def get_report_obj(self):
        return self.env['journal.entry_list.report']

    def get_columns_names(self):
        return [_("Number"), _("Origin Document"), _("Reg. Date"), _("Trans. Date"), _("Reference"), _("User"),
                _("Account"), _("Label"), _("Amount Curr."), _("Debit"), _("Credit")]

    def get_html_columns_names(self):
        return [_("Number"), _("Origin Document"), _("Trans. Date"), _("Reference"),
                _("Account"), _("Label"), _("Amount Curr."), _("Debit"), _("Credit")]

    @api.multi
    def get_columns_types(self):
        return ["text", "link", "date", "date", "text", "text", "text", "text", "text", "number", "number"]

    @api.multi
    def get_html_columns_types(self):
        return ["text", "link", "date", "text", "text", "text", "text", "number", "number"]


    def get_xlsx(self, response):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        report_id = self.get_report_obj()
        sheet = workbook.add_worksheet(report_id.get_title())

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1,
             'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1,
             'font_color': '#FFFFFF'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        sheet.set_column(0, 0, 15)  # Set the first column width to 15

        sheet.write(0, 0, '', title_style)

        y_offset = 0
        if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
            sheet.write(y_offset, 0, '', title_style)
            sheet.write(y_offset, 1, '', title_style)
            x = 2
            for column in self.with_context(is_xls=True).get_special_date_line_names():
                sheet.write(y_offset, x, column, title_style)
                sheet.write(y_offset, x + 1, '', title_style)
                x += 2
            sheet.write(y_offset, x, '', title_style)
            y_offset += 1

        x = 0
        for column in self.with_context(is_xls=True).get_columns_names():
            sheet.write(y_offset, x, column.replace('<br/>', ' ').replace('&nbsp;', ' '), title_style)
            x += 1
        y_offset += 1

        lines = report_id.with_context(no_format=True, print_mode=True).get_lines(self)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(0, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1],
                                style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns'])):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, max_width):
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
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
        }

        body = self.env['ir.ui.view'].render_template(
            "journal_entry_list_report.report_journal_entry_list_letter",
            values=dict(rcontext, lines=lines, footnotes=footnotes, report=report_obj, context=self),
        )

        header = self.env['report'].render(
            "report.internal_layout",
            values=rcontext,
        )
        header = self.env['report'].render(
            "report.minimal_layout",
            values=dict(rcontext, subst=True, body=header),
        )

        landscape = False
        if len(self.get_columns_names()) > 4:
            landscape = True

        return self.env['report']._run_wkhtmltopdf([header], [''], [(0, body)], landscape,
                                                   self.env.user.company_id.paperformat_id,
                                                   spec_paperformat_args={'data-report-margin-top': 10,
                                                                          'data-report-header-spacing': 10})

    def get_full_date_names(self, dt_to, dt_from=None):
        res = super(JournalEntryListContextReport, self).get_full_date_names(dt_to, dt_from)
        if dt_from:
            return res.replace('From', 'Period:').replace('to', '-').replace('<br/>', '')
