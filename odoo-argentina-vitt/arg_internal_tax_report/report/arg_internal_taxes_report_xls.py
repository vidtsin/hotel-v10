# -*- coding: utf-8 -*-
# Copyright 2009-2016 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import xlwt
import time
from odoo.addons.report_xls.report_xls import report_xls
# from .ek_common_reports import CommonReportHeaderXLS
from odoo.report.report_sxw import *
from odoo.tools.translate import _
from odoo.tools.translate import translate, _
from odoo import _, api, fields, models, registry, SUPERUSER_ID

# import logging
# _logger = logging.getLogger(__name__)

_column_sizes = [
    ('date', 12),
    ('period', 12),
    ('move', 20),
    ('journal', 12),
    ('account_code', 12),
    ('partner', 30),
    ('ref', 30),
    ('label', 45),
    ('counterpart', 30),
    ('debit', 15),
    ('credit', 15),
    ('cumul_bal', 15),
    ('curr_bal', 15),
    ('curr_code', 7),
]


class arg_internal_taxex_report_xls_parser(rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(arg_internal_taxex_report_xls_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_lines': self.get_sell_invoice,
            'get_summary': self.get_summary,
            'time': time,
        })
        self.context = context

    def _(self, src):
        lang = self.context.get('lang', 'en_ES')
        return translate(self.cr, _ir_translation_name, 'report', lang, src) \
               or src

    def set_context(self, objects, data, ids, report_type=None):
        return super(arg_internal_taxex_report_xls_parser, self).set_context(objects, data, ids,
                                                                             report_type=report_type)

    def get_sell_invoice(self, data):
        db_registry = registry(self.cr.dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            report_obj = env['report.arg_internal_tax_report.internal_taxes']
            lines = report_obj.get_sell_invoice(data)
            return lines

    def get_summary(self, invoices):
        db_registry = registry(self.cr.dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            report_obj = env['report.arg_internal_tax_report.internal_taxes']
            return report_obj.get_summary(invoices)


class arg_internal_taxes_report_xls(report_xls):
    column_sizes = [x[1] for x in _column_sizes]

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(arg_internal_taxes_report_xls, self).__init__(
            name, table, rml, parser, header, store)

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        report_name = _("Internal Taxes Report")
        ws = wb.add_sheet(report_name[:31])
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 0  # Landscape
        ws.fit_width_to_pages = 1
        row_pos = 0

        # set print header/footer
        ws.header_str = self.xls_headers['standard']
        ws.footer_str = self.xls_footers['standard']

        # Title
        cell_style = xlwt.easyxf(_xs['xls_title'])
        c_specs = [
            ('report_name', 3, 2, 'text', report_name),
        ]
        row_data = self.xls_row_template(c_specs, ['report_name'])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style)
        row_pos += 1

        c_sizes = self.column_sizes
        c_specs = [('empty%s' % i, 1, c_sizes[i], 'text', None)
                   for i in range(0, len(c_sizes))]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data)
        # ------HEADER------#
        cell_format = _xs['bold'] + _xs['fill_blue'] + _xs['borders_all']
        cell_style = xlwt.easyxf(cell_format)
        cell_style_center = xlwt.easyxf(cell_format + _xs['center'])
        c_specs = [
            ('purchase_t', 2, 0, 'text', _('Purchase Tax:')),
            ('sale_t', 2, 0, 'text', _('Sale Tax:')),
            ('from', 2, 0, 'text', _('Date from:')),
            ('to', 2, 0, 'text', _('Date to:')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style_center)

        c_specs = [
            ('purchase_t', 2, 0, 'text', data['purchase_tax_id'][1]),
            ('sale_t', 2, 0, 'text', data['account_tax_id'][1]),
            ('from', 2, 0, 'text', data['date_from']),
            ('to', 2, 0, 'text', data['date_to']),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style_center)
        ws.set_horz_split_pos(row_pos)
        row_pos += 1

        # ------BODY------#
        cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        text_style = xlwt.easyxf(cell_format)
        totals_style = xlwt.easyxf(cell_format + _xs['right'])
        totals_style2 = xlwt.easyxf(_xs['right'])

        c_specs = [
            ('code', 2, 0, 'text', _('Product Code')),
            ('description', 2, 0, 'text', _('Product Description')),
            ('serial_lot', 2, 0, 'text', _('Serial/Lot No.')),
            ('in_date', 1, 0, 'text', _('Stock In Date')),
            ('number', 2, 0, 'text', _('Custom Dispatch No.')),
            ('purchase_tax', 2, 0, 'text', 'Purchase Internal Tax', None, totals_style),
            ('out_date', 2, 0, 'text', _('Stock Out Date')),
            ('customer_invoice', 2, 0, 'text', _('Customer Invoice No.')),
            ('sale_tax', 2, 0, 'text', 'Sales Internal Tax', None, totals_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=text_style)

        cell_format_body = _xs['borders_all']
        text_style_body = xlwt.easyxf(cell_format_body)

        lines = _p['get_lines'](data)
        for line in lines:
            c_specs = [
                ('code', 2, 0, 'text', line['product_code']),
                ('description', 2, 0, 'text', line['description']),
                ('serial_lot', 2, 0, 'text', line['serial_lot']),
                ('in_date', 1, 0, 'text', line['in_date']),
                ('number', 2, 0, 'text', line['dispatch_number']),
                ('purchase_tax', 2, 0, 'number', line['purchase_internal_tax'], None, text_style_body),
                ('out_date', 2, 0, 'text', line['out_date']),
                ('customer_invoice', 2, 0, 'text', line['customer_invoice_no']),
                ('sale_tax', 2, 0, 'number', line['sale_internal_tax'], None, text_style_body),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=text_style_body)

        # ------SUMMARY------#
        cell_format_total= _xs['bold'] + _xs['borders_all']
        text_style_totals = xlwt.easyxf(cell_format_total)
        summary = _p['get_summary'](lines)
        c_specs = [
            ('code', 2, 0, 'text', ''),
            ('description', 2, 0, 'text', ''),
            ('serial_lot', 2, 0, 'text', ''),
            ('in_date', 1, 0, 'text', ''),
            ('number', 2, 0, 'text', ''),
            ('purchase_tax', 2, 0, 'number', summary[0], None, text_style_totals),
            ('out_date', 2, 0, 'text', ''),
            ('customer_invoice', 2, 0, 'text', ''),
            ('sale_tax', 2, 0, 'number', summary[1], None, text_style_totals),
        ]

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=text_style_totals)
        row_pos += 1
        c_specs = [
            ('diff', 1, 0, 'text', 'Difference'),
            ('diff_total', 1, 0, 'number', summary[2]),
        ]
        cell_format_summary = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        text_style_summary = xlwt.easyxf(cell_format_summary)

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=text_style_summary)


arg_internal_taxes_report_xls('report.arg_internal_tax_report.report_internal_taxes.xls',
                              'account.invoice', parser=arg_internal_taxex_report_xls_parser)
