# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  BACG S.A. de C.V.  (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

from odoo import models, fields, api

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):

        invoice_data = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)

        invoice_data['origin'] = str(invoice.display_name)+" / "+str(invoice_data['origin'])

        return invoice_data
