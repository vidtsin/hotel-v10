# -*- coding: utf-8 -*-

from odoo import http, models, fields, api, _
from datetime import datetime
import calendar

class subtype_journal(models.Model):
    _name = 'setting.subtype.journal'

    name = fields.Char(size=64,string="Sub Journal", translate=True)

class AccountPaymentJournal(models.Model):
    _inherit = 'account.payment'

    sub_journal = fields.Many2one('setting.subtype.journal', translate=True,string="Sub Type")


class AccountAccount(models.Model):
    _inherit = 'account.journal'

    sub_journal = fields.Many2one('setting.subtype.journal', translate=True,string="Sub Type")





