# -*- coding: utf-8 -*-

import time
from odoo import api, models
import cStringIO
import base64
from collections import deque
import json

from odoo import http
from odoo.http import request
from odoo.tools import ustr
from odoo.tools.misc import xlwt


class InternalTaxesReport(models.AbstractModel):
    _name = 'report.arg_internal_tax_report.internal_taxes'

    def get_sale_order(self, line):
        if line.invoice_id.type == 'out_refund':
            invoice = self.env['account.invoice'].search(
                [('type', '=', 'out_invoice'), ('number', '=', line.invoice_id.origin),
                 ('journal_id', '=', line.invoice_id.journal_id.id)])
            if invoice and len(invoice.invoice_line_ids):
                line = invoice.invoice_line_ids[0]
        sale_order_line = self.env['sale.order.line'].search([('invoice_lines', '=', line.id)])
        if sale_order_line:
            return sale_order_line.order_id

        return False

    def get_purchase_order(self, picking):
        if picking:
            stock_move = self.env['stock.move'].search([('picking_id', '=', picking.id)])
            purchase_order_line = self.env['purchase.order.line'].search([('move_ids', 'in', stock_move.ids)])
            if len(purchase_order_line):
                return purchase_order_line[0].order_id
        return False

    def get_lot(self, picking, product):
        return picking.pack_operation_product_ids.filtered(lambda x: x.product_id.id == product).mapped(
            'pack_lot_ids')

    def get_picking_receipt(self, lot):
        if lot:
            quant = self.env['stock.quant'].search([('lot_id', '=', lot.id)])
            if len(quant):
                receipt = quant[0].history_ids.filtered(
                    lambda move: move.picking_type_id.code == 'incoming' and move.state == 'done')
                if len(receipt):
                    return receipt[0].picking_id
        return False

    def get_picking_delivery(self, line):
        sale_order = self.get_sale_order(line)
        if sale_order:
            pack_operation_products = sale_order.picking_ids.mapped('pack_operation_product_ids').filtered(
                lambda p: p.product_id.id == line.product_id.id and p.picking_id.state == 'done')
            if len(pack_operation_products):
                return pack_operation_products.mapped('picking_id')
        return False

    def get_stock_in_date(self, picking):
        if picking:
            return picking.date_done
        return ''

    def get_stock_out_date(self, picking):
        if picking:
            return picking.date_done
        return ''

    def get_purchase_internal_taxes(self, tax_id, picking_receipt, lot, qty=False):
        purchase_order = self.get_purchase_order(picking_receipt)
        if purchase_order and lot:
            invoice_line = purchase_order.invoice_ids.mapped('invoice_line_ids').filtered(
                lambda obj: obj.product_id.id == lot.product_id.id and obj.invoice_id.state in ['open', 'paid'])
            if len(invoice_line):
                result = invoice_line.filtered(lambda line: tax_id in line.invoice_line_tax_ids.ids)
                if len(result):
                    return self.compute_taxes_total_include(invoice_line[0], tax_id,
                                                            qty=lot.product_qty if not qty else qty)
        return 0

    def get_dispatch_number(self, picking):
        if picking:
            return picking.custom_dispatch_number
        return ''

    def compute_taxes_total_include(self, line, tax_id, qty=False):
        currency = line.invoice_id and line.invoice_id.currency_id or None
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = False
        invoice_line_tax_id = line.invoice_line_tax_ids.filtered(lambda tax: tax.id == tax_id)
        quantity = line.quantity if not qty else qty
        if invoice_line_tax_id:
            taxes = invoice_line_tax_id.compute_all(price, currency, quantity, product=line.product_id,
                                                    partner=line.invoice_id.partner_id)
        sign = line.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        if taxes:
            return taxes['taxes'][0]['amount'] * sign
        return line.price_subtotal_signed

    def get_lots(self, line):
        result = {}
        picking_deliveries = self.get_picking_delivery(line)
        if picking_deliveries:
            for picking in picking_deliveries:
                pack_lots = self.get_lot(picking, line.product_id.id)
                for pack in pack_lots:
                    if pack.lot_id.id not in result:
                        result[pack.lot_id.id] = {'out_date': picking.date_done, 'lot': pack.lot_id, 'qty': 0}
                    result[pack.lot_id.id]['qty'] += pack.qty

        return result.values()

    def get_sell_invoice(self, data):
        invoices = self.env['account.invoice'].search([('date_invoice', '>=', data['date_from']),
                                                       ('date_invoice', '<=', data['date_to']),
                                                       ('type', 'in', ['out_invoice', 'out_refund']),
                                                       ('state', 'in', ['open', 'paid'])], order='date_invoice asc')
        result = []
        for invoice in invoices:
            invoices_lines = invoice.invoice_line_ids.filtered(
                lambda x: data['account_tax_id'][0] in x.invoice_line_tax_ids.ids)
            for line in invoices_lines:
                lots = self.get_lots(line)
                for obj in lots:
                    lot = obj['lot']
                    picking_receipt = self.get_picking_receipt(lot)
                    result.append(
                        {'product_code': line.product_id.default_code,
                         'description': line.product_id.name,
                         'serial_lot': lot.name,
                         'in_date': self.get_stock_in_date(picking_receipt),
                         'dispatch_number': self.get_dispatch_number(picking_receipt),
                         'out_date': obj['out_date'],
                         'purchase_internal_tax': self.get_purchase_internal_taxes(data['purchase_tax_id'][0],
                                                                                   picking_receipt, lot,
                                                                                   qty=obj['qty']),
                         'customer_invoice_no': invoice.display_name,
                         'sale_internal_tax': self.compute_taxes_total_include(line,
                                                                               data['account_tax_id'][0],
                                                                               qty=obj['qty']),
                         })
        return result

    def get_summary(self, invoices):
        total_purchase = sum([obj['purchase_internal_tax'] for obj in invoices])
        total_sale = sum([obj['sale_internal_tax'] for obj in invoices])
        return total_purchase, total_sale, total_sale - total_purchase

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        invoices = self.get_sell_invoice(data['form'])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_sell_invoice': invoices,
            'get_summary': self.get_summary(invoices),
        }
        return self.env['report'].render('arg_internal_tax_report.report_internal_taxes', docargs)
