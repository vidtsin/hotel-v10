# -*- coding: utf-8 -*-

from odoo import http, models, fields, api, _
from datetime import datetime
import calendar

class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'

    def payment_ids_grouped(self,apg):
        pm = {}
        for pay in apg.payment_ids:
            if pay.journal_id.name in pm.keys():
                pm[pay.journal_id.name] += pay.amount
            else:
                pm.update({pay.journal_id.name:pay.amount})
        return pm

    def payment_ids_t(self,apg):
        pm = {}
        for pay in apg.payment_ids:
            if pay.check_ids:
                if pay.check_ids.number in pm.keys():
                    pm[pay.check_ids.number] += pay.amount
                else:
                    pm.update({pay.check_ids.number:pay.amount})
        return pm

    def getbank_qweb(self,chk,apg):
        for chk_ in apg.payment_ids:
            if chk == chk_.check_ids.number:
                return chk_.check_ids.bank_id.name

    def getCUIT_qweb(self,chk,apg):
        for chk_ in apg.payment_ids:
            if chk == chk_.check_ids.number:
                return chk_.check_ids.partner_id_vat

    def getpaymdate_qweb(self,chk,apg):
        for chk_ in apg.payment_ids:
            if chk == chk_.check_ids.number:
                return chk_.check_ids.payment_date

    def payment_ids_tot1(self,apg):
        tot = 0
        for chk_ in apg.payment_ids:
            tot += chk_.amount
        return tot

    def payment_ids_tot2(self,apg):
        tot = 0
        for chk_ in apg.payment_ids:
            if chk_.check_ids.number:
                tot += chk_.amount
        return tot

    def payment_ids_totlet(self, apg):
        ret = ''
        tot = apg.payment_ids_tot1(apg)
        if apg.company_id.val2words_default:
            val2words_default = apg.company_id.val2words_default
            ret = val2words_default._num_to_text(num=tot, currency=apg.currency_id.name) or ''
        return ret

    def compute_payment_group_matched_amount_qweb(self,apg,pl):
        payment_group_id = apg.id
        payments = self.env['account.payment.group'].browse(payment_group_id).payment_ids
        payment_move_lines = payments.mapped('move_line_ids')
        payment_partial_lines = self.env[
            'account.partial.reconcile'].search([
                '|',
                ('credit_move_id', 'in', payment_move_lines.ids),
                ('debit_move_id', 'in', payment_move_lines.ids),
            ])
        rec = pl
        matched_amount = 0.0
        for pl in (rec.matched_debit_ids + rec.matched_credit_ids):
            if pl in payment_partial_lines:
                matched_amount += pl.amount
        return matched_amount

    def payment_ids_tot3(self,apg):
        tot = 0
        for pl in apg.matched_move_line_ids:
                tot += self.compute_payment_group_matched_amount_qweb(apg,pl)
        return tot

    def payment_ids_tot4(self,apg):
        tot = 0
        for pl in apg.debt_move_line_ids:
                tot += pl.amount_residual
        return tot
