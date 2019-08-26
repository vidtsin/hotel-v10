# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
# from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    report_price_unit = fields.Monetary(
        string='Unit Price',
        compute='_compute_report_prices_and_taxes'
    )
    report_price_subtotal = fields.Monetary(
        string='Amount',
        compute='_compute_report_prices_and_taxes'
    )
    report_price_net = fields.Monetary(
        string='Net Amount',
        compute='_compute_report_prices_and_taxes'
    )
    report_invoice_line_tax_ids = fields.One2many(
        compute="_compute_report_prices_and_taxes",
        comodel_name='account.tax',
        string='Taxes'
    )

    @api.multi
    @api.depends('price_unit', 'price_subtotal', 'invoice_id.document_type_id')
    def _compute_report_prices_and_taxes(self):
        report_price_net = 0.0
        for line in self:
            report_price_subtotal = report_price_unit = 0.0
            invoice = line.invoice_id
            if not invoice.journal_document_type_id.document_type_id.document_letter_id.taxes_included:
                report_price_unit = line.price_unit
                report_price_subtotal = line.price_subtotal
                report_price_net = report_price_unit - (report_price_unit * (line.discount or 0.0) / 100.0)
            else:
                for tax in line.invoice_line_tax_ids:
                    if tax.tax_group_id.tax == 'vat':
                        report_price_unit = line.price_unit + (line.price_unit * tax.amount / 100)
                        report_price_net = report_price_unit - (report_price_unit * (line.discount or 0.0) / 100.0)
                        report_price_subtotal = report_price_net * line.quantity

            line.report_price_subtotal = report_price_subtotal
            line.report_price_unit = report_price_unit
            line.report_price_net = report_price_net
            line.report_invoice_line_tax_ids = None
